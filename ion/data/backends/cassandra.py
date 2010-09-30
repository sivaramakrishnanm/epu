#!/usr/bin/env python
"""
@file ion/data/backends/cassandra.py
@author Paul Hubbard
@author Michael Meisinger
@author Paul Hubbard
@author Dorian Raymer
@author Matt Rodriguez
@brief Implementation of ion.data.store.IStore using Telephus to interface a
        Cassandra datastore backend
@Note Test cases for the cassandra backend are now in ion.data.test.test_store
"""

import re
import logging
logging = logging.getLogger(__name__)

from twisted.internet import defer
from twisted.internet import reactor

from telephus.client import CassandraClient
from telephus.protocol import ManagedCassandraClientFactory
from telephus.cassandra.ttypes import NotFoundException

from ion.core import ioninit
from ion.data.store import IStore

import uuid

CONF = ioninit.config(__name__)
CF_default_keyspace = CONF['default_keyspace']
CF_default_colfamily = CONF['default_colfamily']
CF_default_cf_super = CONF['default_cf_super']
CF_default_namespace = CONF['default_namespace']
CF_default_key = CONF['default_key']


class CassandraStore(IStore):
    """
    Store interface for interacting with the Cassandra key/value store
    @see http://github.com/vomjom/pycassa
    @Note Default behavior is to use a random super column name space!
    """
    def __init__(self, **kwargs):
        self.kvs = None
        self.cass_host_list = None
        self.keyspace = None
        self.colfamily = None
        self.cf_super = True
        self.namespace = None
        self.key=None

    @classmethod
    def create_store(cls, **kwargs):
        """
        @brief Factory method to create an instance of the cassandra store.
        @param kwargs keyword arguments to configure the store.
        @param cass_host_list List of hostname:ports for cassandra host or cluster
        @retval Deferred, for IStore instance.
        """
        logging.info('In create_store method')
        inst = cls(**kwargs)
        inst.kwargs = kwargs
        inst.cass_host_list = kwargs.get('cass_host_list', None)
        inst.keyspace = kwargs.get('keyspace', CF_default_keyspace)
        inst.colfamily = kwargs.get('colfamily', CF_default_colfamily)
        inst.cf_super = kwargs.get('cf_super', CF_default_cf_super)
        inst.key = kwargs.get('key', CF_default_key)
        
        if not inst.key:
            inst.key = str(uuid.uuid4())
        
        if inst.cf_super:
            inst.namespace = kwargs.get('namespace', CF_default_namespace)
            if inst.namespace == None:
                # Must change behavior to set a random namespace so that test don't interfere!
                inst.namespace = ':'
        else:
            if inst.namespace:
                logging.info('Ignoring namespace argument in non super column cassandra store')
            inst.namespace=None
        
        port = 9160
        host = 'amoeba.ucsd.edu'
        inst.manager = ManagedCassandraClientFactory()
        inst.client = CassandraClient(inst.manager, inst.keyspace) 
        inst.connector = reactor.connectTCP(host, port, inst.manager, timeout=1)
        logging.info("Created Cassandra store")
        return defer.succeed(inst)               

    @defer.inlineCallbacks
    def clear_store(self):
        """
        @brief Delete the super column namespace.
        @retval Deferred, None
        """
        if self.cf_super:
            yield self.client.remove(self.key, self.colfamily, super_column=self.namespace)
        else:
            logging.info('Can not clear root of persistent store!')
        defer.returnValue(None)
        
    @defer.inlineCallbacks
    def get(self, col):
        """
        @brief Return a value corresponding to a given key
        @param col Cassandra column
        @retval Deferred, for value from the ion dictionary, or None
        """
        value = None
        logging.info("Calling get on col %s " % col)
        try:
            if self.cf_super:
                logging.info("super_col: Calling get on col %s " % col)
                #logging.info("get self.key: %s  self.colfamily: %s column: %s  super_column: %s" % (self.key, self.colfamily, col, self.namespace))
                value = yield self.client.get(self.key, self.colfamily, column=col, super_column=self.namespace)
                logging.info("super_col: Calling get on col %s " % value)
            else:
                logging.info("standard_col: Calling get on col %s " % col)
                value = yield self.client.get(self.key, self.colfamily, column=col)
        except NotFoundException:     
            #logging.info("standard_col: Calling get on col %s " % value)
            #logging.debug('Key "%s":"%s"' % (self.key, col))
            defer.returnValue(None)
            
        value = value.column.value 
        #logging.info("Got back %s" % value)
        defer.returnValue(value)

    @defer.inlineCallbacks
    def put(self, col, value):
        """
        @brief Write a key/value pair into cassandra
        @param key Lookup key
        @param value Corresponding value
        @note Value is composed into OOI dictionary under keyname 'value'
        @retval Deferred for success
        """
        logging.info("Calling put")
        logging.info('writing key %s value %s' % (col, value))
        if self.cf_super:
            yield self.client.insert(self.key, self.colfamily, value, column=col, super_column=self.namespace) 
        else:
            yield self.client.insert(self.key, self.colfamily, value, column=col)
        defer.returnValue(None)

    @defer.inlineCallbacks
    def query(self, regex):
        """
        @brief Search by regular expression
        @param regex Regular expression to match against the keys
        @retval Deferred, for list, possibly empty, of keys that match.
        @note Uses get_range generator of unknown efficiency.
        """
        #logging.info("searching for regex %s" % regex)
        matched_list = []
        if self.cf_super:
            klist = yield self.client.get(self.key, self.colfamily, super_column=self.namespace)
        else:
            klist = yield self.client.get_slice(self.key, self.colfamily)
        
        #This code could probably be refactored. The data structures returned are different if
        #it is called with a column or super_column. Another possibility is that the code 
        #is removed when the IStore interface doesn't use the query interface.
        if self.cf_super:
            columns = klist.super_column.columns
            for col in columns:
            
                m = re.findall(regex, str(col.name))
                
                if m: 
                    matched_list.append(col.name)

        else:
            for col in klist:
                m = re.findall(regex, str(col.column.name))
                if m:
                    matched_list.append(col.column.name)

        #logging.info("matched_list %s" % matched_list)
        defer.returnValue(matched_list)

    @defer.inlineCallbacks
    def remove(self, col):
        """
        @brief delete a key/value pair
        @param key Key to delete
        @retval Deferred, for success of operation
        @note Deletes are lazy, so key may still be visible for some time.
        """
        if self.cf_super:
            yield self.client.remove(self.key, self.colfamily, column=col, super_column=self.namespace)
        else:
            yield self.client.remove(self.key, self.colfamily, column=col)
        defer.returnValue(None)
