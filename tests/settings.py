# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Standalone test settings for django-qms.

Checkout-integration test modules (stock sync, signal chain, backfill) importorskip
`django_checkout`; the base suite runs with regional + qms only.
"""

import tempfile

import dj_database_url

SECRET_KEY = "test-secret-key-qms"

TMP_DIR = tempfile.gettempdir()
MEDIA_ROOT = tempfile.gettempdir()
MEDIA_URL = "/media/"
STATIC_URL = "/static/"

DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "django_regional",
    "django_utils",
    "django_pim",
    "django_qms",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

# Postgres required (django_pim squash uses UniqueConstraint nulls_distinct);
# CI provides DATABASE_URL, locally point it at any postgres 15+.
DATABASES = {
    "default": dj_database_url.config(default="postgresql://postgres:postgres@localhost:5432/test"),
}

AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]
AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
ROOT_URLCONF = "tests.urls"

# -- Legacy QMS pipeline settings --
QMS_TYPE = "XRAY"
QMS_XRAY_CHUNK_SIZE = 100
QMS_PIT_QUANTITY_BY_CHANNEL_CHUNK_SIZE = 100
QMS_PIT_QUANTITY_CHUNK_SIZE = 100
QMS_PIT_SETUP_QUANTITY_CHUNK_SIZE = 100
DATA_DIR = tempfile.gettempdir()
IMPORT_DIR = tempfile.gettempdir()
EXPORT_DIR = tempfile.gettempdir()
