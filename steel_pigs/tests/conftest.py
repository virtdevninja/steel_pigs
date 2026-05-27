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

"""Pytest setup that runs before any test module imports steel_pigs.

The production default for ``STEEL_PIGS_DATABASE_URL`` is a file-backed
SQLite path. That's the right default for ``docker compose up`` but
breaks tests, which need each class to get its own fresh in-memory
database. ``setdefault`` here flips the default to ``:memory:`` if the
operator hasn't set their own. ``pigs_config`` reads the env var at
module-import time, so this file must execute before any test imports
the package -- pytest's conftest discovery handles that.
"""

import os

os.environ.setdefault("STEEL_PIGS_DATABASE_URL", "sqlite:///:memory:")
