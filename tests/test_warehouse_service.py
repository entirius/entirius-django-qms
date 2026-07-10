# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for warehouse_service — bulk upsert, validation, signal dispatch."""

from unittest.mock import patch

import pytest

from django_qms.models import WarehouseStock
from django_qms.services import warehouse_service


@pytest.mark.django_db
class TestBulkUpsertStock:
    def test_creates_new_stock_records(self, manual_warehouse):
        items = [{"sku": "NEW-001", "quantity": 10}, {"sku": "NEW-002", "quantity": 20}]
        warehouse_service.bulk_upsert_stock(manual_warehouse, items)

        assert WarehouseStock.objects.filter(warehouse=manual_warehouse).count() == 2
        assert WarehouseStock.objects.get(warehouse=manual_warehouse, sku="NEW-001").quantity == 10

    def test_updates_existing_stock(self, manual_warehouse, stock_items):
        items = [{"sku": "SKU-001", "quantity": 999}]
        warehouse_service.bulk_upsert_stock(manual_warehouse, items)

        stock = WarehouseStock.objects.get(warehouse=manual_warehouse, sku="SKU-001")
        assert stock.quantity == 999

    def test_bulk_upsert_mixed_create_and_update(self, manual_warehouse, stock_items):
        items = [
            {"sku": "SKU-001", "quantity": 200},  # update
            {"sku": "NEW-003", "quantity": 30},  # create
        ]
        warehouse_service.bulk_upsert_stock(manual_warehouse, items)

        assert WarehouseStock.objects.get(warehouse=manual_warehouse, sku="SKU-001").quantity == 200
        assert WarehouseStock.objects.get(warehouse=manual_warehouse, sku="NEW-003").quantity == 30

    @patch("django_qms.services.warehouse_service.warehouse_stock_changed")
    def test_signal_dispatched_with_correct_skus(self, mock_signal, manual_warehouse):
        items = [{"sku": "SIG-001", "quantity": 5}, {"sku": "SIG-002", "quantity": 10}]
        warehouse_service.bulk_upsert_stock(manual_warehouse, items)

        mock_signal.send.assert_called_once()
        call_kwargs = mock_signal.send.call_args
        assert call_kwargs.kwargs["warehouse"] == manual_warehouse
        assert set(call_kwargs.kwargs["skus"]) == {"SIG-001", "SIG-002"}

    def test_rejects_inactive_warehouse(self, inactive_warehouse):
        with pytest.raises(ValueError, match="inactive"):
            warehouse_service.bulk_upsert_stock(inactive_warehouse, [{"sku": "X", "quantity": 1}])

    def test_rejects_integration_warehouse_without_override(self, integration_warehouse):
        with pytest.raises(ValueError, match="managed by integration"):
            warehouse_service.bulk_upsert_stock(integration_warehouse, [{"sku": "X", "quantity": 1}])

    def test_allows_integration_warehouse_with_override(self, integration_warehouse):
        items = [{"sku": "INT-001", "quantity": 50}]
        warehouse_service.bulk_upsert_stock(integration_warehouse, items, allow_integration=True)
        assert WarehouseStock.objects.get(warehouse=integration_warehouse, sku="INT-001").quantity == 50

    def test_empty_items_list(self, manual_warehouse):
        result = warehouse_service.bulk_upsert_stock(manual_warehouse, [])
        assert result == []


@pytest.mark.django_db
class TestListWarehouses:
    def test_list_all(self, manual_warehouse, integration_warehouse, inactive_warehouse):
        result = warehouse_service.list_warehouses()
        assert result.count() == 3

    def test_filter_active(self, manual_warehouse, inactive_warehouse):
        result = warehouse_service.list_warehouses(is_active=True)
        assert result.count() == 1
        assert result.first().code == "wh-manual"

    def test_search_by_name(self, manual_warehouse, integration_warehouse):
        result = warehouse_service.list_warehouses(search="Manual")
        assert result.count() == 1


@pytest.mark.django_db
class TestListStock:
    def test_list_all_stock(self, manual_warehouse, stock_items):
        result = warehouse_service.list_stock(manual_warehouse)
        assert result.count() == 3

    def test_search_by_sku(self, manual_warehouse, stock_items):
        result = warehouse_service.list_stock(manual_warehouse, search="001")
        assert result.count() == 1
        assert result.first().sku == "SKU-001"
