# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest
from django.apps import apps

# Importable is not enough: the checkout models load only when the app is in INSTALLED_APPS.
requires_checkout = pytest.mark.skipif(
    not apps.is_installed("django_checkout"), reason="django_checkout is not in INSTALLED_APPS"
)
