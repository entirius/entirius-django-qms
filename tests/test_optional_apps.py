# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Optional sibling apps that are installed but not in INSTALLED_APPS.

Importing the models of such an app raises RuntimeError, not ImportError, so every guard around
an optional sibling has to catch both.
"""

import ast
import builtins
from pathlib import Path
from types import SimpleNamespace

import pytest

import django_qms

SRC = Path(django_qms.__file__).parent
SIBLINGS = {"django_checkout", "django_pim"}
EXEMPT = set()


def _imports_sibling(stmt: ast.stmt) -> bool:
    if isinstance(stmt, ast.ImportFrom):
        names = [stmt.module or ""]
    elif isinstance(stmt, ast.Import):
        names = [alias.name for alias in stmt.names]
    else:
        return False
    return any(name.split(".")[0] in SIBLINGS for name in names)


def _catches_runtime_error(node: ast.Try) -> bool:
    for handler in node.handlers:
        if handler.type is None:
            return True
        caught = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
        if any(isinstance(exc, ast.Name) and exc.id in {"RuntimeError", "Exception"} for exc in caught):
            return True
    return False


def _guards_missing_runtime_error() -> list[str]:
    missing = []
    for path in sorted(SRC.rglob("*.py")):
        relative = path.relative_to(SRC).as_posix()
        if relative in EXEMPT:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Try) and any(map(_imports_sibling, node.body)) and not _catches_runtime_error(node):
                missing.append(f"{relative}:{node.lineno}")
    return missing


def test_sibling_guards_catch_runtime_error():
    assert _guards_missing_runtime_error() == []


@pytest.fixture
def disable_app(monkeypatch):
    """Make imports of one sibling fail the way an installed app outside INSTALLED_APPS does."""

    def _disable(prefix: str) -> None:
        real_import = builtins.__import__

        def _import(name, *args, **kwargs):
            if name == prefix or name.startswith(f"{prefix}."):
                raise RuntimeError(f"{name} isn't in an application in INSTALLED_APPS")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", _import)

    return _disable


def test_checkout_sync_handler_skips_without_checkout(disable_app):
    from django_qms.signals.handlers import on_warehouse_stock_changed_checkout

    disable_app("django_checkout")
    warehouse = SimpleNamespace(is_active=True, code="W1")

    assert on_warehouse_stock_changed_checkout(sender=None, warehouse=warehouse, skus=["X"]) is None


def test_matrix_enqueue_handler_skips_without_pim(disable_app):
    from django_qms.signals.handlers import on_warehouse_stock_changed_matrix

    disable_app("django_pim")
    warehouse = SimpleNamespace(is_active=True, code="W1")

    assert on_warehouse_stock_changed_matrix(sender=None, warehouse=warehouse, skus=["X"]) is None


def test_checkout_storage_manager_names_the_missing_app(disable_app):
    from django_qms.storage_managers import CheckoutStorageManager, StorageDataSet

    disable_app("django_checkout")

    with pytest.raises(Exception, match="can not import django_checkout") as raised:
        CheckoutStorageManager({"channel_idx": "default"}).push_data(StorageDataSet(items=[]))
    assert not isinstance(raised.value, RuntimeError)
