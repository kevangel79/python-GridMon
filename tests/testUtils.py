#!/usr/bin/env python
##############################################################################
#
# NAME:        testUtils.py
#
# FACILITY:    SAM (Service Availability Monitoring)
#
# DESCRIPTION:
#
#         Tests for functions defined in gridmon.utils module.
#
# AUTHORS:     Konstantin Skaburskas, CERN
#
# CREATED:     May 2, 2010
#
# NOTES:
#
# MODIFIED:
#
##############################################################################

"""
tests for functions defined in gridmon.utils module.

Tests for functions defined in gridmon.utils module.

Konstantin Skaburskas <konstantin.skaburskas@cern.ch>, CERN
SAM (Service Availability Monitoring)
"""

import re
import os
import sys
import unittest
import socket

sys.path.insert(1, re.sub('/\w*$','/',os.getcwd()))

from gridmon import utils as samutils

LOCALHOST,_,_ = socket.gethostbyaddr('127.0.0.1')

class TestUtilsDNS(unittest.TestCase):
    def test2(self):
        "dns_lookup_forward('')"
        self.failUnlessRaises(ValueError,
                              samutils.dns_lookup_forward, '')
    def test3(self):
        "dns_lookup_forward('localhost')"
        res = samutils.dns_lookup_forward('localhost')
        self.failUnlessEqual(res, ['127.0.0.1'],
                             "Expected ['127.0.0.1'], got %s" % res)
    def test4(self):
        "dns_lookup_forward('127.0.0.1')"
        res = samutils.dns_lookup_forward('127.0.0.1')
        self.failUnlessEqual(res, ['127.0.0.1'],
                             "Expected ['127.0.0.1'], got %s" % res)
    def test5(self):
        "dns_lookup_forward('lcg-bdii.cern.ch')"
        res = samutils.dns_lookup_forward('lcg-bdii.cern.ch')
        if len(res) < 1:
            self.fail("Expected a list of IPs. Got %r." % res)
        for ip in res:
            if not re.match('^128.142*', ip):
                self.fail("Expected ['127.0.0.1'], got %s" % res)
    def test6(self):
        "dns_lookup_reverse('')"
        self.failUnlessRaises(ValueError,
                              samutils.dns_lookup_reverse, '')
    def test7(self):
        "dns_lookup_reverse('127.0.0.1')"
        res = samutils.dns_lookup_reverse('127.0.0.1')
        if res != 'localhost' and res != LOCALHOST:
            self.fail("Expected localhost, got %s" % res)
    def test8(self):
        "dns_lookup_reverse('128.142.198.41')"
        res = samutils.dns_lookup_reverse('128.142.198.41')
        if res != 'bdii203.cern.ch':
            self.fail("Expected localhost, got %s" % res)
    def test9(self):
        "dns_lookup_reverse('localhost')"
        self.failUnlessRaises(ValueError,
                              samutils.dns_lookup_reverse, 'localhost')

class TestParseURI(unittest.TestCase):
    def test1(self):
        "parse_uri2(''), parse_uri3('')"
        res = samutils.parse_uri2('')
        self.failUnlessEqual(res, ['', None],
                             "Expected ['', None], got %s" % res)
        res = samutils.parse_uri3('')
        self.failUnlessEqual(res, [None, '', None],
                             "Expected [None, '', None], got %s" % res)

    def test2(self):
        "parse_uri2(valid_uri), parse_uri3(valid_uri)"
        proto = 'http://'; host = 'www.test.host'; port = '80'
        uri = '%s%s:%s' % (proto, host, port)

        res = samutils.parse_uri2(uri)
        self.failUnlessEqual(res, [host, port],
                             "Expected [%s, %s], got %s" % (host, port, res))
        res = samutils.parse_uri3(uri)
        self.failUnlessEqual(res, [proto, host, port],
                             "Expected [%s, %s, %s], got %s" % (proto, host,
                                                                port, res))

class TestUtilsURL2HostIP(unittest.TestCase):
    def test1(self):
        "LDAP URL to hostname and IP - ldap_url2hostname_ip('')."
        res = samutils.ldap_url2hostname_ip('')
        self.failUnlessEqual(res, '[ldap://]',
                             "Expected '[ldap://]', got %s" % res)
    def test2(self):
        "LDAP URL to hostname and IP - ldap_url2hostname_ip('127.0.0.1:2170')."
        exp1 = '[ldap://localhost:2170 [127.0.0.1]]'
        exp2 = '[ldap://%s:2170 [127.0.0.1]]' % LOCALHOST
        res = samutils.ldap_url2hostname_ip('127.0.0.1:2170')
        if res != exp1 and res != exp2:
            self.fail("Expected '%s' or '%s', got %s" % (exp1, exp2, res))
    def test3(self):
        "LDAP URL to hostname and IP - ldap_url2hostname_ip('ldap://127.0.0.1:2170')."
        exp1 = '[ldap://localhost:2170 [127.0.0.1]]'
        exp2 = '[ldap://%s:2170 [127.0.0.1]]' % LOCALHOST
        res = samutils.ldap_url2hostname_ip('ldap://127.0.0.1:2170')
        if res != exp1 and res != exp2:
            self.fail("Expected '%s' or '%s', got %s" % (exp1, exp2, res))
    def test4(self):
        "LDAP URL to hostname and IP - ldap_url2hostname_ip('localhost:2170')."
        exp = '[ldap://localhost:2170]'
        res = samutils.ldap_url2hostname_ip('localhost:2170')
        self.failUnlessEqual(res, exp, "Expected '%s', got %s" % (exp, res))

class TestUtilsStatusAndRetcode(unittest.TestCase):
    def testToStatus(self):
        "utils.to_status()"
        assert 'OK' == samutils.to_status(0)
        assert 'WARNING' == samutils.to_status(1)
        assert 'CRITICAL' == samutils.to_status(2)
        assert 'UNKNOWN' == samutils.to_status(3)
        assert 'UNKNOWN' == samutils.to_status(-1)
        assert 'UNKNOWN' == samutils.to_status('foo')

    def testToRetcode(self):
        "utils.to_retcode()"
        for s in (0, 'OK', 'ok', 'Ok'):
            assert 0 == samutils.to_retcode(s)
        for s in (1, 'WARNING', 'warning', 'Warning'):
            assert 1 == samutils.to_retcode(s)
        for s in (2, 'CRITICAL', 'critical', 'Critical'):
            assert 2 == samutils.to_retcode(s)
        for s in (3, 'UNKNOWN', 'Unknown', 'Bad Input'):
            assert 3 == samutils.to_retcode(s)


if __name__ == "__main__":
    testcases = [TestParseURI,
                 TestUtilsDNS,
                 TestUtilsURL2HostIP,
                 TestUtilsStatusAndRetcode]
    for tc in testcases:
        unittest.TextTestRunner(verbosity=2).\
            run(unittest.TestLoader().loadTestsFromTestCase(tc))
