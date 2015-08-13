##############################################################################
#
# NAME:        gridutils.py
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
#         Grid utility functions for 'gridmon' package.
#
# AUTHORS:     Konstantin Skaburskas, CERN
#
# CREATED:     28-May-2009
#
##############################################################################

"""
Grid utility functions for `gridmon` package.
"""

import os
import sys
import re
import commands

from gridmon import utils as samutils

__all__ = ['gfal_ver_ge',
           'lcg_util_ver_ge',
           'cmp_version_ge',
           'bdii_query',
           'LDAP_QE_EMPTYSET',
           'LDAP_QE_LDAP',
           'LDAP_QE_TIMEOUT',
           'LDAP_QE_OTHER',
           'norm_voname_shell',
           'get_testing_DN',
           'get_voms_fqans']

def cmp_version_ge(v, cmd, prefix):
    """Check if installed version is >= to a given one.

    @param cmd: command to use (eg. C{gfal_version})
    @type cmd: L{str}
    @param prefix: package/library name to strip off (eg. C{GFAL-client})
    @type prefix: C{str}

    @return: L{int} in range: (-3 .. 1)
      - 1 - installed version is >= of the given one
      - 0 - installed version is < than the given one
      - <0 - couldn't perform comparison
          - -1 - problem interpreting current version
          - -2 - problem interpreting given version
          - -3 - couldn't determine current version number
    @rtype: L{int}
    """
    stdout = ''
    try:
        stdout = samutils.run_cmd_data(cmd)
    except StandardError,e:
        stdout = str(e)
        if re.search('command not found',stdout):
            return -3

    if stdout:
        vcurr = stdout.split('\n')[0]
        if vcurr.startswith(prefix):
            vcurr = vcurr.replace(prefix, '')
        else:
            vcurr = '0.0.0-0'
    else:
        vcurr = '0.0.0-0'

    # compare
    rc = samutils.cmp_pkgvers(vcurr, v)
    if rc == 1 or rc == 0:
        return 1
    elif rc == 2:
        return 0
    elif rc < 0:
        return rc

def gfal_ver_ge(v, cmd='gfal_version', prefix='GFAL-client-'):
    """Checks if installed C{GFAL} version is >= to a given one.

    @return: see L{cmp_version_ge()}
    @rtype: L{int}
    """
    return cmp_version_ge(v, cmd, prefix)

def lcg_util_ver_ge(v, cmd='lcg-cr --version', prefix='lcg_util-'):
    """Checks if installed C{lcg_util} version is >= to a given one.

    @return: see L{cmp_version_ge()}
    @rtype: L{int}
    """
    return cmp_version_ge(v, cmd, prefix)

def get_lcg_util_gfal_ver():
    """Get lcg_util/GFAL versions.

    @return: C{lcg_util/GFAL} versions or error string
    @rtype: L{str}
    """
    rc, o = commands.getstatusoutput('lcg-cr --version')
    if rc != 0:
        return "Couldn't get lcg_util/GFAL versions. %s" % o
    return o

########################################
# BDII over LDAP.
########################################
"""
BDII over LDAP:
- query_bdii() - BDII query.
"""
try:
    import ldap
    LDAP_LIB = True
except ImportError:
    LDAP_LIB = False
LDAP_LIB = False

LDAP_TIMEOUT_NETWORK  = 20
LDAP_TIMELIMIT_SEARCH = 20

class ErrLDAPTimeout(Exception):
    """LDAP timeout exception.
    """

# Return codes in case of LDAP query errors
LDAP_QE_EMPTYSET = 0
LDAP_QE_LDAP     = 1
LDAP_QE_TIMEOUT  = 2
LDAP_QE_OTHER    = 7

def query_bdii(ldap_filter, ldap_attrlist, ldap_url='', ldap_base='o=grid',
               ldap_timelimit=LDAP_TIMELIMIT_SEARCH,
               net_timeout=LDAP_TIMEOUT_NETWORK):
    """Query BDII (LDAP based).

    Depending on availability uses either LDAP API or CLI.

    @param ldap_filter: non-empty filter.
    @type ldap_filter: L{str}
    @param ldap_attrlist: list of attributes to search for.
    @type ldap_attrlist: L{list}
    @param ldap_url: (default: '') if not given, C{LCG_GFAL_INFOSYS} will be used.
      ldap://<hostname|ip>:port. Comma-separated list is possible.
    @type ldap_url: L{str}
    @param ldap_timelimit: LDAP internal search time limit (default: L{LDAP_TIMELIMIT_SEARCH})
    @type ldap_timelimit: L{int}
    @param net_timeout: connection timeout (default: L{LDAP_TIMEOUT_NETWORK}).
    @type net_timeout: L{int}

    @return:
      - on success:
          - (1, [entries]) - entries : list of tuples as query results
            C{('<LDAPnameSpace>', {'<attribute>': ['<value>',..],..})}. Eg.:
              - ('GlueSALocalID=ops,...,Mds-Vo-name=local,o=grid',
                {'GlueSAStateAvailableSpace': ['197000000000']})
      - on failure:
          - (0, (N, summary, detmsg))
              - N - 0 : query returned empty set
              - N - 1 : CLI/API or LDAP problem (eg., CLI: "command not found")
              - N - 2 : timeout
    @rtype: L{tuple}
    """
    if not ldap_filter:
        msg = 'ldap_filer must be specified (%s())' % \
                        sys._getframe(1).f_code.co_name
        return 0, (LDAP_QE_OTHER, msg, msg)

    if not isinstance(ldap_attrlist, list):
        msg = 'attributes list should be a list object (%s())'  % \
                                   sys._getframe(1).f_code.co_name
        return (0, (LDAP_QE_OTHER, msg, msg))

    ldaps = ldap_url and ldap_url.split(',') or \
                              samutils.get_env('LCG_GFAL_INFOSYS').split(',')
    try:
        ldap_url = get_working_ldap(ldaps) # IP address
    except (TypeError, ValueError, LookupError), e:
        return 0, (LDAP_QE_OTHER,
                   'Failed to get working BDII from [%s].' % ','.join(ldaps), str(e))
    try:
        if LDAP_LIB:
            return __ldap_API(ldap_filter, ldap_attrlist, ldap_url,
                                 ldap_base, ldap_timelimit, net_timeout)
        else:
            return __ldap_CLI(ldap_filter, ldap_attrlist, ldap_url,
                                 ldap_base, ldap_timelimit, net_timeout)
    except Exception, e:
        return 0, (LDAP_QE_OTHER, 'Exception while querying BDII [%s]' % ldap_url,
                   str(e))

def __ldap_API(ldap_filter, ldap_attrlist, ldap_url, ldap_base, ldap_timelimit,
                                                                 net_timetout):
    """Query LDAP using API.

    For signature see L{query_bdii()}

    @raise ValueError,TypeError:
        - C{ValueError} - empty filter
        - C{TypeError}  - attributes list is not a list object
    """

    if not ldap_filter:
        # ldap module fails when filter is an empty string
        raise ValueError('ldap_filer must not be empty.')

    if not isinstance(ldap_attrlist, list):
        raise TypeError('attributes list must be a list object.')

    try:
        l = ldap.initialize(to_full_ldap_url(ldap_url))
        l.protocol_version = ldap.VERSION3
        l.network_timeout = net_timetout
        entries = l.search_st(ldap_base, ldap.SCOPE_SUBTREE,
                              ldap_filter, ldap_attrlist,
                              0, ldap_timelimit)
    except TypeError, e:
        stsmsg = detmsg = 'Error invoking LDAP search API: %s' % str(e)
        return (0, (LDAP_QE_OTHER, stsmsg, detmsg))
    except ErrLDAPTimeout:
        stsmsg = detmsg = 'LDAP search timed out after %i sec. %s' % \
                (ldap_timelimit, samutils.ldap_url2hostname_ip(ldap_url))
        return (0, (LDAP_QE_TIMEOUT, stsmsg, detmsg))
    except ldap.LDAPError, e:
        stsmsg = detmsg = 'LDAPError: %s %s' % (
                                samutils.ldap_url2hostname_ip(ldap_url),
                                e[0]['desc'])
        return (0, (LDAP_QE_LDAP, stsmsg, detmsg))

    if len(entries) == 0:
        return __return_query_failed_emtpy_set(ldap_url, ldap_attrlist,
                                               ldap_filter, ldap_base)
    return (1, entries)

def __ldap_CLI(ldap_filter, ldap_attrlist, ldap_url, ldap_base, ldap_timelimit,
                                                                 net_timetout):
    """Query LDAP using CLI.

    For signature see L{query_bdii()}
    """

    if not isinstance(ldap_attrlist, list):
        stsmsg = detmsg = 'Error invoking LDAP search CPI: attributes '+ \
                            'list should be a list.'
        return (0, (LDAP_QE_OTHER, stsmsg, detmsg))

    bdii = to_full_bdii_url(ldap_url)
# TODO: -o nettimeout seem doesn't properly work on all WNs
#    cmd = "ldapsearch -l %i -x -LLL -h %s -o nettimeout=%i -b %s '%s' %s" % \
#            (ldap_timelimit, bdii, net_timetout, ldap_base, ldap_filter,
#             ' '.join([x for x in ldap_attrlist]))
    cmd = "ldapsearch -l %i -x -LLL -h %s -b %s '%s' %s" % \
            (ldap_timelimit, bdii, ldap_base, ldap_filter,
             ' '.join([x for x in ldap_attrlist]))

    res = ''
    try:
        rc,res = commands.getstatusoutput(cmd)
    except ErrLDAPTimeout:
        stsmsg = detmsg = 'LDAP search timed out after %i sec. %s' % \
                (ldap_timelimit, bdii)
        return (0, (LDAP_QE_TIMEOUT, stsmsg, detmsg))
    except StandardError,e:
        stsmsg = '%s %s' % (str(e).strip(), bdii)
        detmsg = '%s\n%s' % (cmd, stsmsg)
        return (0, (LDAP_QE_LDAP, stsmsg, detmsg))
    else:
        rc = os.WEXITSTATUS(rc)
        if rc != 0:
            stsmsg = '%s %s %i' % (res, bdii, rc)
            detmsg = '%s\n%s' % (cmd, stsmsg)
            return (0, (LDAP_QE_LDAP, stsmsg, detmsg))

    if res:
        # remove line foldings made by ldapsearch
        res = res.replace('\n ','').strip()
        entries = []
        res = res.split('dn: ')
        # loop through values in "dn:"
        for dn in res:
            if dn:
                dl = dn.splitlines()
                # remove empty lines
                for i,v in enumerate(dl):
                    if not v:
                        del dl[i]
                # make dict key/value pairs out
                # of Glue "Attribute: Value" pairs
                d = {}
                for x in dl[1:]:
                    t = x.split(':', 1)
                    t[0] = t[0].strip()
                    t[1] = t[1].strip()
                    if d.has_key(t[0]):
                        d[t[0]].append(t[1])
                    else:
                        d[t[0]] = [t[1]]
                entries.append((dl[0], d))
        return (1, (entries))
    else:
        return __return_query_failed_emtpy_set(ldap_url, ldap_attrlist,
                                               ldap_filter, ldap_base)

def __return_query_failed_emtpy_set(ldap_url, ldap_attrlist, ldap_filter, ldap_base):
    """Formatted output on empty set returned by a query."""
    ldap_url = samutils.ldap_url2hostname_ip(ldap_url)
    stsmsg = 'No information for [attribute(s): %s] in %s.' % \
                (ldap_attrlist, ldap_url)
    detmsg = 'No information for [base: %s; filter: %s; attribute(s): %s] in %s.' % \
        (ldap_base, ldap_filter, ldap_attrlist, ldap_url)
    return (0, (LDAP_QE_EMPTYSET, stsmsg, detmsg))

def get_working_ldap(ldaps, net_timeout=LDAP_TIMEOUT_NETWORK):
    """Test given list of LDAP servers and return a first working one as IP
    address.

    Depending on availability uses either LDAP API or CLI.

    @param  ldaps: list of LDAP endpoints (ldap://<hostname>:[<port>]).
    @type ldaps: L{list}
    @param net_timeout: connection timeout (default: L{LDAP_TIMEOUT_NETWORK}).
    @type net_timeout: L{int}

    @return:
      - on success:
          - C{endpoint} - first working LDAP endpoint as IP address
    @rtype: L{str}

    @raises LookupError,TypeError,ValueError:
      - LookupError - if no working endpoints found.
      - TypeError - L{ldaps} must be a list object.
      - ValueError - list of empty endpoints or empty list is given.
    """

    if not isinstance(ldaps, list):
        raise TypeError('ldaps should be a list object.')
    l = len(ldaps)
    if l == 0:
        raise ValueError('Empty LDAP endpoints list given (%s()).' % \
                         sys._getframe(0).f_code.co_name)
    else:
        i = 0
        for v in ldaps:
            if not v:
                i += 1
        if i == l:
            raise ValueError('List of empty LDAP endpoints given (%s()).' % \
                             sys._getframe(0).f_code.co_name)
    failed_ldaps = {}
    for ldap_url in ldaps:
        proto, hostname, port = samutils.parse_uri3(ldap_url)
        try:
            ips = samutils.dns_lookup_forward(hostname)
        except IOError, e:
            # Forward DNS resolution failed. Continue with the next host.
            failed_ldaps[ldap_url] = str(e)
            continue
        else:
            for ip in ips:
                ldap_url_ip = '%s%s:%s' %(proto or '', ip, port)
                if LDAP_LIB:
                    rc, error = __ldap_bind_API(ldap_url_ip, net_timeout)
                    if rc:
                        return ldap_url_ip
                else:
                    rc, error = __ldap_bind_CLI(ldap_url_ip, net_timeout)
                    if rc:
                        return ldap_url_ip
                host_ip = samutils.ldap_url2hostname_ip(ldap_url_ip)
                failed_ldaps[host_ip] = error
    msg = ''
    for k,v in failed_ldaps.items():
        msg = '%s* %s: %s' % (msg and msg+'\n' or '', k, v)
    raise LookupError(msg)

def __ldap_bind_API(url, net_timeout, who='', cred=''):
    """Bind to LDAP using API.

    @param url: LDAP URI (ldap://<hostname>:[<port>]).
    @type url: L{str}
    @param net_timeout: network timeout
    @type net_timeout: L{int}

    @return:
      - on success: C{(1, '')}
      - on failure: C{(0, 'error message')}
    @rtype: L{tuple}
    """
    try:
        l = ldap.initialize(to_full_ldap_url(url))
        l.network_timeout = net_timeout
        l.bind(who, cred)
        l.unbind()
    except ldap.LDAPError, e:
        return 0, 'LDAPError: %s' % e[0]['desc']
    return 1, ''

def __ldap_bind_CLI(url, net_timeout):
    """Bind to LDAP using CLI.

    @param url: LDAP URI (ldap://<hostname>:[<port>]).
    @type url: L{str}
    @param net_timeout: network timeout
    @type net_timeout: L{int}

    @return:
      - on success: C{(1, '')}
      - on failure: C{(0, 'error message')}
    @rtype: L{tuple}
    """
    # TODO: move back to version with network timeout when WNs are ready.
    #cmd = 'ldapsearch -xLLL -o nettimeout=%i -h %s' % (net_timeout,
    #                                                   to_full_bdii_url(url))
    cmd = 'ldapsearch -xLLL -h %s' % (to_full_bdii_url(url))
    rc, o = commands.getstatusoutput(cmd)
    rc = os.WEXITSTATUS(rc)
    if rc not in (0, 32): # No such object (32)
        return 0, '%s , %i' % (o, rc)
    return 1, ''

def to_full_ldap_url(url, port='2170'):
    """Given LDAP url return full LDAP uri.
    Keyword argument C{port} is used if url:port wasn't found in the given url.

    @return: ldap://<url:hostname>:<url:port>.
    """
    hp = samutils.parse_uri3(url)
    if not hp[0]:
        hp[0] = 'ldap://'
    if not hp[2]:
        hp[2] = port
    return '%s%s:%s' % (hp[0], hp[1], hp[2])

def to_full_bdii_url(url, port='2170'):
    """Given url return <url:hostname>:<url:port>.

    @return: <url:hostname>:<url:port>.
    """
    hp = samutils.parse_uri(url)
    if not hp[1]:
        hp[1] = port
    return '%s:%s' % (hp[0], hp[1])

def check_x509_user_proxy():
    """Check if C{X509_USER_PROXY} is defined and we can open the file.
    If one of the conditions is not satisfied, exit with 3 (Nagios UNKNOWN)
    and print Nagios compliant summary and details message to stdout.

    @return: L{True} if C{X509_USER_PROXY} file can be opened or exit programm.
    @rtype: L{bool}
    """
    try:
        os.stat(os.environ['X509_USER_PROXY'])
        open(os.environ['X509_USER_PROXY']).close()
        return True
    except (OSError, IOError), e:
        sys.stdout.write("UNKNOWN: certificate file error: %s\n"% e)
        sys.stdout.write("UNKNOWN: certificate file error: %s\n"% e)
        sys.exit(3)


########################################
#
########################################
def norm_voname_shell(vo):
    """Normalize VO name for Shell variables.
    Translates to upper case; substitutes '.', '-' with '_'.

    @return: VO name ready to be used in Shell variables.
    @rtype: L{str}
    """
    von = vo.upper()
    repchars = ['.','-']
    for c in repchars:
        von = von.replace(c,'_')
    return von

def get_testing_DN():
    'DN of testing proxy.'
    rc, o = commands.getstatusoutput('voms-proxy-info -subject')
    if rc == 0:
        return o
    else:
        return "couldn't determine DN (%s)" % o

def get_voms_fqans():
    """List of VOMS FQANs.

    @return: VOMS FQANs.
    @rtype: L{list} of L{str}
    """
    rc, o = commands.getstatusoutput('voms-proxy-info -fqan')
    if rc == 0:
        return o.strip('\n').split('\n')
    else:
        return ["couldn't determine VOMS FQANs (%s)" % o]
