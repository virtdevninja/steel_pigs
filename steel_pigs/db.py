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

"""Database management entrypoint.

Two consumers:

* :func:`make_alembic_config` -- used by ``SQL.__init__`` to auto-upgrade
  the schema at startup, and by the CLI below.
* The ``python -m steel_pigs.db`` CLI -- a thin wrapper over the Alembic
  subcommands operators reach for most often (``upgrade``, ``downgrade``,
  ``revision``, ``current``, ``history``, ``stamp``).
"""

import argparse
import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

PACKAGE_DIR = Path(__file__).resolve().parent
ALEMBIC_INI = PACKAGE_DIR / "alembic.ini"
SCRIPT_LOCATION = PACKAGE_DIR / "alembic"


def make_alembic_config(*, db_url=None, engine=None) -> Config:
    """Build an Alembic Config pointing at the in-package migrations.

    ``db_url`` overrides the URL from alembic.ini. ``engine`` (preferred
    when calling from inside the SQL plugin) is threaded through
    ``config.attributes`` so the migration runs on the same connection
    the plugin uses -- required for in-memory SQLite, where each
    connection sees a separate database.
    """
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(SCRIPT_LOCATION))
    if db_url is not None:
        config.set_main_option("sqlalchemy.url", db_url)
    if engine is not None:
        config.attributes["engine"] = engine
    return config


def _cli_config(args):
    """Build a Config from CLI args + environment.

    The ``--url`` arg wins over ``STEEL_PIGS_DATABASE_URL`` wins over the
    fallback in alembic.ini.
    """
    db_url = args.url or os.environ.get("STEEL_PIGS_DATABASE_URL")
    return make_alembic_config(db_url=db_url)


def _cmd_upgrade(args):
    command.upgrade(_cli_config(args), args.revision)


def _cmd_downgrade(args):
    command.downgrade(_cli_config(args), args.revision)


def _cmd_revision(args):
    command.revision(
        _cli_config(args),
        message=args.message,
        autogenerate=args.autogenerate,
    )


def _cmd_current(args):
    command.current(_cli_config(args), verbose=args.verbose)


def _cmd_history(args):
    command.history(_cli_config(args), verbose=args.verbose)


def _cmd_stamp(args):
    command.stamp(_cli_config(args), args.revision)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="python -m steel_pigs.db",
        description="Database migration commands for steel_pigs.",
    )
    parser.add_argument(
        "--url",
        help="SQLAlchemy DB URL. Falls back to $STEEL_PIGS_DATABASE_URL then alembic.ini.",
    )
    subs = parser.add_subparsers(dest="cmd", required=True)

    p_up = subs.add_parser("upgrade", help="Upgrade to a revision (default: head).")
    p_up.add_argument("revision", nargs="?", default="head")
    p_up.set_defaults(func=_cmd_upgrade)

    p_down = subs.add_parser("downgrade", help="Downgrade to a revision.")
    p_down.add_argument("revision")
    p_down.set_defaults(func=_cmd_downgrade)

    p_rev = subs.add_parser("revision", help="Create a new revision file.")
    p_rev.add_argument("-m", "--message", required=True)
    p_rev.add_argument(
        "--autogenerate",
        action="store_true",
        help="Populate the revision by diffing models against the live DB.",
    )
    p_rev.set_defaults(func=_cmd_revision)

    p_cur = subs.add_parser("current", help="Show the current revision.")
    p_cur.add_argument("-v", "--verbose", action="store_true")
    p_cur.set_defaults(func=_cmd_current)

    p_hist = subs.add_parser("history", help="Show the revision history.")
    p_hist.add_argument("-v", "--verbose", action="store_true")
    p_hist.set_defaults(func=_cmd_history)

    p_stamp = subs.add_parser(
        "stamp",
        help="Mark the DB as at a revision without running migrations.",
    )
    p_stamp.add_argument("revision")
    p_stamp.set_defaults(func=_cmd_stamp)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
