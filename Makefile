SPECFILE=python-GridMon.spec
rpmbuild := $(shell [ -x /usr/bin/rpmbuild ] && echo rpmbuild || echo rpm)

sources:
	python setup.py sdist
	mv dist/*.tar.gz .
	rm -rf dist MANIFEST

rpm: sources
	cp *.tar.gz /usr/src/redhat/SOURCES/
	$(rpmbuild) --define 'dist .el5' -ba $(SPECFILE)

srpm: sources
	cp *.tar.gz /usr/src/redhat/SOURCES/
	$(rpmbuild) --define 'dist .el5' -bs $(SPECFILE)

clean:
	rm -rf python-GridMon-* python-GridMon-*.tar.gz MANIFEST
