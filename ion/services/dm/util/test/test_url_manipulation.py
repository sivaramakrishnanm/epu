#!/usr/bin/env python

"""
@file ion/services/dm/util/test/test_url_manipulation.py
@test Tests for ion.services.dm.util/url_manipulation
@author Paul Hubbard
@date 6/4/10
"""

import ion.util.ionlog
log = ion.util.ionlog.getLogger(__name__)

from twisted.trial import unittest

from ion.services.dm.util.url_manipulation import base_dap_url, generate_filename, rewrite_url
from ion.core import ioninit

class BaseUrlTester(unittest.TestCase):
    """
    Test url routine, purely local.
    """
    def setUp(self):
        pass

    def test_config_file(self):
        cfg =  ioninit.config('ion.services.dm.util.url_manipulation')
        ldir = cfg.getValue('local_dir', None)
        self.failUnless(len(ldir) > 0)
        cname = cfg.getValue('cache_hostname', None)
        self.failUnless(len(cname) > 0)

    def test_pydap_urls(self):
        # Variable access, generated by pydap web interface
        b = base_dap_url('http://amoeba.ucsd.edu:8001/glacier.nc.ascii?var232%5B0:1:0%5D%5B0:1:0%5D%5B0:1:601%5D%5B0:1:401%5D&')
        self.assertEqual(b, 'http://amoeba.ucsd.edu:8001/glacier.nc')

        # Same thing, no port number
        b = base_dap_url('http://amoeba.ucsd.edu/glacier.nc.ascii?var232%5B0:1:0%5D%5B0:1:0%5D%5B0:1:601%5D%5B0:1:401%5D&')
        self.assertEqual(b, 'http://amoeba.ucsd.edu/glacier.nc')

    def test_numeric_hostname(self):
        # Most-basic DAP URL, not compressible
        b = base_dap_url('http://127.0.0.1:8001/etopo120.cdf')
        self.assertEqual(b, 'http://127.0.0.1:8001/etopo120.cdf')

    def test_numeric_hostname_no_dap(self):
        b = base_dap_url('http://137.110.112.49:8001/')
        self.assertEqual(b, 'http://137.110.112.49:8001/')

    def test_ref_urls(self):
        # From DAP2 spec, Examples section
        b = base_dap_url('http://server.edu/cgi-bin/nph-dods/data/temp.dat.dds')
        self.assertEqual(b, 'http://server.edu/cgi-bin/nph-dods/data/temp.dat')

        # DAS version
        b = base_dap_url('http://server.edu/cgi-bin/nph-dods/data/temp.dat.das')
        self.assertEqual(b, 'http://server.edu/cgi-bin/nph-dods/data/temp.dat')

        # DODS
        b = base_dap_url('http://server.edu/cgi-bin/nph-dods/data/temp.dat.dods')
        self.assertEqual(b, 'http://server.edu/cgi-bin/nph-dods/data/temp.dat')

    def test_variable_access(self):
        b = base_dap_url('http://server.edu/cgi-bin/nph-dods/grid-data/temp2.dat.dds?g[20:21][40:42]')
        self.assertEqual(b, 'http://server.edu/cgi-bin/nph-dods/grid-data/temp2.dat')

        b = base_dap_url('http://server.edu/grid-data/temp2.dat.das?grid[20:21][40:42]')
        self.assertEqual(b, 'http://server.edu/grid-data/temp2.dat')

        b = base_dap_url('http://server.edu/cgi-bin/nph-dods/grid-data/temp2.dat.dods?g[20:21][40:42]')
        self.assertEqual(b, 'http://server.edu/cgi-bin/nph-dods/grid-data/temp2.dat')

    def test_sequences(self):
        # Also from the DAP2 spec examples section
        b = base_dap_url('http://server.edu/cgi-bin/nph-dods/seq-data/temp3.dat.dds?xval<15')
        self.assertEqual(b, 'http://server.edu/cgi-bin/nph-dods/seq-data/temp3.dat')

        b = base_dap_url('http://server.edu/cgi-bin/nph-dods/seq-data/temp3.dat.dods?xval<15')
        self.assertEqual(b, 'http://server.edu/cgi-bin/nph-dods/seq-data/temp3.dat')

    def test_bad_urls(self):
        b = base_dap_url('ftp://is.not.valid/foo.nc')
        self.assertEqual(b, None)

        b = base_dap_url('webdav://is.no.good/either.cdf')
        self.assertEqual(b, None)

    def test_https(self):
        b = base_dap_url('https://server.edu/cgi-bin/nph-dods/seq-data/temp3.dat.dods?xval<15')
        self.assertEqual(b, 'https://server.edu/cgi-bin/nph-dods/seq-data/temp3.dat')

    def test_fu(self):
        b = base_dap_url('http://foo.example.com/ds.nc')
        self.assertEqual(b, 'http://foo.example.com/ds.nc')

class RewriteTester(unittest.TestCase):
    """
    Test url rewriter, no communications required.
    """
    def setUp(self):
        pass

    def test_pydap_urls(self):
        # Variable access, generated by pydap web interface
        b = rewrite_url('http://amoeba.ucsd.edu:8001/glacier.nc.ascii?var232%5B0:1:0%5D%5B0:1:0%5D%5B0:1:601%5D%5B0:1:401%5D&')
        self.assertEqual(b, 'http://localhost/glacier.nc.ascii?var232%5B0:1:0%5D%5B0:1:0%5D%5B0:1:601%5D%5B0:1:401%5D&')

        # Same thing, no port number
        b = rewrite_url('http://amoeba.ucsd.edu/glacier.nc.ascii?var232%5B0:1:0%5D%5B0:1:0%5D%5B0:1:601%5D%5B0:1:401%5D&')
        self.assertEqual(b, 'http://localhost/glacier.nc.ascii?var232%5B0:1:0%5D%5B0:1:0%5D%5B0:1:601%5D%5B0:1:401%5D&')

    def test_numeric_hostname(self):
        # Base DAP URL
        b = rewrite_url('http://127.0.0.1:8001/etopo120.cdf')
        self.assertEqual(b, 'http://localhost/etopo120.cdf')

        # Base DAP URL plus pathspec
        b = rewrite_url('http://127.0.0.1:8001/foo/bar/baz/quux/etopo121.cdf')
        self.assertEqual(b, 'http://localhost/etopo121.cdf')

    def test_ref_urls(self):
        # From DAP2 spec, Examples section
        b = rewrite_url('http://server.edu/cgi-bin/nph-dods/data/temp.dat.dds')
        self.assertEqual(b, 'http://localhost/temp.dat.dds')

        # DAS version
        b = rewrite_url('http://server.edu/cgi-bin/nph-dods/data/temp.dat.das')
        self.assertEqual(b, 'http://localhost/temp.dat.das')

        # DODS
        b = rewrite_url('http://server.edu/cgi-bin/nph-dods/data/temp.dat.dods')
        self.assertEqual(b, 'http://localhost/temp.dat.dods')

    def test_variable_access(self):
        b = rewrite_url('http://server.edu/cgi-bin/nph-dods/grid-data/temp2.dat.dds?g[20:21][40:42]')
        self.assertEqual(b, 'http://localhost/temp2.dat.dds?g[20:21][40:42]')

        b = rewrite_url('http://server.edu/grid-data/temp2.dat.das?grid[20:21][40:42]')
        self.assertEqual(b, 'http://localhost/temp2.dat.das?grid[20:21][40:42]')

        b = rewrite_url('http://server.edu/cgi-bin/nph-dods/grid-data/temp2.dat.dods?g[20:21][40:42]')
        self.assertEqual(b, 'http://localhost/temp2.dat.dods?g[20:21][40:42]')

class FilenameTester(unittest.TestCase):
    """
    Test filename generation, no communications necessary.
    """
    def setUp(self):
        cfg =  ioninit.config('ion.services.dm.util.url_manipulation')
        self.prefix = cfg.getValue('local_dir', None)

    def test_most_basic(self):
        b = generate_filename('http://amoeba.ucsd.edu/coads.nc')
        self.assertEqual(b, self.prefix + 'coads.nc')

    def test_with_port(self):
        b = generate_filename('http://amoeba.ucsd.edu:65532/coads.nc')
        self.assertEqual(b, self.prefix + 'coads.nc')

    def test_numeric_hostname(self):
        b = generate_filename('http://140.221.9.6/foo/coads.nc')
        self.assertEqual(b, self.prefix + 'coads.nc')

    def test_long_url(self):
        b = generate_filename('http://amoeba.ucsd.edu/foo/bar/baz/quux/getting/very/silly/data.nc')
        self.assertEqual(b, self.prefix + 'data.nc')

    def test_bad_filenames(self):
        b = generate_filename('http://amoeba.ucsd.edu/coads%20two.nc')
        self.assertEqual(b, self.prefix + 'coads20two.nc')

        b = generate_filename('http://amoeba.ucsd.edu/coads&amp;bar.nc')
        self.assertEqual(b, self.prefix + 'coadsampbar.nc')
