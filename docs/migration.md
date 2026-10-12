---
title: Migration Guide
description: How to set up warehouses for existing clients and migrate from the XRay pipeline.
---

## New Client Setup

Every new client needs at least one Warehouse linked to all their Checkout channels.

### 1. Create Warehouse in Django Admin

Go to `/admin/django_qms/warehouse/` and create:

- **code**: unique slug (e.g., `client-manual`)
- **source_type**: `manual` for CMS-editable, `integration` for CSV/API-fed
- **channels**: select ALL Checkout channels this warehouse serves

### 2. Link ALL channels

Easy to miss during configuration. If a warehouse is missing a channel, stock silently won't propagate to that channel's storefront — no error, just no data.

```
Warehouse "client-manual"
  channels: [default-europe, b2b-pro, marcopol24]  ← ALL of them
```

Verify after setup:
```bash
manage.py shell -c "
from django_qms.models import Warehouse
for wh in Warehouse.objects.prefetch_related('channels'):
    print(f'{wh.code}: {[ch.idx for ch in wh.channels.all()]}')
"
```

### 3. Enable in Munin

Create a Munin module record so the CMS panel appears:

```bash
manage.py shell -c "
from django_munin.models import Module
Module.objects.create(app_label='django_qms', key='stock', label='Stock Management', version='2.2.0', has_admin_api=True, has_urls=True, is_active=True, enabled_in_cms=True)
"
```

### 4. Add QMS URLs to service

In `main/urls.py`:
```python
if "django_qms" in settings.INSTALLED_APPS:
    urlpatterns.append(path("", include("django_qms.urls")))
```

---

## Migrating from XRay Pipeline

For existing clients using the old CSV -> XRayStorage -> Checkout flow, migration is optional and per-warehouse.

### Step 1: Backfill from Checkout

```bash
# Preview what would be created
manage.py backfill_warehouse --supplier-code=SUPPLIER_001 --channel-idx=default-europe --dry-run

# Create Warehouse + WarehouseStock from existing Checkout data
manage.py backfill_warehouse --supplier-code=SUPPLIER_001 --channel-idx=default-europe
```

This creates a Warehouse with `source_type=integration` and populates WarehouseStock from existing Checkout Stock records. Idempotent — safe to re-run.

### Step 2: Redirect data source

**Option A** — CSV import writes to WarehouseStock:
```bash
manage.py warehouse_import_csv --warehouse-code=wh-sap --file=/path/to/qty.csv
```

**Option B** — Keep using old pipeline, add Warehouse alongside for CMS visibility.

### Step 3: Verify both flows coexist

The old XRay pipeline and new Warehouse flow can run simultaneously. Each creates its own Supplier in Checkout. The storefront sums all suppliers per channel.

---

## Checklist

- [ ] Warehouse created in Django Admin
- [ ] ALL Checkout channels linked via M2M (verify with shell command above)
- [ ] Munin module created with `key='stock'`, `enabled_in_cms=True`
- [ ] `django_qms.urls` included in service `urls.py`
- [ ] CMS Stock panel visible and loads warehouses
- [ ] Test: edit stock in CMS, verify storefront updates within ~10s (requires Celery running)
