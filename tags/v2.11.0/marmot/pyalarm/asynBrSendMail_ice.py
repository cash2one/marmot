# **********************************************************************
#
# Copyright (c) 2003-2016 ZeroC, Inc. All rights reserved.
#
# This copy of Ice is licensed to you under the terms described in the
# ICE_LICENSE file included in this distribution.
#
# **********************************************************************
#
# Ice version 3.6.2
#
# <auto-generated>
#
# Generated from file `asynBrSendMail.ice'
#
# Warning: do not edit this file.
#
# </auto-generated>
#

import Ice, IcePy

# Start of module alarm
_M_alarm = Ice.openModule('alarm')
__name__ = 'alarm'

if 'BrSendAlarmService' not in _M_alarm.__dict__:
    _M_alarm.BrSendAlarmService = Ice.createTempClass()
    class BrSendAlarmService(Ice.Object):
        def __init__(self):
            if Ice.getType(self) == _M_alarm.BrSendAlarmService:
                raise RuntimeError('alarm.BrSendAlarmService is an abstract class')

        def ice_ids(self, current=None):
            return ('::Ice::Object', '::alarm::BrSendAlarmService')

        def ice_id(self, current=None):
            return '::alarm::BrSendAlarmService'

        def ice_staticId():
            return '::alarm::BrSendAlarmService'
        ice_staticId = staticmethod(ice_staticId)

        def sendAlarm(self, json, current=None):
            pass

        def sendAlarmToPresonal(self, json, current=None):
            pass

        def afreshConfig(self, current=None):
            pass

        def __str__(self):
            return IcePy.stringify(self, _M_alarm._t_BrSendAlarmService)

        __repr__ = __str__

    _M_alarm.BrSendAlarmServicePrx = Ice.createTempClass()
    class BrSendAlarmServicePrx(Ice.ObjectPrx):

        def sendAlarm(self, json, _ctx=None):
            return _M_alarm.BrSendAlarmService._op_sendAlarm.invoke(self, ((json, ), _ctx))

        def begin_sendAlarm(self, json, _response=None, _ex=None, _sent=None, _ctx=None):
            return _M_alarm.BrSendAlarmService._op_sendAlarm.begin(self, ((json, ), _response, _ex, _sent, _ctx))

        def end_sendAlarm(self, _r):
            return _M_alarm.BrSendAlarmService._op_sendAlarm.end(self, _r)

        def sendAlarmToPresonal(self, json, _ctx=None):
            return _M_alarm.BrSendAlarmService._op_sendAlarmToPresonal.invoke(self, ((json, ), _ctx))

        def begin_sendAlarmToPresonal(self, json, _response=None, _ex=None, _sent=None, _ctx=None):
            return _M_alarm.BrSendAlarmService._op_sendAlarmToPresonal.begin(self, ((json, ), _response, _ex, _sent, _ctx))

        def end_sendAlarmToPresonal(self, _r):
            return _M_alarm.BrSendAlarmService._op_sendAlarmToPresonal.end(self, _r)

        def afreshConfig(self, _ctx=None):
            return _M_alarm.BrSendAlarmService._op_afreshConfig.invoke(self, ((), _ctx))

        def begin_afreshConfig(self, _response=None, _ex=None, _sent=None, _ctx=None):
            return _M_alarm.BrSendAlarmService._op_afreshConfig.begin(self, ((), _response, _ex, _sent, _ctx))

        def end_afreshConfig(self, _r):
            return _M_alarm.BrSendAlarmService._op_afreshConfig.end(self, _r)

        def checkedCast(proxy, facetOrCtx=None, _ctx=None):
            return _M_alarm.BrSendAlarmServicePrx.ice_checkedCast(proxy, '::alarm::BrSendAlarmService', facetOrCtx, _ctx)
        checkedCast = staticmethod(checkedCast)

        def uncheckedCast(proxy, facet=None):
            return _M_alarm.BrSendAlarmServicePrx.ice_uncheckedCast(proxy, facet)
        uncheckedCast = staticmethod(uncheckedCast)

        def ice_staticId():
            return '::alarm::BrSendAlarmService'
        ice_staticId = staticmethod(ice_staticId)

    _M_alarm._t_BrSendAlarmServicePrx = IcePy.defineProxy('::alarm::BrSendAlarmService', BrSendAlarmServicePrx)

    _M_alarm._t_BrSendAlarmService = IcePy.defineClass('::alarm::BrSendAlarmService', BrSendAlarmService, -1, (), True, False, None, (), ())
    BrSendAlarmService._ice_type = _M_alarm._t_BrSendAlarmService

    BrSendAlarmService._op_sendAlarm = IcePy.Operation('sendAlarm', Ice.OperationMode.Normal, Ice.OperationMode.Normal, False, None, (), (((), IcePy._t_string, False, 0),), (), ((), IcePy._t_bool, False, 0), ())
    BrSendAlarmService._op_sendAlarmToPresonal = IcePy.Operation('sendAlarmToPresonal', Ice.OperationMode.Normal, Ice.OperationMode.Normal, False, None, (), (((), IcePy._t_string, False, 0),), (), ((), IcePy._t_bool, False, 0), ())
    BrSendAlarmService._op_afreshConfig = IcePy.Operation('afreshConfig', Ice.OperationMode.Normal, Ice.OperationMode.Normal, False, None, (), (), (), ((), IcePy._t_bool, False, 0), ())

    _M_alarm.BrSendAlarmService = BrSendAlarmService
    del BrSendAlarmService

    _M_alarm.BrSendAlarmServicePrx = BrSendAlarmServicePrx
    del BrSendAlarmServicePrx

# End of module alarm
