.. image:: https://github.com/virtdevninja/steel_pigs/actions/workflows/ci.yml/badge.svg?branch=main
    :target: https://github.com/virtdevninja/steel_pigs/actions/workflows/ci.yml
    :alt: CI

Steel PIGS is a Python Flask app that acts as middleware: it talks to remote
inventory systems and uses their data to build custom iPXE boot scripts.
This code is based on work done by Major Hayden and Antony Messerli on a
project called miniplop.

Installing
==========
The latest release on PyPI is the legacy code; to run the modernized code
install from source ::

    git clone https://github.com/virtdevninja/steel_pigs
    cd steel_pigs
    pip install -e .

For development, install the optional ``dev`` extras (pytest + ruff +
pre-commit) ::

    pip install -e ".[dev]"


Running with Docker
===================
A multi-stage ``Dockerfile`` and a ``compose.yaml`` ship in the repo. The
compose file is a dev smoke-test (hard-coded secret, named volume for the
sqlite DB) -- not a production deployment template.

Build and run the stack ::

    docker compose up --build

Then probe the health endpoints ::

    curl http://localhost:8000/healthz
    curl http://localhost:8000/readyz

Hit a mutation endpoint with the dev token configured in ``compose.yaml`` ::

    curl -X POST http://localhost:8000/v1/update/status \
         -H "Authorization: Bearer dev-secret-do-not-use-in-prod" \
         -H "Content-Type: application/json" \
         -d '{"server_number": 555121, "boot_status": "online"}'

The image honours these env vars at runtime:

* ``STEEL_PIGS_SECRET_KEY``, ``STEEL_PIGS_DATABASE_URL``,
  ``STEEL_PIGS_API_TOKEN`` -- see *Getting Started* below.
* ``GUNICORN_WORKERS`` -- worker count, default ``2``.
* ``GUNICORN_BIND`` -- bind address, default ``0.0.0.0:8000``.

For real deployments, override every secret env var and run a separate
container per replica behind a load balancer.


Getting Started
===============
Once steel_pigs is installed you need to create your own custom plugins.
For help doing that see the `wiki <https://github.com/virtdevninja/steel-pigs/wiki>`_.

Configuration is driven by environment variables:

* ``STEEL_PIGS_SECRET_KEY`` -- Flask session / CSRF key. Set this in
  production. If unset, a random key is generated at import time and a
  warning is logged.
* ``STEEL_PIGS_DATABASE_URL`` -- SQLAlchemy URL for the bundled ``SQL``
  inventory plugin. Defaults to ``sqlite:///steel_pigs.db`` (a file in
  CWD). Pointing at ``:memory:`` logs a startup warning -- it's the
  right call for tests but almost always wrong elsewhere.
* ``STEEL_PIGS_API_TOKEN`` -- bearer token expected on the mutation
  endpoints (``POST /v1/update/*``). The bundled ``EnvTokenAuth`` plugin
  rejects every request if this is unset. Swap to a different auth
  plugin (LDAP, OIDC, ...) by editing ``AUTH_PROVIDER_PLUGIN`` in
  ``pigs_config.py``.

Plugin selection lives in ``steel_pigs/pigs_config.py``; swap the dicts to
point at your own plugins.

Once you have your plugins built, installed, and configured, serve the app
with your favourite WSGI server. With gunicorn ::

    gunicorn steel_pigs.webapp:app

Then put nginx (or Apache HTTPD with mod_wsgi) in front of it.


Database migrations
===================
The bundled ``SQL`` inventory plugin manages schema with Alembic. On
startup, the plugin runs ``alembic upgrade head`` against the configured
database. For the default SQLite backend the file lock serializes
worker startup, so multi-worker gunicorn processes are safe.

For Postgres / MySQL deployments, the workers can race on first
migration. Run migrations as a pre-deploy step instead ::

    python -m steel_pigs.db upgrade

The CLI wraps the most-used Alembic subcommands. ``--url`` overrides
``$STEEL_PIGS_DATABASE_URL`` overrides ``alembic.ini`` ::

    python -m steel_pigs.db current                # current revision
    python -m steel_pigs.db upgrade head           # apply all pending
    python -m steel_pigs.db downgrade -1           # back out the last
    python -m steel_pigs.db revision -m "..."      # create empty revision
    python -m steel_pigs.db revision -m "..." --autogenerate  # diff models vs DB
    python -m steel_pigs.db stamp head             # mark DB at head w/o running
    python -m steel_pigs.db history                # show all revisions

After editing the ORM models, generate a new migration with
``--autogenerate`` and review the resulting file before committing.


Contributing
============
Fork the repo, create a feature branch, open a pull request against
``main``. Tests are required where applicable.

After cloning, install the pre-commit hooks once. They run ruff and a
handful of hygiene checks on every commit, and CI runs the same hooks
so what you see locally is what CI checks ::

    pre-commit install

Run all hooks against the whole tree before pushing if you want to be
sure ::

    pre-commit run --all-files

Run the test suite with pytest ::

    pytest

If you wish to contribute a plugin please use the
`steel_pigs_plugins <https://github.com/virtdevninja/steel_pigs_plugins>`_
project on GitHub.


Python Support
==============
* Python 3.10+ (Flask 3, SQLAlchemy 2, bootstrap-flask)

Earlier versions of steel_pigs targeted Python 2.7; that support was
dropped during the modernization.


Reporting Issues
================
To report a problem or request a feature open an
`issue <https://github.com/virtdevninja/steel-pigs/issues>`_ on GitHub.


Usage Examples
==============
See the `wiki <https://github.com/virtdevninja/steel-pigs/wiki>`_ on GitHub.
