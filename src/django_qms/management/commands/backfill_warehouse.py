# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Backfill Warehouse records from existing Checkout Stock data.

Usage:
    manage.py backfill_warehouse --supplier-code=SUPPLIER_001 --channel-idx=default-europe [--dry-run]
"""

from django.core.management.base import BaseCommand, CommandError

from django_qms.models import SourceType, Warehouse
from django_qms.services import warehouse_service

DRY_RUN_PREVIEW_LIMIT = 20


class Command(BaseCommand):
    help = "Create Warehouse + WarehouseStock records from existing Checkout Supplier/Stock data"

    def add_arguments(self, parser):
        parser.add_argument("--supplier-code", required=True, help="Checkout Supplier code")
        parser.add_argument("--channel-idx", required=True, help="Checkout Channel idx")
        parser.add_argument("--warehouse-code", help="Warehouse code to create (defaults to supplier code)")
        parser.add_argument("--dry-run", action="store_true", help="Preview without writing")

    def handle(self, *args, **options):
        supplier_code = options["supplier_code"]
        channel_idx = options["channel_idx"]
        warehouse_code = options["warehouse_code"] or supplier_code
        dry_run = options["dry_run"]

        try:
            from django_checkout.models import Channel, Stock, Supplier
        except ImportError as exc:
            raise CommandError("django_checkout is required for backfill") from exc

        try:
            channel = Channel.objects.get(idx=channel_idx)
        except Channel.DoesNotExist as exc:
            raise CommandError(f"Channel '{channel_idx}' not found") from exc

        try:
            supplier = Supplier.objects.get(code=supplier_code, channel=channel)
        except Supplier.DoesNotExist as exc:
            raise CommandError(f"Supplier '{supplier_code}' not found for channel '{channel_idx}'") from exc

        stocks = Stock.objects.filter(supplier=supplier).select_related("product")
        stock_data = [(s.product.sku, s.quantity) for s in stocks]

        self.stdout.write(f"Found {len(stock_data)} Stock records for {supplier_code}/{channel_idx}")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be made"))
            for sku, qty in stock_data[:DRY_RUN_PREVIEW_LIMIT]:
                self.stdout.write(f"  {sku}: {qty}")
            if len(stock_data) > DRY_RUN_PREVIEW_LIMIT:
                self.stdout.write(f"  ... and {len(stock_data) - DRY_RUN_PREVIEW_LIMIT} more")
            return

        warehouse, created = Warehouse.objects.get_or_create(
            code=warehouse_code,
            defaults={
                "name": f"Backfilled from {supplier_code}",
                "source_type": SourceType.INTEGRATION,
                "is_active": True,
            },
        )
        if created:
            # Link to QMS Channel (same idx as checkout channel)
            from django_qms.models import Channel as QmsChannel

            qms_ch, _ = QmsChannel.objects.get_or_create(idx=channel_idx, defaults={"name": channel_idx})
            warehouse.channels.add(qms_ch)
            self.stdout.write(f"Created Warehouse '{warehouse_code}'")
        else:
            self.stdout.write(f"Warehouse '{warehouse_code}' already exists, adding stock")

        items = [{"sku": sku, "quantity": qty} for sku, qty in stock_data]
        warehouse_service.bulk_upsert_stock(warehouse, items, allow_integration=True)
        warehouse_service.update_last_synced(warehouse)

        self.stdout.write(self.style.SUCCESS(f"Backfilled {len(items)} stock records"))
