# django-qms

Quantity Management System for Volkanos — warehouse-level stock management with CSV import,
admin API and signal-driven propagation to downstream stock consumers.

## Installation

```shell
pip install entirius-django-qms
```

Add the app to your project:

```python
INSTALLED_APPS = [
    ...
    "django_qms",
]
```

## Development

```shell
make install     # sync dependencies (uv)
make check       # lint + format check (ruff)
make test        # test suite (pytest + pytest-django)
```

Development and agent instructions: [AGENTS.md](AGENTS.md).

## License

Mozilla Public License 2.0 — see [LICENSE](LICENSE).
