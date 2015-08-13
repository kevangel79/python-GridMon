##############################################################################
#
# NAME:        metricoutput.py
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
#         MetricOutputHandler class (thread-safe singleton).
#
# AUTHORS:     Konstantin Skaburskas, CERN
#
# CREATED:     Sep 29, 2009
#
##############################################################################


"""
Base and thread-safe singleton container classes to handle metric output.
"""

__docformat__ = 'restructuredtext en'

import sys
import singleton

VERBOSITY_MIN=0
VERBOSITY_MAX=3

__all__ = ['MetricOutputHandler',
           'MetricOutputHandlerSingleton',
           'OutputHandlerSingleton',
           'VERBOSITY_MIN',
           'VERBOSITY_MAX']

class TestOutputContainer(object):
    """Container class to hold and manipulate tests' output.

    :ivar __detdata: details data (multi-line `str`)
    :type __detdata: `str`

    :ivar __summary: summary data (single-line `str`)
    :type __summary: `str`

    :ivar __to_stream: send output directly to `file`-like object?
    :type __to_stream: `bool`

    :ivar __out: output stream (`file`-like object)
    :type __out: `file`
    """
    def __init__(self, stream=False):
        """Initialise `TestOutputContainer`.

        :param stream: send output directly to a `file`-like object?
            (default: `False`)
        :type stream: `bool`
        """
        self.__detdata = ''
        "details data (multi-line `str`)"
        self.__summary = ''
        "summary data (single-line `str`)"
        self.__to_stream = stream
        "send output directly to `file`-like object? (`bool`)"
        self.__out = sys.stdout
        "output stream (`file`-like object)"

    def handle_detdata(self, dd, cr=True, prep=False):
        if self.__to_stream:
            self.__write(dd, cr)
        else:
            if prep:
                self.__prepend_data(dd, cr)
            else:
                self.__append_detdata(dd, cr)

    def handle_summary(self, s):
        if self.__to_stream:
            self.__write(s.strip('\n'))
        else:
            self.__set_summary(s)

    def set_stream(self, stream=True):
        self.__to_stream = stream

    def get_detdata(self):
        if self.__detdata:
            return self.__detdata
        else:
            return self.__summary

    def get_summary(self):
        return self.__summary

    def __write(self, dd, cr=True):
        if cr:
            self.__out.write(dd+'\n')
        else:
            self.__out.write(dd)

    def __append_detdata(self, dd, cr):
        if cr:
            self.__detdata += dd+'\n'
        else:
            self.__detdata += dd

    def __prepend_data(self, dd, cr):
        if cr:
            self.__detdata = '%s\n%s' % (dd, self.__detdata)
        else:
            self.__detdata = '%s%s' % (dd, self.__detdata)

    def __set_summary(self, s):
        self.__summary = s

    def clear_summary(self):
        self.__summary = ''

    def clear_details(self):
        self.__detdata = ''

    def clear_summary_details(self):
        self.clear_summary()
        self.clear_details()

class MetricOutputHandler(TestOutputContainer):
    """Class to handle metric output details and summary data.
    """
    def __init__(self, v=VERBOSITY_MIN, stream=False):
        """Initialise `MetricOutputHandler`.

        :Parameters:
          - `v` (`int`) - verbosity level (default: `VERBOSITY_MIN`)
          - `stream` (`bool`) - send output directly to `file`-like object?
            (default: `False`)
        """
        TestOutputContainer.__init__(self, stream=stream)

        self.verbosity = v
        "verbosity level - `int`"

    def prints(self, s):
        """Set summary. Doesn't append but overwrites previously set data.
        """
        self.handle_summary(s)

    def printd(self, dd, v=VERBOSITY_MIN, cr=True, prep=False):
        """Print details data either to `file`-like object or append to a buffer.

        :Parameters:
          - `dd` (`str`) - details data
          - `v` (`int`) - verbosity level (default: `VERBOSITY_MIN`)
          - `cr` (`bool`) - append carriage return? (default: `True`)
          - `prep` (`bool`) - prepend the string to the buffer? (default: `False`)
        """
        if self.verbosity >= v:
            self.handle_detdata(dd, cr=cr, prep=prep)

    def printdvm(self, dd, cr=True, prep=False):
        """Invoke `printd()` with highest verbosity.
        """
        self.printd(dd, v=VERBOSITY_MAX, cr=cr, prep=prep)

    def write(self, dd, cr=False):
        """Provide `file`-like interface.

        To be used with::
        print >> MetricOutputHandler_object, 'string'

        Treats input as details data.
        """
        self.printd(dd, cr=False)

class MetricOutputHandlerSingleton(MetricOutputHandler, singleton.Singleton):
    """Thread-safe singleton to handle metric output details and summary data.

    Derived from thread-safe singleton. One instance of the
    class is guaranteed.
    """
    def __init__(self, v=VERBOSITY_MIN, stream=False):
        singleton.Singleton.__init__(self)
        MetricOutputHandler.__init__(self, v=v, stream=stream)

class OutputHandlerSingleton(object):
    """A handy decorator to eliminate a necessity of explicitely requesting
    singelton's instance.
    """
    def __init__(self):
        self.__mo = MetricOutputHandlerSingleton.getInstance()

    def printd(self, dd, v=VERBOSITY_MIN, cr=True):
        """Print details data either to `file`-like object or append to a buffer.

        :Parameters:
          - `dd` (`str`) - details data
          - `v` (`int`) - verbosity level (default: `VERBOSITY_MIN`)
          - `cr` (`bool`) - append carriage return? (default: `True`)
        """
        self.__mo.printd(dd, v=v, cr=cr)

    def printdvm(self, dd, cr=True):
        """Invoke `printd()` with highest verbosity.
        """
        self.__mo.printd(dd, v=VERBOSITY_MAX, cr=cr)

    def prints(self, s):
        """Set summary. Doesn't append but overwrites previously set data.
        """
        self.__mo.prints(s)

    def write(self, dd, cr=False):
        """Provide `file`-like interface.

        To be used with::
        print >> MetricOutputHandler_object, 'string'

        Treats input as details data.
        """
        self.__mo.printd(dd, cr=False)

if __name__ == '__main__':

    mo1 = MetricOutputHandlerSingleton.getInstance(v=1)
    mo1.printd('MetricOutput data 1...')
    mo2 = MetricOutputHandlerSingleton.getInstance()
    mo2.printd('MetricOutput data 2...')
    print >> mo1, 'MetricOutput data 3...'
    mo2.verbosity = 3
    print mo1.get_detdata()
    print mo2.get_detdata()
    print mo1.verbosity
