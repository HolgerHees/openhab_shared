# -*- coding: utf-8 -*-

import traceback
import time
import profile, pstats, io
import threading
import sys

from java.lang import NoSuchFieldException
from java.time import ZonedDateTime, Instant, ZoneId
from java.time.format import DateTimeFormatter

from inspect import getframeinfo, stack

from org.slf4j import LoggerFactory

from org.openhab.core.automation import Rule as SmarthomeRule

from org.openhab.core.types import UnDefType
from org.openhab.core.persistence.extensions import PersistenceExtensions
from org.openhab.core.thing import ChannelUID, ThingUID

from shared.jsr223 import scope    
from shared.triggers import ItemStateUpdateTrigger, ItemStateChangeTrigger

from configuration import LOG_PREFIX, allTelegramBots, allTelegramAdminBots

log = LoggerFactory.getLogger(LOG_PREFIX)

actions           = scope.get("actions")

itemRegistry      = scope.get("itemRegistry")
items             = scope.get("items")
things            = scope.get("things")

events            = scope.get("events")
scriptExtension   = scope.get("scriptExtension")

scriptExtension.importPreset("RuleSupport")
automationManager = scope.get("automationManager")

scriptExtension.importPreset("RuleSimple")
SimpleRule = scope.get("SimpleRule")

class rule(object):
    def __init__(self, name,profile=None):
        self.name = name
        self.profile = profile
        
    def __call__(self, clazz):
        proxy = self
        
        filePackage = proxy.getFilePackage(proxy.name)
        classPackage = proxy.getClassPackage(clazz.__name__)

        def init(self, *args, **kwargs):
            SimpleRule.__init__(self)
            #proxy.set_uid_prefix(self,classPackage,filePackage)
            clazz.__init__(self, *args, **kwargs)

            self.triggerItems = {}
            _triggers = []
            for trigger in self.triggers:
                try:
                    self.triggerItems[ trigger.getConfiguration().get("itemName") ] = True
                except NotImplementedError:
                    # openhab 2.4
                    self.triggerItems[ trigger.trigger.getConfiguration().get("itemName") ] = True
                    _triggers.append(trigger.trigger)
            if len(_triggers) > 0:
                self.triggers = _triggers

        subclass = type(clazz.__name__, (clazz, SimpleRule), dict(__init__=init))
        subclass.execute = proxy.executeWrapper(clazz.execute)
        
        #subclass.log = logging.getLogger( LOG_PREFIX + "." + filePackage + "." + classPackage )
        subclass.log = LoggerFactory.getLogger( LOG_PREFIX + "." + filePackage + "." + classPackage )

        automationManager.addRule(subclass())

        subclass.log.debug("Rule initialised")
        
        return subclass
    
    def getFilePackage(self,fileName):
        if fileName.endswith(".py"):
            filePackage = fileName[:-3]
        else:
            filePackage = fileName

        return filePackage

    def getClassPackage(self,className):
        if className.endswith("Rule"):
            classPackage = className[:-4]
        else:
            classPackage = className
        return classPackage
    
    def set_uid_prefix(self, rule, className, fileName):
        
        try:
            uid_field = type(SmarthomeRule).getClass(SmarthomeRule).getDeclaredField(SmarthomeRule, "uid")
        except NoSuchFieldException:
            # openhab 2.4
            uid_field = type(SimpleRule).getClass(SimpleRule).getDeclaredField(SimpleRule, "uid")
        uid_field.setAccessible(True)
        #uid_field.set(rule, "{}-{}".format(prefix, str(UUID.randomUUID())))
        #st = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        #st = datetime.datetime.utcnow().strftime('%H:%M:%S.%f')[:-3]
        #uid_field.set(rule, "{}-{}".format(prefix, st))
        uid_field.set(rule, "{} ({})".format(className, fileName))

    def executeWrapper(self,func):
        proxy = self
        
        def appendDetailInfo(self,event):
            if event is not None:
                if event.getType().startswith("Item"):
                    return u" [Item: {}]".format(event.getItemName())
                elif event.getType().startswith("Group"):
                    return u" [Group: {}]".format(event.getItemName())
                elif event.getType().startswith("Thing"):
                    return u" [Thing: {}]".format(event.getThingUID())
                else:
                    return u" [Other: {}]".format(event.getType())
            return ""

        def func_wrapper(self, module, input):
            
            try:
                event = input['event']
                # *** Filter indirect events out (like for groups related to the configured item)
                if getattr(event,"getItemName",None) is not None and event.getItemName() not in self.triggerItems:
                    self.log.debug("Rule skipped. Event is not related" + appendDetailInfo(self,event) )
                    return
            except KeyError:
                event = None
            
            try:
                start_time = time.clock()
                
                # *** execute
                if proxy.profile:
                    pr = profile.Profile()

                    #self.log.debug(str(getItem("Lights")))
                    #pr.enable()
                    pr.runctx('func(self, module, input)', {'self': self, 'module': module, 'input': input, 'func': func }, {})              
                    status = None
                else:
                    status = func(self, module, input)

                if proxy.profile:
                    #pr.disable()
                    s = io.BytesIO()
                    #http://www.jython.org/docs/library/profile.html#the-stats-class
                    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
                    ps.print_stats()
                    self.log.debug(s.getvalue())

                if status is None or status is True:
                    elapsed_time = round( ( time.clock() - start_time ) * 1000, 1 )

                    msg = "Rule executed in " + "{:6.1f}".format(elapsed_time) + " ms" + appendDetailInfo(self,event)

                    self.log.debug(msg)
                
            except NotInitialisedException as e:
                self.log.warn("Rule skipped: " + str(e))
            except:
                self.log.error("Rule execution failed:\n" + traceback.format_exc())

        return func_wrapper


class NotInitialisedException(Exception):
    pass

def startTimer(log, duration, callback, args=[], kwargs={}, oldTimer = None, groupCount = 0 ):
    if oldTimer != None:
        oldTimer.cancel()
        groupCount = oldTimer.groupCount
            
    groupCount = groupCount - 1
    
    if groupCount == 0:
        callback(*args, **kwargs)
        
        return None

    timer = createTimer(log, duration, callback, args, kwargs )
    timer.start()
    timer.groupCount = groupCount

    return timer

class createTimer:
    def __init__(self,log, duration, callback, args=[], kwargs={}):
        self.log = log
        self.callback = callback
        self.args = args
        self.kwargs = kwargs
        
        self.timer = threading.Timer(duration, self.handler)
        #log.info(str(self.timer))
        
    def handler(self):
        try:
            self.callback(*self.args, **self.kwargs)
        except:
            self.log.error(u"{}".format(traceback.format_exc()))
            raise
          
    def start(self):
        if not self.timer.isAlive():
            #log.info("timer started")
            self.timer.start() 
        else:
            #log.info("timer already started")
            pass
        
    def cancel(self):
        if self.timer.isAlive():
            #log.info("timer stopped")
            self.timer.cancel()
        else:
            #log.info("timer not alive")
            pass



def _getItemName(item):
    if isinstance(item, basestring):
        return item
    else:
        return item.getName()


def _getItem(item):
    if isinstance(item, basestring):
        return getItem(item)
    else:
        return item


# *** Group trigger ***
def _walkRecursive(parent):
    result = []
    items = parent.getAllMembers()
    for item in items:
        if item.getType() == "Group":
            result = result + _walkRecursive(item)
        else:
            result.append(item)
    return result


def getGroupMember(itemOrName):
    return _walkRecursive(_getItem(itemOrName))


def getGroupMemberUpdateTrigger(itemOrName, state=None, triggerName=None):
    triggers = []
    items = getGroupMember(getItem(itemOrName))
    for item in items:
        triggers.append(ItemStateUpdateTrigger(item.getName(), state=state, trigger_name=triggerName))
    return triggers

def getGroupMemberChangeTrigger(itemOrName, state=None, triggerName=None):
    triggers = []
    items = getGroupMember(itemOrName)
    for item in items:
        triggers.append(ItemStateChangeTrigger(item.getName(), state=state, trigger_name=triggerName))
    return triggers


# *** Item getter ***
def getThing(name):
    item = things.get(ThingUID(name))
    if item is None:
        raise NotInitialisedException(u"Thing {} not found".format(name))
    return item

def getChannel(name):
    item = things.getChannel(ChannelUID(name))
    if item is None:
        raise NotInitialisedException(u"Channel {} not found".format(name))
    return item

def getItem(name):
    item = itemRegistry.getItem(name)
    if item is None:
        raise NotInitialisedException(u"Item {} not found".format(name))
    return item


def getFilteredChildItems(itemOrName, state):
    items = getGroupMember(itemOrName)
    if isinstance(state, list):
        return filter(lambda child: child.getState() in state, items)
    else:
        return filter(lambda child: child.getState() == state, items)

def getItemStateWithFallback(itemOrName,fallback):
    state = getItemState(itemOrName)
    if isinstance(state,UnDefType) and fallback is not None:
        state = fallback
    return state
  
def getItemState(itemOrName):
    name = _getItemName(itemOrName)
    state = items.get(name)
    if state is None:
        raise NotInitialisedException(u"Item state for {} not found".format(name))
    return state

def getHistoricItemEntry(itemOrName, refDate):
    item = _getItem(itemOrName)
    historicEntry = PersistenceExtensions.historicState(item, refDate, "jdbc")
    if historicEntry is None:
        raise NotInitialisedException(u"Item history for {} before {} not found".format(item.getName(),refDate))
    return historicEntry


def getHistoricItemState(itemOrName, refDate):
    return getHistoricItemEntry(itemOrName, refDate).getState()


def getMaxItemState(itemOrName, refDate):
    item = _getItem(itemOrName)
    historicState = PersistenceExtensions.maximumSince(item, refDate, "jdbc")
    if historicState is None:
        raise NotInitialisedException(u"Item max state for {} before {} not found".format(item.getName(),refDate))
    return historicState.getState()


# *** Item updates ***
def _checkForUpdates(itemOrName, state):
    currentState = getItemState(itemOrName)
    if type(currentState) is not UnDefType:
        if isinstance(state, basestring):
            if currentState.toString() == state:
                return False
        elif isinstance(state, int):
            if currentState.doubleValue() == float(state):
                return False
        elif isinstance(state, float):
            if currentState.doubleValue() == state:
                return False
        elif currentState == state:
            return False

    return True

def postUpdateIfChanged(itemOrName, state):
    if not _checkForUpdates(itemOrName, state):
        return False

    postUpdate(itemOrName, state)
    return True


def postUpdate(itemOrName, state):
    item = _getItem(itemOrName)
    return events.postUpdate(item, state)


def sendCommandIfChanged(itemOrName, state):
    if not _checkForUpdates(itemOrName, state):
        return False

    sendCommand(itemOrName, state)
    return True

def sendCommand(itemOrName, command):
    item = _getItem(itemOrName)
    return events.sendCommand(item, command)

def itemStateNewerThen(itemOrName, refDate):
    state = getItemState(itemOrName)
    if isinstance(state,UnDefType):
        return False
    return state.getZonedDateTime().toInstant().toEpochMilli() > refDate.toInstant().toEpochMilli()

def itemStateOlderThen(itemOrName, refDate):
    return not itemStateNewerThen(itemOrName, refDate)

def itemLastUpdateNewerThen(itemOrName, refDate):
    try:
        return getItemLastUpdate(itemOrName).isAfter(refDate)
    except NotInitialisedException:
      return False

def itemLastUpdateOlderThen(itemOrName, refDate):
    try:
      return not itemLastUpdateNewerThen(itemOrName, refDate)
    except NotInitialisedException:
      return True

def getItemLastUpdate(itemOrName):
    item = _getItem(itemOrName)
    lastUpdate = PersistenceExtensions.lastUpdate(item)
    if lastUpdate is None:
        return ZonedDateTime.ofInstant(Instant.ofEpochMilli(0), ZoneId.systemDefault())
        #raise NotInitialisedException("Item lastUpdate for '" + item.getName() + "' not found")
    return lastUpdate

def itemLastChangeNewerThen(itemOrName, refDate):
    return getItemLastChange(itemOrName).isAfter(refDate)

def itemLastChangeOlderThen(itemOrName, refDate):
    return not itemLastChangeNewerThen(itemOrName, refDate)

def getItemLastChange(itemOrName):
    item = _getItem(itemOrName)
    lastChange = PersistenceExtensions.lastUpdate(item,"jdbc")
    if lastChange is None:
        raise NotInitialisedException("Item lastChange for '" + item.getName() + "' not found")
    return lastChange

def getStableMinMaxItemState( now, itemName, checkTimeRange ):
        
    currentEndTime = now
    currentEndTimeMillis = currentEndTime.toInstant().toEpochMilli()
    minTimeMillis = currentEndTimeMillis - ( checkTimeRange * 60 * 1000 )

    minValue = None
    maxValue = None

    value = 0.0
    duration = 0

    # get and cache "real" item to speedup getHistoricItemEntry. Otherwise "getHistoricItemEntry" will lookup the item by its name every time
    item = getItem(itemName)

    entry = getHistoricItemEntry(item, now)
    
    while True:
        currentStartMillis = entry.getTimestamp().toInstant().toEpochMilli()

        if currentStartMillis < minTimeMillis:
            currentStartMillis = minTimeMillis

        _duration = currentEndTimeMillis - currentStartMillis
        _value = entry.getState().doubleValue()

        if minValue == None or minValue > _value:
            minValue = _value

        if maxValue == None or maxValue < _value:
            maxValue = _value

        duration = duration + _duration
        value = value + ( _value * _duration )

        currentEndTimeMillis = currentStartMillis -1

        if currentEndTimeMillis < minTimeMillis:
            break

        currentEndTime = ZonedDateTime.ofInstant(Instant.ofEpochMilli(currentEndTimeMillis), ZoneId.systemDefault())

        entry = getHistoricItemEntry(item, currentEndTime )
        
    value = ( value / duration )

    return [ value, minValue, maxValue ]

def getStableItemState( now, itemName, checkTimeRange ):
        
    value, _, _ = getStableMinMaxItemState(now,itemName, checkTimeRange)
        
    return value

# *** Notifications ***
def sendNotification(header, message, url=None, recipients = None):
    chars = {
        u"_": u"\\_"
    }
    for k,v in chars.iteritems():
        message = message.replace(k,v)
        
    if recipients is None:
        recipients = allTelegramBots
    for recipient in recipients:
        if url == None:
            bot = actions.get("telegram", "telegram:telegramBot:{}".format(recipient))
            result = bot.sendTelegram("*" + header + "*: " + message)
            if result == 0:
                caller = getframeinfo(stack()[1][0])
                log.error(u"Failed to send telegram message '{}: {}' from {}:{}".format(header, message, caller.filename, caller.lineno))
        else:
            bot = actions.get("telegram", "telegram:telegramBot:{}".format(recipient))
            result = bot.sendTelegramPhoto(url,"*" + header + "*: " + message)
            if result == 0:
                caller = getframeinfo(stack()[1][0])
                log.error(u"Failed to send telegram message '{}: {}' from {}:{}".format(header, message, caller.filename, caller.lineno))

def sendNotificationToAllAdmins(header, message, url=None):
    sendNotification(header,message,url,allTelegramAdminBots)
