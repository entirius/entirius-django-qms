# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging

import celery
import celery.states
from celery import shared_task
from celery_once import QueueOnce
from django.utils import timezone

from django_qms.bi import QM_ManageQuantitiesStartEvent
from django_qms.enums import QMSType
from django_qms.models import Channel, ZuluPointInTime

# Submodule imports (not the package) — see xray/manage_quantities.py.
from django_qms.tasks.zulu.create_pit_quantity import zulu_create_pit_quantity
from django_qms.tasks.zulu.create_pit_quantity_by_channel import zulu_create_pit_quantity_by_channel
from django_qms.tasks.zulu.process_chain_is_done import zulu_process_chain_is_done
from django_qms.tasks.zulu.process_chain_is_starting import zulu_process_chain_is_starting
from django_qms.tasks.zulu.push_data import zulu_push_data
from django_qms.tasks.zulu.remove_old_pits import zulu_remove_old_pits
from django_qms.tasks.zulu.split_and_setup_quantity import zulu_split_and_setup_quantity

DOMAIN_NAME = QMSType.ZULU

logger = logging.getLogger(__name__)


@shared_task(base=QueueOnce, queue="quantities")
def zulu_manage_quantities() -> dict:
    """
    1. Create snapshot
    2. For every "input" channel (weight = 0) import data from all its storages
    4. split numbers in snapshot
    5. For every "output" channel export quantities
    :return:
    """

    already_running_pits = ZuluPointInTime.objects.filter(proces_status=ZuluPointInTime.ProcessStatus.PROCESSING)
    if len(already_running_pits) > 0:
        for already_running_pit in already_running_pits:
            logger.warning(
                f"QMS {DOMAIN_NAME}: Can not start new Manage Quantities process, "
                f"pit='{already_running_pit.pit}' is already processing"
            )
        return {"status": "skipping"}

    waiting_pits = ZuluPointInTime.objects.filter(proces_status=ZuluPointInTime.ProcessStatus.WAITING)
    if len(waiting_pits) > 0:
        for waiting_pit in waiting_pits:
            logger.warning(
                f"QMS {DOMAIN_NAME}: Can not start new Manage Quantities process, "
                f"pit='{waiting_pit.pit}' is already waiting"
            )
        return {"status": "skipping"}

    pit = ZuluPointInTime.objects.create(pit=timezone.now())
    bev = QM_ManageQuantitiesStartEvent(pit=pit.pit, is_ongoing_event=True)
    try:
        # pull tasks
        input_channels = Channel.objects.filter(qms_type=QMSType.ZULU).exclude(stock_weight__gt=0)
        pull_tasks = (zulu_create_pit_quantity_by_channel.si(channel.pk, pit.id) for channel in input_channels)
        pull_tasks_group = celery.group(*pull_tasks)

        # push tasks
        output_channels = Channel.objects.filter(qms_type=QMSType.ZULU).exclude(stock_weight=0)
        push_tasks = (zulu_push_data.si(channel.pk, pit.id) for channel in output_channels)
        push_tasks_group = celery.group(*push_tasks)

        # process
        process_chain = celery.chain(
            zulu_process_chain_is_starting.si(pit.id),
            pull_tasks_group,
            zulu_create_pit_quantity.si(pit.id),
            zulu_split_and_setup_quantity.si(pit.id),
            push_tasks_group,
            zulu_process_chain_is_done.si(pit.id),
            zulu_remove_old_pits.si(),
        )
        process_chain.delay()
        bev.finish_with_success(finish_tag="process chain is created")
        return {"status": "ok"}
    except BaseException as e:
        bev.finish_with_exception(e)
        pit.set_as_error()
        raise e
