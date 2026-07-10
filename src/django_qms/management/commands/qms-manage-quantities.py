# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from celery_once.tasks import AlreadyQueued
from django.core.management.base import BaseCommand

from django_qms.enums import QMSType
from django_qms.settings import QMS_TYPE
from django_qms.tasks import xray_manage_quantities, zulu_manage_quantities


class Command(BaseCommand):
    help = "Import quantities, split them then export to channels"

    def add_arguments(self, parser):
        parser.add_argument("--channel_idx", type=str, help="Volkanos Channel/Shop IDX")

    def handle(self, *args, **options):
        channel_idx = options["channel_idx"]
        if channel_idx:
            self.stdout.write(f"Channel IDX: {channel_idx}")

        try:
            match QMS_TYPE:
                case QMSType.ZULU:
                    if channel_idx:
                        self.stdout.write(
                            self.style.WARNING(
                                "Choosing channel_idx is not implemented for QMS Zulu and it will be ignored"
                            )
                        )
                    zulu_manage_quantities.delay()
                case QMSType.XRAY:
                    xray_manage_quantities(channel_idx=channel_idx)
                case _:
                    raise NotImplementedError(f"QMS_TYPE={QMS_TYPE} is not implemented")

            self.stdout.write(self.style.SUCCESS("done"))
        except AlreadyQueued:
            self.stdout.write("Task for was already queued")
