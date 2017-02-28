# -*- coding: utf-8 -*-

"""
100credit--警报服务Ice接口
Ice3.6
"""

import json
import Ice

from alarm import BrSendAlarmServicePrx


CONF = {
    # 'Ice.Default.Locator': 'BrIceGrid/Locator:tcp -h 192.168.162.181 -p 4061:tcp -h 192.168.162.182 -p 4061',  # dev
    # 'Ice.Default.Locator': 'BrIceGrid/Locator:tcp -h 192.168.23.111 -p 4061:tcp -h 192.168.23.112 -p 4061',  # pre
    'Ice.Default.Locator': 'DacIceGrid/Locator:tcp -h 192.168.22.59 -p 4061:tcp -h 192.168.22.58 -p 4061',  # prod
    'Ice.ThreadPool.Client.Size': '4',
    'Ice.ThreadPool.Client.SizeMax': '256',
    'Ice.ThreadPool.Client.StackSize': '65536',
    'Ice.MessageSizeMax': '65536',
    'Ice.Override.Timeout': '2000',
    'Ice.Override.ConnectTimeout': '5000',
    # 'Ice.RetryIntervals': '0 1000 5000',
    # 'Ice.ACM.Heartbeat': '2',
    # 'Ice.ACM.Close': '0',
    # 'Ice.Trace.Network': '2',  # 调试信息
}


class Alarm(object):
    ID = 'BrSendAlarmServiceV1.0.0'

    def __init__(self):
        props = Ice.createProperties()
        for k, v in CONF.items():
            props.setProperty(k, v)
        init_data = Ice.InitializationData()
        init_data.properties = props
        self.communicator = Ice.initialize(init_data)
        self.proxy = None

    def initialize(self):
        try:
            self.proxy = BrSendAlarmServicePrx.checkedCast(self.communicator.stringToProxy(self.ID))
        except Ice.ConnectTimeoutException:
            raise RuntimeError('Ice::ConnectTimeoutException')

        if not self.proxy:
            raise RuntimeError('Invalid proxy')

    def send(self, message):
        return self.proxy.sendAlarm(json.dumps(message))

    def send_to_personal(self, message):
        return self.proxy.sendAlarmToPresonal(json.dumps(message))

    def destroy(self):
        if self.communicator:
            self.communicator.destroy()


def send_alarm_to_personal(**kwargs):
    """客户端自定义发送人手机号,邮箱 sendAlarmToPresonal

    Usage::
        >>> from bralarm import send_alarm_to_personal
        >>> send_alarm_to_personal(mails='', msgs='', alarmType=3, mailContent='', mailTitle='', msgContent='')

    :param kwargs
    :param mails: 客户端指定邮箱地址以英文逗号分隔.
    :param msgs: 客户端指定手机号以英文逗号分隔;每个手机号前加86.
    :param alarmType: int 1短信邮件全部 2邮件 3短信 ,邮箱和短信默认都使用群发.
    :param mailContent: string 邮件内容 统一使用utf-8编码.
    :param mailTitle: string 邮件标题 统一使用utf-8编码.
    :param msgContent: string 统一使用utf-8编码,长度*70*,若超过,截取前*70*个字符.
    :rtype:True/False
    """
    alarm = Alarm()
    try:
        alarm.initialize()
    except RuntimeError:
        return False
    else:
        return alarm.send_to_personal(kwargs)
    finally:
        alarm.destroy()


if __name__ == '__main__':
    alarm = Alarm()
    try:
        alarm.initialize()
    except Exception:
        raise
    finally:
        alarm.destroy()

    # print send_alarm_to_personal(
    #     msgs='8618501986039',
    #     alarmType=3,
    #     msgContent='test message'
    # )
