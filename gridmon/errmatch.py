##############################################################################
#
# NAME:        errmatch.py
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
#         Module provides ErrorsMatching class to work with gLite m/w CLI and
#         API errors collection DB.
#
# AUTHORS:     Konstantin Skaburskas, CERN
#
# CREATED:     23-Feb-2009
#
##############################################################################

"""
Provides `ErrorsMatching` class to work with gLite m/w CLI&API errors DB.
"""

__docformat__ = 'restructuredtext en'

import ConfigParser
import re

__all__ = ['ErrorsMatching',
           'ErrErrorsMatchingDictIntegrity']

class ErrErrorsMatchingDictIntegrity(Exception):
    def __init__(self, expression, message):
        self.expression = expression
        self.message = message

class ErrorsMatching:
    """Class to match errors coming from CLI/API against Errors DB.

    Structure of Errors DB is based on format defined by Python's
    ConfigParser module.

    Naming
      - <topic> is a string, eg.: lcg_util, wms, creamce
      - <optName> is a string, eg.: server, client, network
      - <optName_status> can take one of the following values: UNKNOWN, CRITICAL,
        WARNING

    Rules
      - empty <topic> sections are allowed. They will be discarded.
      - empty <optName> options are allowed. They will be discarded along
        with corresponding <optName_status> options
      - if <optName_status> is empty - CRITICAL will be assigned by default

    Definitions in file
      - multiple values of <optName> options must be
          - placed on separate lines with one blank character indentation
          - lines should end with "|"

    Example structure of Errors DB file::

        [topic1]
        optName1_status = <WARNING|CRITICAL|UNKNOWN>
        optName1:
         this is the first error|
         this is the second error|
         this is the third one

        optName2_status = <WARNING|CRITICAL|UNKNOWN>
        optName2:
        # no errors defined (comment)

        [topic2]
        optName1_status = <WARNING|CRITICAL|UNKNOWN>
        optName1:
         one error only

        [topic3]
        client:
        server:
         only one error msg


    :cvar _errdict: hash of hashes holding representation of Errors DB.
    :type _errdict: `dict`


    Structure of `self._errdict` dictionary::

        {'s1' : {
                 'o1'       : 'e1|e2|..|eN',
                 'o1_status': '<WARNING|CRITICAL|UNKNOWN>',
                 'o2'       : 'e1|e2|..|eN',
                 'o2_status': '<WARNING|CRITICAL|UNKNOWN>',
                 ...
                },
         's2' : {
                 'o1'       : 'e1|e2|..|eN',
                 'o1_status': '',
                 ...
                }
        }

    Construction of `self._errdict`:
      - Only the ones with <optName> & <optName>_status are considered to be
        valid key-value pairs.
      - If a value for <optName> is an empty string the <optName> &
        <optName>_status pair is deleted from the topic.
      - If a value for <optName>_status is missing 'CRITICAL' will be assigned.
      - If <optName>_status is missing but <optName> is present - creates
        <optName>_status and assigns 'CRITICAL' to it.
      - If a topic is an empty dictionary it will be removed from self._errdict.
    """


    _errdict = {}

    _statpattern = '_status'
    _defaultstatus = 'CRITICAL'
    _errtopics = []

    def __init__(self, errdb, errtopics=[]):
        """Initialize `ErrorsMatching` object.

          - load configuration file with Errors DB and initialize dictionary
            representation of the Errors DB
          - check integrity of the built dictionary
          - compile regular expressions

        :param errdb: name of Errors DB file.
        :type errdb: `str`
        :param errtopics: topics for which errors should be read and compiled.
        :type errtopics: list of `str`
        """

        self._errtopics = errtopics
        self._load_errors(errdb)
        self._re_compile()

    def _load_errors(self, errdb):
        """Load configuration file representing Errors DB.
        Build dictionary representation of the Errors DB.
        Check the integrity of the built dictionary object."""

        errors = ConfigParser.ConfigParser()

        errors.read(errdb)

        if not self._errtopics:
            # load full errors DB file
            self._errtopics = errors.sections()

        # create dictionary skeleton out of the sections and options
        # defined in the configuration file
        self._errdict = dict.fromkeys(self._errtopics, {})
        for sec in self._errdict.keys():
            self._errdict[sec] = dict.fromkeys(errors.options(sec), '')

        # load whole configuration file
        for sec in self._errdict.keys():
            for opt in self._errdict[sec].keys():
                self._errdict[sec][opt] = errors.get(sec, opt).replace('\n','')

        # delete empty options, so, that they are not taken into account in
        # the successive string matching
        for sec in self._errdict.keys():
            for opt in self._errdict[sec].keys():
                if not opt.endswith(self._statpattern) and len(self._errdict[sec][opt]) == 0:
                    del self._errdict[sec][opt]
                    try:
                        del self._errdict[sec][opt+self._statpattern]
                    except KeyError: pass

        # get rid of empty topics
        for k,v in self._errdict.items():
            if len(v) == 0:
                del self._errdict[k]

        # - assign self._defaultstatus to empty <optName>_status options
        # - if doesn't exist create <optName>_status corresponding to <optName> and
        #   assign self._defaultstatus to it
        for sec in self._errdict.keys():
            for opt in self._errdict[sec].keys():
                if opt.endswith(self._statpattern) and len(self._errdict[sec][opt]) == 0:
                    self._errdict[sec][opt] = self._defaultstatus
                    continue
                if not opt.endswith(self._statpattern):
                    if not self._errdict[sec].has_key(opt+self._statpattern):
                        self._errdict[sec][opt+self._statpattern] = self._defaultstatus

        try:
            self._check_errDictIntegrity()
        except ErrErrorsMatchingDictIntegrity, e:
            pass
            #print e.message

    def _check_errDictIntegrity(self):
        """Check the integrity of the built dictionary object.

        :return: `True` if integrity is OK.
        :rtype: `bool`

        :raise `ErrErrorsMatchingDictIntegrity`: if integrity check failed.
        """
        for sec in self._errdict.keys():
            for key in self._errdict[sec].keys():
                if key.endswith(self._statpattern):
                    if not self._errdict[sec].has_key(key.replace(self._statpattern,'')):
                        raise ErrErrorsMatchingDictIntegrity(self._errdict[sec].has_key(key.replace(self._statpattern,'')), \
                                                    'ERROR: integrity check did not pass!')
        return True

    def _re_compile(self):
        """Compile regular expressions."""

        for topic in self._errdict.keys():
            for opt in self._errdict[topic].keys():
                if not opt.endswith(self._statpattern):
                    self._errdict[topic][opt] = \
                        re.compile(".*("+self._errdict[topic][opt]+").*", re.I)

    def match(self, mstr, matchall=False):
        """Match regular expression against a given (multi-line) string

        :param mstr: (multi-line) string to find a matching pattern in.
        :type mstr: `str`
        :param matchall: traverse all Errors DB? (default: `False` (return first match))
        :type matchall: `bool`

        :return:
           - if `matchall` is `False`, only the first match is returned
             ``[(topic, option, status)]``
           - otherwise, list of tuples ``[(topic, option, status),...]``
        :rtype: `list` of `tuple`
        """
        ret = []
        for topic in self._errdict.keys():
            for opt in self._errdict[topic].keys():
                if not opt.endswith(self._statpattern):
                    if self._errdict[topic][opt].match(mstr.replace('\n',' ')):
                        if not matchall:
                            return [(topic, opt, self._errdict[topic][opt+self._statpattern])]
                        else:
                            ret.append((topic, opt, self._errdict[topic][opt+self._statpattern]))
        return ret
