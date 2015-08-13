#!/usr/bin/env python
##############################################################################
#
# NAME:        testGridutils.py
#
# FACILITY:    SAM (Service Availability Monitoring)
#
# DESCRIPTION:
#
#         Tests for functions in gridmon.gridutils module.
#
# AUTHORS:     Konstantin Skaburskas, CERN
#
# CREATED:     Mar 9, 2010
#
# NOTES:
#
# MODIFIED:
#
##############################################################################
"""
tests for functions in gridmon.gridutils module.

Tests for functions in gridmon.gridutils module.

Konstantin Skaburskas <konstantin.skaburskas@cern.ch>, CERN
SAM (Service Availability Monitoring)
"""

import re
import os
import sys
import unittest
import socket
import commands

sys.path.insert(1, re.sub('/\w*$','/',os.getcwd()))

from gridmon import gridutils
from gridmon import utils as samutils

LOCALHOST,_,_ = socket.gethostbyaddr('127.0.0.1')

class TestGridutilsGetWorkingLDAP(unittest.TestCase):
    def test1TypeError(self):
        'Get working LDAP as IP address - wrong type.'
        self.failUnlessRaises(TypeError,
                              gridutils.get_working_ldap, (''))
    def test2EmptyList(self):
        'Get working LDAP as IP address - empty list.'
        self.failUnlessRaises(ValueError,
                              gridutils.get_working_ldap, [])
    def test3EmptyEndpoints(self):
        'Get working LDAP as IP address - list with empty endpoints.'
        self.failUnlessRaises(ValueError,
                              gridutils.get_working_ldap, ['',''])
    def test4ValidEndpoints(self):
        'Get working LDAP as IP address - valid LDAP endpoints.'
        endpoints = ['lcg-bdii.cern.ch:2170', 'ldap://lcg-bdii.cern.ch:2170']
        for b in [True, False]:
            gridutils.LDAP_LIB = b
            for ldap in endpoints:
                try:
                    ldap_ip = gridutils.get_working_ldap([ldap])
                except Exception, e:
                    self.fail('Failed with: %s' % str(e))
                ip, _ = samutils.parse_uri2(ldap_ip)
                try:
                    socket.inet_aton(ip)
                except socket.error:
                    self.fail('Not an IP address returned by ' + \
                              'gridutils.get_working_ldap().')
    def test5ValidAndFakeEndpoints(self):
        'Get working LDAP as IP address - valid and fake LDAP endpoints.'
        for b in [True, False]:
            gridutils.LDAP_LIB = b
            try:
                ldap_ip = gridutils.get_working_ldap(['fake.bdii.host:2170',
                                                'ldap://lcg-bdii.cern.ch:2170'])
            except Exception, e:
                self.fail('Failed with: %s' % str(e))
            ip, _ = samutils.parse_uri2(ldap_ip)
            try:
                socket.inet_aton(ip)
            except socket.error:
                self.fail('Not an IP address returned by '+\
                                'gridutils.get_working_ldap().')
    def test6AllFakeEndpoints(self):
        'Get working LDAP as IP address - fake LDAP endpoints (name res. failure).'
        self.failUnlessRaises(LookupError, gridutils.get_working_ldap,
                            (['fake1.bdii.host:2170',
                              'ldap://fake2.bdii.host:2170']))
    def test7(self):
        'Get working LDAP as IP address - ldap://localhost:2170.'
        try:
            gridutils.get_working_ldap(['ldap://localhost:2170'])
        except LookupError, e:
            errmsg = str(e)
            self.failUnless(errmsg.startswith('* [ldap://localhost:2170 [127.0.0.1]]') or \
                            errmsg.startswith('* [ldap://%s:2170 [127.0.0.1]]' % LOCALHOST),
                            'Wrong error message returned: %s' % errmsg)
        else:
            self.fail('LookupError exception was expected.')

class TestGridutilsGetWorkingLDAPNoContact(unittest.TestCase):
    def setUp(self):
        commands.getstatusoutput('sudo iptables -A OUTPUT -p tcp --dport 2170 -j REJECT')
    def tearDown(self):
        commands.getstatusoutput('sudo iptables -D OUTPUT -p tcp --dport 2170 -j REJECT')
    def test1(self):
        'Get working LDAP as IP address - ldap://lcg-bdii.cern.ch:2170, 2170 firewalled (wait ~30sec).'
        endpoints = ['ldap://lcg-bdii.cern.ch:2170']
        for b in [True, False]:
            gridutils.LDAP_LIB = b
            for ldap in endpoints:
                self.failUnlessRaises(LookupError,
                                      gridutils.get_working_ldap, ([ldap]))

class TestGridutilsQueryBDII(unittest.TestCase):
    def test1EmptyFilter(self):
        'Query BDII - empty filter.'
        rc, o = gridutils.query_bdii('', [''],
                                     ldap_url='fake.bdii.host')
        self.failUnlessEqual(rc, 0, 'Should have returned 0.')
        if not isinstance(o, tuple):
            self.fail('Expected tuple, got %s.' % type(o))
        self.failUnlessEqual(o[0], gridutils.LDAP_QE_OTHER,
                    'Expected %i, got %i' % (gridutils.LDAP_QE_OTHER, o[0]))
    def test2StringAsQueryAttributes(self):
        'Query BDII - string as query attributes.'
        rc, o = gridutils.query_bdii('filter', 'string',
                                     ldap_url='fake.bdii.host')
        self.failUnlessEqual(rc, 0, 'Should have returned 0.')
        if not isinstance(o, tuple):
            self.fail('Expected tuple, got %s.' % type(o))
        self.failUnlessEqual(o[0], gridutils.LDAP_QE_OTHER,
                    'Expected %i, got %i' % (gridutils.LDAP_QE_OTHER, o[0]))
    def test3ListOfEmptyEndpoints_Input(self):
        'Query BDII - list of empty endpoints on input.'
        rc, o = gridutils.query_bdii('filter', [''], ldap_url=',')
        self.failUnlessEqual(rc, 0, 'Should have returned 0.')
        if not isinstance(o, tuple):
            self.fail('Expected tuple, got %s.' % type(o))
        self.failUnlessEqual(o[0], gridutils.LDAP_QE_OTHER,
                        'Expected %i, got %i' % (gridutils.LDAP_QE_OTHER, o[0]))
    def test4ListOfEmptyEndpoints_Environment(self):
        'Query BDII - list of empty endpoints in LCG_GFAL_INFOSYS.'
        os.environ['LCG_GFAL_INFOSYS'] = ','
        rc, o = gridutils.query_bdii('filter', [''])
        self.failUnlessEqual(rc, 0, 'Should have returned 0.')
        if not isinstance(o, tuple):
            self.fail('Expected tuple, got %s.' % type(o))
        self.failUnlessEqual(o[0], gridutils.LDAP_QE_OTHER,
                        'Expected %i, got %i' % (gridutils.LDAP_QE_OTHER, o[0]))
    def test5CorrectQuery(self):
        'Query BDII - correct query.'
        attr_val = 'msg.broker.stomp'
        rc, res = gridutils.query_bdii(
            '(&(objectClass=GlueService)(GlueServiceType=%s))' % attr_val,
            ['GlueServiceType'], ldap_url='ldap://lcg-bdii.cern.ch:2170')
        self.failUnlessEqual(rc, 1, 'Query failed. Check BDII or query.')
        for dn in res:
            val = dn[1]['GlueServiceType'][0]
            self.failUnlessEqual(val, attr_val,
                                 'Expected %s, got %s' % (attr_val, val))
    def test6CorrectQuery(self):
        'Query BDII - correct query; empty result.'
        attr_val = 'fake.unknown.service'
        for b in [True, False]:
            gridutils.LDAP_LIB = b
            who = b and 'API' or 'CLI'
            rc, res = gridutils.query_bdii(
                '(&(objectClass=GlueService)(GlueServiceType=%s))' % attr_val,
                ['GlueServiceType'], ldap_url='ldap://lcg-bdii.cern.ch:2170')
            self.failUnlessEqual(rc, 0, who+' Query failed. Check BDII or query.')
            self.failUnlessEqual(res[0], gridutils.LDAP_QE_EMPTYSET,
                            who+' Expected LDAP_QE_EMPTYSET error, got %i.' % res[0])
            pattern = "No information for \[attribute\(s\): \['GlueServiceType'\]\] in \[ldap://"
            self.failUnless(re.search(pattern, res[1]),
                            who+' Expected: \n%s\ngot: \n%s' % (pattern, res[1]))

if __name__ == "__main__":
    testcases = [TestGridutilsGetWorkingLDAP,
                 TestGridutilsGetWorkingLDAPNoContact,
                 TestGridutilsQueryBDII]
    for tc in testcases:
        unittest.TextTestRunner(verbosity=2).\
            run(unittest.TestLoader().loadTestsFromTestCase(tc))
