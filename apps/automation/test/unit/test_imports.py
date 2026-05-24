"""Smoke test: every scraut module can be imported without error."""
import importlib
import pkgutil

import pytest
import scraut

_ALL_MODULES = [m.name for m in pkgutil.walk_packages(scraut.__path__, prefix="scraut.")]


@pytest.mark.unit
@pytest.mark.parametrize("module_name", _ALL_MODULES)
def test_module_imports(module_name):
    importlib.import_module(module_name)
