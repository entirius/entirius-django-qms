# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging

from celery import shared_task
from celery_once import QueueOnce

from django_qms.bi import QM_ProcessChainIsStartingEvent
from django_qms.models import ZuluPointInTime

logger = logging.getLogger(__name__)


@shared_task(base=QueueOnce, queue="quantities")
def zulu_process_chain_is_starting(pit_id) -> dict:
    pit = ZuluPointInTime.objects.get(pk=pit_id)
    bev = QM_ProcessChainIsStartingEvent(pit=pit.pit, is_ongoing_event=True)
    try:
        if pit.proces_status != ZuluPointInTime.ProcessStatus.WAITING:
            raise Exception(f"Can not start process chain on pit={pit.pit}, status must be WAITING")
        pit.set_as_processing()
        bev.finish_with_success(finish_tag="process chain is properly started")
        return {"status": "ok"}
    except BaseException as e:
        bev.finish_with_exception(e)
        pit.set_as_error()
        raise e
