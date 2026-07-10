# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""End-to-end signal chain tests: upsert -> signal -> checkout stock created."""

from unittest.mock import patch

import pytest

pytest.importorskip("django_checkout")

from django_qms.models import WarehouseStock
from django_qms.services import warehouse_service


@pytest.mark.django_db
class TestSignalChainEndToEnd:
    @patch("django_checkout.services.stock_sync_service.sync_warehouse_to_checkout")
    def test_upsert_triggers_checkout_sync(self, mock_sync, manual_warehouse, checkout_channel, checkout_channel_2):
        """bulk_upsert_stock -> signal -> checkout sync service called with data."""
        items = [{"sku": "E2E-001", "quantity": 10}]
        warehouse_service.bulk_upsert_stock(manual_warehouse, items)

        mock_sync.assert_called_once()
        call_kwargs = mock_sync.call_args.kwargs
        assert call_kwargs["supplier_code"] == "wh-wh-manual"
        assert "E2E-001" in call_kwargs["skus_with_quantities"]
        # Handler resolves QMS Channel idx -> Checkout Channel objects
        assert len(call_kwargs["channels"]) == 2

    @patch("django_checkout.services.stock_sync_service.sync_warehouse_to_checkout")
    def test_multiple_skus_single_signal(self, mock_sync, manual_warehouse, checkout_channel, checkout_channel_2):
        """All SKUs bundled in a single signal call."""
        items = [
            {"sku": "E2E-001", "quantity": 10},
            {"sku": "E2E-002", "quantity": 20},
            {"sku": "E2E-003", "quantity": 30},
        ]
        warehouse_service.bulk_upsert_stock(manual_warehouse, items)

        mock_sync.assert_called_once()
        skus = set(mock_sync.call_args.kwargs["skus_with_quantities"].keys())
        assert skus == {"E2E-001", "E2E-002", "E2E-003"}

    @patch("django_checkout.services.stock_sync_service.sync_warehouse_to_checkout")
    def test_inactive_warehouse_skips_sync(self, mock_sync, inactive_warehouse):
        """Inactive warehouse -> receiver skips sync."""
        from django_qms.signals.handlers import on_warehouse_stock_changed_checkout

        on_warehouse_stock_changed_checkout(sender=WarehouseStock, warehouse=inactive_warehouse, skus=["X"])
        mock_sync.assert_not_called()

    @patch("django_checkout.services.stock_sync_service.sync_warehouse_to_checkout")
    def test_no_changes_skips_signal(self, mock_sync, manual_warehouse, stock_items):
        """When all quantities are unchanged, signal should NOT fire."""
        items = [{"sku": "SKU-001", "quantity": 100}, {"sku": "SKU-002", "quantity": 50}]
        warehouse_service.bulk_upsert_stock(manual_warehouse, items)
        mock_sync.assert_not_called()

    @patch("django_pim.signals.dispatch.enqueue_product_sync")
    def test_matrix_enqueue_called(self, mock_enqueue, manual_warehouse):
        """Stock change -> matrix Redis enqueue per (channel, sku). Warehouse has 2 QMS channels."""
        from django_qms.signals.handlers import on_warehouse_stock_changed_matrix

        on_warehouse_stock_changed_matrix(sender=WarehouseStock, warehouse=manual_warehouse, skus=["M-001", "M-002"])

        # 2 SKUs x 2 QMS channels = 4 enqueue calls
        assert mock_enqueue.call_count == 4
        calls = {(c.args[0], c.args[1]) for c in mock_enqueue.call_args_list}
        assert ("M-001", "test-channel") in calls
        assert ("M-001", "test-channel-2") in calls
        assert ("M-002", "test-channel") in calls
        assert ("M-002", "test-channel-2") in calls
