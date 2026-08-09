---
title: Checkout Stock Sync
description: How QMS stock data propagates to Checkout ProductRepresentation and Stock — two pipelines, seed gaps, and the sync command.
---

Checkout validates cart items against its own `ProductRepresentation` + `Stock` tables. If a SKU doesn't exist there, the item is rejected with `items_dont_have_stock_or_price`. QMS is responsible for propagating stock data to Checkout.

## Two Propagation Paths

### Warehouse Signal (Runtime)

Warehouse stock changes trigger the `warehouse_stock_changed` signal. The Checkout receiver (`on_warehouse_stock_changed_checkout` in `django_qms/signals/handlers.py`) calls `sync_warehouse_to_checkout()` which:

1. Resolves QMS Channel idx to Checkout Channel objects
2. Creates `Supplier` per (warehouse, channel) with `code="wh-{warehouse.code}"`
3. Creates `ProductRepresentation` per (channel, SKU) if missing
4. Creates or updates `Stock` with the warehouse quantity

This runs automatically on every warehouse stock change — manual CMS edit, CSV import, API sync.

### XRay Pipeline (Legacy)

The older XRay pipeline pushes data through `CheckoutStorageManager.push_data()` which calls `Stock.objects.update_from_qms_dataset()`. Same end result (ProductRepresentation + Stock), different trigger path.

XRay is still functional but requires completed PITs. The warehouse signal path is simpler and doesn't depend on Celery processing.

## The Seed Gap

Neither path runs during `make seed-fresh`:

- `qms-manage-quantities` creates XRay PITs but they need Celery to process. PITs often stay in `waiting` status if Celery is slow.
- Warehouse fixtures have only a few test SKUs (not the full PIM catalog).
- Result: Checkout's `ProductRepresentation` table is empty after seed. Cart operations fail.

## Sync Command

`sync-checkout-stock-from-qms` fills the gap. It populates Checkout ProductRepresentation + Stock from two sources:

```bash
# All channels
manage.py sync-checkout-stock-from-qms

# Specific channel
manage.py sync-checkout-stock-from-qms --channel_idx default-europe

# No fallback stock (warehouse data only)
manage.py sync-checkout-stock-from-qms --default-quantity 0
```

### Data sources (in priority order)

1. **QMS Warehouse stock** — quantities from active warehouses matching the channel
2. **QMS XRay output** — latest completed PIT for checkout output storage (if xray pipeline ran)

No PIM fallback. If QMS has no data, checkout has no stock — that's correct behavior. Fix the QMS seed data instead of faking stock from PIM.

The command auto-creates a global `Supplier` per channel if one doesn't exist.

### Seed pipeline integration

The command runs as Step 9b in `import-package.sh`, after QMS quantities and before Matrix fill:

```
Step 9:  qms-manage-quantities          (XRay PITs + Celery)
Step 9b: sync-checkout-stock-from-qms   (Checkout ProductRepresentation + Stock)
Step 10: fill-read-model                (Matrix)
```

## Checkout Data Model

| Model | Key fields | Created by |
|-------|-----------|-----------|
| `ProductRepresentation` | `sku`, `channel` (unique together) | `update_from_qms_dataset()` or `sync_warehouse_to_checkout()` |
| `Stock` | `product` (FK → ProductRepresentation), `supplier`, `quantity` | Same as above |
| `Supplier` | `code`, `channel`, `is_global` (unique per channel) | Signal handler or sync command |

## Debugging

```bash
# Check if Checkout has products
manage.py shell -c "
from django_checkout.models import ProductRepresentation, Stock
print(f'ProductReps: {ProductRepresentation.objects.count()}')
print(f'Stocks: {Stock.objects.count()}')
"

# Re-sync after seed issues
manage.py sync-checkout-stock-from-qms
```

If cart returns `items_dont_have_stock_or_price` after a fresh seed, run the sync command. If it persists, check that PIM has products in the channel and that Checkout Channel exists with matching `idx`.
