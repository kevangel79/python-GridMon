##############################################################################
#
# NAME:        template.py
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
#         Classes for templated strings substitution.
#
# AUTHORS:     Konstantin Skaburskas, CERN
#
# CREATED:     22-Mar-2010
#
##############################################################################

"""
Classes for templated strings substitution.
"""

__docformat__ = 'restructuredtext en'

import re

MAPKEY='<%s>'

class Template(object):
    """Base class for strings substitution with default mapping key `MAPKEY`.
    """
    def __init__(self, map_key=MAPKEY):
        self.map_key = map_key
        "template for mapping key."
    def substitute(self, templ, mappings):
        """Do regular expression substitution.

        :param templ: template (multi-line string)
        :type templ: `str`
        :param mappings: list of values to substitute within the template.
        :type mappings: `list`

        :return: resulting string with all substituted values.
        :rtype: `str`
        """
        _subst = templ
        for pattern,repl in mappings.items():
            _subst = re.sub(self.map_key % pattern, repl, _subst)
        return _subst

class TemplatedFile(Template):
    """Provide strings substitution from a template file to a resulting one.
    """
    def __init__(self, file_templ, file, mappings={}):
        Template.__init__(self)

        self.__file_templ = file_templ
        self.__file = file
        self.__set_mappings(mappings)
        self.__templ = ''
        self.__substitution = ''

    def __set_mappings(self, mappings):
        self._check_mappings(mappings)
        self.__mappings = mappings
    def __get_mappings(self):
        return self.__mappings
    mappings = property(__get_mappings, __set_mappings, None,
                                    "Substitution mappings.")
    def __set_template(self, _):
        pass
    def __get_template(self):
        return self.__template
    template = property(__get_template, __set_template, None,
                                                "Template.")
    def __set_file_templ(self, _):
        pass
    def __get_file_templ(self):
        return self.__file_templ
    file_templ = property(__get_file_templ, __set_file_templ, None,
                                            "Template file.")
    def __set_file(self, _):
        pass
    def __get_file(self):
        return self.__file
    file = property(__get_file, __set_file, None,
                            "File to store resulting substitution.")
    def __set_substitution(self, _):
        pass
    def __get_substitution(self):
        return self.__substitution
    substitution = property(__get_substitution, __set_substitution, None,
                                                "Resulting substitution.")

    def load(self):
        """Load template from file.

        :raise IOError: problems to open file.
        """
        try:
            self.__template = open(self.file_templ, 'r').read()
        except IOError, e:
            raise IOError('Unable to load template %s. %s' % \
                                                    (self.file_templ, str(e)))
    def subst(self):
        """Make required substitutions (using `self.substitute()`) and store
        the result in memory.
        """
        self.__substitution = self.substitute(self.template, self.mappings)

    def save(self):
        """Save substituted template to file.

        :raise IOError: problems to save data to file.
        """
        try:
            open(self.file, 'w').write(self.substitution)
        except IOError, e:
            raise IOError(
                'Unable to save %s. %s' % (self.file, str(e)))

    def _check_mappings(self, mappings):
        """Check if all mappings are initialised.

        :raise TypeError: if any of mappings not initialised.
        """
        for pattern,repl in mappings.items():
            if not repl:
                raise TypeError('Mapping <%s> not initialised.' % pattern)
