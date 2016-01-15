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
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .pluginbase import ProviderPluginBase

Base = declarative_base()


class ServerDataModel(Base):
    __tablename__ = 'ServerData'
    id = Column(Integer, primary_key=True)
    server_number = Column(Integer, unique=True, nullable=False)
    primary_ip = Column(String(15), nullable=False)
    primary_gw = Column(String(15), nullable=False)
    primary_nm = Column(String(15), nullable=False)
    primary_mac = Column(String(20), nullable=False)
    drac_ip = Column(String(15), nullable=True)
    drac_gw = Column(String(15), nullable=True)
    drac_nm = Column(String(15), nullable=True)
    hostname = Column(String(255), nullable=False)
    dns_domain_name = Column(String(255), default="rpc.local")
    dns_server_primary = Column(String(15), nullable=False)
    dns_server_secondary = Column(String(15), nullable=True)
    dns_server_tertiary = Column(String(15), nullable=True)
    bootstrapped = Column(Boolean, nullable=False)
    boot_os = Column(String(255), nullable=False)
    boot_os_version = Column(String(64), nullable=False)
    boot_profile = Column(String(128), nullable=False)
    boot_status = Column(String(128), nullable=False)
    operational_status = Column(String(255), nullable=False)
    ntp_server = Column(String(128), nullable=False)
    switches = relationship("SwitchInfo", backref="ServerData")
    provision_zone_id = Column(Integer, ForeignKey('ProvisionZone.id'))
    provision_zone = relationship("ProvisionZone")


class ProvisionZone(Base):
    __tablename__ = "ProvisionZone"
    id = Column(Integer, primary_key=True)
    zone_name = Column(String(128), unique=True, nullable=False)
    provision_img_host = Column(String(128), nullable=False)
    provision_mirror_host = Column(String(128), nullable=False)


class SwitchInfo(Base):
    __tablename__ = "SwitchInfo"
    id = Column(Integer, primary_key=True)
    switch_name = Column(String(255), nullable=False)
    switch_port = Column(String(255), nullable=False)
    server_number = Column(Integer, ForeignKey("ServerData.server_number"))


class SQL(ProviderPluginBase):
    _engine = None

    def __init__(self, config):
        """
        Pass in a dict that has required info in it for the plugin configuration.

        The only required key is 'engine' Below is an example using an in memory
        sqlite database:

        {
            'engine': "sqlite:///:memory:"
        }

        :param config: dictionary that contains required info for the plugin
        :return:
        """
        self._engine = config['engine']
        self.engine = create_engine(self._engine, echo=False)
        self.sessionmaker = None
        Base.metadata.create_all(self.engine)

    @contextmanager
    def _session_scope(self):
        """Return a session context to wrap around db operations.
        example:
        with db.session_scope() as session:
            # do some inserts
        :returns: Session context
        """
        session = self._get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _get_session(self):
        """

        :return: sessionmaker
        """
        if not self.engine:
            raise Exception('Engine not created yet.')

        # Check for session maker
        if not self.sessionmaker:
            self.sessionmaker = sessionmaker(bind=self.engine)

        # Call session maker for session
        return self.sessionmaker(bind=self.engine)

    @staticmethod
    def _query_to_dict(data):
        if isinstance(data, ProvisionZone):
            dictret = dict(data.__dict__)
            dictret.pop('_sa_instance_state', None)
            return dictret
        if len(data) != 1:
            return
        dictret = dict(data[0].__dict__)
        dictret.pop('_sa_instance_state', None)
        return dictret

    def get_server_by_name(self, name):
        """
        Retrieve data about a server by name and return an object that
        represents it.
        """
        with self._session_scope() as session:
            query = session.query(ServerDataModel).filter(
                ServerDataModel.hostname == name
            ).limit(1)
            results = query.all()
            results = self._query_to_dict(results)
        return results

    def get_server_by_number(self, number):
        """
        Retrieve data about a server and return a dict that
        represents it.

        :param number: The device number or asset number of a given server
        :return: returns a dict that represents a server
        """
        with self._session_scope() as session:
            query = session.query(ServerDataModel).filter(
                ServerDataModel.server_number == number
            ).limit(1)
            results = query.all()
            ret = self._query_to_dict(results)
            prov = results[0].provision_zone
            prov_d = self._query_to_dict(prov)
            ret["provision_zone"] = prov_d
        return ret

    def get_server_by_mac(self, mac):
        """
        Returns a server_data dict for a given server based on the primary mac address

        :param mac: String representing the mac address of a given server
        :return: returns a dict that represents a server
        """
        with self._session_scope() as session:
            query = session.query(ServerDataModel).filter(
                ServerDataModel.primary_mac == mac
            ).limit(1)
            results = query.all()
            results = self._query_to_dict(results)
        return results

    def get_server_by_switch(self, switch_name, switch_port):
        """
        Fetch a server_data object using the provided switch info

        :param switch_name:
        :param switch_port:
        :return:
        """
        with self._session_scope() as session:
            query = session.query(SwitchInfo).filter(
                SwitchInfo.switch_name == switch_name and SwitchInfo.switch_port == switch_port
            ).limit(1)
            result = query.all()
            retdict = self._query_to_dict(result)
        return retdict

    def set_boot_status(self, server_number, status):
        """
        Sets the boot_status of a given server

        :param server_number:
        :param status:
        :return: Python dict that will be jsonified by flask and returned to user
        """
        logging.info("Setting boot status to {} for {}".format(
            status, server_number
        ))
        with self._session_scope() as session:
            server = session.query(ServerDataModel).filter_by(
                server_number=server_number
            ).first()
            if server:
                server.boot_status = status
                session.commit()
                return {"operation": "success", "status_set": status}
            logging.info("Unable to locate {} to set its boot status.".format(
                server_number
            ))
            return {"operation": "failure", "status_set": "unable to locate device"}

    def set_boot_os(self, server_number, os):
        """
        Sets the boot_os of a given server

        :param server_number:
        :param os:
        :return: Python dict that will be jsonified by flask and returned to user
        """
        logging.info("Setting boot os on {} to {}".format(
            server_number, os
        ))
        with self._session_scope() as session:
            server = session.query(ServerDataModel).filter_by(
                server_number=server_number
            ).first()
            if server:
                logging.info("Found server {}. Setting os to {}".format(
                    server_number, os
                ))
                server.boot_os = os
                session.commit()
                logging.info("Updated boot os.")
                return {"operation": "success", "os_set": os}
            logging.info("Unable to locate {} to update boot os".format(server_number))
            return {"operation": "failure", "set_boot_os": "unable to locate device"}

    def set_operational_status(self, server_number, status):
        """
        Sets the boot_status of a given server

        :param server_number:
        :param status:
        :return: Python dict that will be jsonified by flask and returned to user
        """
        logging.info("Setting Op status on {} to {}".format(
            server_number, status
        ))
        with self._session_scope() as session:
            server = session.query(ServerDataModel).filter_by(
                server_number=server_number
            ).first()
            if server:
                logging.info("Found server {}".format(server_number))
                server.operational_status = status
                session.commit()
                return {"operation": "success", "status_set": status}
            logging.info("Unable to locate server {}".format(server_number))
            return {"operation": "failure", "status_set": "unable to locate device"}

    def create_entry(self, server_info):
        """
        This method should likely only be used in your tests so you can populate
        an in memory or on disk db with info.

        :param server_info: ServerDataModel object
        :return: None
        """
        with self._session_scope() as session:
            session.add(server_info)
            session.commit()

    def add_switch_entry(self, switch_info):
        """
        This is only used to facilitate with testing.

        :param switch_info:
        :return:
        """
        with self._session_scope() as session:
            session.add(switch_info)
            session.commit()
