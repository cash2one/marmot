# -*- coding: utf-8 -*-
import subprocess
import Ice
import IceGrid


# Raised if the password for the given user id is not correct, or if the user is not allowed access.
PermissionDeniedException = IceGrid.PermissionDeniedException

# Raised if the registry doesn't exist.
RegistryNotExistException = IceGrid.RegistryNotExistException

# Raised if the registry could not be reached.
RegistryUnreachableException = IceGrid.RegistryUnreachableException

# Raised if the node doesn't exist.
NodeNotExistException = IceGrid.NodeNotExistException

# Raised if the node could not be reached.
NodeUnreachableException = IceGrid.NodeUnreachableException

# Raised if the session doesn't hold the exclusive lock or if another session is holding the lock.
AccessDeniedException = IceGrid.AccessDeniedException

# Raised if the application doesn't exist.
ApplicationNotExistException = IceGrid.ApplicationNotExistException

# Raised if the server doesn't exist.
ServerNotExistException = IceGrid.ServerNotExistException

# Raised if the server couldn't be started.
ServerStartException = IceGrid.ServerStartException

# Raised if the server couldn't be stopped.
ServerStopException = IceGrid.ServerStopException

# Raised if the server couldn't be deployed on the node.
DeploymentException = IceGrid.DeploymentException


class InitializeException(Exception):
    pass


class FileParser(object):
    """
    Start FileParser server to parse xxx.xml to Application-Descriptor
    """
    def __init__(self, file_, icegridadmin):
        self.communicator = Ice.initialize()
        self.icegridadmin = icegridadmin  # "icegridadmin" cmd path
        self.file = file_
        self.proxy = None
        self.sub = None

    def open(self):
        self.sub = subprocess.Popen(self.icegridadmin, stdout=subprocess.PIPE)
        self.proxy = IceGrid.FileParserPrx.checkedCast(
            self.communicator.stringToProxy(self.sub.stdout.readline()).ice_router(None)
        )

    def parse(self, admin_proxy):
        return self.proxy.parse(self.file, admin_proxy)

    def destroy(self):
        if self.communicator:
            self.communicator.destroy()
        if self.sub:
            self.sub.kill()


class IceGridAdmin(object):
    """
    IceGrid admin interface
    """
    def __init__(self, admin_user, admin_pwd, icegridadmin, **kwargs):
        pattern = ':tcp -h {0} -p {1}'
        prefix = str(kwargs['prefix'])  # BrIceGrid; DacIceGrid
        self.ID = '%s/Registry' % prefix  # Registry Replica-1
        locator = '%s/Locator%s' % (prefix, pattern.format(kwargs['master_ip'], kwargs['master_port']))
        conf = {
            'Ice.Default.Locator': locator,
            'Ice.Override.ConnectTimeout': '5000',
            # 'Ice.RetryIntervals': '0 1000 5000',
            # 'Ice.Trace.Network': '2',  # debug
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
        self.user = admin_user
        self.password = admin_pwd
        self.icegridadmin = icegridadmin
        self.proxy = None
        self.admin_session = None
        self.admin = None

    def initialize(self):
        try:
            self.proxy = IceGrid.RegistryPrx.checkedCast(self.communicator.stringToProxy(self.ID))
        except Ice.ConnectTimeoutException:
            raise InitializeException('Ice::ConnectTimeoutException')
        except Ice.ConnectionRefusedException:
            try:
                self.proxy = IceGrid.RegistryPrx.checkedCast(self.communicator.stringToProxy(self.ID + '-Replica-1'))
            except Exception as e:
                raise InitializeException(unicode(e))
        except Ice.ObjectNotExistException:
            raise InitializeException('Ice::ObjectNotExistException')

        if not self.proxy:
            raise InitializeException('Invalid Proxy')

        try:
            # Create an administrative session.
            self.admin_session = self.proxy.createAdminSession(userId=self.user, password=self.password)
        except PermissionDeniedException:
            raise InitializeException('IceGrid::PermissionDeniedException')
        # Get the admin interface
        self.admin = self.admin_session.getAdmin()

    def get_all_registry_names(self):
        """
        Get all the IceGrid registries currently registered.
        :return: list - The registry names.
        """
        return self.admin.getAllRegistryNames()

    def ping_registry(self, name):
        """
        Ping an IceGrid registry to see if it is active.
        :param name: string - The registry name.
        :return: bool
        :exception: IceGrid::RegistryNotExistException
        """
        return self.admin.pingRegistry(name)

    def get_registry_info(self, name):
        """
        Get the registry information for the registry with the given name.
        :param: string - The registry name.
        :return: IceGrid::RegistryInfo - The registry information.
        :exception: IceGrid::RegistryNotExistException
                    IceGrid::RegistryUnreachableException
        """
        return self.admin.getRegistryInfo(name)

    def get_all_node_names(self):
        """
        Get all the IceGrid nodes currently registered.
        :return: list - The node names.
        """
        return self.admin.getAllNodeNames()

    def get_node_hostname(self, name):
        """
        Get the hostname of this node.
        :param name: string - The node name.
        :return: string - The node hostname.
        :exception: IceGrid::NodeNotExistException
                    IceGrid::NodeUnreachableException
        """
        return self.admin.getNodeHostname(name)

    def get_node_info(self, name):
        """
        Get the node information for the node with the given name.
        :param name: string - The node name.
        :return: IceGrid::NodeInfo
        :exception: IceGrid::NodeNotExistException
                    IceGrid::NodeUnreachableException
        """
        return self.admin.getNodeInfo(name)

    def get_node_load(self, name):
        """
        Get the load averages of the node.
        :param name: string - The node name.
        :return: IceGrid::LoadInfo
        :exception: IceGrid::NodeNotExistException
                    IceGrid::NodeUnreachableException
        """
        return self.admin.getNodeLoad(name)

    def get_all_server_ids(self):
        """
        Get all the server ids registered with IceGrid.
        :return: list - The server ids.
        """
        return self.admin.getAllServerIds()

    def get_server_pid(self, id_):
        """
        Get a server's system process id.
        :param id_: The server id.
        :return: long - The server's process id.
        :exception: IceGrid::ServerNotExistException
                    IceGrid::NodeUnreachableException
                    IceGrid::DeploymentException
        """
        try:
            return self.admin.getServerPid(id_)
        except NodeUnreachableException:
            return ''

    def get_server_state(self, id_):
        """
        :return: IceGrid::ServerState
        :exception: IceGrid::ServerNotExistException
                    IceGrid::NodeUnreachableException
                    IceGrid::DeploymentException
        """
        try:
            return unicode(self.admin.getServerState(id_))
        except NodeUnreachableException:
            return ''

    def get_server_info(self, id_):
        """
        :return: IceGrid::ServerInfo
        :exception: IceGrid::ServerNotExistException
                    IceGrid::NodeUnreachableException
                    IceGrid::DeploymentException
        """
        return self.admin.getServerInfo(id_)

    def enable_server(self, id_, enabled):
        """Enable or disable a server
        :param id_: string: The server id
        :param enabled: bool: enabled — True to enable the server, False to disable it.
        :return: None
        :exception: IceGrid::ServerNotExistException
                    IceGrid::NodeUnreachableException
                    IceGrid::DeploymentException
        """
        return self.admin.enableServer(id_, enabled)

    def is_server_enabled(self, id_):
        """
        Check if the server is enabled or disabled.
        :param id_: string: The server id
        :return: bool
        :exception: IceGrid::ServerNotExistException
                    IceGrid::NodeUnreachableException
                    IceGrid::DeploymentException
        """
        return self.admin.isServerEnabled(id_)

    def start_server(self, id_):
        """Start a server and wait for its activation
        :param id_: string: The server id
        :return: None
        :exception: IceGrid::ServerNotExistException
                    IceGrid::ServerStartException
                    IceGrid::NodeUnreachableException
                    IceGrid::DeploymentException
        """
        return self.admin.startServer(id_)

    def stop_server(self, id_):
        """Stop a server
        :param id_: string: The server id
        :return: None
        :exception: IceGrid::ServerNotExistException
                    IceGrid::ServerStopException
                    IceGrid::NodeUnreachableException
                    IceGrid::DeploymentException
        """
        return self.admin.stopServer(id_)

    def get_all_application_names(self):
        """
        Get all the IceGrid applications currently registered.
        :return: list - The application names.
        """
        return self.admin.getAllApplicationNames()

    def application_exist(self, name):
        return name in self.get_all_application_names()

    def add_application(self, descriptor):
        """Add an application to IceGrid
        :param descriptor: The application descriptor
        :return: None
        :exception: IceGrid::AccessDeniedException
                    IceGrid::DeploymentException
        """
        return self.admin.addApplication(descriptor)

    def xml_to_app_descriptor(self, file_):
        """parse xxx.xml to Application-Descriptor"""
        parser = FileParser(file_, self.icegridadmin)
        parser.open()
        app_descriptor = parser.parse(self.admin)
        parser.destroy()
        return app_descriptor

    @staticmethod
    def get_application_servers_from_descriptor(descriptor):
        servers = []
        for n in descriptor.nodes.values():
            servers.append(n.serverInstances[0].parameterValues['id'])
        return servers

    def start_application_servers(self, descriptor):
        servers = self.get_application_servers_from_descriptor(descriptor)
        for server_id in servers:
            try:
                self.start_server(server_id)
            except Ice.Exception:
                continue

    def deploy_application(self, descriptor):
        self.admin.addApplication(descriptor)
        self.start_application_servers(descriptor)

    def sync_application(self, descriptor):
        """
        Synchronize a deployed application with the given application descriptor.
        This operation will replace the current descriptor with this new descriptor.
        :param descriptor: The application descriptor.
        :return: None
        :exception: IceGrid::AccessDeniedException
                    IceGrid::DeploymentException
                    IceGrid::ApplicationNotExistException
        """
        return self.admin.syncApplication(descriptor)

    def sync_application_without_restart(self, descriptor):
        """
        :exception:IceGrid::AccessDeniedException
                   IceGrid::DeploymentException
                   IceGrid::ApplicationNotExistException
        """
        return self.admin.syncApplicationWithoutRestart(descriptor)

    def get_application_info(self, name):
        """
        :param name: string - application name
        :return: IceGrid.ApplicationInfo
        :exception IceGrid::ApplicationNotExistException
        """
        return self.admin.getApplicationInfo(name)

    def get_application_descriptor(self, name):
        """
        :param name: string - application name
        :return: IceGrid::ApplicationDescriptor
        :exception IceGrid::ApplicationNotExistException
        """
        return self.admin.getApplicationInfo(name).descriptor

    def get_application_servers(self, name):
        """
        :return: dict
        :exception IceGrid::ApplicationNotExistException
        """
        servers = {}
        try:
            descriptor = self.get_application_descriptor(name)
        except ApplicationNotExistException:
            return servers
        if descriptor:
            for k, v in descriptor.nodes.items():
                try:
                    server = v.serverInstances[0].parameterValues['id']
                except IndexError:
                    servers[k] = {'server': '', 'state': '', 'pid': ''}
                    continue
                servers[k] = {
                    'server': server,
                    'state': self.get_server_state(server),
                    'pid': self.get_server_pid(server),
                }
        return servers

    def remove_application(self, name):
        """Remove an application from IceGrid
        :param name: string - application name
        :return: None
        :exception: IceGrid::AccessDeniedException
                    IceGrid::ApplicationNotExistException
        """
        return self.admin.removeApplication(name)

    def destroy(self):
        if self.communicator:
            self.communicator.destroy()
