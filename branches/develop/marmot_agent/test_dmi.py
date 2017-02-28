#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
import time
import subprocess


def dmi_info():
    return {
        'system': {
            'manufacturer': subprocess.check_output(['sudo', 'dmidecode', '-s', 'system-manufacturer']).strip(),
            'product-name': subprocess.check_output(['sudo', 'dmidecode', '-s', 'system-product-name']).strip(),
            'version': subprocess.check_output(['sudo', 'dmidecode', '-s', 'system-version']).strip(),
            'serial-number': subprocess.check_output(['sudo', 'dmidecode', '-s', 'system-serial-number']).strip(),
            'uuid': subprocess.check_output(['sudo', 'dmidecode', '-s', 'system-uuid']).strip(),
        },
        'cpu': {
            'manufacturer': subprocess.check_output(['sudo', 'dmidecode', '-s', 'processor-manufacturer']).strip(),
            'version': subprocess.check_output(['sudo', 'dmidecode', '-s', 'processor-version']).strip(),
            'family': subprocess.check_output(['sudo', 'dmidecode', '-s', 'processor-family']).strip(),
        }
    }


st = time.time()
print dmi_info()
print time.time() - st


def dmidecode_system():
    system_pattern = re.compile(
        r'System\ Information\n\tManufacturer:\ (?P<manufacturer>.*)\n'
        r'\tProduct\ Name:\ (?P<product_name>.*)\n'
        r'\tVersion:\ (?P<version>.*)\n'
        r'\tSerial\ Number:\ (?P<serial_number>.*)\n'
        r'\tUUID:\ (?P<uuid>.*)\n'
        r'\t(.)*\n'
        r'\t(.)*\n'
        r'\tFamily:\ (?P<family>.*)\n'
    )
    output = subprocess.check_output(['sudo', 'dmidecode'])
    group = re.search(system_pattern, output)
    return {
        'manufacturer': group.group('manufacturer'),
        'product-name': group.group('product_name'),
        'version': group.group('version'),
        'serial-number': group.group('serial_number'),
        'uuid': group.group('uuid'),
        'family:': group.group('family'),
    }


st = time.time()
print dmidecode_system()
print time.time() - st


def machine_info():
    output = subprocess.check_output(['sudo', 'dmidecode'])
    lines = iter(output.strip().splitlines())
    for line in lines:
        if 'System Information' in line:
            break
    data = {}
    for line in lines:
        line = line.rstrip()
        if line.startswith('\t'):
            k, v = [i.strip() for i in line.lstrip().split(':', 1)]
            if v:
                data[k] = v
            else:
                data[k] = []
        else:
            break
    return data


st = time.time()
print machine_info()
print time.time() - st
