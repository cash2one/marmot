# -*- coding: utf-8 -*-
# **********************************************************************
#
# Copyright (c) 2003-2016 ZeroC, Inc. All rights reserved.
#
# This copy of Ice is licensed to you under the terms described in the
# ICE_LICENSE file included in this distribution.
#
# **********************************************************************
#
# Ice version 3.6.3
#
# <auto-generated>
#
# Generated from file `asynBrSendMail.ice'
#
# Warning: do not edit this file.
#
# </auto-generated>
#

from sys import version_info as _version_info_
import Ice, IcePy

# Start of module alarm
_M_alarm = Ice.openModule('alarm')
__name__ = 'alarm'

if 'BrSendAlarmNewService' not in _M_alarm.__dict__:
    _M_alarm.BrSendAlarmNewService = Ice.createTempClass()
    class BrSendAlarmNewService(Ice.Object):
        def __init__(self):
            if Ice.getType(self) == _M_alarm.BrSendAlarmNewService:
                raise RuntimeError('alarm.BrSendAlarmNewService is an abstract class')

        def ice_ids(self, current=None):
            return ('::Ice::Object', '::alarm::BrSendAlarmNewService')

        def ice_id(self, current=None):
            return '::alarm::BrSendAlarmNewService'

        def ice_staticId():
            return '::alarm::BrSendAlarmNewService'
        ice_staticId = staticmethod(ice_staticId)

        def sendAlarm(self, json, current=None):
            pass

        def sendAlarmToPresonal(self, json, current=None):
            pass

        def operateQueue(self, json, current=None):
            pass

        def modifyFlagTot(self, flag, time, current=None):
            pass

        def removeOrAddExclude(self, exceptionCode, flag, time, current=None):
            pass

        def commonAttr(self, json, current=None):
            pass

        def __str__(self):
            return IcePy.stringify(self, _M_alarm._t_BrSendAlarmNewService)

        __repr__ = __str__

    _M_alarm.BrSendAlarmNewServicePrx = Ice.createTempClass()
    class BrSendAlarmNewServicePrx(Ice.ObjectPrx):

        def sendAlarm(self, json, _ctx=None):
            return _M_alarm.BrSendAlarmNewService._op_sendAlarm.invoke(self, ((json, ), _ctx))

        def begin_sendAlarm(self, json, _response=None, _ex=None, _sent=None, _ctx=None):
            return _M_alarm.BrSendAlarmNewService._op_sendAlarm.begin(self, ((json, ), _response, _ex, _sent, _ctx))

        def end_sendAlarm(self, _r):
            return _M_alarm.BrSendAlarmNewService._op_sendAlarm.end(self, _r)

        def sendAlarmToPresonal(self, json, _ctx=None):
            return _M_alarm.BrSendAlarmNewService._op_sendAlarmToPresonal.invoke(self, ((json, ), _ctx))

        def begin_sendAlarmToPresonal(self, json, _response=None, _ex=None, _sent=None, _ctx=None):
            return _M_alarm.BrSendAlarmNewService._op_sendAlarmToPresonal.begin(self, ((json, ), _response, _ex, _sent, _ctx))

        def end_sendAlarmToPresonal(self, _r):
            return _M_alarm.BrSendAlarmNewService._op_sendAlarmToPresonal.end(self, _r)

        def operateQueue(self, json, _ctx=None):
            return _M_alarm.BrSendAlarmNewService._op_operateQueue.invoke(self, ((json, ), _ctx))

        def begin_operateQueue(self, json, _response=None, _ex=None, _sent=None, _ctx=None):
            return _M_alarm.BrSendAlarmNewService._op_operateQueue.begin(self, ((json, ), _response, _ex, _sent, _ctx))

        def end_operateQueue(self, _r):
            return _M_alarm.BrSendAlarmNewService._op_operateQueue.end(self, _r)

        def modifyFlagTot(self, flag, time, _ctx=None):
            return _M_alarm.BrSendAlarmNewService._op_modifyFlagTot.invoke(self, ((flag, time), _ctx))

        def begin_modifyFlagTot(self, flag, time, _response=None, _ex=None, _sent=None, _ctx=None):
            return _M_alarm.BrSendAlarmNewService._op_modifyFlagTot.begin(self, ((flag, time), _response, _ex, _sent, _ctx))

        def end_modifyFlagTot(self, _r):
            return _M_alarm.BrSendAlarmNewService._op_modifyFlagTot.end(self, _r)

        def removeOrAddExclude(self, exceptionCode, flag, time, _ctx=None):
            return _M_alarm.BrSendAlarmNewService._op_removeOrAddExclude.invoke(self, ((exceptionCode, flag, time), _ctx))

        def begin_removeOrAddExclude(self, exceptionCode, flag, time, _response=None, _ex=None, _sent=None, _ctx=None):
            return _M_alarm.BrSendAlarmNewService._op_removeOrAddExclude.begin(self, ((exceptionCode, flag, time), _response, _ex, _sent, _ctx))

        def end_removeOrAddExclude(self, _r):
            return _M_alarm.BrSendAlarmNewService._op_removeOrAddExclude.end(self, _r)

        def commonAttr(self, json, _ctx=None):
            return _M_alarm.BrSendAlarmNewService._op_commonAttr.invoke(self, ((json, ), _ctx))

        def begin_commonAttr(self, json, _response=None, _ex=None, _sent=None, _ctx=None):
            return _M_alarm.BrSendAlarmNewService._op_commonAttr.begin(self, ((json, ), _response, _ex, _sent, _ctx))

        def end_commonAttr(self, _r):
            return _M_alarm.BrSendAlarmNewService._op_commonAttr.end(self, _r)

        def checkedCast(proxy, facetOrCtx=None, _ctx=None):
            return _M_alarm.BrSendAlarmNewServicePrx.ice_checkedCast(proxy, '::alarm::BrSendAlarmNewService', facetOrCtx, _ctx)
        checkedCast = staticmethod(checkedCast)

        def uncheckedCast(proxy, facet=None):
            return _M_alarm.BrSendAlarmNewServicePrx.ice_uncheckedCast(proxy, facet)
        uncheckedCast = staticmethod(uncheckedCast)

        def ice_staticId():
            return '::alarm::BrSendAlarmNewService'
        ice_staticId = staticmethod(ice_staticId)

    _M_alarm._t_BrSendAlarmNewServicePrx = IcePy.defineProxy('::alarm::BrSendAlarmNewService', BrSendAlarmNewServicePrx)

    _M_alarm._t_BrSendAlarmNewService = IcePy.defineClass('::alarm::BrSendAlarmNewService', BrSendAlarmNewService, -1, (), True, False, None, (), ())
    BrSendAlarmNewService._ice_type = _M_alarm._t_BrSendAlarmNewService

    BrSendAlarmNewService._op_sendAlarm = IcePy.Operation('sendAlarm', Ice.OperationMode.Normal, Ice.OperationMode.Normal, False, None, (), (((), IcePy._t_string, False, 0),), (), ((), IcePy._t_string, False, 0), ())
    BrSendAlarmNewService._op_sendAlarmToPresonal = IcePy.Operation('sendAlarmToPresonal', Ice.OperationMode.Normal, Ice.OperationMode.Normal, False, None, (), (((), IcePy._t_string, False, 0),), (), ((), IcePy._t_string, False, 0), ())
    BrSendAlarmNewService._op_operateQueue = IcePy.Operation('operateQueue', Ice.OperationMode.Normal, Ice.OperationMode.Normal, False, None, (), (((), IcePy._t_string, False, 0),), (), ((), IcePy._t_string, False, 0), ())
    BrSendAlarmNewService._op_modifyFlagTot = IcePy.Operation('modifyFlagTot', Ice.OperationMode.Normal, Ice.OperationMode.Normal, False, None, (), (((), IcePy._t_bool, False, 0), ((), IcePy._t_long, False, 0)), (), ((), IcePy._t_bool, False, 0), ())
    BrSendAlarmNewService._op_removeOrAddExclude = IcePy.Operation('removeOrAddExclude', Ice.OperationMode.Normal, Ice.OperationMode.Normal, False, None, (), (((), IcePy._t_int, False, 0), ((), IcePy._t_int, False, 0), ((), IcePy._t_long, False, 0)), (), ((), IcePy._t_bool, False, 0), ())
    BrSendAlarmNewService._op_commonAttr = IcePy.Operation('commonAttr', Ice.OperationMode.Normal, Ice.OperationMode.Normal, False, None, (), (((), IcePy._t_string, False, 0),), (), ((), IcePy._t_string, False, 0), ())

    _M_alarm.BrSendAlarmNewService = BrSendAlarmNewService
    del BrSendAlarmNewService

    _M_alarm.BrSendAlarmNewServicePrx = BrSendAlarmNewServicePrx
    del BrSendAlarmNewServicePrx

# End of module alarm
