##############################################################################
#
# NAME:        nagios.py
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
#         - Nagios passive checks publisher via NSCA and Nagios command file.
#
# AUTHORS:     Konstantin Skaburskas, CERN
#
# CREATED:     24-Feb-2009
#
##############################################################################

"""
- Nagios passive checks publisher. Supports publication via
  NSCA and Nagios command file. It is configured from ``/etc/nagios-submit.conf``.
  `publishPassiveResult()` function should be used.
"""

__docformat__ = 'restructuredtext en'

import os
import time

from gridmon.utils import run_cmd_data
from gridmon.config import ConfigParserFlat, ErrConfigParserFlatNoOpt, ErrConfigParserFlat


PASSIVE_MODE_FILE = '/etc/nagios-submit.conf'

# defaults assumed in PASSIVE_MODE_FILE
SUBMIT_METHOD = 'nagioscmd'
NAGIOSCMD   = '/var/nagios/rw/nagios.cmd'
NSCA_BIN    = '/usr/sbin/send_nsca'
NSCA_CONFIG = '/etc/nagios/send_nsca.cfg'
NSCA_PORT   = '5667'

DELIM = ';'
"delimiter between command parts for results inteded for Nagios command file."

__all__ = ['ErrNagiosLib',
           'publishPassiveResult',
           'publishPassiveResultNSCA',
           'publishPassiveResultNAGCMD']

class ErrNagiosLib(StandardError):
    "Nagios library exception."
    args = 'Nagios submit passive check. '
    def __init__(self, msg):
        self.args += msg

def __getPassiveResultString(attrs, delim=';'):
    """Produce formated results strings ready to be fed to Nagios.

    :param attrs: list of dictionaries with keys:
            ``host, service, status, summary, details``
    :type attrs: `list`
    :param delim: delimiter for the fields in the results

    :return: `list` of strings of the form:
            ``host<delim>service<delim>status<delim>summary+details``
    :rtype: `list`

    :raises `ErrNagiosLib`: on missing attributes.
    """

    res = []
    for a in attrs:
        ln = '%s<d>%s<d>%s<d>%s'.replace('<d>',delim)
        try:
            res.append(ln % (a['host'],
                       a['service'],
                       a['status'],
                       a['summary']+'\\n' +\
                       a['details'].replace('\n','\\n')))
        except KeyError, e:
            raise ErrNagiosLib, \
                'Missing attribute: %s'%str(e)
    return res

def publishPassiveResultNSCA(bin, conf, host, port, reslist, delim=';'):
    """Form and run NSCA command to publish passive results.

    :Parameters:
      - `bin`  NSCA binary (full path)
      - `conf` NSCA configuration file
      - `host` NSCA server
      - `port` (`str`) NSCA port
      - `reslist` (`list`) list of results. Elements can be strings or
        dictionaries. In case of dictionaries `__getPassiveResultString()` is
        used to flatten the `dict` to get proper the result representing string.
      - `delim` delimiter for the fields in the results string

    :raises `ErrNagiosLib`: on a problem invoking NSCA client.
    """

    if isinstance(reslist[0], dict):
        reslist = __getPassiveResultString(reslist, delim=delim)

    cmd = '%s -c %s -H %s -p %s -d "%s"' % (bin,
                        conf, host, port, delim)
    for r in reslist:
        try:
            run_cmd_data(cmd, r+'\n')
        except Exception, e:
            raise ErrNagiosLib, \
                'Problem invoking NSCA client. %s' % str(e)

def publishPassiveResultNAGCMD(nagcmd, reslist):
    """Publish passive results to Nagios command file.

    :Parameters:
      - `nagcmd` file to write results to
      - `reslist` (`list`) list of results. Elements can be strings or
        dictionaries. In case of dictionaries `__getPassiveResultString()` is
        used to flatten the `dict` to get proper the result representing string.

    :raises `ErrNagiosLib`: on failure opening Nagios command file.
    """

    if isinstance(reslist[0], dict):
        reslist = __getPassiveResultString(reslist, delim=DELIM)

    try:
        os.stat(nagcmd)
        fn = open(nagcmd,'w')
    except (OSError, IOError), e:
        raise ErrNagiosLib, \
            'Failed opening Nagios command file %s. %s' % (nagcmd,
                                                           str(e))

    timenow = str(int(time.time()))
    for r in reslist:
        fn.write('[%s] PROCESS_SERVICE_CHECK_RESULT;%s\n' % (timenow, r))
        fn.flush()
    fn.close()

def publishPassiveResult(attrs, modefile=PASSIVE_MODE_FILE):
    """Publish passive test results to Nagios: NSCA or Nagios
    command file are possible. Method and parameters are taken
    from configuration file.

    :Parameters:
      - `attrs` (`list`) list of dictionaries with keys:
        ``host, service, status, summary, details``
      - `modefile` configuration file that defines passive checks
        publication mode

    :raises `ErrNagiosLib`:
      - on failure opening or parsing configuration file
      - on unknown passive checks publication mechanism specified
    """

    # return if no data to publish were given
    if not attrs:
        return False

    if not isinstance(attrs, list):
        raise ErrNagiosLib, "'attrs' must be a list of hashes."

    reslist = __getPassiveResultString(attrs, delim=DELIM)

    nc = ConfigParserFlat()
    try:
        nc.read(modefile)
    except IOError, e:
        raise ErrNagiosLib, \
            'Failed opening configuration file %s. %s' % (modefile, str(e))

    try:
        try:
            method = nc.get('SUBMIT_METHOD')
        except ErrConfigParserFlatNoOpt:
            method = SUBMIT_METHOD
        if method == 'nagioscmd':
            try:
                nagcmd = nc.get('NAGIOSCMD')
            except ErrConfigParserFlatNoOpt:
                nagcmd = NAGIOSCMD
            publishPassiveResultNAGCMD(nagcmd, reslist)
        elif method == 'nsca':
            nsca_host = nc.get('NSCA_HOST')
            try:
                nsca_bin  = nc.get('NSCA_BIN')
            except ErrConfigParserFlatNoOpt:
                nsca_bin = NSCA_BIN
            try:
                nsca_conf = nc.get('NSCA_CONFIG')
            except ErrConfigParserFlatNoOpt:
                nsca_conf = NSCA_CONFIG
            try:
                nsca_port = nc.get('NSCA_PORT')
            except ErrConfigParserFlatNoOpt:
                nsca_port = NSCA_PORT
            publishPassiveResultNSCA(nsca_bin, nsca_conf, nsca_host,
                                 nsca_port, reslist, delim=DELIM)
        else:
            raise ErrNagiosLib, 'Unknown mechanism defined in %s: %s. %s' % \
                    (modefile, method, ' Valid options are: nsca, nagioscmd.')
    except (ErrConfigParserFlat, ErrConfigParserFlatNoOpt), e:
        raise ErrNagiosLib, \
                'Problem parsing configuration file. %s ' % str(e)
