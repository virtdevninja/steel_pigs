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

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship

Base = declarative_base()

from .pluginbase import ProviderPluginBase


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
    switches = relationship("SwitchInfo", backref="ServerData")


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
        Base.metadata.create_all(self.engine)

    @staticmethod
    def _query_to_dict(data):
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
        session_maker = sessionmaker(bind=self.engine)
        session = session_maker()
        query = session.query(ServerDataModel).filter(
            ServerDataModel.hostname == name
        ).limit(1)
        results = query.all()
        session.close()
        return self._query_to_dict(results)

    def get_server_by_number(self, number):
        """
        Retrieve data about a server and return a dict that
        represents it.

        :param number: The device number or asset number of a given server
        :return: returns a dict that represents a server
        """
        session_maker = sessionmaker(bind=self.engine)
        session = session_maker()
        query = session.query(ServerDataModel).filter(
            ServerDataModel.server_number == number
        ).limit(1)
        results = query.all()
        session.close()
        return self._query_to_dict(results)

    def get_server_by_mac(self, mac):
        """
        Returns a server_data dict for a given server based on the primary mac address

        :param mac: String representing the mac address of a given server
        :return: returns a dict that represents a server
        """
        session_maker = sessionmaker(bind=self.engine)
        session = session_maker()
        query = session.query(ServerDataModel).filter(
            ServerDataModel.primary_mac == mac
        ).limit(1)
        results = query.all()
        session.close()
        return self._query_to_dict(results)

    def get_server_by_switch(self, switch_name, switch_port):
        """
        Fetch a server_data object using the provided switch info

        :param switch_name:
        :param switch_port:
        :return:
        """
        session_maker = sessionmaker(bind=self.engine)
        session = session_maker()
        query = session.query(SwitchInfo).filter(
            SwitchInfo.switch_name == switch_name and SwitchInfo.switch_port == switch_port
        ).limit(1)
        result = query.all()
        retdict = result[0].ServerData.__dict__
        retdict.pop('_sa_instance_state', None)
        session.close()
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
        session_maker = sessionmaker(bind=self.engine)
        session = session_maker()
        server = session.query(ServerDataModel).filter_by(
            server_number=server_number
        ).first()
        if server:
            server.boot_status = status
            session.commit()
            session.close()
            return {"operation": "success", "status_set": status}
        logging.info("Unable to locate {} to set its boot status.".format(
            server_number
        ))
        session.close()
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
        session_maker = sessionmaker(bind=self.engine)
        session = session_maker()
        server = session.query(ServerDataModel).filter_by(
            server_number=server_number
        ).first()
        if server:
            logging.info("Found server {}. Setting os to {}".format(
                server_number, os
            ))
            server.boot_os = os
            session.commit()
            session.close()
            logging.info("Updated boot os.")
            return {"operation": "success", "os_set": os}
        logging.info("Unable to locate {} to update boot os".format(server_number))
        session.close()
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
        session_maker = sessionmaker(bind=self.engine)
        session = session_maker()
        server = session.query(ServerDataModel).filter_by(
            server_number=server_number
        ).first()
        if server:
            logging.info("Found server {}".format(server_number))
            server.operational_status = status
            session.commit()
            session.close()
            return {"operation": "success", "status_set": status}
        session.close()
        logging.info("Unable to locate server {}".format(server_number))
        return {"operation": "failure", "status_set": "unable to locate device"}

    def create_entry(self, server_info):
        """
        This method should likely only be used in your tests so you can populate
        an in memory or on disk db with info.

        :param server_info: ServerDataModel object
        :return: None
        """
        session_maker = sessionmaker(bind=self.engine)
        session = session_maker()
        session.add(server_info)
        session.commit()
        session.close()

    def add_switch_entry(self, switch_info):
        """
        This is only used to facilitate with testing.

        :param switch_info:
        :return:
        """
        session_maker = sessionmaker(bind=self.engine)
        session = session_maker()
        session.add(switch_info)
        session.commit()
        session.close()

