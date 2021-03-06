# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re
import json
import socket
import httplib
import xmlrpclib
import logging

from django.shortcuts import get_object_or_404, render
from django.core.urlresolvers import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponseRedirect, Http404
from django.views.generic import (
    CreateView, ListView, UpdateView,
    DetailView, DeleteView, FormView
)
from django.contrib.auth.decorators import login_required
from django.utils.http import urlencode
from django.conf import settings

from utils.node_proxy import NodeProxy
from utils.mixins import LoginRequiredMixin, PermissionRequiredMixin

from .models import (
    Idc, Cabinet, Server, NetworkDevice,
    NetCard, ProcessMonitor
)
from .forms import (
    IdcForm, CabinetForm, NetworkDeviceForm,
    ServerForm, ProcessMonitorForm, ServerCheckForm
)


logger = logging.getLogger('marmot')

NODE_PORT = settings.NODE_PORT
IP_PATTERN = re.compile(r'^192\.168\.(\d{1,3})\.(\d{1,3})$')


class IdcCreate(PermissionRequiredMixin, CreateView):
    model = Idc
    form_class = IdcForm
    template_name = 'assets/idc_form.html'
    success_url = reverse_lazy('idc_list')
    permission_required = 'assets.add_idc'


class IdcUpdate(PermissionRequiredMixin, UpdateView):
    model = Idc
    form_class = IdcForm
    template_name = 'assets/idc_form.html'
    permission_required = 'assets.change_idc'


class IdcDetail(LoginRequiredMixin, DetailView):
    model = Idc
    context_object_name = 'idc'
    template_name = 'assets/idc_detail.html'


class IdcDelete(PermissionRequiredMixin, DeleteView):
    model = Idc
    context_object_name = 'idc'
    template_name = 'assets/idc_confirm_delete.html'
    success_url = reverse_lazy('idc_list')
    permission_required = 'assets.delete_idc'


class IdcList(LoginRequiredMixin, ListView):
    model = Idc
    context_object_name = 'idc_list'
    template_name = 'assets/idc_list.html'


class CabinetCreate(PermissionRequiredMixin, CreateView):
    model = Cabinet
    form_class = CabinetForm
    template_name = 'assets/cabinet_form.html'
    permission_required = 'assets.add_cabinet'

    def get_initial(self):
        initial = super(CabinetCreate, self).get_initial()
        self.idc = Idc.objects.get(id=self.args[0])
        initial['idc'] = self.idc
        return initial

    def get_context_data(self, **kwargs):
        context = super(CabinetCreate, self).get_context_data(**kwargs)
        context['idc'] = self.idc
        return context

    def get_success_url(self):
        return self.idc.get_absolute_url()


class CabinetUpdate(PermissionRequiredMixin, UpdateView):
    model = Cabinet
    form_class = CabinetForm
    context_object_name = 'cabinet'
    template_name = 'assets/cabinet_form.html'
    permission_required = 'assets.change_cabinet'


class CabinetDetail(LoginRequiredMixin, DetailView):
    model = Cabinet
    context_object_name = 'cabinet'
    template_name = 'assets/cabinet_detail.html'


class CabinetDelete(PermissionRequiredMixin, DeleteView):
    model = Cabinet
    context_object_name = 'cabinet'
    template_name = 'assets/cabinet_confirm_delete.html'
    permission_required = 'assets.delete_cabinet'

    def get_success_url(self):
        return self.object.idc.get_absolute_url()


class ServerCheck(PermissionRequiredMixin, FormView):
    form_class = ServerCheckForm
    template_name = 'assets/server_check.html'
    permission_required = 'assets.add_server'

    def get_success_url(self):
        return reverse('server_create', args=(self.args[0],))

    def form_valid(self, form):
        print self.get_success_url() + '?ip=%s' % form.cleaned_data['ip']
        return HttpResponseRedirect(self.get_success_url() + '?ip=%s' % form.cleaned_data['ip'])

    def get_context_data(self, **kwargs):
        context = super(ServerCheck, self).get_context_data(**kwargs)
        context['cabinet'] = get_object_or_404(Cabinet, id=self.args[0])
        return context


class ServerCreate(PermissionRequiredMixin, CreateView):
    model = Server
    form_class = ServerForm
    template_name = 'assets/server_add.html'
    permission_required = 'assets.add_server'

    def get(self, request, *args, **kwargs):
        self.object = None
        form = self.form_class(**self.get_form_kwargs())
        return self.render_to_response(self.get_context_data(form=form))

    def get_initial(self):
        initial = super(ServerCreate, self).get_initial()
        server_ip = self.request.GET['ip']
        self.cabinet = get_object_or_404(Cabinet, id=self.args[0])
        node = NodeProxy(server_ip, settings.NODE_PORT)
        try:
            base_info = node.get_base_info()
        except (IOError, xmlrpclib.Fault, httplib.BadStatusLine):
            return initial
        dmi = base_info['dmi']
        cpu_info = base_info['cpu_info']
        initial.update({
            'cabinet': self.cabinet,
            'hostname': base_info['hostname'],
            'ip': server_ip,
            'os': base_info['os_distribution'],
            'serial_num': dmi['serial-number'],
            'manufacturer': dmi['manufacturer'],
            'product_model': dmi['product-name'],
            'cpu_model': cpu_info['model'],
            'cpu_logic_nums': cpu_info['core_num'],
            'mem_size': base_info['memory_total'],
            'disk_size': base_info['disk_size'],
        })
        return initial

    def get_context_data(self, **kwargs):
        context = super(ServerCreate, self).get_context_data(**kwargs)
        context['cabinet'] = self.cabinet
        return context

    def get_success_url(self):
        return self.cabinet.get_absolute_url()

    def form_valid(self, form):
        cleaned_data = form.cleaned_data
        monitor_enabled = cleaned_data['monitor_enabled']
        server_ip = cleaned_data['ip']
        # cpu_level = cleaned_data['cpu_level']
        memory_level = cleaned_data['memory_level']
        disk_level = cleaned_data['disk_level']
        alarm_interval = cleaned_data['alarm_interval']

        node = NodeProxy(server_ip, settings.NODE_PORT)
        try:
            netcard_info = node.get_netcard_info()
            node.set_memory_monitor_level(memory_level)
            node.set_disk_monitor_level(disk_level)
            node.set_alarm_interval(alarm_interval)
            if monitor_enabled:
                node.start_monitor()
        except (IOError, xmlrpclib.Fault, httplib.BadStatusLine):
            logger.exception('Connect node error')
            return super(ServerCreate, self).form_valid(form)
        self.object = form.save()
        for card, data in netcard_info.items():
            NetCard.objects.create(
                server=self.object, name=card,
                ip_addr=data['addr'], net_addr=data['broadcast'],
                mac_addr=data['mac'], sub_mask=data['mask']
            )
        return HttpResponseRedirect(self.get_success_url())


class ServerUpdate(PermissionRequiredMixin, UpdateView):
    model = Server
    form_class = ServerForm
    context_object_name = 'server'
    template_name = 'assets/server_update.html'
    permission_required = 'assets.change_server'

    def get_success_url(self):
        return self.object.get_absolute_url()

    def form_valid(self, form):
        cleaned_data = form.cleaned_data
        monitor_enabled = cleaned_data['monitor_enabled']
        server_ip = cleaned_data['ip']
        # cpu_level = cleaned_data['cpu_level']
        memory_level = cleaned_data['memory_level']
        disk_level = cleaned_data['disk_level']
        alarm_interval = cleaned_data['alarm_interval']

        node = NodeProxy(server_ip, settings.NODE_PORT)
        try:
            netcard_info = node.get_netcard_info()
            node.set_memory_monitor_level(memory_level)
            node.set_disk_monitor_level(disk_level)
            node.set_alarm_interval(alarm_interval)
            if monitor_enabled:
                node.start_monitor()
            else:
                node.stop_monitor()
        except (IOError, xmlrpclib.Fault, httplib.BadStatusLine):
            logger.exception('Node Error')
            return super(ServerUpdate, self).form_valid(form)

        self.object = form.save()

        for card, data in netcard_info.items():
            updated_values = {
                'ip_addr': data['addr'],
                'net_addr': data['broadcast'],
                'mac_addr': data['mac'],
                'sub_mask': data['mask'],
            }
            NetCard.objects.update_or_create(server=self.object, name=card, defaults=updated_values)
        return HttpResponseRedirect(self.get_success_url())


class ServerDetail(LoginRequiredMixin, DetailView):
    model = Server
    context_object_name = 'server'
    template_name = 'assets/server_detail.html'


class ServerDelete(PermissionRequiredMixin, DeleteView):
    model = Server
    context_object_name = 'server'
    template_name = 'assets/server_confirm_delete.html'
    permission_required = 'assets.delete_server'

    def get_success_url(self):
        return self.object.cabinet.get_absolute_url()

    def get_context_data(self, **kwargs):
        context = super(ServerDelete, self).get_context_data(**kwargs)
        context['center'] = self.object.master_server_set.all().first()  # ICE注册中心
        return context


class ServerList(LoginRequiredMixin, ListView):
    model = Server
    paginate_by = 20
    context_object_name = 'servers'
    template_name = 'assets/server_list.html'

    def get_queryset(self):
        queryset = super(ServerList, self).get_queryset()
        self.host_type = self.request.GET.get('hostType', '')
        self.master_host = self.request.GET.get('masterHost', '')
        if self.host_type:
            queryset = queryset.filter(type=self.host_type)
        if self.master_host:
            queryset = queryset.filter(master_host=self.master_host)
        return queryset

    def get_context_data(self, **kwargs):
        context = super(ServerList, self).get_context_data(**kwargs)
        context['master_hosts'] = Server.objects.filter(type=1).all()  # 所有的物理机
        context['host_type'] = self.host_type  # selected
        try:
            context['master_host'] = int(self.master_host) if self.master_host else ''  # selected
        except ValueError:
            raise Http404
        print urlencode({'hostType': self.host_type, 'masterHost': self.master_host})
        context['extra_url_param'] = urlencode({'hostType': self.host_type, 'masterHost': self.master_host})
        return context


class ProcessMonitorCreate(PermissionRequiredMixin, CreateView):
    model = ProcessMonitor
    form_class = ProcessMonitorForm
    template_name = 'assets/process_monitor_form.html'
    permission_required = 'assets.add_processmonitor'

    def get_initial(self):
        initial = super(ProcessMonitorCreate, self).get_initial()
        self.server = Server.objects.get(id=self.args[0])
        initial['server'] = self.server
        return initial

    def get_context_data(self, **kwargs):
        context = super(ProcessMonitorCreate, self).get_context_data(**kwargs)
        context['server'] = self.server
        return context

    def get_success_url(self):
        return self.server.get_absolute_url()


class ProcessMonitorUpdate(PermissionRequiredMixin, UpdateView):
    model = ProcessMonitor
    form_class = ProcessMonitorForm
    context_object_name = 'process_monitor'
    template_name = 'assets/process_monitor_form.html'
    permission_required = 'assets.change_processmonitor'


class ProcessMonitorDetail(LoginRequiredMixin, DetailView):
    model = ProcessMonitor
    context_object_name = 'process_monitor'
    template_name = 'assets/process_monitor_detail.html'


class ProcessMonitorDelete(PermissionRequiredMixin, DeleteView):
    model = ProcessMonitor
    form_class = ProcessMonitorForm
    context_object_name = 'process_monitor'
    template_name = 'assets/process_monitor_confirm_delete.html'
    permission_required = 'assets.delete_processmonitor'

    def get_success_url(self):
        return self.object.server.get_absolute_url()


def server_conf(request):
    hostname = request.GET.get('hostname')
    try:
        server = Server.objects.get(hostname=hostname)
    except Server.DoesNotExist:
        server = None
    return JsonResponse({
            'monitor': {
                'enabled': server.monitor_enabled if server else False,
                'cpu': server.cpu_level if server else 99.0,
                'memory': server.memory_level if server else 80,
                'disk': server.disk_level if server else 90,
                'alarm_interval': server.alarm_interval if server else 20,
            }
        })


def server_process_monitors(request):
    hostname = request.GET.get('hostname')
    try:
        server = Server.objects.get(hostname=hostname)
    except Server.DoesNotExist:
        return JsonResponse({'monitors': []})
    process_monitors = server.processmonitor_set.values('name', 'cmd', 'port')
    return JsonResponse({'monitors': process_monitors})


@login_required
def server_is_alive(request):
    hostname = request.GET.get('hostname')
    try:
        server = Server.objects.get(hostname=hostname)
    except Server.DoesNotExist:
        return JsonResponse({'msg': 'Server[%s] does not exists'})
    status = server.is_alive
    return JsonResponse({'msg': 0 if status else 1, 'isAlive': status})


@login_required
def server_runtime_view(request):
    hostname = request.GET.get('hostname')
    server = get_object_or_404(Server, hostname=hostname)
    return render(request, "assets/server_runtime.html", {'server': server})


@login_required
def server_runtime_data(request):
    hostname = request.GET.get('hostname')
    try:
        server = Server.objects.get(hostname=hostname)
    except Server.DoesNotExist:
        return JsonResponse({'msg': 'Server[%s] does not exists'})
    data = server.get_runtime_data()
    ret = {
        'msg': 0 if data else 1,
        'data': data or '',
    }
    return JsonResponse(ret)


def socket_constants(prefix):
    return dict((getattr(socket, n), n) for n in dir(socket) if n.startswith(prefix))


@login_required
def server_connections_view(request,
                            socket_families=socket_constants('AF_'),
                            socket_types=socket_constants('SOCK_'),
                            states=('LISTEN', 'ESTABLISHED', 'SYN_SENT',
                                    'SYN_RECV', 'FIN_WAIT1', 'FIN_WAIT2',
                                    'TIME_WAIT', 'CLOSE', 'CLOSE_WAIT',
                                    'LAST_ACK', 'CLOSING', 'NONE')):

    hostname = request.GET.get('hostname')
    server = get_object_or_404(Server, hostname=hostname)
    context = {
        'server': server,
        'socket_families': socket_families,
        'socket_types': socket_types,
        'states': states,
    }
    return render(request, "assets/server_connections.html", context)


@login_required
def server_connections(request):
    hostname = request.GET.get('hostname')
    try:
        server = Server.objects.get(hostname=hostname)
    except Server.DoesNotExist:
        return JsonResponse({'msg': 'Server[%s] does not exists'})

    conns = server.get_connections(family=request.GET.get('family', ''),
                                   type=request.GET.get('type', ''),
                                   state=request.GET.get('state', ''))
    ret = {
        'msg': 0 if conns is not None else 1,
        'conns': conns or '',
    }
    return JsonResponse(ret)


@login_required
def server_network_interfaces(request):
    hostname = request.GET.get('hostname')
    try:
        server = Server.objects.get(hostname=hostname)
    except Server.DoesNotExist:
        return JsonResponse({'msg': 'Server[%s] does not exists'})

    netifs = server.get_network_interfaces()
    ret = {
        'msg': 0 if netifs is not None else 1,
        'netifs': netifs if netifs is not None else '',
    }
    return JsonResponse(ret)


@login_required
def server_process_list_view(request):
    hostname = request.GET.get('hostname')
    server = get_object_or_404(Server, hostname=hostname)
    return render(request, "assets/server_process_list.html", {'server': server})


@login_required
def server_process_list(request):
    hostname = request.GET.get('hostname')
    try:
        server = Server.objects.get(hostname=hostname)
    except Server.DoesNotExist:
        return JsonResponse({'msg': 'Server[%s] does not exists'})

    procs = server.get_process_list()
    ret = {
        'msg': 0 if procs is not None else 1,
        'procs': procs if procs is not None else '',
    }
    return JsonResponse(ret)


class NetworkDeviceCreate(PermissionRequiredMixin, CreateView):
    model = NetworkDevice
    form_class = NetworkDeviceForm
    template_name = 'assets/network_device_form.html'
    permission_required = 'assets.add_networkdevice'

    def get_initial(self):
        initial = super(NetworkDeviceCreate, self).get_initial()
        self.cabinet = get_object_or_404(Cabinet, id=self.args[0])
        initial['cabinet'] = self.cabinet
        return initial

    def get_context_data(self, **kwargs):
        context = super(NetworkDeviceCreate, self).get_context_data(**kwargs)
        context['cabinet'] = self.cabinet
        return context

    def get_success_url(self):
        return self.cabinet.get_absolute_url()


class NetworkDeviceUpdate(PermissionRequiredMixin, UpdateView):
    model = NetworkDevice
    form_class = NetworkDeviceForm
    context_object_name = 'network_device'
    template_name = 'assets/network_device_form.html'
    permission_required = 'assets.change_networkdevice'


class NetworkDeviceDetail(LoginRequiredMixin, DetailView):
    model = NetworkDevice
    context_object_name = 'network_device'
    template_name = 'assets/network_device_detail.html'


class NetworkDeviceDelete(PermissionRequiredMixin, DeleteView):
    model = NetworkDevice
    context_object_name = 'network_device'
    template_name = 'assets/network_device_confirm_delete.html'
    permission_required = 'assets.delete_networkdevice'

    def get_success_url(self):
        return self.object.cabinet.get_absolute_url()
