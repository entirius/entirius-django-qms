# Changelog

## [Unreleased]

- Access: the module declares its own access areas on its AppConfig and its admin views (copied from the
  entirius-django-access defaults; behaviour unchanged).

## 4.0.2 — 2026-08-06

- Stamp `last_synced_at` after integration backfill.

## 4.0.1 — 2026-07-15

- Substitute only the `csv_path` placeholders the host actually defines;
  support pathlib settings dirs.

## 4.0.0 — 2026-07-10

- Initial public release: quantity management — warehouses (manual and
  integration-fed), channel-scoped stock, and checkout synchronization.
- Migrations squashed into a single initial migration for the Entirius epoch.
