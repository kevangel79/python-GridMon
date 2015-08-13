##############################################################################
#
# NAME:        popenpgrp.py
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
#         Wrapper for forking session leaders with popen2.{Popen3,Popen4}.
#
# AUTHORS:     Konstantin Skaburskas, CERN
#
# CREATED:     21-Nov-2008
#
##############################################################################

"""
Wrapper for forking session leaders with popen2.{Popen3,Popen4}.

Wrapper around 'popen2' module's Popen3 and Popen4 classes for
forking processes as session leaders. Plus definition of respective
kill() methods.
"""

__docformat__ = 'restructuredtext en'

from popen2 import Popen3, Popen4
import os
import signal

class Popenpgrp3(Popen3):
    """Wrapper around `Popen3` class for forking processes as session
    leaders."""
    def __init__(self, cmd, capturestderr=False, bufsize=-1):
        Popen3.__init__(self, cmd, capturestderr, bufsize)

    def _run_child(self, cmd):
        "Set process group and run child."
        os.setpgrp()
        Popen3._run_child(self, cmd)

    def kill(self, sig=signal.SIGTERM):
        "Kill entire group."
        os.kill(-self.pid, sig)

class Popenpgrp4(Popen4):
    """Wrapper around `Popen3` class for forking processes as session
    leaders."""
    def __init__(self, cmd, bufsize=-1):
        Popen4.__init__(self, cmd, bufsize)

    def _run_child(self, cmd):
        "Set process group and run child."
        os.setpgrp()
        Popen4._run_child(self, cmd)

    def kill(self, sig=signal.SIGTERM):
        "Kill entire group."
        os.kill(-self.pid, sig)
