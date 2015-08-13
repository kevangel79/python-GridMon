##############################################################################
#
# NAME:        pexpectpgrp.py
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
#         Wrapping pexpect.spawn class to fork processes as session leaders.
#
# AUTHORS:     Konstantin Skaburskas, CERN
#
# CREATED:     06-Jan-2009
#
##############################################################################

"""
Wrapping `pexpect.spawn` class to fork processes as session leaders.

`SpawnPgrp` wrapper around `pexpect.spawn` class for forking processes as
session leaders. `spawn_cmd()` - function to spawn and follow a process
using `SpawnPgrp`.
"""

__docformat__ = 'restructuredtext en'

import os
import signal

from pexpect import spawn, TIMEOUT

class SpawnPgrp(spawn):
    """Wrapper around `pexpect.spawn` class for forking processes as session
    leaders.
    """
    def __init__(self, command, setpgrp=False, timeout=30):
        """Initialise `spawn` class and private attributes.

        :param command: command to launch
        :type command: `str`
        :param setpgrp: set new process group for the spawned process (default:
            `False`)
        :type setpgrp: `bool`
        :param timeout: timeout on getting output from child's stdout/stderr
        :type timeout: `int`
        """
        spawn.__init__(self, command, args=[], timeout=timeout,
                       maxread=2000, searchwindowsize=None,
                       logfile=None, env=None)
        self.__output = ''
        self.__setpgrp = setpgrp

    def __fork_pty(self):
        if self.__setpgrp:
            # make us the session leader
            os.setpgrp()
        spawn.__fork_pty(self)

    def kill(self, sig=signal.SIGTERM):
        "Kill entire group."
        try:
            os.kill(-self.pid, sig)
        except OSError:
            pass

    def __set_output(self, o):
        self.__output += o
    def __get_output(self):
        return self.__output
    output = property(__get_output, __set_output)

def spawn_cmd(cmd, setpgrp=False):
    """Use `SpawnPgrp` to spawn a process. Line-buffered pipes from/to child.

    :param cmd: command to run
    :type cmd: `str`
    :param setpgrp: set new process group for the spawned process (default:
        `False`)
    :type setpgrp: `bool`

    :return: return code and process output as a tuple
    :rtype: `tuple`
    """
    from gridmon.process import signaling

    read_timeout = 30 # default value in Pexpect is 30 sec
    process = SpawnPgrp(cmd, setpgrp=setpgrp, timeout=read_timeout)

    signaling.proc[process.pid] = process

    line = None
    while True:
        try:
            line = process.readline()
        except TIMEOUT:
            process.output = "\n* Timed out after %i sec " % read_timeout + \
                                "while waiting for output from child.\n"
            continue
            if not process.isalive():
                process.output = "* Child process %i died.\n" % process.pid
                break
        if not line:
            break
        else:
            process.output = line

    # Hack. Otherwise obtaining exit status and return code
    # of the child process doesn't work properly.
    process.isalive()
    try:
        _, status = os.waitpid(process.pid,os.WNOHANG)
    except OSError:
        status = process.status

    ln = process.output
    del signaling.proc[process.pid]

    return (os.WEXITSTATUS(status), ln)
