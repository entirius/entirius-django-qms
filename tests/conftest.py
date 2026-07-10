# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from django_qms.models import SourceType, Warehouse, WarehouseStock

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(username="admin", password="admin123", email="admin@test.com")


@pytest.fixture
def admin_client(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(username="user", password="user123", email="user@test.com")


@pytest.fixture
def regular_client(api_client, regular_user):
    api_client.force_authenticate(user=regular_user)
    return api_client


# --- QMS Channel fixtures (for Warehouse.channels M2M) ---


@pytest.fixture
def qms_channel(db):
    """QMS Channel — used for Warehouse.channels M2M."""
    from django_qms.models import Channel

    return Channel.objects.create(idx="test-channel", name="test-channel", qms_type="XRAY")


@pytest.fixture
def qms_channel_2(db):
    from django_qms.models import Channel

    return Channel.objects.create(idx="test-channel-2", name="test-channel-2", qms_type="XRAY")


# --- Checkout Channel fixtures (for sync tests that need actual checkout objects) ---


@pytest.fixture
def _regional_deps(db):
    """Create regional dependencies needed by Checkout Channel."""
    from django_regional.models import Country, Currency, Language

    lang, _ = Language.objects.get_or_create(
        iso2="en", defaults={"iso3": "eng", "name_en": "English", "name_pl": "Angielski", "name_source": "English"}
    )
    currency, _ = Currency.objects.get_or_create(
        iso3="EUR", defaults={"name_en": "Euro", "name_pl": "Euro", "symbol": "€"}
    )
    country = Country.objects.filter(iso2="PL").first()
    if not country:
        Country.objects.bulk_create([Country(iso2="PL", iso3="POL", name_en="Poland", name_pl="Polska")])
        country = Country.objects.get(iso2="PL")
    return lang, currency, country


@pytest.fixture
def checkout_channel(_regional_deps, qms_channel):
    """Checkout Channel with global Supplier — mirrors QMS channel for sync/backfill tests."""
    from django_checkout.models import Channel, Supplier

    lang, currency, country = _regional_deps
    ch = Channel.objects.create(
        idx="test-channel",
        label="Test Channel",
        default_language=lang,
        default_currency=currency,
        default_country=country,
    )
    Supplier.objects.create(code="test-channel", name="Test Channel Global", is_global=True, channel=ch)
    return ch


@pytest.fixture
def checkout_channel_2(_regional_deps, qms_channel_2):
    from django_checkout.models import Channel, Supplier

    lang, currency, country = _regional_deps
    ch = Channel.objects.create(
        idx="test-channel-2",
        label="Test Channel 2",
        default_language=lang,
        default_currency=currency,
        default_country=country,
    )
    Supplier.objects.create(code="test-channel-2", name="Test Channel 2 Global", is_global=True, channel=ch)
    return ch


# --- Warehouse fixtures (use QMS Channels) ---


@pytest.fixture
def manual_warehouse(db, qms_channel, qms_channel_2):
    wh = Warehouse.objects.create(
        code="wh-manual",
        name="Manual Warehouse",
        description="Test manual warehouse",
        source_type=SourceType.MANUAL,
        is_active=True,
    )
    wh.channels.add(qms_channel, qms_channel_2)
    return wh


@pytest.fixture
def integration_warehouse(db, qms_channel, qms_channel_2):
    wh = Warehouse.objects.create(
        code="wh-integration", name="Integration Warehouse", source_type=SourceType.INTEGRATION, is_active=True
    )
    wh.channels.add(qms_channel, qms_channel_2)
    return wh


@pytest.fixture
def inactive_warehouse(db):
    return Warehouse.objects.create(
        code="wh-inactive", name="Inactive Warehouse", source_type=SourceType.MANUAL, is_active=False
    )


@pytest.fixture
def stock_items(manual_warehouse):
    """Create sample stock records for manual warehouse."""
    items = [
        WarehouseStock(warehouse=manual_warehouse, sku="SKU-001", quantity=100),
        WarehouseStock(warehouse=manual_warehouse, sku="SKU-002", quantity=50),
        WarehouseStock(warehouse=manual_warehouse, sku="SKU-003", quantity=0),
    ]
    return WarehouseStock.objects.bulk_create(items)
