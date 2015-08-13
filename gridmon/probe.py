##############################################################################
#
# NAME:        probe.py
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
#         A reasonably generic probe framework.
#
# AUTHORS:     James Casey, CERN
#              Konstantin Skaburskas, CERN
#
# CREATED:     16-Jan-2009
#
##############################################################################

"""
A reasonably generic probe framework.
"""

MODULE_VERSION = '1.0'

import os
import sys
import getopt
import time
import re

import signal

from gridmon.process import popenpgrp, signaling, pexpectpgrp
from gridmon.nagios import nagios
from gridmon.nagios import perfdata
from gridmon.errmatch import *
from gridmon import utils as samutils
from gridmon import gridutils
from gridmon.metricoutput import MetricOutputHandlerSingleton, \
                                    VERBOSITY_MIN, \
                                    VERBOSITY_MAX

__all__ = ['MetricGatherer',
           'Runner',
           'ProbeFormatRenderer',
           'ErrProbe',
           #'to_status',
           'to_retcode'
           ]

#
# Exceptions
#
class ErrProbe(Exception):
    """ """
    def __init__(self, expression, message):
        self.expression = expression
        self.message = message

class ErrProbeMetricOutputTypeError(TypeError):
    """ """

#
# Classes
#
class ProbeFormatRenderer(object):
    """A class to abstract out the rendering of the test results.

    @ivar output: output stream where the test results should be rendered
    @type output: file-like object

    @ivar sanitize: sanitize output using L{gridmon.utils.outputsanitiser()}
    @type sanitize: boolean
    """

    def __init__(self, stream=sys.stdout, sanitize=True):
        """Initialize the renderer.

        @keyword stream: output stream where the test results should be rendered.
        @type stream: C{file-like object}

        @kwarg sanitize: sanitize output using L{gridmon.utils.outputsanitiser()}
        @type sanitize: C{boolean}
        """
        self.output = stream
        self.sanitize = sanitize

    def render(self, data={}, sanitize=True):
        """Render Nagios compliant output from a given data to L{self.output}
        stream.

        @param data: expected keys C{metricStatus}, C{summaryData}, C{detailsData},
            C{perfData}. Mandatory: C{metricStatus} and C{summaryData}.
        @type data: C{dict}

        @param sanitize: sanitize output using L{gridmon.utils.outputsanitiser}
        @type sanitize: C{boolean}
        """
        saveout = sys.stdout
        sys.stdout = self.output

        if not data:
            print "UNKNOWN: No results given to render."
            sys.stdout = saveout
            return 3
        for key in ['metricStatus', 'summaryData']:
            if not data.has_key(key):
                print "UNKNOWN: %s not given to renderer." % key
                sys.stdout = saveout
                return 3

        for k in ['summaryData', 'detailsData']:
            try:
                if data[k].endswith('\n'):
                    data[k] = data[k].rstrip('\n')
            except KeyError:
                pass

        if not self.sanitize or not sanitize:
            if data.has_key('perfData') and data['perfData']:
                if data.has_key('detailsData'):
                    print data['summaryData']
                    print '%s|%s' % (data['detailsData'], data['perfData'])
                else:
                    print '%s|%s' % (data['summaryData'], data['perfData'])
            else:
                print data['summaryData']
                if data.has_key('detailsData'):
                    print data['detailsData']
        else:
            if data.has_key('perfData') and data['perfData']:
                if data.has_key('detailsData'):
                    print samutils.outputsanitiser(data['summaryData'])
                    print '%s|%s' % (
                            samutils.outputsanitiser(data['detailsData']),
                            data['perfData'])
                else:
                    print '%s|%s' % (
                            samutils.outputsanitiser(data['summaryData']),
                            data['perfData'])
            else:
                print samutils.outputsanitiser(data['summaryData'])
                if data.has_key('detailsData'):
                    print samutils.outputsanitiser(data['detailsData'])

        sys.stdout = saveout

        if samutils.to_status(data['metricStatus']).upper()   == 'UNKNOWN':
            return 3
        elif samutils.to_status(data['metricStatus']).upper() == 'CRITICAL':
            return 2
        elif samutils.to_status(data['metricStatus']).upper() == 'WARNING':
            return 1
        return 0

    def renderDesc(self, data={}):
        """Render metrics' description to L{self.output} stream.

        @param data: dictionary with keys presenting descriptive meta-data about
            metrics.
        @type data: dict
        """
        saveout = sys.stdout
        sys.stdout = self.output

        for attr,value in data.items():
            if attr != 'detailsData':
                print "%s: %s"%(attr, value)
        print "EOT"

        sys.stdout = saveout


class MetricGatherer(object):
    """A Base class for Metrics.  All methods starting with 'metric'
    are considered metrics with the signature:
    (C{RETVAL}, C{STATUSDATA}, C{DETAILSDATA}) = metricFoo()


    L{metrics} dictionary
    =====================
    Dictionary describing implemented metrics. It's used to

      - render description when listing metrics. Required but not mandatory keys
        C{metricDescription}, C{metricLocality}, C{metricType}, C{metricVersion}

      - determine required command line options. C{cmdLineOptions} - list with
        definitions of long command line options for C{getopt} options parser.
        E.g.: C{['opt-one=','opt-two']}. C{opt-one} requires any arguments.
        C{opt-two} doesn't require an argument.

      - define dependencies between metrics.

    L{metrics} dictionary should be updated from the children of the current
    class by L{set_metrics()} method.

    @cvar metrics: dictionary describing metrics
    @type metrics: C{dict}

    @cvar methodMap: methods to metrics map
    @type methodMap: C{dict}

    """

    __lib_version = '0.7'

    probeinfo = {}

    metrics = {'Default' :
                {'metricDescription': "Default wrapper metric to launch "+\
                                      "all metrics defined in the probe.",
                'metricLocality'    : 'local',
                'metricType'        : 'wrapper',
                'cmdLineOptionsReq' : [],
                'metricChildren'    : []}
               }
    description = {}
    methodMap   = {}
    __metrSuff2metrName = {}
    serviceType = 'Undefined'
    execMetric  = 'Default'
    verbosity   = VERBOSITY_MIN
    # return codes a'la Nagios
    retCodes    = samutils.retCodes
    usage       = ''

    voName = 'ops'
    fqan = ''
    fqan_norm = ''
    ns = ''

    # Main configuration file
    main_config = '/etc/gridmon/gridmon.conf'

    # Errors DB
    errorDBFile = '/etc/gridmon/gridmon.errdb'
    errorTopics = ['default']

    chldproc = None

    # Reporting passive checks - NSCA or Nagios command file
    __passcheckdests = ['nsca', 'nagcmd', 'active', 'config']
    passcheckdest = 'config' # <'config'|'active'|'nsca'|'nagcmd'>

    passcheckconf = ''

    nsca_server    = None
    nsca_port      = '5667'
    send_nsca      = '/usr/sbin/send_nsca'
    send_nsca_conf = '/etc/nagios/send_nsca.cfg'
    nagcmdfile = '/var/nagios/rw/nagios.cmd'

    # object (singleton) to hold and manipulate metrics output
    __mo = MetricOutputHandlerSingleton.getInstance()

    # Nagios performance data
    __perf_data = ''

    """
    /< workdir_run >/<voName>/<ns>/<serviceType>/<nodeName>
    |- workdir_run -|        |    |             |         |
    |--- workdir_vo ---------|    |             |         |
    |------ workdir_ns -----------|             |         |
    |---------- workdir_service ----------------|         |
    |-------------- workdir_metric -----------------------|
    """
    workdir_run     = '/var/lib/gridprobes'
    workdir_vo      = ''
    workdir_ns      = ''
    workdir_service = ''
    workdir_metric  = ''

    testing_from = ''
    testing_DN = ''
    details_header = ''
    set_details_header = True

    __usage = """    Metrics common parameters:

Reporting passive checks (when used with wrapper checks)

--pass-check-dest <config|nsca|nagcmd|active> (Default: %s)

--pass-check-conf <path> Configuration file for reporting passive checks.
                         Used with '--pass-check-dest config'. Overrides
                         passive checks submission library default one.

--nsca-server <fqdn|ip> NSCA server FQDN or IP. Required if --pass-check-dest
                        is set to 'nsca'.
--nsca-port <port>      Port NSCA is listening on (Default: %s)
--send-nsca <path>      NSCA client binary.  (Default: %s)
--send-nsca-conf <path> NSCA configuration file. (Default: %s)

--nagcmdfile <path>   Nagios command file.
                      Order: $NAGIOS_COMMANDFILE, --nagcmdfile
                      (Default: %s)

--vo <name>           Virtual Organization. (Default: %s)
--vo-fqan <name>      VOMS primary attribute as FQAN. If given, will be used
                      along with --vo.
--err-db <file>       Full path. Database file containing gLite CLI/API errors
                      for categorizing runtime errors. (Default: %s)
--err-topics <top1,>  Comma separated list of topics (Default: %s)

--work-dir <dir>      Working directory for metrics.
                      (Default: %s)

--stdout              Detailed output of metrics will be printed to stdout as
                      it is being produced by metrics. The default is to store
                      the output in a container and, then, produce Nagios
                      compiant output.

--no-details-header   Don't include header in details data.

"""%(passcheckdest,
     nsca_port,
     send_nsca,
     send_nsca_conf,
     nagcmdfile,
     voName,
     errorDBFile,
     ','.join(errorTopics),
     workdir_run
     #probes_workdir+'/<VO>'
     )

    cmdopts_long = ['pass-check-dest=',
                    'pass-check-conf=',
                    'nsca-server=',
                    'nsca-port=',
                    'send-nsca=',
                    'send-nsca-conf=',
                    'nagcmdfile=',
                    'vo=',
                    'err-db=',
                    'err-topics=',
                    'work-dir=',
                    'stdout',
                    'no-details-header',
                    'vo-fqan=']

    sanitize = True

    def __init__(self, tuples, type):
        """ """

        self.serviceType = type

        if tuples.has_key('metric'):
            self.set_execMetric(tuples['metric'])

        if not tuples.has_key('serviceURI'):
            raise TypeError("No serviceURI passed in")
        [self.hostName, self.portNumber] = samutils.parse_uri(tuples['serviceURI'])

        if tuples.has_key('verbosity'):
            self.verbosity = tuples['verbosity']
            self.__mo.verbosity = self.verbosity

        # parse command-line arguments
        try:
            args = tuples['metricOptions']
        except KeyError:
            args = ''
        # let unrecognised long options to pass through
        opts,_ = samutils.getops_flexlongs(args.split(),
                                           '',
                                           self.cmdopts_long)
        self._parseopts_super(opts)

        if self.set_details_header:
            self._set_details_header()

    def set_metrics(self, metrics):
        """
        Build
          - L{metrics} dictionary to hold description of the metrics
            defined in this and derived classes
          - methods to metrics map L{methodMap}
          - metrics suffixes to metric names map

        @param metrics: dictionary describing metrics defined in child class
            in the form C{{'MetricName': {'key':'val',...},...}}
        @type metrics: C{dict}

        @raise TypeError: if C{metrics} is not of type C{dict}
        """

        if type(metrics) != dict:
            raise TypeError('set_metrics() - argument should be a dictionary.')

        self.metrics.update(metrics)

        # metrics' prefix
        mp = self.ns+'.'+self.serviceType
        self.set_metricsPrefix(mp)

        # Build methods-to-metrics map and metrics descriptions
        for m,v in self.metrics.items():
            mn  = mp+'-'+m
            self.methodMap[mn] = 'metric'+m
            try:
                mloc = v['metricLocality']
            except KeyError:
                mloc = 'remote'
            try:
                mtype = v['metricType']
            except KeyError:
                mtype = 'status'
            try:
                mdesc = v['metricDescription']
            except KeyError:
                mdesc = ''
            try:
                clo = v['cmdLineOptions']
            except KeyError:
                clo = ''
            self.description[mn] = {
                                    'metricName'        : mn,
                                    'metricLocality'    : mloc,
                                    'metricType'        : mtype,
                                    'metricDescription' : mdesc,
                                    'cmdLineOptions'    : clo
                                    }

        # build metricSuffix-to-metricName map
        for  ms,v in self.metrics.items():
            mn  = self.ns+'.'+self.serviceType+'-'+ms
            self.__metrSuff2metrName[ms] = mn

    def _parseopts_super(self, opts):

        for o,v in opts:
            if o == '--pass-check-dest':
                if v in self.__passcheckdests:
                    self.passcheckdest = v
                    # set up gathering of output
                    if self.passcheckdest == 'active':
                        self.__mo.set_stream()
                else:
                    errstr = '--pass-check-dest must be one of <'+\
                        '|'.join([x for x in self.__passcheckdests])+'>. '+v+' given.'
                    raise getopt.GetoptError(errstr)
            elif o == '--pass-check-conf':
                self.passcheckconf = v
            elif o == '--nsca-server':
                self.nsca_server = v
            elif o == '--nsca-port':
                self.nsca_port = v
            elif o == '--send-nsca':
                self.send_nsca = v
            elif o == '--send-nsca-conf':
                self.send_nsca_conf = v
            elif o == '--nagcmdfile':
                self.nagcmdfile = v
            elif o == '--vo':
                self.voName = v
            elif o == '--err-db':
                try:
                    p = os.path.abspath(v)
                    os.stat(p)
                except OSError, e:
                    status = 'UNKNOWN'
                    stsmsg = status+': Error DB file is missing\n'
                    detmsg = stsmsg+str(e)+'\n'
                    sys.stdout.write(stsmsg)
                    sys.stdout.write(detmsg)
                    sys.exit(self.retCodes[status])
                else:
                    self.errorDBFile = p
            elif o == '--err-topics':
                for t in v.split(','):
                    if not self.errorTopics.count(t) and t != '':
                        self.errorTopics.append(t)
            elif o == '--work-dir':
                self.workdir_run = v
            elif o == '--stdout':
                self.__mo.set_stream()
            elif o == '--no-details-header':
                self.set_details_header = False
            elif o == '--vo-fqan':
                self.__set_fqan(v)

        if self.passcheckdest == 'nsca' and not self.nsca_server:
            errstr = "--nsca-server must be set if --pass-check-dest is set to 'nsca'."
            raise getopt.GetoptError(errstr)

        # overwrite Nagios command file path if defined in environment
        try:
            self.nagcmdfile = os.environ['NAGIOS_COMMANDFILE']
        except KeyError, e:
            pass

    def __set_fqan(self, fqan):
        self.__fqan = fqan
        self.fqan_norm = self.__norm_fqan(fqan)
    def __get_fqan(self):
        try:
            return self.__fqan
        except AttributeError:
            return ''
    fqan = property(__get_fqan, __set_fqan)

    def __norm_fqan(self, fqan):
        return re.sub('/','.',fqan.strip('/'))

    def parse_cmd_args(self, tuples, cmdopts=None, func=None):
        """Parse metric's command arguments.

        - tuples  - dictionary with 'metricOptions' key, which value is a list
                    containing command-line arguments - ie. 'sys.argv'.
        - cmdopts - list of long command line arguments to be appended to
                    the ones to be parsed by parent and, then, passed
                    to getopt.getopt(). Then, the ouput of calling
                    getopt.getopt() - list of (option, value) pairs
                    ['optlist'] - will be passed to user supplied function.
                    But before that parsed by parent 'optlist' parser.
        - func    - child function to call to parse command line parameters
                    defined for the metrics in the client class (Default:
                    self.parse_args() - one should re-implement the method
                    defined as a stub in MetricGatherer class); the method
                    should accept a list of options given by
                    'optlist,_ = getopt.getopt()' - ie. list of tupeles
                    of option/value pairs. One can raise getopt.GetoptError() in
                    the function.
        """

        if not self.isset_execMetric():
            return

        try:
            args = tuples['metricOptions']
        except KeyError:
            args = ''

        # if no options were given, check if there are required for the metric
        if len(args) == 0:
            metrSuff = self.execMetric2MetricSuff()
            if self.metrics[metrSuff].has_key('cmdLineOptionsReq') and \
                    len(self.metrics[metrSuff]['cmdLineOptionsReq']) != 0:
                sys.stdout.write(self.help())
                sys.stdout.write("Error : One or more of required options for "+\
                                 self.execMetric+" were not given.\n")
                sys.exit(1)

        # get command line options defined for metrics in client class
        argchld = cmdopts or self.__get_cmd_opts_client()

        try:
            # Include parsing of command line options for client class
            self.cmdopts_long.extend(argchld)
            optlist,_ = getopt.getopt(args.split(),'',
                            self.cmdopts_long)

            # parent parses command line parameters
            # NB! removed: super class must do this during its init process
            #self._parseopts_super(optlist)

            # client function to parse command parameters
            if func and callable(func):
                func(optlist)
            else:
                self.parse_args(optlist)

        except (getopt.GetoptError, ValueError, AttributeError), e:
            sys.stdout.write(self.help())
            sys.stdout.write("Error : %s\n"% e)
            sys.exit(1)

    def parse_args(self, args):
        """Stub. Implement in child class.

        Parse metric's command arguments.
        - args - a string of options with arguments, i.e. args[1:]
        """
        raise NotImplementedError('Not implemented method %s.%s()' %
                                    (self.__class__.__name__,
                                     sys._getframe(0).f_code.co_name))

    def _set_details_header(self):
        'Header for details data.'
        import socket
        self.testing_from = 'Testing from: %s' % socket.gethostname() #@UndefinedVariable
        self.testing_DN = 'DN: %s' % gridutils.get_testing_DN()
        self.testing_VOMS_FQANs = 'VOMS FQANs: %s' % \
                                        ', '.join(gridutils.get_voms_fqans())
        self.details_header = '%s\n%s\n%s' % (self.testing_from,
                                              self.testing_DN,
                                              self.testing_VOMS_FQANs)

    def __get_cmd_opts_client(self):
        """Parse self.metrics dict to get command line options defined
        for each metric.

        Returns:
        - list of long command line options defined for client metrics
          ready to be passed to getopt.getopt()
        """

        argchld = []
        if self.execMetric2MetricSuff() in ['Default', 'All']:
            try:
                m_attrs_All = self.metrics['All']
            except KeyError:
                pass
            else:
                try: # by default extend the list from metric 'All'
                    argchld.extend(m_attrs_All['cmdLineOptions'])
                except KeyError:
                    pass
                # continue by adding command line options from other metrics
                ms = self.metrics.keys()
                for r in ['Default', 'All']:
                    ms.remove(r)
                for m in ms:
                    try:
                        for v in self.metrics[m]['cmdLineOptions']:
                            if not v in argchld:
                                argchld.append(v)
                    except KeyError:
                        pass
        else:
            try: # by default extend the list from metric 'All'
                argchld.extend(self.metrics['All']['cmdLineOptions'])
            except KeyError:
                pass
            try:
                for v in self.metrics[self.execMetric2MetricSuff()]['cmdLineOptions']:
                    if not v in argchld:
                        argchld.append(v)
            except StandardError:
                pass

        return argchld

    def get_optarg_from_Tuples(self, tuples, opt):
        """Retun argument of a parameter as provided on CLI or empty string
        if the parameter is not found. Exits the program if argument
        for the parameter is not provided on CLI.

        tuples
            dictionary with 'metricOptions'
        opt
            parameter to search for
        """
        try:
            all_opts = tuples['metricOptions']
        except KeyError:
            return ''
        if re.search(opt, all_opts):
            try:
                opts,_ = samutils.getops_flexlongs(all_opts.split(),
                                                   '', [opt+'='])
            except getopt.GetoptError, e:
                sys.stdout.write(self.usage)
                sys.stdout.write("Error: %s\n"% str(e))
                sys.exit(1)
            for k,v in opts:
                if k == '--'+opt:
                    return v
        return ''

    def make_workdir(self):
        """If a metric for execution is defined, creates working directory
        /<workdir_run>/<voName>/<ns>/<serviceType>/<nodeName>

        Sets the object fields:

        workdir_run, workdir_vo, workdir_ns, workdir_service, workdir_metric

        ::

        /< workdir_run >/<voName>/<ns>/<serviceType>/<nodeName>
        |- workdir_run -|        |    |             |         |
        |--- workdir_vo ---------|    |             |         |
        |------ workdir_ns -----------|             |         |
        |---------- workdir_service ----------------|         |
        |-------------- workdir_metric -----------------------|
        """

        if self.isset_execMetric():
            self.workdir_vo      = '%s/%s' % (self.workdir_run, self.fqan_norm or self.voName)
            self.workdir_ns      = '%s/%s' % (self.workdir_vo, self.ns)
            self.workdir_service = '%s/%s' % (self.workdir_ns, self.serviceType)
            self.workdir_metric  = '%s/%s' % (self.workdir_service, self.hostName)
            if not os.path.isdir(self.workdir_metric):
                try:
                    os.makedirs(self.workdir_metric)
                except OSError, e:
                    status = 'UNKNOWN'
                    stsmsg = detmsg = status+": OSError: "+str(e)+'\n'
                    sys.stdout.write(stsmsg)
                    sys.stdout.write(detmsg)
                    sys.exit(self.retCodes[status])

    def list(self):
        "List all metric methods in this class"
        metrics = []
        for k in self.description.keys():
            metrics.append(k)
        metrics.sort()
        return metrics

    def __get_perf_data(self):
        return self.__perf_data
    def __set_perf_data(self, data):
        """Set Nagios performance data. Overloaded setter.
        data - PerfData|str|[('key', str|[int|long|float|str,..]|(int|long|float|str,..)), ..]
        Order of list elements should always be preserved. RRD needs this.
        Raises:
        TypeError if one of the type requrements is not met.
        """
        if isinstance(data, str):
            self.__perf_data = data
        elif isinstance(data, list) or isinstance(data, tuple):
            pd = []
            for v in data:
                if type(v) not in [tuple, list]:
                    raise TypeError('Expected tuple or string as performance '+\
                                        'data elements, got %s' % type(v))
                if v:
                    if len(v) > 1:
                        # TODO: when Python 2.4 becomes available on WNs
                        # s = PerfData.value2str(v[1])
                        s = perfdata.value2str(v[1])
                    else:
                        s = perfdata.PerfData.empty
                    if v[0]:
                        pd.append('%s=%s' % (v[0], s))
            self.__perf_data = ' '.join(pd)
        elif isinstance(data, perfdata.PerfData):
            self.__perf_data = data.get()
        else:
            raise TypeError('Expected str, list or tuple, got %s' % type(data))
    perf_data = property(__get_perf_data, __set_perf_data, None,
                         "Performance data (in Nagios sense).")

    def _handle_metric_output(self, ret):
        """Process output from metric.
        ret - can be
              * integer 0-3,
              * string 'OK' etc.
              * list [status, summary, details]
              * tuple (status, summary, details)

        If 'ret' tuple or list didn't contain summary or details data
        the code assumes that they were gathered using "output capture"
        mechanism, and tries to get them from global container holding the data.

        Return:
        dictionary - {'metricStatus': '<str>',
                      'summaryData' : '<str>',
                      'detailsData' : '<str>',
                      'perfData'    : '<str>'}
        """
        out = {}
        if isinstance(ret, str) or isinstance(ret, int): # e.g., 'OK' or 0
            status = samutils.to_status(ret)
            out = {'metricStatus': status}
            summary = self.__get_summary()
            details = self.__get_detdata()
        elif isinstance(ret, list) or isinstance(ret, tuple): # e.g., ('OK','S','D')
            status = samutils.to_status(ret[0])
            out = {'metricStatus': status}
            try:
                summary = ret[1]
            except IndexError:
                summary = self.__get_summary()
            try:
                details = ret[2]
            except IndexError:
                details = self.__get_detdata()
        else:
            raise ErrProbeMetricOutputTypeError(
                    'Metrics can only return integer, string, list, tuple.')

        if summary.startswith(status+':'):
            out['summaryData'] = summary
        else:
            out['summaryData'] = '%s: %s' % (status, summary)
        if details.startswith(status+':'):
            out['detailsData'] = details
        else:
            if self.details_header:
                out['detailsData'] = '%s\n%s\n%s' % (out['summaryData'],
                                                     self.details_header,
                                                     details)
            else:
                out['detailsData'] = '%s\n%s' % (out['summaryData'], details)

        if self.perf_data:
            out['perfData'] = self.perf_data

        return out

    def gather(self, metric, clear_summary_details=True):
        "Run a given metric instance, and return the result"

        self.set_execMetric(metric)

        if clear_summary_details:
            self.__clear_summary_and_details()

        if self.methodMap.has_key(metric):
            methodName = self.methodMap[metric]
        else:
            methodName = "metric" + metric

        if hasattr(self,methodName):
            try:
                ret = getattr(self,methodName)()
            except StandardError:
                samutils.exit_trace('UNKNOWN',
                           'unhandled exception while gathering metric results.')
            try:
                return self._handle_metric_output(ret)
            except ErrProbeMetricOutputTypeError:
                samutils.exit_trace('UNKNOWN',
                            'exception while processing metric results.')
        else:
            status = samutils.to_status(3)
            return {'metricStatus' : status,
                    'summaryData' : "%s: Metric %s does not exist." % \
                                    (status, metric)}

    def desc(self, metric):
        "Return the test definition block"
        desc = None
        if self.description.has_key(metric):
            desc = {}
            for k,v in self.description[metric].items():
                if k != 'cmdLineOptions':
                    desc[k] = v
            desc['serviceType'] = self.serviceType
        return desc

    def print_versions(self):
        print "libVersion: ", self.__lib_version
        for k,v in self.probeinfo.items():
            if k.endswith('Version'):
                print k+': '+v

    def help(self):
        return '%s%s' % (self.__usage, self.usage)

    def printd(self, dd, v=VERBOSITY_MIN, cr=True, prep=False):
        """Print string either to stdout or append to a buffer.

        dd : str
            string

        v : int
            verbosity level

        cr : boolean : True
            append carriage return or not

        prep : bololean : False
            prepend data to the metrics output container
        """
        self.__mo.printd(dd, v=v, cr=cr, prep=prep)

    def printdvm(self, dd, cr=True, prep=False):
        'Invokes printd() with highest verbosity.'
        self.__mo.printd(dd, v=VERBOSITY_MAX, cr=cr, prep=prep)

    def prints(self, s):
        """Sets summary for the metric output.

        s : str
            summary
        """
        self.__mo.prints(s)

    def print_time(self, v=VERBOSITY_MIN):
        'Print current time in iso8601 (%Y-%m-%dT%H:%M:%SZ)'
        self.printd(samutils.time_now(), v)

    def __get_detdata(self):
        return self.__mo.get_detdata()
    "Retuns detailed data collected for the test."
    get_detdata = __get_detdata

    def __get_summary(self):
        return self.__mo.get_summary()
    "Retuns summary set for the test."
    get_summary = __get_summary

    def __clear_summary_and_details(self):
        'Clear summary and details data.'
        self.__mo.clear_summary_details()

    def set_metricsPrefix(self, mp):
        "Sets envoked metric prefix."
        self.__metricsPrefix = mp
    def get_metricsPrefix(self):
        "Gives envoked metric prefix"
        return self.__metricsPrefix

    def set_execMetric(self, metricName):
        "Set a name of a metric that was called."
        self.execMetric = metricName

    def get_execMetric(self):
        "Gives name of the metic being executed."
        return self.execMetric

    def isset_execMetric(self):
        """Check if the name of the currently executed metric is set.
        """
        if self.execMetric == 'Undefined' or \
            self.execMetric == None or \
            self.execMetric == '':
            return False
        return True

    def execMetric2MetricSuff(self):
        """Map a name of the currently executed metric to the metric's
        "suffix" in self.metrics dictionary.
        """
        if self.execMetric == 'Default':
            return 'Default'

        try:
            return self.methodMap[self.execMetric].lstrip('metric')
        except KeyError, e:
            status = 'UNKNOWN'
            msg = '%s: unknown metric specified - %s\n'%(status, str(e))
            sys.stderr.write(msg)
            sys.stderr.write(msg)
            sys.exit(samutils.to_retcode(status))

    def metrSuff2metrName(self, ms):
        """Given metric's suffix return metric's name.
        """
        return self.__metrSuff2metrName[ms]

    def run_cmd(self, cmd, verb='-v', _verbosity=0, setpgrp=False):
        """Run a given command. Uses L{pexpectpgrp.spawn_cmd()}

        @param cmd: command to run
        @type cmd: C{str}

        @param verb: verbosity
        @type str: C{str}

        @param _verbosity: custom verbosity level (C{0})
        @type _verbosity: C{int}

        @param setpgrp: when spawning a command create a new process group (C{False})
        @type setpgrp: C{boolean}

        @return: (retcode, status, details)
            - retcode (C{str or int}) - C{'OK' : 0, 'WARNING' : 1, 'CRITICAL' : 2, 'UNKNOWN' : 3}
            - status  (C{str}) - one line status message
            - details (C{str}) - multi-line details output
        @rtype: C{tuple}
        """

# TODO: cleanup verb='-v'. This is simply not needed

        verbosity = _verbosity or self.verbosity

        metricSuff = self.execMetric2MetricSuff()
        try:
            if verbosity >= 2:
                cmd = cmd % verb
            else:
                cmd = cmd % ''
        except TypeError:
            pass

        rc, lines = pexpectpgrp.spawn_cmd(cmd, setpgrp=setpgrp)

        if rc == 0:
            status = 'OK'
            try:
                stsmsg = self.metrics[metricSuff]['statusMsgs'][status]
            except KeyError:
                stsmsg = ''
            detmsg = stsmsg+'\n'+lines
        else:
            em = ErrorsMatching(self.errorDBFile, self.errorTopics)
            er = em.match(lines)
            if er:
                status = er[0][2]
                try:
                    stsmsg = self.metrics[metricSuff]['statusMsgs'][status]+\
                                ' [ErrDB:'+str(er)+']'
                except KeyError:
                    stsmsg = ''
            else:
                status = 'CRITICAL'
                try:
                    stsmsg = self.metrics[metricSuff]['statusMsgs'][status]
                except KeyError:
                    stsmsg = ''
            detmsg = stsmsg+'\n'+lines

        return(self.retCodes[status], stsmsg, detmsg)

#    def run_cmd2(self, cmd, verb='-v', _verbosity=None):
#        """Run a command given by a user.
#        The command will be started and the output processed in accordance
#        with the four verbosity levels specified.
#        Returns a tuple: (retcode, status, details)
#        - retcode: integer {'OK': 0, 'WARNING' : 1, 'CRITICAL' : 2, 'UNKNOWN' : 3}
#        - status: one line status message
#        - details: multi-line details output
#        """
#        # TODO: if verbosity > 2 use Pexpect for combined stdout+stderr line-buffered output
#
#        verbosity = _verbosity or self.verbosity
#
#        metricSuff = self.execMetric2MetricSuff()
#        if verbosity == VERBOSITY_MIN:
#            try:
#                cmd = cmd%('')
#            except TypeError:
#                pass
#            self.chldproc = popenpgrp.Popenpgrp3(cmd, capturestderr=True)
#            # stdout = self.chldproc.fromchild.read().rstrip('\n')
#            stderr = self.chldproc.childerr.read().rstrip('\n')
#            exitstatus = self.chldproc.poll()
#            while exitstatus < 0:
#                self.chldproc.wait()
#                exitstatus = self.chldproc.poll()
#            retcode = os.WEXITSTATUS(exitstatus)
#            # stdout = stderr = ''
#            detmsg = ''
#            if retcode == 0:
#                status = 'OK'
#                try:
#                    stsmsg = self.metrics[metricSuff]['statusMsgs'][status]
#                except KeyError:
#                    stsmsg = ''
#            else:
#                em = ErrorsMatching(self.errorDBFile, self.errorTopics)
#                er = em.match(stderr)
#                if er:
#                    status = er[0][2]
#                    try:
#                        stsmsg = self.metrics[metricSuff]['statusMsgs'][status]+\
#                                    ' [ErrDB:'+str(er)+']'
#                    except KeyError:
#                        stsmsg = ''
#                else:
#                    status = 'CRITICAL'
#                    try:
#                        stsmsg = self.metrics[metricSuff]['statusMsgs'][status]
#                    except KeyError:
#                        stsmsg = ''
#        elif verbosity == 1:
#            try:
#                cmd = cmd%('')
#            except TypeError:
#                pass
#            self.chldproc = popenpgrp.Popenpgrp3(cmd, capturestderr=True)
#            # stdout = self.chldproc.fromchild.read().rstrip('\n')
#            stderr = self.chldproc.childerr.read().rstrip('\n')
#            exitstatus = self.chldproc.poll()
#            while exitstatus < 0:
#                self.chldproc.wait()
#                exitstatus = self.chldproc.poll()
#            retcode = os.WEXITSTATUS(exitstatus)
#            # stdout = stderr = ''
#            if retcode == 0:
#                status = 'OK'
#                try:
#                    stsmsg = detmsg = self.metrics[metricSuff]['statusMsgs'][status]
#                except KeyError:
#                    stsmsg = detmsg = ''
#            else:
#                em = ErrorsMatching(self.errorDBFile, self.errorTopics)
#                er = em.match(stderr)
#                if er:
#                    status = er[0][2]
#                    try:
#                        stsmsg = self.metrics[metricSuff]['statusMsgs'][status]+\
#                                    ' [ErrDB:'+str(er)+']'
#                    except KeyError:
#                        stsmsg = ''
#                else:
#                    status = 'CRITICAL'
#                    try:
#                        stsmsg = self.metrics[metricSuff]['statusMsgs'][status]
#                    except KeyError:
#                        stsmsg = ''
#                detmsg = stsmsg+'\n'+cmd+'\n'+stderr
#        elif verbosity == 2:
#            try:
#                cmd = cmd%(verb)
#            except TypeError:
#                pass
#            self.chldproc = popenpgrp.Popenpgrp4(cmd)
#            stdout = self.chldproc.fromchild.read().rstrip('\n')
#            # stderr = self.chldproc.childerr.read().rstrip('\n')
#            exitstatus = self.chldproc.poll()
#            while exitstatus < 0:
#                self.chldproc.wait()
#                exitstatus = self.chldproc.poll()
#            retcode = os.WEXITSTATUS(exitstatus)
#            # stdout = stderr = ''
#            if retcode == 0:
#                status = 'OK'
#                try:
#                    stsmsg = self.metrics[metricSuff]['statusMsgs'][status]
#                except KeyError:
#                    stsmsg = ''
#                detmsg = stsmsg+'\n'+stdout
#            else:
#                em = ErrorsMatching(self.errorDBFile, self.errorTopics)
#                er = em.match(stdout)
#                if er:
#                    status = er[0][2]
#                    try:
#                        stsmsg = self.metrics[metricSuff]['statusMsgs'][status]+\
#                                    ' [ErrDB:'+str(er)+']'
#                    except KeyError:
#                        stsmsg = ''
#
#                else:
#                    status = 'CRITICAL'
#                    try:
#                        stsmsg = self.metrics[metricSuff]['statusMsgs'][status]
#                    except KeyError:
#                        stsmsg = ''
#                detmsg = stsmsg+'\n'+cmd+'\n'+stdout
#        elif verbosity == VERBOSITY_MAX:
#            try:
#                cmd = cmd%(verb)
#            except TypeError:
#                pass
#            self.chldproc = popenpgrp.Popenpgrp4(cmd)
#            stdout = self.chldproc.fromchild.read().rstrip('\n')
#            #stderr = self.chldproc.childerr.read().rstrip('\n')
#            exitstatus = self.chldproc.poll()
#            while exitstatus < 0:
#                self.chldproc.wait()
#                exitstatus = self.chldproc.poll()
#            retcode = os.WEXITSTATUS(exitstatus)
#            # stdout = stderr = ''
#            config = ''
#            if retcode == 0:
#                status = 'OK'
#                try:
#                    stsmsg = self.metrics[metricSuff]['statusMsgs'][status]
#                except KeyError:
#                    stsmsg = ''
#                detmsg = stsmsg+'\n'+config+'\n'+cmd+'\n'+stdout
#            else:
#                em = ErrorsMatching(self.errorDBFile, self.errorTopics)
#                er = em.match(stdout)
#                if er:
#                    status = er[0][2]
#                    try:
#                        stsmsg = self.metrics[metricSuff]['statusMsgs'][status]+\
#                                    ' [ErrDB:'+str(er)+']'
#                    except KeyError:
#                        stsmsg = ''
#                else:
#                    status = 'CRITICAL'
#                    try:
#                        stsmsg = self.metrics[metricSuff]['statusMsgs'][status]
#                    except KeyError:
#                        stsmsg = ''
#                detmsg = stsmsg+'\n'+config+'\n'+cmd+'\n'+stdout
#        else:
#            # raise SomeExeptionToBeCoughtHigherUp
#            pass
#
#        return(self.retCodes[status], stsmsg, detmsg)

    def thr_run_cmd(self, cmd, verb='-v', _verbosity=None):
        """Run a command given by a user.
        The command will be started and the output processed in accordance
        with the four verbosity levels specified.
        Returns a tuple: (retcode, status, details)
        - retcode: integer {'OK': 0, 'WARNING' : 1, 'CRITICAL' : 2, 'UNKNOWN' : 3}
        - status: one line status message
        - details: multi-line details output
        """
        # TODO: if verbosity > 2 use Pexpect for combined stdout+stderr line-buffered output

        verbosity = _verbosity or self.verbosity

        metricSuff = self.execMetric2MetricSuff()
        if verbosity == 0:
            try:
                cmd = cmd%('')
            except TypeError:
                pass
            chldproc = popenpgrp.Popenpgrp3(cmd, capturestderr=True)
            # stdout = chldproc.fromchild.read().rstrip('\n')
            stderr = chldproc.childerr.read().rstrip('\n')
            exitstatus = chldproc.poll()
            while exitstatus < 0:
                chldproc.wait()
                exitstatus = chldproc.poll()
            retcode = os.WEXITSTATUS(exitstatus)
            # stdout = stderr = ''
            detmsg = ''
            if retcode == 0:
                status = 'OK'
                try:
                    stsmsg = self.metrics[metricSuff]['statusMsgs'][status]
                except KeyError:
                    stsmsg = status+': '
            else:
                em = ErrorsMatching(self.errorDBFile, self.errorTopics)
                er = em.match(stderr)
                if er:
                    status = er[0][2]
                    try:
                        stsmsg = self.metrics[metricSuff]['statusMsgs'][status]+\
                                    ' [ErrDB:'+str(er)+']'
                    except KeyError:
                        stsmsg = status+': '
                else:
                    status = 'CRITICAL'
                    try:
                        stsmsg = self.metrics[metricSuff]['statusMsgs'][status]
                    except KeyError:
                        stsmsg = status+': '
        elif verbosity == 1:
            try:
                cmd = cmd%('')
            except TypeError:
                pass
            chldproc = popenpgrp.Popenpgrp3(cmd, capturestderr=True)
            # stdout = chldproc.fromchild.read().rstrip('\n')
            stderr = chldproc.childerr.read().rstrip('\n')
            exitstatus = chldproc.poll()
            while exitstatus < 0:
                chldproc.wait()
                exitstatus = chldproc.poll()
            retcode = os.WEXITSTATUS(exitstatus)
            # stdout = stderr = ''
            if retcode == 0:
                status = 'OK'
                try:
                    stsmsg = detmsg = self.metrics[metricSuff]['statusMsgs'][status]
                except KeyError:
                    stsmsg = detmsg = status+': success.'
            else:
                em = ErrorsMatching(self.errorDBFile, self.errorTopics)
                er = em.match(stderr)
                if er:
                    status = er[0][2]
                    try:
                        stsmsg = self.metrics[metricSuff]['statusMsgs'][status]+\
                                    ' [ErrDB:'+str(er)+']'
                    except KeyError:
                        stsmsg = status+': '
                else:
                    status = 'CRITICAL'
                    try:
                        stsmsg = self.metrics[metricSuff]['statusMsgs'][status]
                    except KeyError:
                        stsmsg = status+': '
                detmsg = '%s\n%s\n%s' % (stsmsg,cmd,stderr)
        elif verbosity == 2:
            try:
                cmd = cmd%(verb)
            except TypeError:
                pass
            chldproc = popenpgrp.Popenpgrp4(cmd)
            stdout = chldproc.fromchild.read().rstrip('\n')
            # stderr = chldproc.childerr.read().rstrip('\n')
            exitstatus = chldproc.poll()
            while exitstatus < 0:
                chldproc.wait()
                exitstatus = chldproc.poll()
            retcode = os.WEXITSTATUS(exitstatus)
            # stdout = stderr = ''
            if retcode == 0:
                status = 'OK'
                try:
                    stsmsg = self.metrics[metricSuff]['statusMsgs'][status]
                except KeyError:
                    stsmsg = status+': success.'
                detmsg = '%s\n%s\n%s' % (stsmsg,cmd,stdout)
            else:
                em = ErrorsMatching(self.errorDBFile, self.errorTopics)
                er = em.match(stdout)
                if er:
                    status = er[0][2]
                    try:
                        stsmsg = self.metrics[metricSuff]['statusMsgs'][status]+\
                                    ' [ErrDB:'+str(er)+']'
                    except KeyError:
                        stsmsg = status+': '

                else:
                    status = 'CRITICAL'
                    try:
                        stsmsg = self.metrics[metricSuff]['statusMsgs'][status]
                    except KeyError:
                        stsmsg = status+': '
                detmsg = '%s\n%s\n%s' % (stsmsg,cmd,stdout)
        elif verbosity == 3:
            try:
                cmd = cmd%(verb)
            except TypeError:
                pass
            chldproc = popenpgrp.Popenpgrp4(cmd)
            stdout = chldproc.fromchild.read().rstrip('\n')
            #stderr = chldproc.childerr.read().rstrip('\n')
            exitstatus = chldproc.poll()
            while exitstatus < 0:
                chldproc.wait()
                exitstatus = chldproc.poll()
            retcode = os.WEXITSTATUS(exitstatus)
            # stdout = stderr = ''
            # TODO: provide meaningful config
            config = ''
            if retcode == 0:
                status = 'OK'
                try:
                    stsmsg = self.metrics[metricSuff]['statusMsgs'][status]
                except KeyError:
                    stsmsg = status+': success.'
                detmsg = '%s\n%s\n%s\n%s' % (stsmsg,config,cmd,stdout)
            else:
                em = ErrorsMatching(self.errorDBFile, self.errorTopics)
                er = em.match(stdout)
                if er:
                    status = er[0][2]
                    try:
                        stsmsg = self.metrics[metricSuff]['statusMsgs'][status]+\
                                    ' [ErrDB:'+str(er)+']'
                    except KeyError:
                        stsmsg = status+': '
                else:
                    status = 'CRITICAL'
                    try:
                        stsmsg = self.metrics[metricSuff]['statusMsgs'][status]
                    except KeyError:
                        stsmsg = status+': '
                detmsg = '%s\n%s\n%s\n%s' % (stsmsg,config,cmd,stdout)
        else:
            # raise SomeExeptionToBeCoughtHigherUp
            pass

        return(self.retCodes[status], stsmsg, detmsg)

    def __submit_service_check_active(self, chres):
        """Format and print metric results to stdout.

        - chres   - list of hashes with keys:
                    host, service, status, summary, details
        """
        for d in chres:
            print 'metric results >>> <%s,%s>' % (str(d['host']),str(d['service']))
            print d['summary'].replace('\\n','\n')
            print d['details'].replace('\\n','\n')

    def _submit_service_checks(self, chres):
        """Publishe passive metrics to either of
        - Nagios command file
        - NSCA

        - chres - list of hashes with keys:
                  host, service, status, summary, details
        """
        if self.sanitize:
            for i in range(len(chres)):
                try:
                    chres[i]['summary'] = samutils.outputsanitiser(chres[i]['summary'])
                except StandardError: pass
                try:
                    chres[i]['details'] = samutils.outputsanitiser(chres[i]['details'])
                except StandardError: pass
        try:
            if self.passcheckdest == 'nagcmd':
                nagios.publishPassiveResultNAGCMD(self.nagcmdfile, chres)

            elif self.passcheckdest == 'nsca':
                try:
                    os.stat(self.send_nsca)
                except OSError:
                    raise ErrProbe(os.stat(self.send_nsca),
                            "ERROR: NSCA client doesn't exist.")
                try:
                    os.stat(self.send_nsca_conf)
                except OSError:
                    raise ErrProbe(os.stat(self.send_nsca_conf),
                            "ERROR: Nagios command file doesn't exist.")

                nagios.publishPassiveResultNSCA(self.send_nsca,
                                self.send_nsca_conf, self.nsca_server,
                                self.nsca_port, chres)

            elif self.passcheckdest == 'active':
                self.__submit_service_check_active(chres)

            elif self.passcheckdest == 'config':
                if self.passcheckconf:
                    nagios.publishPassiveResult(chres,
                                                modefile=self.passcheckconf)
                else:
                    nagios.publishPassiveResult(chres)
            else:
                print "UNKNOWN: Unsupported passive check submission method: %s" % \
                    self.passcheckdest
                sys.exit(3)

        except nagios.ErrNagiosLib, e:
            status = 'UKNOWN'
            sys.stdout.write(status+': exception publishing passive check\n')
            sys.stdout.write(status+': exception publishing passive check\n%s\n'%\
                             str(e))
            sys.exit(samutils.to_retcode(status))

    def metricAll(self, metricsRun = 'All'):
        """Run metrics specified in self.metrics[metricsRun]['metricsOrder']
        """

        # hostname to uniquely define a service
        hostname = ''
        try:
            hostname = os.environ['NAGIOS_HOSTNAME']
        except KeyError:
            hostname = self.hostName

        all_status = 'OK'
        all_summary = 'success.'
        all_detmsg = ''

        try:
            self.metrics[metricsRun]
        except KeyError:
            all_status = 'UNKNOWN'
            m = '%s-%s' % (self.get_metricsPrefix(), metricsRun)
            msg = "%s: the metric set in the probe doesn't define %s" % (
                                                                all_status, m)
            sys.stdout.write(msg+'\n')
            sys.stdout.write(msg+'\n')
            msl = self.list()
            try:
                msl.remove(self.metrSuff2metrName('Default'))
            except StandardError:
                pass
            sys.stdout.write('Defined metrics are:\n'+'\n'.join(msl)+'\n')
            sys.exit(samutils.to_retcode(all_status))

        for metricSuff in self.metrics[metricsRun]['metricsOrder']:
            metricPref = self.get_metricsPrefix()
            metricName = self.metrSuff2metrName(metricSuff)
            all_detmsg += 'Invoking metric: [%s] %s\n' % \
                        (samutils.time_now(), metricName)
            ret = dict.fromkeys(['metricStatus','summaryData','detailsData'],'')
            timedout = False
            try:
                # run metric
                # TODO : exception is needed to catch fatal errors in the metrics
                #
                ret = self.gather(metricName)
                #
                # TODO : exception is needed to catch fatal errors in the metrics
            except signaling.TimeoutError, e:
                ret = {}
                ret['metricStatus'] = 'WARNING'
                ret['summaryData'] = 'Timed out. %s' % str(e)
                # get what the metric was able to gather so far
                if len(signaling.proc) == 1: # was running in a single threaded mode
                    self.printd(signaling.proc.values()[0].output, cr=False)
                ret['detailsData'] = self.get_detdata()
                timedout = True
                signal.alarm(3)

            # NB! Nasty HACK to overcome Nagios's deficiency.
            #     Relevant when reporting passive check results.
            #     Mangle actual VO-neutral metric name and add VO to it.
            metricNameNagios = '%s-%s' % (metricName, self.fqan or self.voName)

            try:
                self._submit_service_checks([{
                             'host'   : hostname,
                             'service': metricNameNagios,
                             'status' : samutils.to_retcode(ret['metricStatus']),
                             'summary': ret['summaryData'],
                             'details': ret['detailsData'].replace('\n','\\n')}])
                met_status = ret['metricStatus']
                if met_status != 'OK':
                    # publish Nagios passive check results with WARNING for the
                    # siblings of the "node" metric
                    if len(self.metrics[metricSuff]['metricChildren']) > 0 or timedout:
                        child_status = 'WARNING'
                        child_summary = '%s: Masked by %s - "%s"' % \
                                        (child_status, metricName, ret['summaryData'])
                        metric_res = []
                        for msuff in self.metrics[metricSuff]['metricChildren']:
                            metric_res.append({'host' : hostname,
                                'service'  : metricPref+'-'+msuff+'-%s' % (self.fqan or self.voName),
                                'status'   : str(self.retCodes[child_status]),
                                'summary'  : child_summary,
                                'details'  : ''})
                        self._submit_service_checks(metric_res)
                        all_summary = 'METRIC FAILED [%s]: %s' % \
                                    (metricName, ret['summaryData'])
                        all_detmsg += '%s\n' % all_summary
                        signal.alarm(0)
                        return (met_status, all_summary, all_detmsg)
                    # set proper status for failed "leaf" metrics
                    elif self.metrics[metricSuff].has_key('critical') and \
                        self.metrics[metricSuff]['critical'] == 'Y':
                        c = False
                        if all_status == 'OK':
                            c = True
                        elif met_status == 'CRITICAL' and all_status != 'CRITICAL':
                            c = True
                        elif met_status == 'WARNING'  and all_status not in ('WARNING','CRITICAL'):
                            c = True
                        if c:
                            all_status = met_status
                            all_summary = 'METRIC FAILED [%s]: %s' % \
                                        (metricName, ret['summaryData'])
                            all_detmsg += '%s\n' % all_summary
                    else:
                        """Leaf metricis w/o "critical: Y"
                           don't affect status of the wrapper."""
            except signaling.TimeoutError, e:
                all_status = 'UNKOWN'
                all_summary = 'Timed out while publishing metric results. %s' % str(e)
                all_detmsg += all_summary + '\n'
                all_detmsg += '='*25 + '\n'
                all_detmsg += '* Last metric: %s\n' % metricName
                all_detmsg += '* Details data:\n%s' % ret['detailsData']
                return (all_status, all_summary, all_detmsg)

        return (all_status, all_summary, all_detmsg)

    def metricDefault(self):
        'By default run MetricGatherer.metricAll().'
        return self.metricAll()


class Runner:
    """Metrics runner.
    """
    def __init__(self, gathererClass, renderer = ProbeFormatRenderer()):
        """Set metrics gatherer and metric results format renderer.

        @param gathererClass: metrics gatherer class
        @type gathererClass: L{MetricGatherer}

        @param renderer: object to render the test results
        @
        """
        self.gathererClass = gathererClass
        self.renderer = renderer

    def _set_probeshome(self):
        if not os.environ.has_key('PROBES_HOME'):
            os.environ['PROBES_HOME'] = \
                os.path.normpath(os.path.dirname(os.path.abspath(sys.argv[0])))

    def run(self, argv):
        """Parse command line parameters. Depending on requested action
        - run a metric from a probe
        - list available metrics in the launched probe
        - display help

        @param argv: command line parameters
        @type argv: string
        """
        self._set_probeshome()

        tuples={
                'metricOptions' : '',
                'timeout' : 600,
                'verbosity' : VERBOSITY_MIN}
        metric='Default'
        list_versions=None
        list_metrics=None
        help=None
        sanitize = True
        # order: X509_USER_PROXY, -x, default
        proxy = os.environ.get('X509_USER_PROXY',
                               '/tmp/x509up_u'+str(os.geteuid()))

        usage="""Usage: %s
[-H|--hostname <FQDN>]|[-u|--uri <URI>] [-m|--metric <name>] [-t|--timeout sec]
[-V] [-h|--help] [--wlcg] [-v|--verbose %i-%i] [-l|--list] [-x proxy] [<metric
specific parameters>]

-V                 Displays version
-h|--help          Displays help
-t|--timeout sec   Sets metric's global timeout. (Default: %i)
-m|--metric <name> Name of a metric to be collected. Eg. org.sam.SRMv2-Put.
                   If not given, a default wrapper metric will be executed.
-H|--hostname FQDN Hostname where a service to be tested is running on
-u|--uri <URI>     Service URI to be tested
-v|--verbose %i-%i   Verbosity. (Default: %i)
                   0 Single line, minimal output. Summary
                   1 Single line, additional information
                   2 Multi line, configuration debug output
                   3 Lots of details for plugin problem diagnosis
-l|--list          Metrics list in WLCG format
-x                 VOMS proxy (Order: -x, X509_USER_PROXY, /tmp/x509up_u<UID>)
--nosanity         Don't sanitize metrics output.

  Mandatory paramters: hostname (-H) or URI (-u).

  If specified with -m|--metric <name>, the given metric will be executed.
  Otherwise, a wrapper metric (acting as an active check) will be run. The
  latter is equivalent to "-m|--metric <nameSpace>.<Service>-All"

"""%(argv[0],
     VERBOSITY_MIN,
     VERBOSITY_MAX,
     tuples['timeout'],
     VERBOSITY_MIN,
     VERBOSITY_MAX,
     tuples['verbosity'])

        opts,_ = (None,None)
        try:
            # let unrecognised long options to pass through
            opts,_ = samutils.getops_flexlongs(argv[1:],
                                               'Vht:m:u:H:v:lx:o:',
                                               ['help',
                                                'timeout=',
                                                'metric=',
                                                'uri=',
                                                'hostname=',
                                                'verbose=',
                                                'list',
                                                'wlcg'])
        except getopt.GetoptError, e:
            sys.stdout.write(usage)
            sys.stdout.write("Error: %s\n"% str(e))
            sys.exit(1)
        except StandardError, e:
            samutils.exit_trace('UNKNOWN',
                       'exception while processing command line parameters.')

        k = [x[0] for x in opts]
        if ('-u' in k and '-H' in k) or \
            ('-u' in k and '--hostname' in k) or \
            ('--uri' in k and '-H' in k) or \
            ('--uri' in k and '--hostname' in k):
            sys.stdout.write(usage)
            sys.stdout.write("""Error:
 -u|--uri and -H|--hostname cannot be given together.
""")
            sys.exit(1)

        try:
            for o,v in opts:
                if o in ('--help', '-h'):
                    tuples['metricOptions'] = ''
                    help = 1
                    break
                elif o == '-V':
                    tuples['metricOptions'] = ''
                    list_versions = 1
                    break
                elif o in ('-l','--list'):
                    tuples['metricOptions'] = ''
                    list_metrics = 1
                    break
                elif o in ('-m','--metric'):
                    metric=v
                    # a hack for MetricGatherer.parse_cmd_args()
                    tuples['metric'] = metric
                elif o in ('-u', '--uri'):
                    tuples['serviceURI']=v
                elif o in ('-H', '--hostname'):
                    tuples['serviceURI']=v
                elif o in ('-t', '--timeout'):
                    tuples['timeout']=v
                elif o in ('-v','--verbose'):
                    vrb = int(v)
                    if vrb > VERBOSITY_MAX: vrb = VERBOSITY_MAX
                    if vrb < VERBOSITY_MIN: vrb = VERBOSITY_MIN
                    tuples['verbosity'] = vrb
                elif o in ('-x'):
                    proxy = v
                elif o == '--nosanity':
                    sanitize = False
                else:
                    tuples['metricOptions'] += ' '+o+' '+v+' '

            tuples['sanitize'] = sanitize

        except (getopt.GetoptError, ValueError), e:
            sys.stdout.write(usage)
            sys.stdout.write("Error : %s\n"% e)
            sys.exit(1)

        os.environ['X509_USER_PROXY'] = proxy

        if not tuples.has_key('serviceURI'):
            # UGH ! Need to do this, just to pull some version stuff
            # out of the probe
            tuples['serviceURI']= 'http://foo.example.com:8888/'
            tuples['metric'] = None
            try:
                gatherer = self.gathererClass(tuples)
            except StandardError:
                samutils.exit_trace('UNKNOWN',
                           'exception while initializing metric gatherer.')
            if help:
                sys.stderr.write(usage)
                sys.stderr.write(gatherer.help())
                sys.exit()
            elif list_metrics:
                for metric in gatherer.list():
                    self.renderer.renderDesc(gatherer.desc(metric))
                sys.exit()
            elif list_versions:
                gatherer.print_versions()
                sys.exit()
            else:
                sys.stdout.write(usage)
                sys.stdout.write("Error : missing mandatory options: -H|--hostname <FQDN> or -u|--uri <URI>\n")
                sys.stdout.write("Use -h for help.\n")
                sys.exit(1)

        try:
            gatherer = self.gathererClass(tuples)
        except StandardError:
            samutils.exit_trace('UNKNOWN',
                       'exception while initializing metric gatherer.')

        # gather the metric, if specified
        if not metric:
            sys.stderr.write(usage)
            sys.stderr.write('Available metrics are:\n')
            for metric in gatherer.list():
                sys.stderr.write('\t%s\n'%metric)
            sys.stderr.write('Use -h for help.\n')
            print >> sys.stderr
            sys.exit(1)

        signal.signal(signal.SIGTERM, signaling.sig_alrm)
        signal.signal(signal.SIGALRM, signaling.sig_alrm)
        signal.alarm(int(tuples['timeout']))
        try:
            result = gatherer.gather(metric, clear_summary_details=False)
        except signaling.TimeoutError, e:
            summary = 'Timed out. %s' % str(e)
            if len(signaling.proc) == 1: # was running in a single threaded mode
                gatherer.printd(signaling.proc.values()[0].output, cr=False)
            gatherer.printd('\n' + summary)
            return self.renderer.render(
                        gatherer._handle_metric_output(('WARNING', summary)),
                                                        sanitize=sanitize)
        except KeyboardInterrupt, e:
            sys.stdout.write('KeyboardInterrupt\n')
            sys.exit(1)

        return self.renderer.render(result, sanitize=sanitize)
