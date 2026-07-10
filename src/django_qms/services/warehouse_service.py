# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Warehouse business logic — single entry point for all stock mutations.

All stock writes go through this service. Views and management commands
never call WarehouseStock.save() or bulk_update() directly.
"""

from __future__ import annotations

from django.db.models import Q, QuerySet
from django.utils import timezone

from django_qms.models import SourceType, Warehouse, WarehouseStock
from django_qms.settings import QMS_BULK_BATCH_SIZE
from django_qms.signals import warehouse_stock_changed


def get_warehouse(code: str) -> Warehouse:
    """Get warehouse by code or raise DoesNotExist."""
    return Warehouse.objects.get(code=code)


def list_warehouses(is_active: bool | None = None, search: str | None = None) -> QuerySet[Warehouse]:
    """List warehouses with optional filters. Prefetches channels for serialization."""
    qs = Warehouse.objects.prefetch_related("channels")
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    if search:
        qs = qs.filter(Q(code__icontains=search) | Q(name__icontains=search))
    return qs


def list_stock(warehouse: Warehouse, search: str | None = None) -> QuerySet[WarehouseStock]:
    """List stock for a warehouse, optionally filtered by SKU search."""
    qs = WarehouseStock.objects.filter(warehouse=warehouse).order_by("sku")
    if search:
        qs = qs.filter(sku__icontains=search)
    return qs


def list_products_for_warehouse(warehouse: Warehouse, search: str | None = None) -> QuerySet:
    """List all RealProduct SKUs annotated with has_stock and stock_quantity for this warehouse.

    Uses the PriceManager Exists() annotation pattern — lets CMS filter by has_stock=false
    to find products that need stock added.
    """
    from django.db.models import Exists, OuterRef, Subquery

    try:
        from django_pim.models import RealProduct
    except ImportError:
        return WarehouseStock.objects.none()

    qs = RealProduct.objects.only("sku").order_by("sku")

    qs = qs.annotate(
        has_stock=Exists(WarehouseStock.objects.filter(warehouse=warehouse, sku=OuterRef("sku"))),
        stock_quantity=Subquery(
            WarehouseStock.objects.filter(warehouse=warehouse, sku=OuterRef("sku")).values("quantity")[:1]
        ),
    )

    if search:
        qs = qs.filter(sku__icontains=search)

    return qs


def serialize_warehouse(warehouse: Warehouse) -> dict:
    """Serialize a warehouse to a dict. Reads from prefetch cache when available."""
    channel_idxs = [ch.idx for ch in warehouse.channels.all()]
    return {
        "id": warehouse.id,
        "code": warehouse.code,
        "name": warehouse.name,
        "description": warehouse.description,
        "source_type": warehouse.source_type,
        "is_active": warehouse.is_active,
        "last_synced_at": warehouse.last_synced_at,
        "channel_idxs": channel_idxs,
    }


def bulk_upsert_stock(
    warehouse: Warehouse, items: list[dict], *, allow_integration: bool = False, fire_signal: bool = True
) -> list[dict]:
    """Upsert stock records and optionally fire signal. Returns list of upserted items.

    Args:
        warehouse: Target warehouse.
        items: List of {"sku": str, "quantity": int} dicts.
        allow_integration: If True, skip source_type check (for management commands).
        fire_signal: If False, skip signal dispatch (for async CSV imports).

    Raises:
        ValueError: If warehouse is inactive or integration (without override).
    """
    if not warehouse.is_active:
        raise ValueError(f"Warehouse '{warehouse.code}' is inactive")
    if warehouse.source_type == SourceType.INTEGRATION and not allow_integration:
        raise ValueError(f"Warehouse '{warehouse.code}' is managed by integration — use CSV import or API sync")

    skus = [item["sku"] for item in items]
    if not skus:
        return items

    # Fetch existing stock for these SKUs in one query
    existing = {ws.sku: ws for ws in WarehouseStock.objects.filter(warehouse=warehouse, sku__in=skus)}

    to_create = []
    to_update = []
    for item in items:
        sku, qty = item["sku"], item["quantity"]
        if sku in existing:
            ws = existing[sku]
            if ws.quantity != qty:
                ws.quantity = qty
                to_update.append(ws)
        else:
            to_create.append(WarehouseStock(warehouse=warehouse, sku=sku, quantity=qty))

    if to_create:
        WarehouseStock.objects.bulk_create(to_create, batch_size=QMS_BULK_BATCH_SIZE)
    if to_update:
        WarehouseStock.objects.bulk_update(to_update, fields=["quantity"], batch_size=QMS_BULK_BATCH_SIZE)

    if fire_signal and (to_create or to_update):
        warehouse_stock_changed.send(sender=WarehouseStock, warehouse=warehouse, skus=skus)

    return items


def update_last_synced(warehouse: Warehouse) -> None:
    """Mark warehouse as just synced (for integration imports)."""
    Warehouse.objects.filter(pk=warehouse.pk).update(last_synced_at=timezone.now())


def get_stock_by_sku(sku: str) -> list[dict]:
    """Get stock for a SKU across all active warehouses (product-centric view)."""
    warehouses = Warehouse.objects.filter(is_active=True).order_by("name")
    stock_map = {
        ws.warehouse_id: ws.quantity for ws in WarehouseStock.objects.filter(sku=sku, warehouse__is_active=True)
    }
    return [
        {
            "warehouse_code": wh.code,
            "warehouse_name": wh.name,
            "source_type": wh.source_type,
            "is_active": wh.is_active,
            "quantity": stock_map.get(wh.pk, 0),
            "has_stock": wh.pk in stock_map,
        }
        for wh in warehouses
    ]


def upsert_stock_by_sku(sku: str, items: list[dict]) -> list[dict]:
    """Upsert stock for a single SKU across multiple warehouses. Fires signal per warehouse."""
    if not items:
        return items

    codes = [item["warehouse_code"] for item in items]
    warehouses = {wh.code: wh for wh in Warehouse.objects.filter(code__in=codes, is_active=True)}

    for item in items:
        wh = warehouses.get(item["warehouse_code"])
        if not wh:
            raise ValueError(f"Warehouse '{item['warehouse_code']}' not found or inactive")
        if wh.source_type == SourceType.INTEGRATION:
            raise ValueError(f"Warehouse '{wh.code}' is managed by integration")
        bulk_upsert_stock(wh, [{"sku": sku, "quantity": item["quantity"]}])

    return items
