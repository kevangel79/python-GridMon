# Generate documentation for 'gridmon' package.
# Check epydoc.cfg for configuration options.
#
# Or if generating for pre-installed or separately available package, use:
# 
# export PYTHOPATH=/path/to/packages
# epydoc -o html/ --html gridmon

DOCHTML=html
doc:
	rm -rf $(DOCHTML)
	mkdir -p $(DOCHTML)
	export PYTHONPATH=${PWD}/../; epydoc --config epydoc.cfg
