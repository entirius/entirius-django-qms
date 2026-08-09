---
title: QMS (Quantity Management System)
description: Warehouse-level stock management for Volkanos — physical warehouse mapping, CMS editing, signal-driven propagation to Checkout and Matrix.
sidebar:
  label: Overview
  collapsed: true
---

QMS manages stock quantities across physical warehouses. Each warehouse has a flat stock table (SKU + quantity), a list of channels it serves, and a source type that determines who can edit it.

## Two Coexisting Flows

QMS has two stock pipelines that run side by side:

**XRay Pipeline (v1)** — CSV file -> XRayStorage -> XRayStorageLink -> Checkout Stock. Configured per (QMS Channel, storage direction). Still works, still supported. Not going away.

**Warehouse Pipeline (v2.2)** — Warehouse -> WarehouseStock -> signal -> Checkout Stock + Matrix. One warehouse serves multiple channels. CMS can edit manual warehouses directly. Integration warehouses fed by CSV import or API.

The Warehouse pipeline doesn't replace XRay. A deployment can use both, or just one, per warehouse/channel.

## Key Concepts

### Source Types

| Type | Who writes | CMS behavior |
|------|-----------|-------------|
| `manual` | CMS admin via inline edit | Full edit, Save All, Add SKU |
| `integration` | CSV import, management command, API sync | Read-only display, last_synced_at shown |

### Channel Mapping

A Warehouse has a M2M relationship to QMS Channels (not Checkout Channels directly). The signal handler resolves QMS Channel idx values to Checkout Channel objects at propagation time. Stock is written to the **existing global Supplier** per Checkout Channel — the same supplier Cynthia reads from — so changes are visible to the storefront immediately.

A warehouse serving 3 channels and 500 SKUs generates ~5-6 SQL queries total, not 1500.

### Signal Chain

```
warehouse_service.bulk_upsert_stock()
  → warehouse_stock_changed signal (1 signal, all SKUs)
    → Checkout receiver: bulk upsert Stock per (channel × SKU)
    → Matrix receiver: Redis debounce → read model rebuild
```

## Module Dependencies

**Depends on:**
- `django-checkout` — Stock propagation target (global Supplier's Stock records)
- `django-utils` — BaseModel (created_at, modified_at)

**Optional:**
- `django-pim` — `enqueue_product_sync()` for Matrix rebuild debounce
- `django-matrix` — `flush_pending_matrix_sync` Celery task (consumes Redis queue)

## Pages

- [Warehouse Data Model](./warehouse/) — models, constraints, source types
- [Configuration](./configuration/) — settings reference
- [Migration Guide](./migration/) — backfill from existing Checkout Stock
