# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for Warehouse and WarehouseStock models.

Covers: CRUD, constraints, TextChoices validation, CheckConstraint.
"""

import pytest
from django.db import IntegrityError

from django_qms.models import SourceType, Warehouse, WarehouseStock


@pytest.mark.django_db
class TestWarehouseModel:
    def test_create_manual_warehouse(self, qms_channel):
        wh = Warehouse.objects.create(code="wh-test", name="Test Warehouse")
        wh.channels.add(qms_channel)
        assert wh.code == "wh-test"
        assert wh.source_type == SourceType.MANUAL
        assert wh.is_active is True
        assert wh.last_synced_at is None
        assert wh.description == ""
        assert list(wh.channels.values_list("idx", flat=True)) == ["test-channel"]

    def test_create_integration_warehouse(self):
        wh = Warehouse.objects.create(
            code="wh-sap",
            name="SAP Warehouse",
            source_type=SourceType.INTEGRATION,
            description="Synced from SAP hourly",
        )
        assert wh.source_type == SourceType.INTEGRATION
        assert wh.description == "Synced from SAP hourly"

    def test_code_uniqueness(self, manual_warehouse):
        with pytest.raises(IntegrityError):
            Warehouse.objects.create(code="wh-manual", name="Duplicate")

    def test_str_representation(self, manual_warehouse):
        assert str(manual_warehouse) == "Manual Warehouse (wh-manual)"

    def test_source_type_choices(self):
        assert SourceType.MANUAL == "manual"
        assert SourceType.INTEGRATION == "integration"
        assert len(SourceType.choices) == 2

    def test_is_active_default_true(self):
        wh = Warehouse.objects.create(code="wh-default", name="Default")
        assert wh.is_active is True

    def test_channels_m2m(self, manual_warehouse, qms_channel_2):
        # manual_warehouse already has qms_channel + qms_channel_2
        assert manual_warehouse.channels.count() == 2

    def test_ordering_by_name(self, db):
        Warehouse.objects.create(code="wh-z", name="Zebra")
        Warehouse.objects.create(code="wh-a", name="Alpha")
        names = list(Warehouse.objects.values_list("name", flat=True))
        assert names == ["Alpha", "Zebra"]


@pytest.mark.django_db
class TestWarehouseStockModel:
    def test_create_stock(self, manual_warehouse):
        stock = WarehouseStock.objects.create(warehouse=manual_warehouse, sku="SKU-001", quantity=100)
        assert stock.sku == "SKU-001"
        assert stock.quantity == 100

    def test_quantity_default_zero(self, manual_warehouse):
        stock = WarehouseStock.objects.create(warehouse=manual_warehouse, sku="SKU-ZERO")
        assert stock.quantity == 0

    def test_negative_quantity_raises_integrity_error(self, manual_warehouse):
        with pytest.raises(IntegrityError):
            WarehouseStock.objects.create(warehouse=manual_warehouse, sku="SKU-NEG", quantity=-1)

    def test_unique_together_warehouse_sku(self, manual_warehouse):
        WarehouseStock.objects.create(warehouse=manual_warehouse, sku="SKU-DUP", quantity=10)
        with pytest.raises(IntegrityError):
            WarehouseStock.objects.create(warehouse=manual_warehouse, sku="SKU-DUP", quantity=20)

    def test_str_representation(self, manual_warehouse):
        stock = WarehouseStock.objects.create(warehouse=manual_warehouse, sku="SKU-001", quantity=42)
        assert str(stock) == "wh-manual:SKU-001 = 42"

    def test_cascade_delete(self, manual_warehouse):
        WarehouseStock.objects.create(warehouse=manual_warehouse, sku="SKU-DEL", quantity=5)
        manual_warehouse.delete()
        assert WarehouseStock.objects.count() == 0
