import unittest
from gridmon.probe import *

class SimpleMockGatherer(MetricGatherer):
    def __init__(self):
        MetricGatherer.__init__(self, {'serviceURI':''}, 'Bar')
        self.description = {'Foo' : {'x':'y', 'a':'b'}}
        self.methodMap = {'Foo' : 'metricFoo'}

    def metricFoo(self):
        return (0, 'hello!')

class ComplexMockGatherer(MetricGatherer):
    def __init__(self):
        MetricGatherer.__init__(self, {'serviceURI':''}, 'Bar')
        self.description = {'org.wlcg.Foo' : {'x':'y', 'a':'b'}}
        self.methodMap = {'org.wlcg.Foo' : 'gatherFoo'}

    def gatherFoo(self):
        return (0, 'hello!')

class MockStdout:
    def __init__(self, expectedLines):
        self.lines = []
        self.expected = expectedLines
        pass

    def write(self, string):
        if string != '\n':
            self.lines.append(string)

    def check(self):
        """Simple check on the consistency of the output
        - all lines there, and last line is a bare 'EOT'"""

        assert len(self.lines) > 0
        for actual, expected in zip(self.lines[:-1], self.expected):
            assert actual == expected
        #assert self.lines[-1] == 'EOT'

class testRenderer(unittest.TestCase):
    def testNullRenderer(self):
        results = {}
        expected = []
        mstdout = MockStdout(expected)
        r = ProbeFormatRenderer(stream = mstdout)
        r.render(results)
        mstdout.check()

#    def testSingleValueRenderer(self):
#        results = {'a' : 'b'}
#        expected = ['a: b']
#        mstdout = MockStdout(expected)
#        r = ProbeFormatRenderer(stream = mstdout)
#        r.render(results)
#        mstdout.check()
    def testSingleValueRenderer(self):
        results = {'summaryData' : 'a',
                   'metricStatus': 'OK'}
        expected = ['a']
        mstdout = MockStdout(expected)
        r = ProbeFormatRenderer(stream = mstdout)
        rc = r.render(results)
        assert 0 == rc
        mstdout.check()

#    def testMultiValueRenderer(self):
#        results = {'a' : 'b', 'x' : 'y'}
#        expected = ['a: b', 'x: y']
#        mstdout = MockStdout(expected)
#        r = ProbeFormatRenderer(stream = mstdout)
#        r.render(results)
#        mstdout.check()
    def testMultiValueRenderer(self):
        results = {'summaryData' : 'a',
                   'detailsData' : 'b',
                   'metricStatus': 'OK'}
        expected = ['a', 'b']
        mstdout = MockStdout(expected)
        r = ProbeFormatRenderer(stream = mstdout)
        rc = r.render(results)
        assert 0 == rc
        mstdout.check()

class testMetricGatherer(unittest.TestCase):
    def testNullGatherer(self):
        mg = MetricGatherer({'serviceURI':''}, 'LFC')
        assert mg.serviceType == 'LFC'

        metrics = mg.list()
        assert 0 == len(metrics)

        desc = mg.desc('foo')
        assert None == desc

    def testMissingDesc(self):
        mg = MetricGatherer({'serviceURI':''}, 'LFC')
        assert None == mg.desc('foo')

    def testSimpleMock(self):
        mg = SimpleMockGatherer()
        assert mg.serviceType == 'Bar'

        metrics = mg.list()
        assert 1 == len(metrics)
        assert metrics[0] == 'Foo'

        desc = mg.desc('Foo')
        assert None != desc
        assert 3 == len(desc)
        assert desc['a'] == 'b'
        assert desc['x'] == 'y'
        assert desc['serviceType'] == mg.serviceType


    def testGatherSimpleMock(self):
        mg = SimpleMockGatherer()
        results = mg.gather('Foo')
        assert 3 == len(results)
        #assert None != results['timestamp']
        assert 'OK: hello!' == results['summaryData']
        assert 'OK' == results['metricStatus']
        #assert 'Foo' == results['metricName']
        #assert 'Bar' == results['serviceType']

    def testGatherComplexMock(self):
        mg = ComplexMockGatherer()
        results = mg.gather('org.wlcg.Foo')
        assert 3 == len(results)
        #assert None != results['timestamp']
        assert 'OK: hello!' == results['summaryData']
        assert 'OK' == results['metricStatus']
        #assert 'org.wlcg.Foo' == results['metricName']
        #assert 'Bar' == results['serviceType']

if __name__ == '__main__':
    unittest.main()
