# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for CSV import service."""

import io

import pytest

from django_qms.models import WarehouseStock
from django_qms.services.csv_import_service import import_csv_to_warehouse


def _make_csv(content: str):
    return io.BytesIO(content.encode("utf-8"))


@pytest.mark.django_db
class TestCSVImport:
    def test_valid_csv_imports(self, manual_warehouse):
        csv = _make_csv("sku,quantity\nSKU-A,10\nSKU-B,20\n")
        report = import_csv_to_warehouse(manual_warehouse, csv)
        assert report["rows_parsed"] == 2
        assert report["rows_imported"] == 2
        assert report["rows_skipped"] == 0
        assert WarehouseStock.objects.get(warehouse=manual_warehouse, sku="SKU-A").quantity == 10

    def test_valid_csv_updates_last_synced(self, manual_warehouse):
        assert manual_warehouse.last_synced_at is None
        csv = _make_csv("sku,quantity\nSKU-LS,10\n")
        import_csv_to_warehouse(manual_warehouse, csv)
        manual_warehouse.refresh_from_db()
        assert manual_warehouse.last_synced_at is not None

    def test_alternative_column_names(self, manual_warehouse):
        csv = _make_csv("product_sku,qty\nSKU-C,30\n")
        report = import_csv_to_warehouse(manual_warehouse, csv)
        assert report["rows_imported"] == 1

    def test_empty_sku_skipped(self, manual_warehouse):
        csv = _make_csv("sku,quantity\n,10\nSKU-D,20\n")
        report = import_csv_to_warehouse(manual_warehouse, csv)
        assert report["rows_imported"] == 1
        assert report["rows_skipped"] == 1
        assert report["errors"][0]["error"] == "Empty SKU"

    def test_invalid_quantity_skipped(self, manual_warehouse):
        csv = _make_csv("sku,quantity\nSKU-E,abc\nSKU-F,20\n")
        report = import_csv_to_warehouse(manual_warehouse, csv)
        assert report["rows_imported"] == 1
        assert report["rows_skipped"] == 1

    def test_negative_quantity_skipped(self, manual_warehouse):
        csv = _make_csv("sku,quantity\nSKU-G,-5\nSKU-H,20\n")
        report = import_csv_to_warehouse(manual_warehouse, csv)
        assert report["rows_imported"] == 1
        assert report["rows_skipped"] == 1
        assert "Negative" in report["errors"][0]["error"]

    def test_missing_sku_column_raises(self, manual_warehouse):
        csv = _make_csv("product,quantity\nSKU-I,10\n")
        with pytest.raises(ValueError, match="SKU column"):
            import_csv_to_warehouse(manual_warehouse, csv)

    def test_missing_quantity_column_raises(self, manual_warehouse):
        csv = _make_csv("sku,count\nSKU-J,10\n")
        with pytest.raises(ValueError, match="quantity column"):
            import_csv_to_warehouse(manual_warehouse, csv)

    def test_empty_csv_raises(self, manual_warehouse):
        csv = _make_csv("")
        with pytest.raises(ValueError, match="empty"):
            import_csv_to_warehouse(manual_warehouse, csv)

    def test_integration_warehouse_rejected(self, integration_warehouse):
        """Integration guard is enforced by warehouse_service.bulk_upsert_stock."""
        csv = _make_csv("sku,quantity\nSKU-K,10\n")
        with pytest.raises(ValueError, match="managed by integration"):
            import_csv_to_warehouse(integration_warehouse, csv)

    def test_integration_warehouse_allowed_with_override(self, integration_warehouse):
        csv = _make_csv("sku,quantity\nSKU-L,10\n")
        report = import_csv_to_warehouse(integration_warehouse, csv, allow_integration=True)
        assert report["rows_imported"] == 1
