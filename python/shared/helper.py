# -*- coding: utf-8 -*-

import traceback
import time
import profile, pstats, io
import threading

#from java.util import UUID
#import datetime
from java.lang import NoSuchFieldException
from org.openhab.core.automation import Rule as SmarthomeRule

try:
    from org.eclipse.smarthome.core.types import UnDefType
    from org.eclipse.smarthome.model.persistence.extensions import PersistenceExtensions
    from org.eclipse.smarthome.core.thing import ChannelUID, ThingUID

    from org.joda.time import DateTime
    from org.joda.time.format import DateTimeFormat
            
    isOpenhab2 = True
except Exception as e:
  
    from org.openhab.core.types import UnDefType
    from org.openhab.core.persistence.extensions import PersistenceExtensions
    from org.openhab.core.thing import ChannelUID, ThingUID
    
    from java.time import ZonedDateTime, Instant, ZoneId
    from java.time.format import DateTimeFormatter
        
    isOpenhab2 = False

from core.jsr223 import scope
from core.triggers import ItemStateUpdateTrigger, ItemStateChangeTrigger

if isOpenhab2:
    from core.actions import Telegram #, XMPP
else:
    class Telegram(object):
      @staticmethod
      def sendTelegram(recipient, message):
          bot = scope.actions.get("telegram", "telegram:telegramBot:{}".format(recipient))
          bot.sendTelegram(message)
          
      @staticmethod
      def sendTelegramPhoto(recipient, url, message):
          bot = scope.actions.get("telegram", "telegram:telegramBot:{}".format(recipient))
          bot.sendTelegramPhoto(url,message)

from org.slf4j import LoggerFactory

from configuration import LOG_PREFIX, allTelegramBots, allTelegramAdminBots

log = LoggerFactory.getLogger(LOG_PREFIX)

scriptExtension = scope.scriptExtension
itemRegistry = scope.itemRegistry
things = scope.things
items = scope.items
events = scope.events

automationManager = scope.automationManager
SimpleRule = scope.SimpleRule

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
        triggers.append(ItemStateUpdateTrigger(item.getName(), state, triggerName))
    return triggers

def getGroupMemberChangeTrigger(itemOrName, state=None, triggerName=None):
    triggers = []
    items = getGroupMember(itemOrName)
    for item in items:
        triggers.append(ItemStateChangeTrigger(item.getName(), state, triggerName))
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

#class DecimalHelper(object):
#    @staticmethod
#    def intValue(state,fallback=0):
#        return fallback if isinstance(state,UnDefType) else state.intValue()

# *** DateTime helper ***  
if isOpenhab2:
    class DateTimeHelper(object):
        @staticmethod
        def getNow():
            return DateTime.now()
        
        @staticmethod
        def getMillis(refDate):
            return refDate.getMillis()
          
        @staticmethod
        def getMillisFromHistoricItem(historicItem):
            return historicItem.getTimestamp().getTime()
          
        @staticmethod
        def getHour(refDate):
            return refDate.getHourOfDay()

        @staticmethod
        def getMinute(refDate):
            return refDate.getMinuteOfHour()

        @staticmethod
        def createFromMillis(millis):
            return DateTime(millis)
          
        @staticmethod
        def createFromDateTimeType(dateTimeType):
            return DateTime(dateTimeType.calendar.getTimeInMillis())

        @staticmethod
        def createAtStartOfDay(refDate):
            return refDate.withTimeAtStartOfDay()
            
        @staticmethod
        def createWithDate(refDate,year,month,day):
            return refDate.withDate(year,month,day)
            
        @staticmethod
        def createWithZone(refDate,zone):
            return refDate.toDateTime(zone)
        
        @staticmethod
        def getFormat(pattern):
            return DateTimeFormat.forPattern(pattern)

        @staticmethod
        def printFormatted(refDate,pattern):
            return pattern.print(refDate)

        @staticmethod
        def getAsState(refDate):
            return refDate.toString()
else:
    class DateTimeHelper(object):
        @staticmethod
        def getNow():
            return ZonedDateTime.now()

        @staticmethod
        def getMillis(refDate):
            return refDate.toInstant().toEpochMilli()
        
        @staticmethod
        def getMillisFromHistoricItem(historicItem):
            return historicItem.getTimestamp().toInstant().toEpochMilli()
          
        @staticmethod
        def getHour(refDate):
            return refDate.getHour()

        @staticmethod
        def getMinute(refDate):
            return refDate.getMinute()

        @staticmethod
        def createFromMillis(millis):
            return ZonedDateTime.ofInstant(Instant.ofEpochMilli(millis), ZoneId.systemDefault())
          
        @staticmethod
        def createFromDateTimeType(dateTimeType):
            return dateTimeType.getZonedDateTime()

        @staticmethod
        def createAtStartOfDay(refDate):
            return refDate.toLocalDate().atStartOfDay(refDate.getZone())

        @staticmethod
        def createWithDate(refDate,year,month,day):
            return refDate.withYear(year).withMonth(month).withDayOfMonth(day)

        @staticmethod
        def createWithZone(refDate,zone):
            return refDate.withZoneSameInstant(zone)

        @staticmethod
        def getFormat(pattern):
            return DateTimeFormatter.ofPattern(pattern)

        @staticmethod
        def printFormatted(refDate,pattern):
            return pattern.format(refDate)

        @staticmethod
        def getAsState(refDate):
            return refDate.toLocalDateTime().toString()

def itemStateNewerThen(itemOrName, refDate):
    return DateTimeHelper.getMillis(DateTimeHelper.createFromDateTimeType(getItemState(itemOrName))) > DateTimeHelper.getMillis(refDate)

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
        return DateTimeHelper.createFromMillis(0)
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

def getStableItemState( now, itemName, checkTimeRange ):
        
    currentEndTime = now
    currentEndTimeMillis = DateTimeHelper.getMillis(currentEndTime)
    minTimeMillis = currentEndTimeMillis - ( checkTimeRange * 60 * 1000 )

    value = 0.0
    duration = 0

    # get and cache "real" item to speedup getHistoricItemEntry. Otherwise "getHistoricItemEntry" will lookup the item by its name every time
    item = getItem(itemName)

    entry = getHistoricItemEntry(item, now)
    
    while True:
        currentStartMillis = DateTimeHelper.getMillisFromHistoricItem(entry)

        if currentStartMillis < minTimeMillis:
            currentStartMillis = minTimeMillis

        _duration = currentEndTimeMillis - currentStartMillis
        _value = entry.getState().doubleValue()

        duration = duration + _duration
        value = value + ( _value * _duration )

        currentEndTimeMillis = currentStartMillis -1

        if currentEndTimeMillis < minTimeMillis:
            break

        currentEndTime = DateTimeHelper.createFromMillis(currentEndTimeMillis)

        entry = getHistoricItemEntry(item, currentEndTime )
        
    value = ( value / duration )

    return value

# *** Notifications ***
def sendNotification(header, message, url=None, recipients = None):
    if recipients is None:
        recipients = allTelegramBots
    for recipient in recipients:
        if url == None:
            Telegram.sendTelegram(recipient, "*" + header + "*: " + message)
        else:
            Telegram.sendTelegramPhoto(recipient, url, "*" + header + "*: " + message)

def sendNotificationToAllAdmins(header, message, url=None):
    sendNotification(header,message,url,allTelegramAdminBots)
