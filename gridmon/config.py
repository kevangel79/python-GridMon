##############################################################################
#
# NAME:        config.py
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
#         Parser of configuration files in a flat section-less format.
#
# AUTHORS:     Konstantin Skaburskas, CERN
#
# CREATED:     24-Feb-2009
#
##############################################################################

"""
Parser of configuration files in a flat section-less format.

KEY=value
"""

__docformat__ = 'restructuredtext en'

import re

__all__ = ['ConfigParserFlat',
           'ErrConfigParserFlat',
           'ErrConfigParserFlatNoOpt']

class ErrConfigParserFlat(StandardError):
    "Configuration parser exception."

class ErrConfigParserFlatNoOpt(KeyError):
    "Wrapper for KeyError exception."

class ConfigParserFlat(object):
    """Parser of configuration files in a flat section-less format.
    Assumes case-insensitive keys.

    :ivar attrs: configuration ``key:value`` pairs.
    :type attrs: `dict`
    """
    def __init__(self, fn=''):
        """Initialise `ConfigParserFlat`.

        :param fn: configuration file name (default: ``no name``).
        """
        self.reg = re.compile("^[a-zA-Z]", re.I)
        self.attrs = {}
        self.fn = fn
        "configuration file name."
        if fn:
            self.read(fn)

    def read(self, fn):
        """Read configuration file `fn`.
        """
        self.fn = fn
        for ln in open(fn,'r').readlines():
            if self.reg.match(ln):
                p = ln.strip().split('=')
                try:
                    self.attrs[p[0].lower()] = p[1].strip()
                except IndexError:
                    self.attrs[p[0].lower()] = ''

    def get(self, key):
        """Get value for a `key`.

        :param key: key for which a value is requested.
        :return: value for a given `key`.
        :rtype: `str`

        :raises `ErrConfigParserFlatNoOpt`:
        """
        try:
            return self.attrs[key.lower()]
        except KeyError:
            raise ErrConfigParserFlatNoOpt, \
                "No option '%s' in '%s'" % (key, self.fn)

    def list(self):
        "Print out ``key:value`` pairs loaded from the configuration file."
        for k,v in self.attrs.items():
            print k+' : '+v
