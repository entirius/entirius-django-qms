# AGENTS.md

Quantity Management System — distribution `entirius-django-qms`, Django app `django_qms`.
Warehouse-level stock management: warehouses, per-SKU stock, CSV import, admin API,
signal-driven sync to downstream consumers.

## Commands

| Command | Meaning |
|---|---|
| `make install` | sync dependencies (uv, incl. extras) |
| `make check` | lint + format-check (ruff) |
| `make fix` | auto-fix lint + format |
| `make test` | test suite (pytest + pytest-django) |

## Conventions

- English only: code, docs, commits, branches, PRs.
- MPL-2.0: every non-trivial source file carries the license header (pre-commit inserts it).
- Toolchain: uv + ruff + hatchling + pytest; all config in `pyproject.toml`; `uv.lock` committed.
- Git flow: `master` (production) + `develop` (integration); changes land via PR; semver tag on `master`.
- Never rename the package / Django app_label / DB table prefix `django_qms` — it is a schema contract.
- Migrations are part of the public contract — never edit an already released migration.
- Default: do not commit — git is the user's call.
- Access: areas live on the AppConfig (`access_areas`, `access_route_rules`), every admin view carries
  `access_area`; a new admin route without one fails `tests/test_access_ownership.py`.

## Architecture

- `models/` — `Channel` (idx, stock_weight, qms_type), `Warehouse` (code, source_type, channels M2M),
  `WarehouseStock` (warehouse FK, sku, quantity); `xray/` and `zulu/` legacy pipeline models
  (PIT, Storage, StorageLink…).
- `services/` — `warehouse_service` (bulk_upsert_stock, product listing), `csv_import_service`.
- `api/v2/` — `WarehouseViewSet` (JWT + IsAdminUser), pagination, permissions.
- `signals/` — `warehouse_stock_changed` signal; handlers sync stock to `django_checkout`
  and enqueue `django_pim` matrix updates (both optional, lazy imports).
- `management/commands/` — `warehouse_import_csv`, `backfill_warehouse` (requires checkout),
  legacy pipeline runners (`qms-manage-quantities`, `qms-status`).
- `storage_managers.py` — pluggable storage backends for the legacy pipelines.

## Gotchas

- `django_checkout` and `django_pim` integrations are lazy imports with `try/except ImportError`
  no-op fallbacks — the module works standalone.
- Checkout-integration tests (`test_stock_sync_service`, `test_signal_chain`, backfill class)
  `importorskip` / `skipif` on `django_checkout` — they activate once checkout is installed.
- Stock propagation is signal-driven: `bulk_upsert_stock` fires `warehouse_stock_changed`;
  never call the checkout sync service directly from QMS code paths.
