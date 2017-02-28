# -*- coding: utf-8 -*-
import os
import subprocess
import Ice
import IceGrid

from django.conf import settings


class FileParser(object):

    def __init__(self, file_):
        self.communicator = Ice.initialize()
        self.sub = subprocess.Popen(settings.ICEGRIDADMIN, stdout=subprocess.PIPE)
        self.proxy = None
        self.file = file_

    def open(self):
        self.proxy = IceGrid.FileParserPrx.checkedCast(
            self.communicator.stringToProxy(self.sub.stdout.readline()).ice_router(None)
        )

    def parse(self, admin_proxy):
        return self.proxy.parse(self.file, admin_proxy)

    def destroy(self):
        if self.communicator:
            self.communicator.destroy()
        self.sub.kill()


class IceGridAdmin(object):
    # 'Ice.Default.Locator': 'BrIceGrid/Locator:tcp -h 192.168.162.181 -p 4061:tcp -h 192.168.162.182 -p 4061',  # dev
    # 'Ice.Default.Locator': 'BrIceGrid/Locator:tcp -h 192.168.23.111 -p 4061:tcp -h 192.168.23.112 -p 4061',  # pre
    # 'Ice.Default.Locator': 'BrIceGrid/Locator:tcp -h 192.168.21.54 -p 4061:tcp -h 192.168.21.55 -p 4061',  # prod
    ID = 'BrIceGrid/Registry'

    def __init__(self, admin_user, admin_pwd, **kwargs):
        pattern = ':tcp -h {0} -p {1}'
        locator = 'BrIceGrid/Locator%s' % pattern.format(kwargs['master_ip'], kwargs['master_port'])
        conf = {
            'Ice.Default.Locator': locator,
            'Ice.Override.ConnectTimeout': '5000',
        }
        slave_ip = kwargs.get('slave_ip')
        slave_port = kwargs.get('slave_port')
        if slave_ip and slave_port:
            conf['Ice.Default.Locator'] = locator + pattern.format(slave_ip, slave_port)
        props = Ice.createProperties()
        for k, v in conf.items():
            props.setProperty(k, v)
        init_data = Ice.InitializationData()
        init_data.properties = props
        self.communicator = Ice.initialize(init_data)
        self.proxy = None
        self.admin_proxy = None
        self.user = admin_user
        self.password = admin_pwd

    def initialize(self):
        try:
            self.proxy = IceGrid.RegistryPrx.checkedCast(self.communicator.stringToProxy(self.ID))
        except Ice.ConnectTimeoutException:
            raise RuntimeError("Ice::ConnectTimeoutException")
        except Ice.ConnectionRefusedException:
            raise RuntimeError('Ice::ConnectionRefusedException')

        if not self.proxy:
            raise RuntimeError("Invalid proxy")

        self._create_admin_session()

    def _create_admin_session(self):
        self.admin_proxy = self.proxy.createAdminSession(userId=self.user, password=self.password).getAdmin()

    def xml_to_app_descriptor(self, file_):
        """parse xxx.xml to application descriptor"""
        if not os.path.exists(file_):
            raise ValueError('file: %s does not exist!' % file_)
        parser = FileParser(file_)
        parser.open()
        app_descriptor = parser.parse(self.admin_proxy)
        parser.destroy()
        return app_descriptor

    @staticmethod
    def parse_descriptor_dir(descriptor, ice_project_dir):
        options = descriptor.serverTemplates['ServerTemplate'].descriptor.options
        project_dir = []
        for option in options:
            if ice_project_dir not in option:
                project_dir = option.split(':')
        return project_dir

    def get_all_registry_names(self):
        return self.admin_proxy.getAllRegistryNames()

    def get_registry_info(self, name):
        return self.admin_proxy.getRegistryInfo(name)

    def get_all_node_names(self):
        return self.admin_proxy.getAllNodeNames()

    def get_node_hostname(self, name):
        try:
            return self.admin_proxy.getNodeHostname(name)
        except IceGrid.NodeUnreachableException:
            return ''

    def get_node_info(self, name):
        try:
            return self.admin_proxy.getNodeInfo(name)
        except IceGrid.NodeUnreachableException:
            return ''

    def get_node_load(self, name):
        try:
            return self.admin_proxy.getNodeLoad(name)
        except IceGrid.NodeUnreachableException:
            return ''

    def get_all_server_ids(self):
        return self.admin_proxy.getAllServerIds()

    def get_server_pid(self, id_):
        try:
            return self.admin_proxy.getServerPid(id_)
        except IceGrid.NodeUnreachableException:
            return ''

    def get_server_state(self, id_):
        try:
            return unicode(self.admin_proxy.getServerState(id_))
        except IceGrid.NodeUnreachableException:
            return ''

    def get_server_info(self, id_):
        try:
            return self.admin_proxy.getServerInfo(id_)
        except IceGrid.NodeUnreachableException:
            return ''

    def enable_server(self, id_, enabled):
        """Enable or disable a server
        :param id_: string: The server id
        :param enabled: bool: enabled — True to enable the server, False to disable it.
        :return: None
        :exception: IceGrid::ServerNotExistException — Raised if the server doesn't exist.
                    IceGrid::NodeUnreachableException — Raised if the node could not be reached.
                    IceGrid::DeploymentException — Raised if the server couldn't be deployed on the node.
        """
        return self.admin_proxy.enableServer(id_, enabled)

    def is_server_enabled(self, id_):
        return self.admin_proxy.isServerEnabled(id_)

    def start_server(self, id_):
        """Start a server and wait for its activation
        :param id_: string: The server id
        :return: None
        :exception: IceGrid::ServerNotExistException — Raised if the server doesn't exist.
                    IceGrid::ServerStartException — Raised if the server couldn't be started.
                    IceGrid::NodeUnreachableException — Raised if the node could not be reached.
                    IceGrid::DeploymentException — Raised if the server couldn't be deployed on the node.
        """
        return self.admin_proxy.startServer(id_)

    def stop_server(self, id_):
        """Stop a server
        :param id_: string: The server id
        :return: None
        :exception: IceGrid::ServerNotExistException — Raised if the server doesn't exist.
                    IceGrid::ServerStopException — Raised if the server couldn't be stopped.
                    IceGrid::NodeUnreachableException — Raised if the node could not be reached.
                    IceGrid::DeploymentException — Raised if the server couldn't be deployed on the node.
        """
        return self.admin_proxy.stopServer(id_)

    def restart_server(self, id_):
        self.stop_server(id_)
        self.start_server(id_)

    def get_all_application_names(self):
        return self.admin_proxy.getAllApplicationNames()

    def application_exist(self, name):
        return name in self.get_all_application_names()

    def add_application(self, descriptor):
        """Add an application to IceGrid"""
        return self.admin_proxy.addApplication(descriptor)

    @staticmethod
    def get_application_nodes_from_descriptor(descriptor):
        nodes = []
        for node in descriptor.nodes.values():
            nodes.append(node.serverInstances[0].parameterValues['id'])
        return nodes

    def start_application_server(self, descriptor):
        nodes = []
        for node in descriptor.nodes.values():
            nodes.append(node.serverInstances[0].parameterValues['id'])
        for server in nodes:
            try:
                self.start_server(server)
            except Exception:
                continue

    def deploy_application(self, descriptor):
        self.admin_proxy.addApplication(descriptor)
        self.start_application_server(descriptor)

    def sync_application(self, descriptor):
        """
        Synchronize a deployed application with the given application descriptor.
        This operation will replace the current descriptor with this new descriptor.
        """
        return self.admin_proxy.syncApplication(descriptor)

    def sync_application_without_restart(self, descriptor):
        """
        :exception:
        IceGrid::AccessDeniedException — Raised if the session doesn't hold the exclusive lock or
                if another session is holding the lock.
        IceGrid::DeploymentException — Raised if application deployment failed.
        IceGrid::ApplicationNotExistException — Raised if the application doesn't exist.
        """
        return self.admin_proxy.syncApplicationWithoutRestart(descriptor)

    def update_application(self, descriptor):
        # TODO IceGrid::ApplicationUpdateDescriptor
        return self.admin_proxy.updateApplication(descriptor)

    def update_application_without_restart(self, descriptor):
        return self.admin_proxy.updateApplicationWithoutRestart(descriptor)

    def get_application_info(self, name):
        try:
            return self.admin_proxy.getApplicationInfo(name)
        except IceGrid.ApplicationNotExistException:
            return

    def get_application_descriptor(self, name):
        try:
            return self.admin_proxy.getApplicationInfo(name).descriptor
        except IceGrid.ApplicationNotExistException:
            return

    def get_application_nodes(self, name):
        descriptor = self.get_application_descriptor(name)
        nodes = {}
        if descriptor:
            for k, v in descriptor.nodes.items():
                server = v.serverInstances[0].parameterValues['id']
                nodes[k] = {
                    'server': server,
                    'state': self.get_server_state(server),
                    'pid': self.get_server_pid(server),
                }
        return nodes

    def remove_application(self, name):
        """Remove an application from IceGrid
        :param name: string
        :return: None
        """
        return self.admin_proxy.removeApplication(name)

    def destroy(self):
        if self.communicator:
            self.communicator.destroy()


if __name__ == '__main__':
    admin = IceGridAdmin(
        'admin', 'beijing',
        master_ip='192.168.162.181', master_port='4061',
        slave_ip='192.168.162.182', slave_port='4061'
    )
    # admin = IceGridAdmin(
    #     'admin', 'qazwsx',
    #     master_ip='192.168.23.111', master_port='4061',
    #     slave_ip='192.168.23.112', slave_port='4061'
    # )    
    admin.initialize()

    # esmd5_ids = admin.get_application_nodes('AppEsMd5')
    # print esmd5_ids
    # # admin.stop_server(esmd5_ids.keys()[0])
    # desc_old = admin.get_application_descriptor('AppEsMd5')
    # print desc_old
    # desc_new = admin.xml_to_app_descriptor('app_esmd5.xml')
    # print desc_new
    #
    # print desc_new == desc_old

    # admin.add_application('app_esmd5.xml')

    # for i in admin.get_all_application_names():
    #     print i
    #     print admin.get_application_nodes(i)

    # print {name: admin.get_application_nodes(name) for name in admin.get_all_application_names()}

    # print admin.remove_application('EsMd5')

    # print
    #
    # print
    #
    # for i in admin.get_all_server_ids():
    #     print i
    #     print admin.get_server_pid(i)
    #     print admin.get_server_state(i)
    #     print admin.get_server_info(i)

    # for i in admin.get_all_node_names():
    #     print i
    #     print admin.get_node_hostname(i)
    #     print admin.get_node_info(i)
        # print type(admin.get_node_info(i))
        # print admin.get_node_load(i)

    # for i in admin.get_all_registry_names():
    #     print admin.get_registry_info(i)
    #     print type(admin.get_registry_info(i))

    # desc = admin.get_application_descriptor('AppDemo')
    # print desc.name
    # print desc.nodes.keys()
    # print desc.nodes['node-1'].serverInstances
    # print

    node = admin.get_node_load('node-0')
    print type(node)
    admin.destroy()
