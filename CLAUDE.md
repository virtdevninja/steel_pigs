# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Steel PIGS is an APIFlask service that serves dynamically-generated iPXE boot scripts. Incoming PXE requests (by server number, MAC, or switch name/port) are resolved against a pluggable inventory backend, and responses are rendered from Jinja2 iPXE templates.

The project targets **Python 3.10+** and runs on APIFlask 3 (Flask 3 underneath), SQLAlchemy 2 (`Mapped[]` + `select()`), bootstrap-flask (Bootstrap 5), flask-wtf 1.x, pytest, and ruff. Packaging is pyproject.toml (PEP 621); there is no `setup.py`, `requirements.txt`, or `MANIFEST.in`. The HTTP API is documented by the auto-generated OpenAPI 3 spec at `/openapi.json` with Swagger UI at `/docs`.

The default branch is `main` (renamed from `master`); the old `development` branch was deleted as part of the modernization. PRs target `main`.

## Commands

```bash
# Install (Python 3.10+ venv). [dev] adds pytest + ruff + pre-commit.
pip install -e ".[dev]"

# Run the dev server (Flask debug mode, port 5000)
python -m steel_pigs.webapp

# Or via a WSGI server in production
gunicorn steel_pigs.webapp:app           # uses the module-level `app = create_app()`
gunicorn "steel_pigs.webapp:create_app()"  # equivalent factory form

# Tests
pytest                                                    # full suite
pytest steel_pigs/tests/test_flask_app.py                 # one file
pytest steel_pigs/tests/test_flask_app.py::TestFlaskApp::test_versions_json

# Lint / format -- pre-commit drives ruff + hygiene hooks (CI runs the same)
pre-commit install              # one-time, sets up the git hook
pre-commit run --all-files      # run every hook against the whole tree
ruff check . && ruff format .   # if you want to skip pre-commit and just run ruff
```

## Environment variables

* `STEEL_PIGS_SECRET_KEY` — Flask session / CSRF key. **Set in production.** If unset, `pigs_config.py` generates a random key at import time and logs a warning; sessions and CSRF tokens won't survive a restart.
* `STEEL_PIGS_DATABASE_URL` — SQLAlchemy URL for the bundled `SQL` inventory plugin. Defaults to `sqlite:///steel_pigs.db`. `:memory:` logs a warning at startup (tests opt back into it via `steel_pigs/tests/conftest.py`).

Plugin *selection* (which class to load per role) stays code-level in `pigs_config.py`; only secrets / per-deployment values come from env.

## Architecture

### App factory

`steel_pigs/webapp.py` exports `create_app(config_overrides=None, plugins=None) -> Flask`. The module also creates a top-level `app = create_app()` so `gunicorn steel_pigs.webapp:app` keeps working.

Routes live on the `api` blueprint (defined in the same module). They look up plugins via `current_app.extensions["steel_pigs"]`, which holds a frozen `Plugins` dataclass with five fields: `server_data`, `version`, `formatter`, `pxe`, `provision`. Tests inject a pre-built `Plugins` instance via the `plugins=` kwarg so route handlers and seed data share the same SQL plugin (kills the old `_add_server_data` two-instance wart).

### Plugin loading

`create_app` resolves each plugin via `_load_plugin(spec)`, which calls `importlib.import_module(spec["namespace"])` then `getattr(module, spec["class"])(spec)`. The five spec dicts live in `pigs_config.py`:

| Config key | Role | Abstract base |
| --- | --- | --- |
| `PROVIDER_PLUGIN` | Inventory backend (server lookups, status updates) | `pluginbase.ProviderPluginBase` |
| `VERSION_PROVIDER_PLUGIN` | Software version info for `/versions` | `versionbase.VersionProviderBase` |
| `PXE_PROVIDER_PLUGIN` | Renders the iPXE script for `/pxe` | `ipxebase.PXEProvider` |
| `FORMATTER_PROVIDER_PLUGIN` | Normalizes MAC / switch / port strings | `formatterbase.DataFormatterProvider` |
| `PROVISION_PROVIDER_PLUGIN` | Returns kickstart/preseed for `/provision/os/start` | `provisionosbase.ProvisionOsBase` |

Bundled default plugins live in `steel_pigs/plugins/providers/` and are demo-grade. Real deployments override them via the external [`steel_pigs_plugins`](https://github.com/virtdevninja/steel_pigs_plugins) project — don't bake site-specific logic into the bundled defaults.

### Request flow for `/pxe`

`get_pxe_script` picks a lookup strategy from query params in this order: `number` → `server_number` → `mac` → (`switch_name` + `switch_port`). MAC and switch values are normalized through the formatter plugin before hitting the provider. The resulting server dict is handed to `pxe.generate_ipxe_script(server_data=..., request=...)`, which owns the mimetype and Flask response — `webapp.py` does not wrap it.

### SQL plugin

`plugins/providers/sql.py` uses SQLAlchemy 2.0 idioms: `DeclarativeBase`, `Mapped[T]` + `mapped_column()`, `select().where()` + `session.execute().scalar_one_or_none()`. `_session_scope()` is a context manager that commits on success and rolls back on exception. The session factory is built once in `__init__` with `expire_on_commit=False` so attributes remain accessible after commit but before the session closes.

`set_boot_os` returns the failure key `set_boot_os` while success uses `os_set` — this asymmetry is preserved for backwards compat with the original API (other setters use `status_set` for both).

Schema is managed by Alembic. `SQL.__init__` calls `alembic upgrade head` via `steel_pigs.db.make_alembic_config(engine=self.engine)` — passing the engine through `config.attributes` so migrations share the connection (matters for `:memory:`). Migration files live in `steel_pigs/alembic/versions/`; `steel_pigs/alembic.ini` is the Alembic config; `steel_pigs/db.py` is both the Config factory and the `python -m steel_pigs.db ...` CLI. For non-SQLite backends multiple workers can race on first-time `upgrade`; deploy via `python -m steel_pigs.db upgrade` as a pre-deploy step.

### Templates

`steel_pigs/templates/` holds three kinds of templates:

1. **iPXE scripts** (`pigs.ipxe`, `hardware.ipxe`) — rendered by `StaticPXEProvider` and the `/hardware` route. `StaticPXEProvider._indenter` uses `textwrap.indent` to format a JSON dump of `server_data` as `#   `-prefixed iPXE comments.
2. **Preseed fragments** (`rpc-pre-seed.j2` + `rpc_default_*.j2`) — assembled by `RPCProvision` for `/provision/os/start`.
3. **HTML for the demo frontend** (`base.html`, `home_form.html`) — `base.html` is a hand-written Bootstrap 5 shell that pulls CSS/JS via bootstrap-flask's `bootstrap.load_css()` / `bootstrap.load_js()` helpers. The navbar is inlined here (no flask-nav). `home_form.html` uses `render_form` from bootstrap-flask's `bootstrap5/form.html`.

### Frontend blueprint

`pigs_app_settings/frontend.py` is a minimal Flask-WTF demo (search-by-name form). It's wired up in `create_app` but is not part of the iPXE serving path. Forms inherit from `FlaskForm`.
