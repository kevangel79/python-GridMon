#!/usr/bin/env python

from distutils.core import setup

setup(name='python-GridMon',
      version='1.1.13',
      description='Helper package for python grid-monitoring applications',
      author='James Casey',
      author_email='james.casey@cern.ch',
      url='http://cern.ch/',
      packages=['gridmon', 'gridmon.security', 'gridmon.nagios',
                'gridmon.process'],
      data_files=[('/etc', ['etc/nagios-submit.conf']),
                  ('/etc/gridmon', ['etc/gridmon.errdb', 'etc/gridmon.conf'])]
     )

