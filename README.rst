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

For development, install the optional ``dev`` extras (pytest + ruff) ::

    pip install -e ".[dev]"


Getting Started
===============
Once steel_pigs is installed you need to create your own custom plugins.
For help doing that see the `wiki <https://github.com/virtdevninja/steel-pigs/wiki>`_.

Configuration is driven by environment variables:

* ``STEEL_PIGS_SECRET_KEY`` -- Flask session / CSRF key. Set this in
  production. If unset, a random key is generated at import time and a
  warning is logged.
* ``STEEL_PIGS_DATABASE_URL`` -- SQLAlchemy URL for the bundled ``SQL``
  inventory plugin. Defaults to ``sqlite:///:memory:``.

Plugin selection lives in ``steel_pigs/pigs_config.py``; swap the dicts to
point at your own plugins.

Once you have your plugins built, installed, and configured, serve the app
with your favourite WSGI server. With gunicorn ::

    gunicorn steel_pigs.webapp:app

Then put nginx (or Apache HTTPD with mod_wsgi) in front of it.


Contributing
============
Fork the repo, create a feature branch, open a pull request against
``main``. Tests are required where applicable.

Lint and format with ruff before pushing ::

    ruff check .
    ruff format .

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
