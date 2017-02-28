# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import urlparse
import re
import json
import logging

import redis

from django.core.urlresolvers import reverse_lazy, reverse
from django.shortcuts import render
from django.http import JsonResponse, Http404, HttpResponseRedirect
from django.views.generic import CreateView, ListView, UpdateView, DetailView, DeleteView
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.conf import settings

from utils import connect_node
from utils.mixins import LoginRequiredMixin, PermissionRequiredMixin
from .models import Idc, Cabinet, Server, NetworkDevice, NetCard
from .forms import IdcForm, CabinetForm, NetworkDeviceForm, ServerForm


RDS = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)

errlog = logging.getLogger('marmot')


class IdcCreate(PermissionRequiredMixin, CreateView):
    model = Idc
    form_class = IdcForm
    template_name = 'assets/idc_form.html'
    success_url = reverse_lazy('idc_list')
    permission_required = 'assets.add_idc'
    raise_exception = True


class IdcUpdate(PermissionRequiredMixin, UpdateView):
    model = Idc
    form_class = IdcForm
    template_name = 'assets/idc_form.html'
    permission_required = 'assets.change_idc'
    raise_exception = True


class IdcDetail(LoginRequiredMixin, DetailView):
    model = Idc
    context_object_name = 'idc'
    template_name = 'assets/idc_detail.html'

    def get_context_data(self, **kwargs):
        context = super(IdcDetail, self).get_context_data(**kwargs)
        context['cabinet_list'] = self.object.cabinet_set.all()
        return context


class IdcDelete(PermissionRequiredMixin, DeleteView):
    model = Idc
    context_object_name = 'idc'
    template_name = 'assets/idc_confirm_delete.html'
    success_url = reverse_lazy('idc_list')
    permission_required = 'assets.delete_idc'
    raise_exception = True


class IdcList(LoginRequiredMixin, ListView):
    model = Idc
    context_object_name = 'idc_list'
    template_name = 'assets/idc_list.html'


class CabinetCreate(PermissionRequiredMixin, CreateView):
    model = Cabinet
    form_class = CabinetForm
    template_name = 'assets/cabinet_form.html'
    success_url = '/assets/idc/%s'
    permission_required = 'assets.add_cabinet'
    raise_exception = True

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
        return self.success_url % self.args[0]


class CabinetUpdate(PermissionRequiredMixin, UpdateView):
    model = Cabinet
    form_class = CabinetForm
    context_object_name = 'cabinet'
    template_name = 'assets/cabinet_form.html'
    permission_required = 'assets.change_cabinet'
    raise_exception = True


class CabinetDetail(LoginRequiredMixin, DetailView):
    model = Cabinet
    context_object_name = 'cabinet'
    template_name = 'assets/cabinet_detail.html'

    def get_context_data(self, **kwargs):
        context = super(CabinetDetail, self).get_context_data(**kwargs)
        context['server_list'] = self.object.server_set.all()
        context['network_device_list'] = self.object.networkdevice_set.all()
        context['servers_online'] = RDS.keys()
        return context


class CabinetDelete(PermissionRequiredMixin, DeleteView):
    model = Cabinet
    context_object_name = 'cabinet'
    template_name = 'assets/cabinet_confirm_delete.html'
    success_url = '/assets/idc/%s'
    permission_required = 'assets.delete_cabinet'
    raise_exception = True

    def get_success_url(self):
        return self.success_url % self.object.idc.id


class ServerAdd(PermissionRequiredMixin, CreateView):
    model = Server
    form_class = ServerForm
    template_name = 'assets/server_add.html'
    success_url = '/assets/cabinet/%s'
    permission_required = 'assets.add_server'
    raise_exception = True

    def get_initial(self):
        initial = super(ServerAdd, self).get_initial()
        server_ip = self.request.GET['ip']
        self.cabinet = Cabinet.objects.get(id=self.args[0])
        try:
            node = connect_node(server_ip)
            base_info = node.get_base_info()
        except Exception:
            return initial
        system = base_info['system']
        cpu_info = base_info['cpu_info']
        initial.update({
            'cabinet': self.cabinet,
            'hostname': base_info['hostname'],
            'ip': server_ip,
            'os': base_info['os_distribution'],
            'serial_num': system['serial-number'],
            'manufacturer': system['manufacturer'],
            'product_model': system['product-name'],
            'cpu_model': cpu_info['model'],
            'cpu_logic_nums': cpu_info['core_num'],
            'mem_size': base_info['memory_total'],
            'disk_size': base_info['disk_size'],
        })
        return initial

    def get_context_data(self, **kwargs):
        context = super(ServerAdd, self).get_context_data(**kwargs)
        context['cabinet'] = self.cabinet
        return context

    def get_success_url(self):
        return self.success_url % self.args[0]

    def form_valid(self, form):
        cleaned_data = form.cleaned_data
        monitor_enabled = cleaned_data['monitor_enabled']
        server_ip = cleaned_data['ip']
        # cpu_level = cleaned_data['cpu_level']
        memory_level = cleaned_data['memory_level']
        disk_level = cleaned_data['disk_level']
        alarm_interval = cleaned_data['alarm_interval']
        try:
            node = connect_node(server_ip)
            netcard_info = node.get_netcard_info()
            node.set_memory_monitor_level(memory_level)
            node.set_disk_monitor_level(disk_level)
            node.set_alarm_interval(alarm_interval)
            if monitor_enabled:
                node.start_monitor()
        except Exception:
            errlog.exception('Connect node error')
            return super(ServerAdd, self).form_valid(form)
        self.object = form.save()
        # bond = netcard_info['bond']
        for card, data in netcard_info.items():
            NetCard.objects.create(
                server=self.object, name=card, ip_addr=data['addr'], net_addr=data['broadcast'],
                mac_addr=data['mac'], sub_mask=data['mask']
            )
        return HttpResponseRedirect(self.get_success_url())


class ServerUpdate(PermissionRequiredMixin, UpdateView):
    model = Server
    form_class = ServerForm
    context_object_name = 'server'
    template_name = 'assets/server_update.html'
    permission_required = 'assets.change_server'
    raise_exception = True

    def form_valid(self, form):
        cleaned_data = form.cleaned_data
        monitor_enabled = cleaned_data['monitor_enabled']
        server_ip = cleaned_data['ip']
        # cpu_level = cleaned_data['cpu_level']
        memory_level = cleaned_data['memory_level']
        disk_level = cleaned_data['disk_level']
        alarm_interval = cleaned_data['alarm_interval']
        try:
            node = connect_node(server_ip)
            netcard_info = node.get_netcard_info()
            node.set_memory_monitor_level(memory_level)
            node.set_disk_monitor_level(disk_level)
            node.set_alarm_interval(alarm_interval)
            if monitor_enabled:
                node.start_monitor()
            else:
                node.stop_monitor()
        except Exception:
            errlog.exception('Node Error')
            return super(ServerUpdate, self).form_valid(form)
        self.object = form.save()
        # bond = netcard_info['bond']
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

    def get_context_data(self, **kwargs):
        context = super(ServerDetail, self).get_context_data(**kwargs)
        context['netcard_list'] = self.object.netcard_set.all()
        return context


class ServerDelete(PermissionRequiredMixin, DeleteView):
    model = Server
    context_object_name = 'server'
    template_name = 'assets/server_confirm_delete.html'
    success_url = '/assets/cabinet/%s'
    permission_required = 'assets.delete_server'
    raise_exception = True

    def get_success_url(self):
        return self.success_url % self.object.cabinet.id

    def get_context_data(self, **kwargs):
        context = super(ServerDelete, self).get_context_data(**kwargs)
        context['center'] = self.object.master_server_set.all().first()
        return context


class ServerList(LoginRequiredMixin, ListView):
    model = Server
    paginate_by = 20
    context_object_name = 'servers'
    template_name = 'assets/server_list.html'

    def get_context_data(self, **kwargs):
        context = super(ServerList, self).get_context_data(**kwargs)
        context['servers_online'] = RDS.keys()
        return context


def server_conf(request):
    ip = request.GET['ip']
    try:
        server = Server.objects.get(ip=ip)
    except Server.DoesNotExist:
        return JsonResponse({
            'alarm_url': urlparse.urljoin(settings.MAIN_URL, reverse('alarm')),
            'monitor': {
                'enabled': False,
                'cpu': 99.0,
                'memory': 80,
                'disk': 80,
                'alarm_interval': 20,
            }
        })
    return JsonResponse({
        'alarm_url': urlparse.urljoin(settings.MAIN_URL, reverse('alarm')),
        'monitor': {
            'enabled': server.monitor_enabled,
            'cpu': server.cpu_level,
            'memory': server.memory_level,
            'disk': server.disk_level,
            'alarm_interval': server.alarm_interval,
        }
    })


def server_runtime_info(request):
    ip = request.GET['ip']
    info = RDS.get(ip)
    ret = {
        'ip': ip,
        'msg': 1 if info else 0,
        'info': json.loads(info) if info else '',
    }
    return JsonResponse(ret)


@login_required
def server_online_list(request):
    cabinet_id = request.GET.get('cabinet')
    try:
        cabinet = Cabinet.objects.get(id=cabinet_id)
    except (Cabinet.DoesNotExist, ValueError):
        raise Http404
    pattern = re.compile(r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$')
    servers_online = []
    for k in RDS.keys():
        if re.match(pattern, k):
            servers_online.append(k)
    context = {
        'cabinet': cabinet,
        'servers_added': dict(Server.objects.values_list('ip', 'id')),
        'servers_online': {server: json.loads(RDS.get(server))['hostname'] for server in servers_online}
    }
    return render(request, 'assets/server_online_list.html', context)


class NetworkDeviceCreate(PermissionRequiredMixin, CreateView):
    model = NetworkDevice
    form_class = NetworkDeviceForm
    template_name = 'assets/network_device_form.html'
    success_url = '/assets/cabinet/%s'
    permission_required = 'assets.add_networkdevice'
    raise_exception = True

    def get_initial(self):
        initial = super(NetworkDeviceCreate, self).get_initial()
        self.cabinet = Cabinet.objects.get(id=self.args[0])
        initial['cabinet'] = self.cabinet
        return initial

    def get_context_data(self, **kwargs):
        context = super(NetworkDeviceCreate, self).get_context_data(**kwargs)
        context['cabinet'] = self.cabinet
        return context

    def get_success_url(self):
        return self.success_url % self.args[0]


class NetworkDeviceUpdate(PermissionRequiredMixin, UpdateView):
    model = NetworkDevice
    form_class = NetworkDeviceForm
    context_object_name = 'network_device'
    template_name = 'assets/network_device_form.html'
    permission_required = 'assets.change_networkdevice'
    raise_exception = True


class NetworkDeviceDetail(LoginRequiredMixin, DetailView):
    model = NetworkDevice
    context_object_name = 'network_device'
    template_name = 'assets/network_device_detail.html'


class NetworkDeviceDelete(PermissionRequiredMixin, DeleteView):
    model = NetworkDevice
    context_object_name = 'network_device'
    template_name = 'assets/network_device_confirm_delete.html'
    success_url = '/assets/cabinet/%s'
    permission_required = 'assets.delete_networkdevice'
    raise_exception = True

    def get_success_url(self):
        return self.success_url % self.object.cabinet.id
