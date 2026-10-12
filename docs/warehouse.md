---
title: Warehouse Data Model
description: Warehouse and WarehouseStock models — fields, constraints, relationships.
---

## Models

### Warehouse

Physical or virtual stock source. Each warehouse has a unique `code`, a human-readable `name`, and a `source_type` that controls editing behavior.

| Field | Type | Notes |
|-------|------|-------|
| `code` | CharField(128) | Unique identifier (e.g., `wh-main`, `wh-sap`) |
| `name` | CharField(255) | Display name |
| `description` | TextField | Optional, shown in CMS and admin |
| `source_type` | TextChoices | `manual` or `integration` |
| `is_active` | BooleanField | Inactive warehouses skip signal propagation |
| `last_synced_at` | DateTimeField | Set by CSV import/API sync, null for manual |
| `channels` | M2M → Checkout Channel | Channels this warehouse serves |
| `created_at` | DateTimeField | Auto (from BaseModel) |
| `modified_at` | DateTimeField | Auto (from BaseModel) |

### WarehouseStock

One row per SKU per warehouse.

| Field | Type | Notes |
|-------|------|-------|
| `warehouse` | FK → Warehouse | CASCADE delete |
| `sku` | CharField(128) | Indexed, part of unique constraint |
| `quantity` | PositiveIntegerField | Non-negative enforced by DB CHECK constraint |
| `created_at` | DateTimeField | Auto (from BaseModel) |
| `modified_at` | DateTimeField | Auto (from BaseModel) |

**Constraints:**
- `unique_together: (warehouse, sku)` — one stock row per product per warehouse
- `CheckConstraint: quantity >= 0` — prevents negative stock at DB level

## Source Type Behavior

| Source Type | CMS | Admin API PATCH | Management command | CSV import |
|-------------|-----|----------------|-------------------|-----------|
| `manual` | Edit + Save All | Allowed | Allowed | Allowed |
| `integration` | Read-only | 400 error | Allowed (`--force`) | Allowed |

## Channel Propagation

When WarehouseStock changes, the signal receiver creates or updates:

1. **Supplier** per (warehouse, channel) — `code="wh-{warehouse.code}"`, `is_global=False`
2. **ProductRepresentation** per (channel, SKU) — auto-created if missing
3. **Stock** record — `(product_rep, supplier)` with the warehouse quantity

All done in bulk — constant query count regardless of data volume.
