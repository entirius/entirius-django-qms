# entirius-django-qms

A Django module for stock quantities in Entirius, the open-source modular ecommerce platform. It keeps stock per
warehouse and SKU, imports it from CSV files, and passes every change on to the checkout and the product catalog.

[![PyPI](https://img.shields.io/pypi/v/entirius-django-qms.svg)](https://pypi.org/project/entirius-django-qms/)
[![Python](https://img.shields.io/pypi/pyversions/entirius-django-qms.svg)](https://pypi.org/project/entirius-django-qms/)
[![License: MPL-2.0](https://img.shields.io/badge/license-MPL--2.0-blue.svg)](https://github.com/entirius/entirius-django-qms/blob/develop/LICENSE)

## What it does

- Models warehouses, the sales channels they serve and the stock of each SKU in each warehouse.
- Imports stock from CSV files with the `warehouse_import_csv` management command.
- Exposes an admin REST API for warehouses and their stock, used by the CMS.
- Sends a signal on every stock change; optional handlers update the checkout and the product catalog when those
  modules are installed.
- Runs standalone: the checkout and catalog integrations are skipped when the modules are missing.

## Installation

```shell
uv add entirius-django-qms
pip install entirius-django-qms
```

```python
INSTALLED_APPS = [
    ...
    "django_utils",
    "django_qms",
]

# urls.py
urlpatterns = [
    path("", include("django_qms.urls")),
]
```

The Celery tasks and the legacy pipelines need `BI_ENVIRONMENT` and `BI_BUSINESS_UNIT` (read when their event
definitions are imported). Optional settings (`QMS_BULK_BATCH_SIZE`, `QMS_SUPPLIER_CODE_PREFIX`) are listed with
their defaults in https://github.com/entirius/entirius-django-qms/blob/develop/docs/configuration.md.

## Quick start

```python
from django_qms.services.warehouse_service import bulk_upsert_stock, get_warehouse

warehouse = get_warehouse("wh-main")
bulk_upsert_stock(warehouse, [{"sku": "SKU-1", "quantity": 12}])
```

The same from a CSV file: `python manage.py warehouse_import_csv --warehouse-code wh-main --file stock.csv`.

## Requirements

- Python 3.11 or newer, Django 5.0 or newer.
- PostgreSQL.
- Entirius packages pulled in: `entirius-django-utils`, `entirius-py-bievents`, `entirius-py-idx-normalizator`,
  `entirius-py-process-logger`.

## Documentation

- Module docs: https://github.com/entirius/entirius-django-qms/tree/develop/docs
- Entirius documentation: https://docs.entirius.com/
- Changelog: https://github.com/entirius/entirius-django-qms/blob/develop/CHANGELOG.md

## Part of Entirius

This module runs inside the Entirius backend service (Volkanos) and feeds stock to the checkout and the catalog.

- Backend service: https://github.com/entirius/entirius-service-volkanos
- Docker harness: https://github.com/entirius/entirius-zeno
- Sibling modules: https://github.com/entirius/entirius-django-checkout,
  https://github.com/entirius/entirius-django-pim

## Development

```shell
make install     # sync dependencies (uv)
make check       # lint + format check (ruff)
make test        # test suite (pytest + pytest-django, needs PostgreSQL via DATABASE_URL)
```

Development and agent instructions: https://github.com/entirius/entirius-django-qms/blob/develop/AGENTS.md

## License

Mozilla Public License 2.0 (MPL-2.0) — see https://github.com/entirius/entirius-django-qms/blob/develop/LICENSE.
