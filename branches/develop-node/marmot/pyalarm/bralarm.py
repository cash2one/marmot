# -*- coding: utf-8 -*-

"""
100credit--新警报服务Ice接口
Ice-3.6

Ice接口说明:
http://redmine.100credit.cn/projects/dev/wiki/%E6%96%B0%E6%8A%A5%E8%AD%A6%E6%9C%8D%E5%8A%A1

设置地址:
http://alarm.100credit.cn

marmot设置:
项目ID: marmot
邮件接受人:
chao.zhang@100credit.com,haibo.duan@100credit.com,hewei.chen@100credit.com,
hongliang.zuo1@100credit.com,langxian.chen@100credit.com,li.sun@100credit.com,
shupeng.sun@100credit.com,xin.cao@100credit.com,xinjing.wang@100credit.com,
xue.bai@100credit.com,yingchun.zou@100credit.com,hua.qiao@100credit.com,jie.zhang@100credit.com
微信接受人:
张超,段海波,陈贺巍,左红亮,陈浪仙,孙立,孙树朋,曹鑫,王新静,白雪,邹迎春,乔华,闫龙,解远东,张洁

"""

from __future__ import absolute_import
import json
import Ice
import alarm


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
    # 'Ice.Trace.Network': '2',  # debug
}


class Alarm(object):
    ID = 'BrSendAlarmNewServiceV1.0.0'

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
            self.proxy = alarm.BrSendAlarmNewServicePrx.checkedCast(self.communicator.stringToProxy(self.ID))
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


def send_alarm(**kwargs):
    """
    Usage::
        >>> from pyalarm.bralarm import send_alarm
        >>> send_alarm(appType='marmot', exceptionCode=41001, mailTitle='', mailContent='', wechatContent='')

    :param kwargs
    :param alarmLevel: int 1实时; 2某一时间段(默认5min,100次)
    :param alarmType: int 1短信邮件全部; 2邮件; 3短信, 邮箱和短信默认都使用群发; 4微信; 5微信+邮件;
    :param exceptionCode:  int 代表唯一一个异常
    :param mailContent: string 邮件内容 统一使用utf-8编码.
    :param mailTitle: string 邮件标题 统一使用utf-8编码.

    :param msgContent: string 统一使用utf-8编码,长度*65*. 若超过截取前*65*个字符.
            大致文本:【异常代码；exceptionCode】+内容 +【监控】
    :param appType: string  配置项目名称
    :param invokedIP: string  "ip:port" 如果此参数有值, 警报ip替换成此ip.
            如果没有, 则警报ip使用服务端获取的ip地址
    :rtype: string {"result":41001,"code":"000","msg":"success"}

            ("000","success"),
            ("001","system error"),
            ("002","msgContent is  null"),
            ("003","wechat tosend is  null"),
            ("004","wechatContent is null"),
            ("005","exceptionCode is null"),
            ("006","onlycode alarmType mails msgs toUser toTag toDep content... is error"),
            ("008","flagTot is off"),
            ("009","this exceptionCode be excluded"),
            ("010","mail address is error"),
            ("011","send alarm is fail"),
            ("012","intel is blocking,send later");

    """
    a = Alarm()
    try:
        a.initialize()
    except RuntimeError as e:
        return False, str(e)
    else:
        ret = json.loads(a.send(kwargs))
        if ret['code'] != '000':
            return False, ret['msg']
        return True, ''
    finally:
        a.destroy()


def send_alarm_to_personal(**kwargs):
    """客户端自定义发送人手机号, 邮箱

    Usage::
        >>> from pyalarm.bralarm import send_alarm_to_personal
        >>> send_alarm_to_personal(mails='', msgs='', alarmType=3, mailContent='', mailTitle='', msgContent='')

    :param kwargs
    :param mails: 客户端指定邮箱地址以英文逗号分隔.
    :param msgs: 客户端指定手机号以英文逗号分隔;每个手机号前加86.
    :param alarmType: int 1短信邮件全部; 2邮件; 3短信, 邮箱和短信默认都使用群发; 4微信; 5微信+邮件;
    :param onlyCode: int 唯一码
    :param mailContent: string 邮件内容 统一使用utf-8编码.
    :param mailTitle: string 邮件标题 统一使用utf-8编码.
    :param msgContent: string 统一使用utf-8编码,长度*70*,若超过,截取前*70*个字符.
    :param sendType: string  指定发件人邮箱 使用该功能需预先定义好自己的发件人邮箱及密码
    :param msgType: string  选择使用发送短信通道签名 1百融 2虾球 3保筑科技 默认百融
    :param toUser: string  微信接收人姓名
    :param toDep: string  微信接收组
    :param toTag: string  微信接收标签 {"ta19":"Marmot"}
    :param wechatContent: string
    :rtype: string
    """
    a = Alarm()
    try:
        a.initialize()
    except RuntimeError as e:
        return False, str(e)
    else:
        ret = json.loads(a.send_to_personal(kwargs))
        if ret['code'] != '000':
            return False, ret['msg']
        return True, ''
    finally:
        a.destroy()


if __name__ == '__main__':
    # a = Alarm()
    # try:
    #     a.initialize()
    # except Exception:
    #     raise
    # finally:
    #     a.destroy()

    print send_alarm(
        appType='marmot',
        exceptionCode=41001,
        mailTitle='marmot-测试警报请忽略',
        mailContent='marmot测试警报',
        wechatContent='marmot测试警报',
    )

    # print send_alarm_to_personal(
    #     msgs='8618501986039',
    #     alarmType=3,
    #     msgContent='test message'
    # )

    # print send_alarm_to_personal(
    #     mails='xue.bai@100credit.com',
    #     msgs='8618501986039',
    #     alarmType=1,
    #     mailTitle='alarm ice test',
    #     mailContent='alarm ice test',
    #     msgContent='test message'
    # )
