#!/usr/bin/env python
##############################################################################
#
# NAME:        signaling.py
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
#         Auxiliary module for handling signals.
#
# AUTHORS:     Konstantin Skaburskas, CERN
#
# CREATED:     Jun 2, 2010
#
##############################################################################

"""
Auxiliary module for handling signals.
"""

__docformat__ = 'restructuredtext en'

import signal
from gridmon.process.pexpectpgrp import SpawnPgrp

sig_names = dict([(k, v) for v, k in signal.__dict__.iteritems() if v.startswith('SIG')])
"Dictionary with names of signals (`int`:`str` key-pair)."

proc = {}
"global hash for bookkeeping forked processes."

class TimeoutError(Exception):
    ''

def sig_alrm(sig, frame):
    """Signal handler operating on processes stored in `signaling.proc`.
    """
    if proc:
        for p in proc.values():
            if isinstance(p, SpawnPgrp):
                p.kill()
    raise TimeoutError('Caught signal %s.' % sig_names[sig])
