##############################################################################
#
# NAME:        testProbeFormatRenderer.py
#
# FACILITY:    SAM (Service Availability Monitoring)
#
# COPYRIGHT:
#         Copyright (c) 2009, Members of the EGEE Collaboration.
#         http://www.eu-egee.org/partners/
#         Licensed under the Apache License, Version 2.0.
#         http://www.apache.org/licenses/LICENSE-2.0
#         This software is provided "as is", without warranties
#         or conditions of any kind, either express or implied.
#
# DESCRIPTION:
#
#         Set of tests for gridmon.probe.ProbeFormatRenderer class.
#
# AUTHORS:     Konstantin Skaburskas, CERN
#
# CREATED:     Oct 15, 2009
#
# NOTES:
#
# MODIFIED:
#
##############################################################################

"""
set of tests for gridmon.probe.ProbeFormatRenderer class.

Set of tests for gridmon.probe.ProbeFormatRenderer class.

Konstantin Skaburskas <konstantin.skaburskas@cern.ch>, CERN
SAM (Service Availability Monitoring)
"""
import os
import re
import sys
import unittest

sys.path.insert(1, re.sub('/\w*$','/',os.getcwd()))

from gridmon.probe import ProbeFormatRenderer
from gridmon import utils as samutils

class TestProbeFormatRenderer(unittest.TestCase):
    class Writer:
        buf = ''
        def write(self, str):
            self.buf += str
        def print_(self):
            return self.buf
    summary = 'OK: | ||'
    detdata = 'OK: || |'

    def setUp(self):
        self.wr = self.Writer()
        self.tuples = {'summaryData' : self.summary,
                       'detailsData' : self.detdata,
                       'metricStatus': 0}
    def tearDown(self):
        self.wr = None
        self.tuples = {}

    def test1SanitizePipesTrue(self):
        'Sanitize "pipes".'
        expected = 'OK: OR OR\nOK: OR OR'
        ProbeFormatRenderer(stream=self.wr).render(self.tuples)
        self.failUnlessEqual(self.wr.print_(),
                             expected+'\n',
                             'Check against expected output failed.')
        self.failUnlessEqual(self.wr.print_(),
                             samutils.outputsanitiser('%s\n%s\n' % (self.summary,
                                                                    self.detdata)),
                             'Check against outputsanitiser() failed.')
    def test2SanitizePipesFalseInit(self):
        'Do not sanitize "pipes". "False" in __init__()'
        expected = '%s\n%s' % (self.summary, self.detdata)
        ProbeFormatRenderer(stream=self.wr, sanitize=False).render(self.tuples)
        self.failUnlessEqual(self.wr.print_(),
                             expected+'\n',
                             'Check against expected output failed.')
    def test3SanitizePipesFalseRender(self):
        'Do not sanitize "pipes". "False" in render()'
        expected = '%s\n%s' % (self.summary, self.detdata)
        ProbeFormatRenderer(stream=self.wr).render(self.tuples, sanitize=False)
        self.failUnlessEqual(self.wr.print_(),
                             expected+'\n',
                             'Check against expected output failed.')
    def test4PerformanceData(self):
        'Performance data - summary and empty performance data.'
        expected = 'OK: OR OR\n'
        tuples = {'summaryData' : self.summary,
                  'metricStatus': 0}
        for v in ['', None]:
            tuples.update({'perfData' : v})
            ProbeFormatRenderer(stream=self.wr).render(tuples)
            res = self.wr.print_()
            self.failUnlessEqual(res, expected,
                                 'Expected %s, got %s' % (expected, res))
            self.wr = self.Writer()
    def test5PerformanceData(self):
        'Performance data - summary and performance data.'
        expected = 'OK: OR OR|a=1;2;3\n'
        tuples = {'summaryData' : self.summary,
                  'metricStatus': 0,
                  'perfData'    : 'a=1;2;3'}
        ProbeFormatRenderer(stream=self.wr).render(tuples)
        res =self.wr.print_()
        self.failUnlessEqual(res, expected,
                             'Expected %s, got %s' % (expected, res))
    def test6PerformanceData(self):
        'Performance data - summary, details and empty performance data.'
        expected = 'OK: OR OR\nOK: OR OR\n'
        for v in ['', None]:
            self.tuples.update({'perfData' : v})
            ProbeFormatRenderer(stream=self.wr).render(self.tuples)
            res = self.wr.print_()
            self.failUnlessEqual(res, expected,
                                 'Expected %s, got %s' % (expected, res))
            self.wr = self.Writer()
    def test7PerformanceData(self):
        'Performance data - summary, details and performance data.'
        expected = 'OK: OR OR\nOK: OR OR|a=1;2;3\n'
        self.tuples.update({'perfData' : 'a=1;2;3'})
        ProbeFormatRenderer(stream=self.wr).render(self.tuples)
        res =self.wr.print_()
        self.failUnlessEqual(res, expected,
                             'Expected %s, got %s' % (expected, res))
    def test8MissingKyes(self):
        'Mandatory keys missing.'
        self.failUnlessEqual(ProbeFormatRenderer(stream=self.wr).render({'a':1}),
                             3, 'Should have exited with 3 on missing mandatory keys.')

if __name__ == "__main__":
    testcases = [TestProbeFormatRenderer]
    for tc in testcases:
        unittest.TextTestRunner(verbosity=2).\
            run(unittest.TestLoader().loadTestsFromTestCase(tc))
