#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
import os
import platform
import subprocess
import pprint
import unittest

from marmot import dmidecode_system


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


def _linux_os_release():
    """Try to determine the name of a Linux distribution.
    This function checks for the /etc/os-release file.
    It takes the name from the 'NAME' field and the version from 'VERSION_ID'.
    An empty string is returned if the above values cannot be determined.
    """
    pretty_name = ''
    ashtray = {}
    keys = ['NAME', 'VERSION_ID']
    try:
        with open(os.path.join('/etc', 'os-release')) as f:
            for line in f:
                for key in keys:
                    if line.startswith(key):
                        ashtray[key] = line.strip().split('=')[1][1:-1]
    except (OSError, IOError):
        return pretty_name

    if ashtray:
        if 'NAME' in ashtray:
            pretty_name = ashtray['NAME']
        if 'VERSION_ID' in ashtray:
            pretty_name += ' {}'.format(ashtray['VERSION_ID'])

    return pretty_name


def get_system():
    _system = {
        'hostname': platform.node(),
        'os_name': platform.system(),
        'os_verbose': platform.platform(),
        'platform': platform.architecture()[0],
        'os_version': platform.release(),
    }
    linux_distro = platform.linux_distribution()
    if linux_distro[0] == '':
        _system['linux_distro'] = _linux_os_release()
    else:
        _system['linux_distro'] = ' '.join(linux_distro[:2])
    return _system


class DmiTestCase(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_dmi_info(self):
        info = dmi_info()
        pprint.pprint(info)
        self.assertIsNotNone(info)

    def test_dmidecode_system(self):
        info = dmidecode_system()
        pprint.pprint(info)
        self.assertIsNotNone(info)

    def test_system(self):
        info = get_system()
        pprint.pprint(info)
        self.assertIsNotNone(info)


if __name__ == "__main__":
    unittest.main()
