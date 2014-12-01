PYTEST_ARGS := --pdb

all: test

.PHONY: tests test clean deploy

tests: test

test: clean
	@git diff --shortstat
	. env/bin/activate && flake8 --exclude=./env . tests
	. env/bin/activate && python setup.py install
	. env/bin/activate && py.test $(PYTEST_ARGS) --ignore=env

clean:
	@echo Deleting pyc files...
	@find . -name '*.py[co]' -exec rm -f '{}' ';' 2> /dev/null

upload: test
	@echo Uploading to PyPI
	. env/bin/activate && python setup.py sdist upload
