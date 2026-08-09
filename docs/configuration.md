---
title: Configuration
description: QMS module settings reference.
---

## Django Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `QMS_BULK_BATCH_SIZE` | `500` | Batch size for `bulk_create` / `bulk_update` operations |
| `QMS_SUPPLIER_CODE_PREFIX` | `"wh-"` | Prefix for auto-created Checkout Supplier codes |

## Management Commands

### `warehouse_import_csv`

Import stock from a CSV file. Allowed for both manual and integration warehouses.

```bash
manage.py warehouse_import_csv --warehouse-code=wh-sap --file=/path/to/qty.csv
```

CSV must have `sku` and `quantity` (or `qty`) columns. Rows with empty SKU, non-numeric quantity, or negative quantity are skipped. Report printed to stdout.

### `backfill_warehouse`

Create Warehouse + WarehouseStock records from existing Checkout Stock data.

```bash
manage.py backfill_warehouse --supplier-code=SUPPLIER_001 --channel-idx=default-europe [--dry-run]
```

Idempotent — skips existing records. Use `--dry-run` to preview.
