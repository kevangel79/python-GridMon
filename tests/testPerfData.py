#!/usr/bin/env python
##############################################################################
#
# NAME:        testPerfData.py
#
# FACILITY:    SAM (Service Availability Monitoring)
#
# DESCRIPTION:
#
#         Nagios performance data.
#
# AUTHORS:     Konstantin Skaburskas, CERN
#
# CREATED:     May 4, 2010
#
# NOTES:
#
# MODIFIED:
#
##############################################################################

"""
Nagios performance data.

Nagios performance data.

Konstantin Skaburskas <konstantin.skaburskas@cern.ch>, CERN
SAM (Service Availability Monitoring)
"""

import os
import re
import sys
import unittest

sys.path.insert(1, re.sub('/\w*$','/',os.getcwd()))

from gridmon.probe import MetricGatherer
from gridmon.nagios.perfdata import PerfData

class TestPerfDataClass(unittest.TestCase):
    def test1InvalidInput(self):
        'PerfData class - invalid inputs.'
        self.failUnlessRaises(TypeError, PerfData, '')
        self.failUnlessRaises(TypeError, PerfData, {})

    def test2ValidInput(self):
        'PerfData class - valid inputs.'
        pd = PerfData(('a','b','c'))
        assert pd.get() == 'a=0;; b=0;; c=0;;'
        pd.update({'a':1,'c':2})
        assert pd.get() == 'a=1;; b=0;; c=2;;'
        pd.update({'b':[1,2,3.2],'a':10,'c':'123'})
        assert pd.get() == 'a=10;; b=1;2;3.2 c=123;;'

class TestPerfDataField(unittest.TestCase):
    def test1ValidInput(self):
        'MetricGatherer.perf_data - all possible valid assignments.'
        mg = MetricGatherer({'serviceURI':''}, 'Bar')

        for d in ['', [], (), [()], ([]), [('',)]]:
            mg.perf_data = d
            assert mg.perf_data == ''

        mg.perf_data = [('size',)]
        assert mg.perf_data == 'size=0;;'
        mg.perf_data = [('size',),('',)]
        assert mg.perf_data == 'size=0;;'

        exp = 'size=123.4;;'
        for v in [exp, [('size','123.4')], [('size',123.4)]]:
            mg.perf_data = v
            assert mg.perf_data == exp

        exp = 'perf1=1;2;3.0;4.4'
        mg.perf_data = [('perf1',[1,2,3.0,'4.4'])]
        assert mg.perf_data == exp

        exp = 'perf1=1;2;3 perf2=1;2;3'
        mg.perf_data = [('perf1',[1,2,3]), ('perf2',(1,2,3))]
        assert mg.perf_data == exp
        mg.perf_data = (('perf1',[1,2,3]), ('perf2',(1,2,3)))
        assert mg.perf_data == exp

    def test2InvalidInput(self):
        'MetricGatherer.perf_data - invalid assignments.'
        mg = MetricGatherer({'serviceURI':''}, 'Bar')
        for d in [{}, [{}], [{'':''}]]:
            try:
                mg.perf_data = d
            except TypeError:
                pass
            else:
                self.fail('Should have failed with TypeError.')

    def test3HandleMetricOutput(self):
        'Handle metric output with performance data.'
        ret = (0, 'summary', 'details')
        mg = MetricGatherer({'serviceURI':''}, 'Bar')

        mg.perf_data = ''
        res = mg._handle_metric_output(ret)
        self.failIf(res.has_key('perfData'),
                    "'perfData' key shouldn't have been set.")

        exp = 'perf=1;2;3'
        mg.perf_data = exp
        res = mg._handle_metric_output(ret)
        assert res.has_key('perfData')
        assert res['perfData'] == exp

if __name__ == "__main__":
    testcases = [TestPerfDataClass,
                 TestPerfDataField]
    for tc in testcases:
        unittest.TextTestRunner(verbosity=2).\
            run(unittest.TestLoader().loadTestsFromTestCase(tc))
