##############################################################################
#
# NAME:        utils.py
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
#         Utility functions for 'gridmon' package.
#
# AUTHORS:     Konstantin Skaburskas, CERN
#
# CREATED:     24-Feb-2009
#
##############################################################################

"""
Utility functions for `gridmon` package.
"""

__docformat__ = 'restructuredtext en'

import os
import re
import commands
from random import choice
import popen2
import time
import sys
import socket
import getopt

__all__ = ['time_now',
           'parse_uri',
           'parse_uri2',
           'parse_uri3',
           'uuidgen',
           'uuidstr',
           'run_cmd_data',
           'cmp_pkgvers',
           'get_env',
           'to_status',
           'to_retcode',
           'do_longs',
           'getops_flexlongs',
           'get_launchdir',
           'arch_zip',
           'arch_unzip',
           'dns_lookup_forward',
           'dns_lookup_reverse',
           'ldap_url2hostname_ip'
           ]

retCodes = {'OK': 0, 'WARNING' : 1, 'CRITICAL' : 2, 'UNKNOWN' : 3}

def time_now(ms=False):
    """Time in iso8601 format (%Y-%m-%dT%H:%M:%SZ).

    :param ms: output time down to milliseconds? (default: `False`)
    :type ms: bool

    :return: Time in iso8601 format (%Y-%m-%dT%H:%M:%SZ).
    :rtype: `str`
    """
    if not ms:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ",
                             time.gmtime(time.time()))
    try:
        from datetime import datetime
        return '%sZ' % datetime.utcnow().isoformat()
    except ImportError:
        from xml.utils.iso8601 import tostring as toiso8601
        return toiso8601(time.time())

def parse_uri(uri):
    """Return [host, port] from given URI.

    :param uri: one of:
      ``proto://host/``,
      ``proto://host:port/``,
      ``proto://host``,
      ``proto://host:port``,
      ``host``,
      ``host:port``;
      where ``proto`` can be ``[a-zA-Z0-9\_]*``. Eg.: ``srm_v1``.
    :type uri: `str`
    :return: [host, port]
    :rtype: `list`
    """
    match = re.match('([a-zA-Z0-9_]*://)?([^/:$]*):?(\d+)?/?', uri)
    return [match.group(2), match.group(3)]
parse_uri2 = parse_uri
"alias to `parse_uri()`; two-element list [host, port] is returned."

def parse_uri3(uri):
    """Return [proto, host, port] from given URI.

    :param uri: see `parse_uri()`
    :return: [proto, host, port]
    :rtype: `list`
    """
    m = re.match('([a-zA-Z0-9_]*://)?([^/:$]*):?(\d+)?/?', uri)
    return [m.group(1), m.group(2), m.group(3)]

def unlink(fn, ignore=True):
    """Unlink file. By default, ignore any problems.

    :param fn: file name
    :type fn: `str`
    :param ignore: ignore problems? (default: `True`)
    :type ignore: `bool`
    :raise `StandardError`: if `ignore` is `False`, raise the exception on any
       problem unlinking file.
    """
    try:
        os.unlink(fn)
    except StandardError, e:
        if ignore:
            pass
        else:
            raise e

def uuidgen():
    """Generate UUID with unix uuidgen.

    :return: UUID
    :rtype: `str`
    """
    return commands.getoutput('uuidgen')

def uuidstr(len=12, chars='0123456789abcdef'):
    """Pseudo-random string of a given length based on a set of chars.

    :param len: length of string to be generated
    :type len: `int`
    :param chars: alphabet to generate from
    :type chars: `str`
    :return: `str`
    """
    # Python >=2.5 :(
    # import uuid
    # return uuid.uuid4().split('-')[4]

    #from random import Random
    #return ''.join(Random().sample(chars, len))

    # seems like this works faster
    return ''.join([choice(chars) for i in range(len)])

def run_cmd_data(cmd, data=''):
    """Block-buffered fork. Catches stdout and stderr from the child.
    stdout and stderr are not merged. On success stdout is returned.
    On failure - exception is raised with stderr.

    Similar to running "echo data | cmd" or "cmd <<< data".

    :Parameters:
      - `cmd` (`str`) command to run
      - `data` (`str`) data to be fed to the command from stdin

    :raise `StandardError`: on any errors in running the given command

    :return: (multi-line) output of the run command
    :rtype: `str`
    """
    p = popen2.Popen3(cmd, 1)
    p.tochild.write(data)
    p.tochild.close()
    tmp = p.fromchild.readlines()
    p.fromchild.close()
    err = p.childerr.readlines()
    p.childerr.close()
    status = p.poll()
    while status < 0:
        p.wait()
        status = p.poll()
    rc = os.WEXITSTATUS(status)
    if rc > 0:
        if err:
            raise StandardError("".join(err))
    return ''.join(tmp)

def cmp_pkgvers(a, b):
    """Compare versions of two packages A and B.

    Version cat be eg.: ``1.56.7test-3alpha``

    :Parameters:
      - `a` (`str`) package A version
      - `b` (`str`) package B version

    :return:
      - 0: A and B are the same version
      - 1: A is newer than B
      - 2: B is newer than A
      - -1: couldn't convert A's version to `int`
      - -2: couldn't convert B's version to `int`
    :rtype: `int`
    """
    # remove ASCII chars and '_'; substitute . and - with ' '
    # make list object
    a = re.sub(r'\.|-',' ',re.sub(r'[a-zA-Z_]','',a)).split()
    b = re.sub(r'\.|-',' ',re.sub(r'[a-zA-Z_]','',b)).split()

    # equalize lengths of the version numbers
    # pad with zeros
    la = len(a)
    lb = len(b)
    if la > lb:
        b.extend([0]*(la-lb))
    elif lb > la:
        a.extend([0]*(lb-la))

    # convert to numbers removing probable non numerics
    for i in range(len(a)):
        try:
            a[i] = int(a[i])
        except ValueError:
            return -1
        try:
            b[i] = int(b[i])
        except ValueError:
            return -2

    for i in range(len(a)):
        if a[i] > b[i]:
            return 1
        elif b[i] > a[i]:
            return 2
    return 0

def get_env(ev, status='CRITICAL'):
    """Return a value of environment variable or exit
    gracefully in Nagios compliant way.

    :Parameters:
      - `ev` (`str`) name of environment variable
      - `status` (`str`) Nagios compliant return status (default: CRITICAL)
    :return: value of environment variable
    :rtype: `str`
    """
    try:
        return os.environ[ev]
    except KeyError:
        stsmsg = detmsg = '%s: %s is not defined on %s.' % \
            (status, ev, socket.gethostname())
        sys.stdout.write(stsmsg+'\n')
        sys.stdout.write(detmsg+'\n')
        sys.exit(to_retcode(status))

def to_status(code):
    """Map given return code to Nagios status (eg: 0 -> OK).

    :param code: return code to map status
    :type code: `int` or `str`
    :return: Nagios status
    :rtype: `str`
    """
    if code in (0, 'OK', 'ok', 'Ok'):
        return 'OK'
    elif code in (1, 'WARNING', 'warning', 'Warning'):
        return 'WARNING'
    elif code in (2, 'CRITICAL', 'critical', 'Critical'):
        return 'CRITICAL'
    else:
        return 'UNKNOWN'

def to_retcode(status):
    """Map given Nagios status to a return code (eg: OK -> 0).

    :param status: status to be maped to return code
    :return: Nagios return code
    :rtype: `int`
    """
    if status in (0, 'OK', 'ok', 'Ok'):
        return 0
    elif status in (1, 'WARNING', 'warning', 'Warning'):
        return 1
    elif status in (2, 'CRITICAL', 'critical', 'Critical'):
        return 2
    else:
        return 3

def outputsanitiser(str):
    """Apply string substitutions to make our schedulers happy.

    :param str: string to sanitise
    :return: sanitised string
    :rtype: `str`
    """
    patterns = {
                # Nagios treats data after pipes as performance data
                '\|\||\|' : 'OR'
                }
    for p,s in patterns.items():
        str = re.sub(p, s, str)
    return str

def do_longs(opts, opt, longopts, args):
    """Modified version of `getopt.do_longs()` which doesn't bail out if
    a long option is not in the list of command line arguments.

    :Parameters:
      - `opts` (`list`) list of tuples (long option, value)
      - `opt` (`str`) option to check
      - `longopts` (`list`) defined long options
      - `args` (`str`) list of provided arguments

    :return: (opts, args) `opts` tuple (long option, value) and arguments
    :rtype: `tuple`
    :raise `getopt.GetoptError`: problem with arguments to an option
    """
    try:
        i = opt.index('=')
    except ValueError:
        optarg = None
    else:
        opt, optarg = opt[:i], opt[i+1:]

    # has_arg, opt = getopt.long_has_args(opt, longopts)

    # catch 'not recognized' exception and add some logic
    # ============
    try:
        opt_save = opt
        has_arg, opt = getopt.long_has_args(opt, longopts)
    except getopt.GetoptError, e:
        if 'not recognized' in str(e):
            if args and not args[0].startswith('-'):
                has_arg = True
                opt = opt_save
            else:
                opts.append(('--' + opt_save, ''))
                return opts, args
        else:
            raise getopt.GetoptError(e.msg, e.opt)
    # ============

    if has_arg:
        if optarg is None:
            if not args:
                raise getopt.GetoptError('option --%s requires argument' % opt, opt)
            optarg, args = args[0], args[1:]
    elif optarg:
        raise getopt.GetoptError('option --%s must not have an argument' % opt, opt)
    opts.append(('--' + opt, optarg or ''))
    return opts, args

def getops_flexlongs(argv, shortopts, longopts):
    """Given command line arguments - return options list
    parsed by getopt.getopt() with modified version of getopt.do_longs()
    that allows to pass in unrecognised command line arguments.

    Hack to allow undefined long options to pass through.
    Then it's up the caller to pass the arguments to a
    normal getopt.getopt() for proper parsing.

    - re-define getopt.do_longs()
    - save reference to the initial function
    - substitute the function of 'getopt' module with ours
    - do arguments parsing
    - assign back the initial function

    :Parameters:
      - `argv` (`str`) list of command line arguments
      - `shortopts` (`str`) short options
      - `longopts` (`list`) long options

    :return: (opts, args) `opts` tuple (long option, value) and arguments
    :rtype: `tuple`
    """
    _do_longs = getopt.__dict__['do_longs']
    getopt.__dict__['do_longs'] = do_longs

    opts, args = getopt.getopt(argv,
                              shortopts,
                              longopts)

    getopt.__dict__['do_longs'] = _do_longs
    return (opts, args)

def get_launchdir(path=None):
    """Return normalised working directory of sys.argv[0] or of a given path.

    :rtype: `str`
    """
    return os.path.normpath(
                os.path.dirname(
                    os.path.abspath(
                        path or sys.argv[0])))

def exit_trace(status, msg):
    """Exit programm with stack trace.

    :Parameters:
      - `status` (`str` or `int`) Nagios compliant status
      - `msg` (`str`) message to exit with
    """
    import traceback
    exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
    stsmsg = detmsg = '%s: %s\n' % (status, msg)
    sys.stdout.write(stsmsg)
    sys.stdout.write(detmsg)
    traceback.print_exception(exceptionType, exceptionValue, exceptionTraceback,
                              file=sys.stdout)
    sys.stdout.write('\nReport to: https://tomtools.cern.ch/jira/\n')
    sys.exit(to_retcode(status))

def arch_zip(path, filelist, exclude=[]):
    """Create zipped tarball using system tar utility.
    Uses `run_cmd_data()`.

    :Parameters:
      - `path` (`str`) path to tar
      - `filelist` (`list`) list of files to tar
      - `exclude` (`list`) files to exclude (patterns possible)
    """
    excl = ''
    if exclude:
        for e in exclude:
            excl += '--exclude %s ' % e
    run_cmd_data('tar -zcf %s %s %s' % (path, excl, ' '.join(filelist)), '')

def arch_unzip(path, directory='.'):
    """Extract from zipped tarball using system tar utility.
    Uses `run_cmd_data()`.

    :Parameters:
      - `path` (`str`) path to tarball
      - `directory` (`str`) path to untar to
    """
    path = os.path.abspath(path)
    directory = os.path.abspath(directory)
    run_cmd_data('cd %s && tar -zxf %s' % (directory, path), '')

def dns_lookup_forward(hostname):
    """Forward DNS lookup.

    :param hostname: hostname
    :type hostname: `str`
    :return: list of IPs as strings
    :rtype: `list`
    :raises ValueError,IOError:
      - ValueError - on empty hostname
      - IOError - on any IP address resolution errors
    """
    if not hostname:
        raise ValueError('Empty hostname provided.')
    try:
        _, _, ips = socket.gethostbyname_ex(hostname)
    except (socket.gaierror, socket.herror), e:
        raise IOError(str(e))
    return ips

def dns_lookup_reverse(ip):
    """Reverse DNS lookup.

    :param ip: valid IP as string
    :type ip: `str`
    :return: hostname
    :rtype: `str`
    :raises ValueError,IOError:
      - ValueError - not valid IP address given
      - IOError - on any hostname resolution errors
    """
    try:
        socket.inet_aton(ip)
    except socket.error:
        raise ValueError('Not valid IP address given: %r' % ip)
    try:
        hostname, _, _ = socket.gethostbyaddr(ip)
    except (socket.gaierror, socket.herror), e:
        raise IOError(str(e))
    return hostname

def ldap_url2hostname_ip(ldap_url):
    """Given LDAP URL, return
      - [ldap://hostname:port [ip]] - if ldap_url based on IP address
      - [ldap://hostname:port] - in other cases

    :rtype: `str`
    """
    host, port = parse_uri2(ldap_url)
    try:
        socket.inet_aton(host)
        hostname = dns_lookup_reverse(host)
    except (socket.error, IOError):
        return '[ldap://%s%s]' % (host, port and ':'+port or '')
    else:
        return '[ldap://%s%s [%s]]' % (hostname, port and ':'+port or '',
                                       host)
