# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging

from celery import shared_task

from django_qms.enums import QMSType
from django_qms.models import ZuluPointInTime

DOMAIN_NAME = QMSType.ZULU

logger = logging.getLogger(__name__)


@shared_task(queue="quantities")
def zulu_remove_old_pits() -> dict:
    ids_to_delete = []
    pits_done = 0
    pits_error = 0
    pits_canceled = 0
    for pit in ZuluPointInTime.objects.all().order_by("-pit"):
        if pit.proces_status == ZuluPointInTime.ProcessStatus.DONE:
            pits_done += 1
            if pits_done > 3:
                ids_to_delete.append(pit.id)
        if pit.proces_status == ZuluPointInTime.ProcessStatus.CANCELED:
            pits_canceled += 1
            if pits_canceled > 1:
                ids_to_delete.append(pit.id)
        if pit.proces_status == ZuluPointInTime.ProcessStatus.ERROR:
            pits_error += 1
            if pits_error > 1:
                ids_to_delete.append(pit.id)
    if len(ids_to_delete) > 0:
        logger.info(f"QMS {DOMAIN_NAME} is removing old {len(ids_to_delete)} PITs")
        ZuluPointInTime.objects.filter(id__in=ids_to_delete).delete()
    return {"status": "ok"}
