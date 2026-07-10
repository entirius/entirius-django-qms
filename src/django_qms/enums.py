# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from enum import unique

from django.db.models import TextChoices


@unique
class QMSType(TextChoices):
    ALPHA = "ALPHA"
    BRAVO = "BRAVO"
    CHARLIE = "CHARLIE"
    DELTA = "DELTA"
    ECHO = "ECHO"
    FOXTROT = "FOXTROT"
    GOLF = "GOLF"
    HOTEL = "HOTEL"
    INDIA = "INDIA"
    JULIET = "JULIET"
    KILO = "KILO"
    LIMA = "LIMA"
    MIKE = "MIKE"
    NOVEMBER = "NOVEMBER"
    OSCAR = "OSCAR"
    PAPA = "PAPA"
    QUEBEC = "QUEBEC"
    ROMEO = "ROMEO"
    SIERRA = "SIERRA"
    TANGO = "TANGO"
    UNIFORM = "UNIFORM"
    VICTOR = "VICTOR"
    WHISKEY = "WHISKEY"
    XRAY = "XRAY"
    ZULU = "ZULU"

    @staticmethod
    def is_implemented(qms_type: str) -> bool:
        match qms_type:
            case QMSType.ZULU:
                return True
            case QMSType.XRAY:
                return True
            case _:
                return False
