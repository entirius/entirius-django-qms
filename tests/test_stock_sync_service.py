# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for Checkout stock_sync_service — bulk propagation via global supplier."""

import pytest

pytest.importorskip("django_checkout")

from django_qms.settings import QMS_SUPPLIER_CODE_PREFIX


def _sync(warehouse, skus_with_quantities):
    """Helper to call sync — mirrors signal handler's idx resolution."""
    from django_checkout.models import Channel as CheckoutChannel
    from django_checkout.services.stock_sync_service import sync_warehouse_to_checkout

    qms_channel_idxs = [ch.idx for ch in warehouse.channels.all()]
    checkout_channels = list(CheckoutChannel.objects.filter(idx__in=qms_channel_idxs))
    return sync_warehouse_to_checkout(
        channels=checkout_channels,
        supplier_code=f"{QMS_SUPPLIER_CODE_PREFIX}{warehouse.code}",
        supplier_name=warehouse.name,
        skus_with_quantities=skus_with_quantities,
    )


@pytest.mark.django_db
class TestSyncWarehouseToCheckout:
    def test_creates_stock_via_global_supplier(self, manual_warehouse, checkout_channel, checkout_channel_2):
        """Sync writes to existing global Supplier, creating Stock if needed."""
        from django_checkout.models import Stock, Supplier

        # Global suppliers created by checkout_channel fixtures
        report = _sync(manual_warehouse, {"SYNC-001": 42})

        assert report["channels"] == 2
        assert report["stocks_upserted"] == 2

        # Stock written to the global supplier, not a new one
        sup = Supplier.objects.get(channel=checkout_channel, is_global=True)
        stock = Stock.objects.get(product__sku="SYNC-001", supplier=sup)
        assert stock.quantity == 42

    def test_updates_existing_stock(self, manual_warehouse, checkout_channel, checkout_channel_2):
        """Re-sync updates quantity on global supplier without creating duplicates."""
        from django_checkout.models import Stock

        _sync(manual_warehouse, {"SYNC-002": 10})
        _sync(manual_warehouse, {"SYNC-002": 99})

        assert Stock.objects.filter(product__sku="SYNC-002").count() == 2  # 2 channels
        assert Stock.objects.filter(product__sku="SYNC-002").first().quantity == 99

    def test_multiple_channels(self, manual_warehouse, checkout_channel, checkout_channel_2):
        """Sync to 2 channels writes to 2 global Suppliers."""
        from django_checkout.models import Stock, Supplier

        report = _sync(manual_warehouse, {"SYNC-003": 7})

        assert report["channels"] == 2
        assert report["stocks_upserted"] == 2
        # No new suppliers created — uses existing global ones
        assert Supplier.objects.filter(is_global=True).count() == 2
        assert Stock.objects.filter(product__sku="SYNC-003").count() == 2

    def test_no_channels_skips(self, db):
        """No channels -> no sync, no error."""
        from django_checkout.services.stock_sync_service import sync_warehouse_to_checkout

        report = sync_warehouse_to_checkout(
            channels=[], supplier_code="wh-empty", supplier_name="Empty", skus_with_quantities={"X": 1}
        )
        assert report["channels"] == 0

    def test_multiple_skus_bulk(self, manual_warehouse, checkout_channel, checkout_channel_2):
        """Bulk sync of multiple SKUs across all channels."""
        from django_checkout.models import Stock

        report = _sync(manual_warehouse, {"B-001": 10, "B-002": 20, "B-003": 30})
        # 2 channels x 3 SKUs = 6 Stock records
        assert report["stocks_upserted"] == 6
        assert Stock.objects.filter(product__sku__startswith="B-").count() == 6

    def test_idempotent_no_duplicate_suppliers(self, manual_warehouse, checkout_channel, checkout_channel_2):
        """Calling sync twice doesn't create new Suppliers — always uses global."""
        from django_checkout.models import Supplier

        _sync(manual_warehouse, {"IDEM-001": 5})
        _sync(manual_warehouse, {"IDEM-001": 5})

        # Still only global suppliers exist
        assert Supplier.objects.filter(channel=checkout_channel).count() == 1
        assert Supplier.objects.get(channel=checkout_channel).is_global is True
