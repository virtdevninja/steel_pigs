#   Copyright 2026 Michael Rice <michael@michaelrice.org>
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

"""Alembic runtime environment for steel_pigs.

Two callers reach this file:

* The CLI (``python -m steel_pigs.db upgrade``) and direct ``alembic``
  invocations -- both supply a database URL through alembic.ini or the
  ``STEEL_PIGS_DATABASE_URL`` env var. We build an engine from that.
* The SQL plugin's startup auto-upgrade -- it passes the already-created
  engine in via ``config.attributes['engine']`` so migrations run on the
  same connection the plugin uses. This matters for in-memory SQLite,
  where each connection sees a different DB.
"""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from steel_pigs.plugins.providers.sql import Base

config = context.config

# Env var wins over alembic.ini's value so operators can point Alembic at
# the same DB the running app uses without editing the ini file.
db_url = os.environ.get("STEEL_PIGS_DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

if config.config_file_name is not None:
    # disable_existing_loggers default is True, which would silently
    # disable the steel_pigs.audit logger (not listed in alembic.ini)
    # whenever migrations run. Keep the loggers that already exist.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = config.attributes.get("engine")
    if connectable is None:
        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
