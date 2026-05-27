#   Copyright 2015 Michael Rice <michael@michaelrice.org>
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

import logging
from contextlib import contextmanager

from alembic import command
from sqlalchemy import ForeignKey, String, create_engine, select
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    sessionmaker,
)

from steel_pigs.db import make_alembic_config

from .pluginbase import ProviderPluginBase

log = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


class ProvisionZone(Base):
    __tablename__ = "ProvisionZone"

    id: Mapped[int] = mapped_column(primary_key=True)
    zone_name: Mapped[str] = mapped_column(String(128), unique=True)
    provision_img_host: Mapped[str] = mapped_column(String(128))
    provision_mirror_host: Mapped[str] = mapped_column(String(128))


class ServerDataModel(Base):
    __tablename__ = "ServerData"

    id: Mapped[int] = mapped_column(primary_key=True)
    server_number: Mapped[int] = mapped_column(unique=True)
    primary_ip: Mapped[str] = mapped_column(String(15))
    primary_gw: Mapped[str] = mapped_column(String(15))
    primary_nm: Mapped[str] = mapped_column(String(15))
    primary_mac: Mapped[str] = mapped_column(String(20))
    drac_ip: Mapped[str | None] = mapped_column(String(15))
    drac_gw: Mapped[str | None] = mapped_column(String(15))
    drac_nm: Mapped[str | None] = mapped_column(String(15))
    hostname: Mapped[str] = mapped_column(String(255))
    dns_domain_name: Mapped[str] = mapped_column(String(255), default="rpc.local")
    dns_server_primary: Mapped[str] = mapped_column(String(15))
    dns_server_secondary: Mapped[str | None] = mapped_column(String(15))
    dns_server_tertiary: Mapped[str | None] = mapped_column(String(15))
    bootstrapped: Mapped[bool]
    boot_os: Mapped[str] = mapped_column(String(255))
    boot_os_version: Mapped[str] = mapped_column(String(64))
    boot_profile: Mapped[str] = mapped_column(String(128))
    boot_status: Mapped[str] = mapped_column(String(128))
    operational_status: Mapped[str] = mapped_column(String(255))
    ntp_server: Mapped[str] = mapped_column(String(128))

    provision_zone_id: Mapped[int | None] = mapped_column(ForeignKey("ProvisionZone.id"))
    provision_zone: Mapped[ProvisionZone | None] = relationship()
    switches: Mapped[list["SwitchInfo"]] = relationship(back_populates="server")


class SwitchInfo(Base):
    __tablename__ = "SwitchInfo"

    id: Mapped[int] = mapped_column(primary_key=True)
    switch_name: Mapped[str] = mapped_column(String(255))
    switch_port: Mapped[str] = mapped_column(String(255))
    server_number: Mapped[int | None] = mapped_column(ForeignKey("ServerData.server_number"))
    server: Mapped[ServerDataModel | None] = relationship(back_populates="switches")


def _row_to_dict(row):
    if row is None:
        return None
    d = dict(row.__dict__)
    d.pop("_sa_instance_state", None)
    return d


class SQL(ProviderPluginBase):
    """SQLAlchemy-backed inventory provider.

    Config dict must include 'engine' (a SQLAlchemy URL). Example:
        {'engine': 'sqlite:///:memory:'}
    """

    def __init__(self, config):
        self.engine = create_engine(config["engine"], echo=False)
        self._session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)
        # Auto-upgrade the schema. Safe for the default SQLite backend
        # (the file lock serializes worker startup). For Postgres/MySQL,
        # multiple workers can race -- see README on running
        # `python -m steel_pigs.db upgrade` as a pre-deploy step instead.
        alembic_cfg = make_alembic_config(engine=self.engine)
        command.upgrade(alembic_cfg, "head")

    @contextmanager
    def _session_scope(self):
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_server_by_name(self, name):
        stmt = select(ServerDataModel).where(ServerDataModel.hostname == name).limit(1)
        with self._session_scope() as s:
            return _row_to_dict(s.execute(stmt).scalar_one_or_none())

    def get_server_by_number(self, number):
        stmt = select(ServerDataModel).where(ServerDataModel.server_number == number).limit(1)
        with self._session_scope() as s:
            server = s.execute(stmt).scalar_one_or_none()
            if server is None:
                return None
            ret = _row_to_dict(server)
            ret["provision_zone"] = _row_to_dict(server.provision_zone)
            return ret

    def get_server_by_mac(self, mac):
        stmt = select(ServerDataModel).where(ServerDataModel.primary_mac == mac).limit(1)
        with self._session_scope() as s:
            return _row_to_dict(s.execute(stmt).scalar_one_or_none())

    def get_server_by_switch(self, switch_name, switch_port):
        stmt = (
            select(SwitchInfo)
            .where(SwitchInfo.switch_name == switch_name)
            .where(SwitchInfo.switch_port == switch_port)
            .limit(1)
        )
        with self._session_scope() as s:
            return _row_to_dict(s.execute(stmt).scalar_one_or_none())

    def _update_server_attr(self, server_number, attr, value):
        stmt = select(ServerDataModel).where(ServerDataModel.server_number == server_number)
        with self._session_scope() as s:
            server = s.execute(stmt).scalar_one_or_none()
            if server is None:
                return None
            setattr(server, attr, value)
            return server

    def set_boot_status(self, server_number, status):
        log.info("Setting boot status to %s for %s", status, server_number)
        if self._update_server_attr(server_number, "boot_status", status) is None:
            log.info("Unable to locate %s to set its boot status.", server_number)
            return {"operation": "failure", "status_set": "unable to locate device"}
        return {"operation": "success", "status_set": status}

    def set_boot_os(self, server_number, boot_os):
        log.info("Setting boot os on %s to %s", server_number, boot_os)
        if self._update_server_attr(server_number, "boot_os", boot_os) is None:
            log.info("Unable to locate %s to update boot os", server_number)
            # NOTE: the original API used a different failure key here
            # ('set_boot_os') than the success key ('os_set'). Preserved for
            # backwards compatibility with any existing clients.
            return {"operation": "failure", "set_boot_os": "unable to locate device"}
        log.info("Updated boot os.")
        return {"operation": "success", "os_set": boot_os}

    def set_operational_status(self, server_number, status):
        log.info("Setting Op status on %s to %s", server_number, status)
        if self._update_server_attr(server_number, "operational_status", status) is None:
            log.info("Unable to locate server %s", server_number)
            return {"operation": "failure", "status_set": "unable to locate device"}
        return {"operation": "success", "status_set": status}

    def create_entry(self, server_info):
        """Insert a ServerDataModel row. Intended for tests / data loading."""
        with self._session_scope() as s:
            s.add(server_info)

    def add_switch_entry(self, switch_info):
        """Insert a SwitchInfo row. Intended for tests / data loading."""
        with self._session_scope() as s:
            s.add(switch_info)
