# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for management commands: warehouse_import_csv and backfill_warehouse."""

import importlib.util
import io
import tempfile

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from django_qms.models import Warehouse, WarehouseStock


@pytest.mark.django_db
class TestWarehouseImportCSVCommand:
    def test_import_valid_csv(self, manual_warehouse):
        csv_content = "sku,quantity\nCMD-001,10\nCMD-002,20\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            f.flush()
            out = io.StringIO()
            call_command("warehouse_import_csv", warehouse_code="wh-manual", file=f.name, stdout=out)

        assert WarehouseStock.objects.filter(warehouse=manual_warehouse).count() == 2
        assert "Imported: 2" in out.getvalue()

    def test_import_unknown_warehouse(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("sku,quantity\nX,1\n")
            f.flush()
            with pytest.raises(CommandError, match="not found"):
                call_command("warehouse_import_csv", warehouse_code="nonexistent", file=f.name)


@pytest.mark.django_db
@pytest.mark.skipif(importlib.util.find_spec("django_checkout") is None, reason="django_checkout not installed")
class TestBackfillWarehouseCommand:
    def test_backfill_creates_warehouse_and_stock(self, checkout_channel):
        from django_checkout.models import ProductRepresentation, Stock, Supplier

        # Use the global supplier created by checkout_channel fixture
        supplier = Supplier.objects.get(channel=checkout_channel, is_global=True)
        supplier.code = "OLD-SUP"
        supplier.save()
        pr = ProductRepresentation.objects.create(sku="BF-001", channel=checkout_channel)
        Stock.objects.create(product=pr, supplier=supplier, quantity=77)

        out = io.StringIO()
        call_command("backfill_warehouse", supplier_code="OLD-SUP", channel_idx="test-channel", stdout=out)

        wh = Warehouse.objects.get(code="OLD-SUP")
        assert wh.source_type == "integration"
        assert wh.channels.filter(idx="test-channel").exists()
        assert WarehouseStock.objects.get(warehouse=wh, sku="BF-001").quantity == 77
        assert "Backfilled 1" in out.getvalue()

    def test_backfill_dry_run(self, checkout_channel):
        from django_checkout.models import ProductRepresentation, Stock, Supplier

        supplier = Supplier.objects.get(channel=checkout_channel, is_global=True)
        supplier.code = "DRY-SUP"
        supplier.save()
        pr = ProductRepresentation.objects.create(sku="DRY-001", channel=checkout_channel)
        Stock.objects.create(product=pr, supplier=supplier, quantity=5)

        out = io.StringIO()
        call_command(
            "backfill_warehouse", supplier_code="DRY-SUP", channel_idx="test-channel", dry_run=True, stdout=out
        )

        assert not Warehouse.objects.filter(code="DRY-SUP").exists()
        assert "DRY RUN" in out.getvalue()

    def test_backfill_unknown_channel(self):
        with pytest.raises(CommandError, match="not found"):
            call_command("backfill_warehouse", supplier_code="X", channel_idx="nonexistent")

    def test_backfill_unknown_supplier(self, checkout_channel):
        with pytest.raises(CommandError, match="not found"):
            call_command("backfill_warehouse", supplier_code="NOSUP", channel_idx="test-channel")
