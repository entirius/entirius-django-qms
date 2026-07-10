# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.management.base import BaseCommand

from django_qms.enums import QMSType
from django_qms.settings import QMS_TYPE
from django_qms.utils import xray_print_status, zulu_print_status


class Command(BaseCommand):
    help = "Prints QMS process status"

    def handle(self, *args, **options):
        match QMS_TYPE:
            case QMSType.ZULU:
                zulu_print_status()
            case QMSType.XRAY:
                xray_print_status()
            case _:
                raise NotImplementedError(f"QMS_TYPE={QMS_TYPE} is not implemented")
