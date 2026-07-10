# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Import stock quantities from a CSV file into a warehouse.

Usage:
    manage.py warehouse_import_csv --warehouse-code=wh-sap --file=/path/to/qty.csv
"""

from django.core.management.base import BaseCommand, CommandError

from django_qms.models import Warehouse
from django_qms.services import warehouse_service
from django_qms.services.csv_import_service import import_csv_to_warehouse


class Command(BaseCommand):
    help = "Import stock quantities from a CSV file into a warehouse"

    def add_arguments(self, parser):
        parser.add_argument("--warehouse-code", required=True, help="Warehouse code (e.g., wh-sap)")
        parser.add_argument("--file", required=True, help="Path to CSV file")

    def handle(self, *args, **options):
        code = options["warehouse_code"]
        filepath = options["file"]

        try:
            warehouse = warehouse_service.get_warehouse(code)
        except Warehouse.DoesNotExist as exc:
            raise CommandError(f"Warehouse '{code}' not found") from exc

        try:
            with open(filepath, "rb") as f:
                report = import_csv_to_warehouse(warehouse, f, allow_integration=True)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(f"Parsed:   {report['rows_parsed']}")
        self.stdout.write(f"Imported: {report['rows_imported']}")
        self.stdout.write(f"Skipped:  {report['rows_skipped']}")
        if report["errors"]:
            self.stdout.write(self.style.WARNING(f"Errors (first {len(report['errors'])}):"))
            for err in report["errors"]:
                self.stdout.write(f"  Row {err['row']}: {err['error']}")
        self.stdout.write(self.style.SUCCESS("Done"))
