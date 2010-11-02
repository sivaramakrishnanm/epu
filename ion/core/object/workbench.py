#!/usr/bin/env python
"""
@Brief Workbench for operating on GPB backed objects

TODO
Remove repository name - what to do instead?

"""

from twisted.internet import defer

from ion.core.object import repository
from ion.core.object import gpb_wrapper

from twisted.internet import defer

import ion.util.ionlog
log = ion.util.ionlog.getLogger(__name__)

from net.ooici.core.container import container_pb2
from net.ooici.core.mutable import mutable_pb2
from net.ooici.core.type import type_pb2
from net.ooici.core.link import link_pb2

class WorkBench(object):
 
 
    MutableClassType = type_pb2.GPBType()
    MutableClassType.protofile = mutable_pb2.MutableNode.DESCRIPTOR.file.name.split('/')[-1]
    MutableClassType.package = mutable_pb2.MutableNode.DESCRIPTOR.file.package
    MutableClassType.cls = mutable_pb2.MutableNode.DESCRIPTOR.name
 
    LinkClassType = type_pb2.GPBType()
    LinkClassType.protofile = link_pb2.CASRef.DESCRIPTOR.file.name.split('/')[-1]
    LinkClassType.package = link_pb2.CASRef.DESCRIPTOR.file.package
    LinkClassType.cls = link_pb2.CASRef.DESCRIPTOR.name
 
    CommitClassType = type_pb2.GPBType()
    CommitClassType.protofile = mutable_pb2.CommitRef.DESCRIPTOR.file.name.split('/')[-1]
    CommitClassType.package = mutable_pb2.CommitRef.DESCRIPTOR.file.package
    CommitClassType.cls = mutable_pb2.CommitRef.DESCRIPTOR.name
 
 
    def __init__(self, myprocess):   
    
        self._process = myprocess
        
        self._repos = {}
        
        self._repository_nicknames = {}
                
        self._hashed_elements={}
        """
        A shared dictionary for hashed objects
        """            
        
        
    def clone(self, ID_Ref, name=None):
        """
        Clone a repository from the data store
        Check out the head or 
        """
        # rpc_send - datastore, clone, ID_REf
        
    def op_clone(self, content, headers, msg):
        """
        The operation which responds to a clone
        """
        
    
    def _load_repo_from_mutable(self,head):
        """
        Load a repository from a mutable - helper for clone and other methods
        that send and receive an entire repo.
        head is a raw (unwrapped) gpb message
        """
        
        new_repo = repository.Repository(head)
            
                
        new_repo._workbench = self
            
        new_repo._hashed_elements = self._hashed_elements
        
        
        # Load all of the commit refs that came with this head.
        
        for branch in new_repo.branches:
            link = branch.get_link('commitref')
            self._load_commits(new_repo,link)
            
            
        # Check and see if we already have one of these repositorys
        existing_repo = self.get_repository(new_repo.repository_key)
        if existing_repo:
            
            # Merge the existing head with the new one.
            repo = self._merge_repo_heads(existing_repo, new_repo)
            
        else:
            repo = new_repo
            
        if not repo.branchnicknames.has_key('master'):
            repo.branchnicknames['master']=repo.branches[0].branchkey
        
        self.put_repository(repo)
        
        return repo 
            
    
    def _load_commits(self, repo, link):
                
        if repo._commit_index.has_key(link.key):
            return repo._commit_index.get(link.key)

        elif repo._hashed_elements.has_key(link.key):
            
            element = repo._hashed_elements.get(link.key)
            
            
            if not link.type.package == element.type.package and \
                    link.type.cls == element.type.cls:
                raise Exception, 'The link type does not match the element type!'
            
            cref = repo._load_element(element)
            
            if cref.GPBType == self.CommitClassType:
                repo._commit_index[cref.myid]=cref
                cref.readonly = True
            else:
                raise Exception, 'This method should only load commits!'
            
            for parent in cref.parentrefs:
                link = parent.get_link('commitref')
                # Call this method recursively for each link
                self._load_commits(link)
        else:
            
            # This commit ref was not actually sent!
            return
    
    def _merge_repo_heads(self, existing_repo, new_repo):
        
        # examine all the branches in new and merge them into existing
        for new_branch in new_repo.branches:
            
            new_branchkey = new_branch.branchkey
            
            for existing_branch in existing_repo.branches:
                
                if new_branchkey == existing_branch.branchkey:
                    # We need to merge the state of these branches
                    
                    self._resolve_branch_state(existing_branch, new_branch)
                        
                    # We found the new branch in existing - exit the outter for loop
                    break
                
            else:
                # the branch in new is not in existing - add its head and move on
                branch = existing_repo.branches.add()
                
                branch.branchkey = new_branchkey
                # Get the cref and then link it in the existing repository
                cref = new_branch.commitref 
                branch.commitref = cref
                
            
        return existing_repo
    
    
    def _resolve_branch_state(self, existing_branch, new_branch):
        """
        I don't think this code is tested yet!
        """
        
        new_link = new_branch.get_link('commitref')
        existing_link = existing_branch.get_link('commitref')
            
        # test to see if we need to merge
        if new_link == existing_link:
            # If these branches have the same state we are good.
            return

        # Get the repositories we are working from
        existing_repo = existing_branch.repository
        new_repo = new_branch.repository
        
        # Look in the commit index of the existing repo to see if the new link is an old commit to existing
        common_cref = existing_repo._commit_index.get(new_link.key, None)
        if common_cref:
            # The branch in new_repo is out of date with what exists here.
            return    
        
        # Look in the commit index of the new repo to see if the existing link is an old commit in new
        common_cref = new_repo._commit_index.get(existing_link.key, None)
        if common_cref:
            # The existing repo can be fast forwarded to the new state!
            existing_branch.commitref = common_ref
            link = existing_branch.get_link('commitref')
            self._load_commits(existing_repo, link) # Load the new ancestors!
            return
            
        # This is a non fastforward merge!
        # The branch has diverged and must be reconciled!
            
        # It is also possible that the new_repo just did not include all of its
        # commit history as an optimization! This is a problem!
        
        mor = existing_branch.mergeonread.add()
        
        new_cref = new_repo._commit_index.get(new_link.key)
        
        mor.set_link(new_ref)
            
        # Note this in the branches merge on read field and punt this to some
        # other part of the process.
        return
            
        
        
    def init_repository(self, rootclass=None, name=None):
        """
        Initialize a new repository
        Factory method for creating a repository - this is the responsibility
        of the workbench.
        """
        
        repo = repository.Repository()
        repo._workbench = self
            
        repo._hashed_elements = self._hashed_elements
            
        # Set the default branch
        repo.branch(nickname='master')
           
        if rootclass:
            rootobj = repo.create_wrapped_object(rootclass)
        
            repo._workspace_root = rootobj
        
        else:
            rootobj = None
        
        self.put_repository(repo)
        
        if name:
            self._repository_nicknames[name] = repo._dotgit.repositorykey
        
        return repo, rootobj

        
    def fork(self, structure, name):
        """
        Fork the structure in the wrapped gpb object into a new repository.
        """
        
    @defer.inlineCallbacks
    def push(self, target, name):
        """
        Push the current state of the repository
        """
        
        
        targetname = self._process.get_scoped_name('system', target)
        repo = self.get_repository(name)
        (content, headers, msg) = yield self._process.rpc_send(targetname,'push', repo)
        
        status = headers.get('status',None)
        if status == 'OK':
            log.info( 'Push returned Okay!')
        elif status == 'ERROR':
            raise Exception, 'Push returned an exception!' % headers.get('errmsg',None)
        
        
    @defer.inlineCallbacks
    def op_push(self, repo, headers, msg):
        """
        The Operation which responds to a push
        """
        log.info('op_push: content type, %s' % type(repo))
                
        cref_links = set()
        for branch in repo.branches:
            cref_links.add(branch.get_link('commitref'))
            
        objs_to_get = set()
        refs_touched = set()
        while len(cref_links) > 0:
            
            new_links = set()
            
            for ref_link in cref_links:
                refs_touched.add(ref_link)
                
                cref= repo.get_linked_object(ref_link)
                    
                obj_link = cref.get_link('objectroot')
                obj = self._hashed_elements.get(obj_link.key,None)
                
                if not obj:
                    objs_to_get.add(obj_link)
                    
                    for pref in cref.parentrefs:
                        ref_link = pref.get_link('commitref')
                        if not ref_link in refs_touched:
                            new_links.add(ref_link)
                
                # If we have that object, assume we have all the objects before it.
                
            cref_links = new_links
            
            
        # Recursively get the structure
        while len(objs_to_get) > 0:

            new_links = set()
            
            # Get the objects we don't have
            yield self.fetch_linked_objects(headers.get('reply-to'), objs_to_get)

            for link in objs_to_get:
                if not link.isleaf:
                    obj = repo.get_linked_object(link)
                    for child_link in obj._child_links:
                        if not self._hashed_elements.has_key(child_link.key):
                            new_links.add(child_link)
            
            objs_to_get = new_links
            



        # The following line shows how to reply to a message
        yield self._process.reply_ok(msg)
         
        
    def pull(self,name):
        """
        Pull the current state of the repository
        """
    
    def op_pull(self,content, headers, msg):
        """
        The operation which responds to a pull 
        """
    
    @defer.inlineCallbacks
    def fetch_linked_objects(self, send_to, links):
        """
        Fetch the linked objects from the data store service
        """     
            
            
        cs = container_pb2.Structure()
            
        for link in links:
            se = cs.items.add()
        
            # Can not set the pointer directly... must set the components
            se.value = link.SerializeToString()
            
            se.key = gpb_wrapper.sha1hex(se.value)
            se.isleaf = link.isleaf # What does this mean in this context?
            se.type.CopyFrom(link.GPBType) # Copy is okay - this is small
            
        (objs, headers, msg) = yield self._process.rpc_send(send_to,'fetch_linked_objects', cs)
                        
        for obj in objs:
            self._hashed_elements[obj.key]=obj
        return
        
            
    @defer.inlineCallbacks
    def op_fetch_linked_objects(self, elements, headers, message):
        """
        Send a linked object back to a requestor if you have it!
        """
        cs = container_pb2.Structure()
                
        for se in elements:
            
            assert se.type == self.LinkClassType, 'This is not a link element!'
    
            link = link_pb2.CASRef()
            link.ParseFromString(se.value)

            se = cs.items.add()
        
            item = self._hashed_elements.get(link.key,None)
            
            if not item:
                raise Exception, 'Requested object not found!'
                    
            assert item.type == link.type, 'Link type does not match item type!'
            assert item.isleaf == link.isleaf, 'Link islead does not match item isleaf!'
        
            # Can not set the pointer directly... must set the components
            se.value = item.value

            se.key = item.key
            se.isleaf = item.isleaf # What does this mean in this context?
            se.type.CopyFrom(item.type) # Copy is okay - this is small
        
        
        yield self._process.reply_ok(message,cs)
    
    
    
    def get_repository(self,key):
        """
        Simple getter for the repository dictionary
        """
        
        rkey = self._repository_nicknames.get(key, None)
        if not rkey:
            rkey = key
            
        return self._repos.get(rkey,None)
        
    def list_repositories(self):
        """
        Simple list tool for repository names - not sure this will exist?
        """
        return self._repos.keys()
        
    def put_repository(self,repo):
        
        self._repos[repo._dotgit.repositorykey] = repo
        
        
    def pack_repository_commits(self,repo):
        """
        pack just the mutable head and the commits!
        By default send all commits in the history. Too damn complex on the other
        side to deal with merge otherwise.
        """

        # Can not do this once the repo storage is more complex!
        # assert repo in self._repos.values(), 'This repository is not in the process workbench!'
        
        mutable = repo._dotgit
        # Get the Structure Element for the mutable head
        structure = {}
        mutable._recurse_commit(structure)
        root_obj = structure.get(mutable.myid)
            
        cref_set = set()
        for branch in mutable.branches:
            cref = branch.commitref
            
            # Keep track of the commits
            cref_set.add(cref)
            
        obj_set = set()
            
        while len(cref_set)>0:                
            new_set = set()
            
            for commit in cref_set:
                obj_set.add(cref.myid)
                    
                for prefs in commit.parentrefs:
                    new_set.add(prefs.commitref)
            
            # Now recurse on the ancestors    
            cref_set = new_set
            
            
        obj_list = []
        for key in obj_set:
            obj_list.append(key)
                
        serialized = self._pack_container(root_obj, obj_list)
        
        return serialized
                
        
        
    def pack_structure(self, wrapper, include_leaf=True):
        """
        Pack all children of the wrapper stucture into a message. Stop at the leaf
        links if include_leaf=False.
        Return the content as a container object.
        """
        assert isinstance(wrapper, gpb_wrapper.Wrapper), 'Pack Structure received a wrapper argument which is not a wrapper?'
        
        repo = wrapper.repository
        #assert repo in self._repos.values(), 'This object is not in the process workbench!'
        
        if not repo.status == repo.UPTODATE:
            repo.commit(comment='Sending message with wrapper %s'% wrapper.myid)
        
        obj_set=set()
        root_obj = None
        obj_list = []
        
        # If we are sending the mutable head object
        if wrapper is repo._dotgit:
            structure = {}
            wrapper._recurse_commit(structure)
            root_obj = structure.get(wrapper.myid)
            
            items = set()
            for branch in wrapper.branches:
                cref = branch.commitref
                obj = self._hashed_elements.get(cref.myid,None)
                if not obj:
                    # Debugging exception - remove later
                    raise Exception, 'Hashed CREF not found! Please call David'
                items.add(obj)
            
        else:
            # Else we are sending just the commited root object
            root_obj = self._hashed_elements.get(wrapper.myid,None)
            items = set([root_obj])

        
        # Recurse through the DAG and add the keys to a set - obj_set.
        while len(items) > 0:
            child_items = set()
            for item in items:
                
                if len(item._child_links) >0:
                    
                    obj_set.add(item.key)    
                    
                    for key in item._child_links:
                    
                        obj = self._hashed_elements.get(key,None)
                        if not obj:
                            # Debugging exception - remove later
                            raise Exception, 'Hashed element not found! Please call David'
                    
                        child_items.add(obj)
                        
                elif include_leaf:
                    obj_set.add(item.key)
                    
            items = child_items

        if root_obj.key in obj_set:
            #Make a list in the right order        
            obj_set.discard(root_obj.key)

        for key in obj_set:
            obj_list.append(key)
        
        #print 'OBJLIST',obj_list
        
        serialized = self._pack_container(root_obj, obj_list)
        
        return serialized
        
    
    def _pack_container(self, head, object_keys):
        """
        Helper for the sender to pack message content into a container in order
        """
        
        # An unwrapped GPB Structure message to put stuff into!
        cs = container_pb2.Structure()
        
        cs.head.key = head._element.key
        cs.head.type.CopyFrom(head._element.type)
        cs.head.isleaf = head._element.isleaf
        cs.head.value = head._element.value
            
        for key in object_keys:
            hashed_obj = self._hashed_elements.get(key)         
            gpb_obj = hashed_obj._element
            
            
            se = cs.items.add()
        
            # Can not set the pointer directly... must set the components
            se.key = gpb_obj.key
            se.isleaf = gpb_obj.isleaf
            se.type.CopyFrom(gpb_obj.type) # Copy is okay - this is small
            se.value = gpb_obj.value # Let python's object manager keep track of the pointer to the big things!
        
        
        
        serialized = cs.SerializeToString()
        
        return serialized
        
        
        
        
    def unpack_structure(self, serialized_container):
        """
        Take a container object and load a repository with its contents
        May want to provide more arguments to give this new repository a special
        name based on the 
        """
        
        head, obj_list = self._unpack_container(serialized_container)
        
        assert len(obj_list) > 0, 'There should be objects in the container!'

        
        if not head:
            # Only fetch links should hit this!
            return obj_list
        
        if head.type == self.MutableClassType:
            
            # This is a pull or clone and we don't know the context here.
            # Return the mutable head as the content and let the process
            # operation figure out what to do with it!
                        
            for item in obj_list:
                self._hashed_elements[item.key]=item
            
            repo = self._load_repo_from_mutable(head)
            
            
            
            return repo
        
        else:
                
            for item in obj_list:
                self._hashed_elements[item.key]=item
            
            # Create a new repository for the structure in the container
            repo, none = self.init_repository()
                
           
            # Load the object and set it as the workspace root
            root_obj = repo._load_element(head)
            repo._workspace_root = root_obj
            repo._workspace[root_obj.myid] = root_obj

            # Use the helper method to make a commit ref to our new object root
            cref = repo._create_commit_ref(comment='Message for you Sir!')
            
            # Set the current (master) branch to point at this commit
            brnch = repo._current_branch
            brnch.commitref = cref
            
            # Now load the rest of the linked objects - down to the leaf nodes.
            repo._load_links(root_obj)
            
            return root_obj
        
        
        
    def _unpack_container(self,serialized_container):
        """
        Helper for the receiver for unpacking message content
        Returns the content as a list of ids in order now in the workbench
        hashed elements dictionary
        """
            
        # An unwrapped GPB Structure message to put stuff into!
        cs = container_pb2.Structure()
            
        cs.ParseFromString(serialized_container)
                
        # Return arguments
        head = None
        obj_list=[]
        
        if cs.HasField('head'):
            # The head field is optional - if not included this is a fetch links op            
            head = gpb_wrapper.StructureElement.wrap_structure_element(cs.head)
            #self._hashed_elements[head.key]=head
            obj_list.append(head)
            
        for se in cs.items:
            wse = gpb_wrapper.StructureElement.wrap_structure_element(se)
            
            #self._hashed_elements[wse.key]=wse
            #obj_list.append(wse.key)
            obj_list.append(wse)
        
    
        return head, obj_list
        