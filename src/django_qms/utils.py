# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


def format_package_name(package_name: str) -> str:
    return str(package_name).replace("models.", "").replace(".", "_")


def zulu_print_status():
    from django_qms.models import ZuluPointInTime

    cnt = len(
        ZuluPointInTime.objects.filter(
            proces_status__in=[ZuluPointInTime.ProcessStatus.PROCESSING, ZuluPointInTime.ProcessStatus.WAITING]
        )
    )
    if cnt > 0:
        print("QMS Zulu is processing")
    else:
        print("QMS Zulu is not processing")


def xray_print_status():
    from django_qms.models import XrayPointInTime

    cnt = len(
        XrayPointInTime.objects.filter(
            proces_status__in=[XrayPointInTime.ProcessStatus.PROCESSING, XrayPointInTime.ProcessStatus.WAITING]
        )
    )
    if cnt > 0:
        print("QMS XRay is processing")
    else:
        print("QMS XRay is not processing")
