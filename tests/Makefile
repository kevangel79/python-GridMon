# make sure python-ldap module with respecitve _ldap.so are in lib of Python 2.3

export PYTHONPATH=/opt/python2.3.4/lib:/opt/python2.3.4/lib/site-packages
PYTHON=/opt/python2.3.4/bin/python2.3

Probe: testProbe.py
	@echo "--- $? ---"
	@export PYTHONPATH=`pwd`/..:${PYTHONPATH}; \
	$(PYTHON) $?

ProbeFormatRenderer: testProbeFormatRenderer.py
	@echo "--- $? ---"
	@export PYTHONPATH=`pwd`/..:${PYTHONPATH}; \
	$(PYTHON) $?

Template: testTemplate.py
	@echo "--- $? ---"
	@export PYTHONPATH=`pwd`/..:${PYTHONPATH}; \
	$(PYTHON) $?

Gridutils: testGridutils.py
	@echo "--- $? ---"
	@export PYTHONPATH=`pwd`/..:${PYTHONPATH}; \
	$(PYTHON) $?

Utils: testUtils.py
	@echo "--- $? ---"
	@export PYTHONPATH=`pwd`/..:${PYTHONPATH}; \
	$(PYTHON) $?

PerfData: testPerfData.py
	@echo "--- $? ---"
	@export PYTHONPATH=`pwd`/..:${PYTHONPATH}; \
	$(PYTHON) $?

tests: Probe \
	ProbeFormatRenderer \
	Template \
	Utils \
	Gridutils \
	PerfData

test: tests clean

clean:
	rm -f *.pyc
