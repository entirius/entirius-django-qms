# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""CSV import service — parse and bulk upsert warehouse stock from CSV files."""

from __future__ import annotations

import csv
import io
import logging

from django_qms.models import Warehouse
from django_qms.services import warehouse_service

logger = logging.getLogger("django_qms.csv_import")

VALID_SKU_COLUMNS = {"sku", "product_sku", "sku_code"}
VALID_QTY_COLUMNS = {"quantity", "qty", "stock", "amount"}
CSV_IMPORT_MAX_ERRORS = 50


def import_csv_to_warehouse(warehouse: Warehouse, file_obj, *, allow_integration: bool = False) -> dict:
    """Parse CSV and upsert stock records.

    CSV must have at least two columns: one for SKU and one for quantity.
    Column names are matched case-insensitively.

    Returns:
        Report dict with rows_parsed, rows_imported, rows_skipped, errors.
    """
    content = file_obj.read()
    if isinstance(content, bytes):
        content = content.decode("utf-8-sig")

    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        raise ValueError("CSV file is empty or has no headers")

    sku_col = _find_column(reader.fieldnames, VALID_SKU_COLUMNS)
    qty_col = _find_column(reader.fieldnames, VALID_QTY_COLUMNS)

    if not sku_col:
        raise ValueError(f"CSV missing SKU column. Expected one of: {', '.join(sorted(VALID_SKU_COLUMNS))}")
    if not qty_col:
        raise ValueError(f"CSV missing quantity column. Expected one of: {', '.join(sorted(VALID_QTY_COLUMNS))}")

    items = []
    errors = []
    rows_parsed = 0

    for row_num, row in enumerate(reader, start=2):
        rows_parsed += 1
        sku = (row.get(sku_col) or "").strip()
        qty_raw = (row.get(qty_col) or "").strip()

        if not sku:
            errors.append({"row": row_num, "error": "Empty SKU"})
            continue

        try:
            quantity = int(qty_raw)
        except (ValueError, TypeError):
            errors.append({"row": row_num, "sku": sku, "error": f"Invalid quantity: '{qty_raw}'"})
            continue

        if quantity < 0:
            errors.append({"row": row_num, "sku": sku, "error": f"Negative quantity: {quantity}"})
            continue

        items.append({"sku": sku, "quantity": quantity})

    rows_imported = 0
    if items:
        warehouse_service.bulk_upsert_stock(warehouse, items, allow_integration=allow_integration)
        warehouse_service.update_last_synced(warehouse)
        rows_imported = len(items)

    report = {
        "rows_parsed": rows_parsed,
        "rows_imported": rows_imported,
        "rows_skipped": len(errors),
        "errors": errors[:CSV_IMPORT_MAX_ERRORS],
    }
    logger.info(
        "CSV import for %s: %d parsed, %d imported, %d skipped", warehouse.code, rows_parsed, rows_imported, len(errors)
    )
    return report


def _find_column(fieldnames: list[str], valid_names: set[str]) -> str | None:
    """Find the first matching column name (case-insensitive)."""
    lower_map = {f.lower().strip(): f for f in fieldnames}
    for name in valid_names:
        if name in lower_map:
            return lower_map[name]
    return None
