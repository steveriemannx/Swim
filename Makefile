PYTHON ?= python3
SWIM   := ./bin/swim

.PHONY: help test test-update examples check clean version

help:
	@echo "make test         run the full test suite"
	@echo "make test-update  regenerate expected outputs"
	@echo "make examples     run all example programs"
	@echo "make check        compile-check all examples and tests"
	@echo "make clean        clean caches and generated files"
	@echo "make version      print the compiler version"

test:
	$(PYTHON) tests/run_tests.py

test-update:
	$(PYTHON) tests/run_tests.py --update

examples:
	@for f in examples/*.sw examples/programs/*.sw; do \
		printf '%-42s' "$$f"; \
		if $(SWIM) run "$$f" >/dev/null 2>&1; then echo OK; else echo FAIL; fi; \
	done

check:
	@for f in examples/*.sw examples/programs/*.sw tests/cases/*.sw \
		tests/projects/*/main.sw; do \
		$(SWIM) check "$$f" >/dev/null || exit 1; \
	done
	@echo "all examples and tests type-check"

clean:
	rm -rf .swim-cache __pycache__ src/swimc/__pycache__ tests/__pycache__
	rm -f examples/*.nim examples/programs/*.nim
	find . -name '*.pyc' -delete

version:
	$(SWIM) version
