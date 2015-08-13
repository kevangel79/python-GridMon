##############################################################################
#
# NAME:        perfdata.py
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
#         Nagios compliant performance data container and handler.
#
# AUTHORS:     Konstantin Skaburskas, CERN
#
# CREATED:     May 9, 2010
#
##############################################################################

"""
Nagios compliant performance data container and handler.
"""

__docformat__ = 'restructuredtext en'

__all__ = ['PerfData',
           'value2str',
           'perfdata']

def perfdata(order):
    """Factory producing instance of `PerfData`.

    :param order: `list` or `tuple` of strings, representing order of
      elements in performance data.
    :type order: `list` or `tuple`

    :returns: instance of `PerfData`.
    :rtype: `PerfData`
    """
    return PerfData(order)

def value2str(d):
    """Translate performance data values into Nagios compliant
    string representation.

    :returns: Nagios compliant string representation of performance data.
    :rtype: `str`

    :raises `TypeError`: only ``int, long, float, str, list, tuple`` are allowed.
    """
    if type(d) in [int, long, float, str]:
        s = '%s;;' % str(d)
    elif type(d) in [list, tuple]:
        s = ';'.join([ str(i) for i in d ])
    else:
        raise TypeError('Expected int, long, float, str, '+\
                    'list, tuple as performance data, '+\
                    'got %s.' % type(d))
    return s

class PerfData(object):
    """Represents Nagios performance data as a set of ordered key-value pairs in
    a predefined format.
    """
    __perf_data = ''
    __pd = {}
    empty = '0;;'
    "zero value for performance data."

    def __init__(self, order):
        """Initialise `PerfData`.

        :param order: `list` or `tuple` of strings, representing order of
          elements in performance data.
        :type order: `list` or `tuple`
        :raises `TypeError`: if `order` neither `list` or `tuple`.
        """
        if type(order) in [list, tuple]:
            self.__order = order
            self.update({})
        else:
            raise TypeError('Order should be list or tuple. %s given.' % \
                            type(order))
    def set(self, data):
        """Set performance data as string.

        :param data: performance data as string.
        :type data: `str`
        :raises `TypeError`: if non `str` is given.
        """
        if isinstance(data, str):
            self.__perf_data = data
        else:
            raise TypeError('Expected str, got %s' % type(data))
    def update(self, data):
        """Update performance data. Order the data by the order defined at
        the object initialisation.

        :param data: performance data as key-value pairs
        :type data: `dict`
        :raises `TypeError`: `data` should be `dict`
        """
        if isinstance(data, dict):
            self.__pd.update(data)
            pd = []
            for o in self.__order:
                s = self.empty
                try:
                    d = data[o]
                except KeyError:
                    pass
                else:
                    s = self.value2str(d)
                pd.append('%s=%s' % (o, s))
            self.__perf_data = ' '.join(pd)
        else:
            raise TypeError('Expected dict, got %s' % type(data))
    def value2str(self, d):
        """Translate performance data values into Nagios compliant
        string representation. See `perfdata.value2str()`.

        :returns: Nagios compliant string repr of performance data.
        :rtype: `str`

        :raises `TypeError`: only ``int, long, float, str, list, tuple`` are allowed.
        """
        return value2str(d)
# TODO: put this "sugar" back when Python 2.4 becomes available on all WNs
#    @staticmethod
#    def value2str(d):
#        """Translate performance data values into Nagios compliant
#        string representation.
#        """
#        if type(d) in [int, long, float, str]:
#            s = '%s;;' % str(d)
#        elif type(d) in [list, tuple]:
#            s = ';'.join([ str(i) for i in d ])
#        else:
#            raise TypeError('Expected int, long, float, str, '+\
#                        'list, tuple as performance data, '+\
#                        'got %s.' % type(d))
#        return s
    def get(self):
        """Get generated performance data.

        :return: Nagios performance data as string (no "new line")
        :rtype: `str`
        """
        return self.__perf_data.lstrip().rstrip()
