# -*- coding: utf-8 -*-

import traceback
import time
import profile, pstats, io
import threading
import sys

from java.lang import NoSuchFieldException
from java.time import ZonedDateTime, Instant, ZoneId
from java.time.format import DateTimeFormatter
from java.time.temporal import ChronoUnit

from inspect import getframeinfo, stack

from org.slf4j import LoggerFactory

from org.openhab.core.automation import Rule as SmarthomeRule
#from org.openhab.core.automation.module.script.LifecycleScriptExtensionProvider import LifecycleTracker

from org.openhab.core.types import UnDefType
from org.openhab.core.persistence.extensions import PersistenceExtensions
from org.openhab.core.thing import ChannelUID, ThingUID

from org.openhab.core.library.types import OnOffType

from shared.jsr223 import scope
from shared.triggers import ItemStateUpdateTrigger, ItemStateChangeTrigger
from shared.services import get_service

from configuration import LOG_PREFIX, userConfigs

log = LoggerFactory.getLogger(LOG_PREFIX)

LOCATION_PROVIDER = get_service("org.openhab.core.i18n.LocaleProvider")
language          = LOCATION_PROVIDER.getLocale().getLanguage()

actions           = scope.get("actions")

itemRegistry      = scope.get("itemRegistry")
items             = scope.get("items")
things            = scope.get("things")

events            = scope.get("events")
scriptExtension   = scope.get("scriptExtension")

scriptExtension.importPreset("RuleSupport")
automationManager = scope.get("automationManager")
lifecycleTracker = scope.get("lifecycleTracker")

scriptExtension.importPreset("RuleSimple")
SimpleRule = scope.get("SimpleRule")

def scriptUnloaded():
    log.info("unload")

class rule(object):
    def __init__(self, name = None, profile=None):
        self.name = name
        self.profile = profile

    def __call__(self, clazz):
        proxy = self

        filePackage = proxy.getFilePackage(proxy.name) if proxy.name is not None else None
        classPackage = proxy.getClassPackage(clazz.__name__)

        def init(self, *args, **kwargs):
            SimpleRule.__init__(self)
            #proxy.set_uid_prefix(self,classPackage,filePackage)
            try:
                clazz.__init__(self, *args, **kwargs)
            except Exception as e:
                self.log.error("Rule init failed:\n" + traceback.format_exc())
                raise e

            self.triggerItems = {}
            _triggers = []
            for trigger in self.triggers:
                self.triggerItems[ trigger.trigger.getConfiguration().get("itemName") ] = True
                _triggers.append(trigger.trigger)
            self.triggers = _triggers

        subclass = type(clazz.__name__, (clazz, SimpleRule), dict(__init__=init))
        subclass.execute = proxy.executeWrapper(clazz.execute)

        #subclass.log = logging.getLogger( LOG_PREFIX + "." + filePackage + "." + classPackage )
        if filePackage is not None:
            subclass.log = LoggerFactory.getLogger( LOG_PREFIX + "." + filePackage + "." + classPackage )
        else:
            subclass.log = LoggerFactory.getLogger( LOG_PREFIX + "." + classPackage )

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
                self.log.warn("Rule skipped: " + str(e) + " \n" + traceback.format_exc())
            except:
                self.log.error("Rule execution failed:\n" + traceback.format_exc())

        return func_wrapper


class NotInitialisedException(Exception):
    pass

# could also be solved by storing it in a private cache => https://next.openhab.org/docs/configuration/jsr223.html
# because Timer & ScheduledFuture are canceled when a private cache is cleaned on unload or refresh
activeTimer = []
def cleanTimer():
    for timer in list(activeTimer):
        #log.info("cleanup")
        timer.cancel()
lifecycleTracker.addDisposeHook(cleanTimer)

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
            try:
                activeTimer.remove(self)
            except ValueError:
                # can happen when timer is executed and canceled at the same time
                # could be solved with a LOCK, but this solution is more efficient, because it works without a LOCK
                pass
        except:
            self.log.error(u"{}".format(traceback.format_exc()))
            raise

    def start(self):
        if not self.timer.isAlive():
            #log.info("timer started")
            activeTimer.append(self)
            self.timer.start()
        else:
            #log.info("timer already started")
            pass

    def cancel(self):
        if self.timer.isAlive():
            #log.info("timer stopped")
            activeTimer.remove(self)
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


# *** Group trigger **
def isMember(itemOrName, groupName):
    item = getItem(itemOrName)
    group_names = getItem(itemOrName).getGroupNames()
    return groupName in group_names

def _walkGroupMemberRecursive(parent):
    result = []
    items = parent.getAllMembers()
    for item in items:
        if item.getType() == "Group":
            result = result + _walkGroupMemberRecursive(item)
        else:
            result.append(item)
    return result


def getGroupMember(itemOrName):
    return _walkGroupMemberRecursive(_getItem(itemOrName))


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

def getPreviousItemState(itemOrName):
    item = getItem(itemOrName)

    entry = getHistoricItemEntry(item, ZonedDateTime.now())
    entryTime = entry.getTimestamp()

    previousEntry = getHistoricItemEntry(item, entryTime.minusNanos(1))

    #previousEntry = PersistenceExtensions.previousState(item, True, "jdbc")

    return previousEntry.getState()

def getHistoricItemEntry(itemOrName, refDate):
    item = _getItem(itemOrName)
    historicEntry = PersistenceExtensions.persistedState(item, refDate, "jdbc")
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

def getMinItemState(itemOrName, refDate):
    item = _getItem(itemOrName)
    historicState = PersistenceExtensions.minimumSince(item, refDate, "jdbc")
    if historicState is None:
        raise NotInitialisedException(u"Item min state for {} before {} not found".format(item.getName(),refDate))
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
    minTime = currentEndTime.minusMinutes( checkTimeRange )

    minValue = None
    maxValue = None

    value = 0.0
    duration = 0

    # get and cache "real" item to speedup getHistoricItemEntry. Otherwise "getHistoricItemEntry" will lookup the item by its name every time
    item = getItem(itemName)

    entry = getHistoricItemEntry(item, now)

    while True:
        currentStartTime = entry.getTimestamp()

        if currentStartTime.isBefore( minTime ):
            currentStartTime = minTime

        _duration = ChronoUnit.NANOS.between( currentStartTime, currentEndTime )
        _value = entry.getState().doubleValue()

        if minValue == None or minValue > _value:
            minValue = _value

        if maxValue == None or maxValue < _value:
            maxValue = _value

        duration = duration + _duration
        value = value + ( _value * _duration )

        currentEndTime = currentStartTime.minusNanos(1)

        if currentEndTime.isBefore( minTime ):
            break

        entry = getHistoricItemEntry(item, currentEndTime )

    value = ( value / duration )

    return [ value, minValue, maxValue ]

def getStableItemState( now, itemName, checkTimeRange ):

    value, _, _ = getStableMinMaxItemState(now,itemName, checkTimeRange)

    return value

class UserHelper:
    @staticmethod
    def getUserNames():
        return userConfigs.keys()

    @staticmethod
    def getUserByStateItem(stateItem):
        for userName in userConfigs:
            if userConfigs[userName]["state_item"] != stateItem:
                continue
            return userName

    @staticmethod
    def getPresentUser():
        return list(UserHelper.getPresentUserData().keys())

    @staticmethod
    def getPresentUserData():
        usernames = {}
        for userName in userConfigs:
            if not userConfigs[userName]["state_item"]:
                continue
            stateItem = getItem(userConfigs[userName]["state_item"])
            if getItemState(stateItem) != OnOffType.ON:
                continue
            usernames[userName] = stateItem
        return usernames

    @staticmethod
    def getStateItem(userName):
        return getItem(userConfigs[userName]["state_item"])

    @staticmethod
    def getName(userName):
        return userConfigs[userName]["name"]

class NotificationHelper:
    PRIORITY_INFO = 1
    PRIORITY_NOTICE = 2
    PRIORITY_WARN = 3
    PRIORITY_ERROR = 4
    PRIORITY_ALERT = 5

    # *** Notifications ***
    @staticmethod
    def _sendNotification(notification_config, notification_type, mapped_sound, mapped_priority, action, header, message, url=None, retry = 1 ):
        success = False
        if url == None:
            if notification_type == "telegram":
                success = action.sendTelegram("*" + header + "*: " + message)
            elif notification_type == "pushover":
                success = action.sendMessage(message, header, mapped_sound, None, None, None, None, mapped_priority, notification_config[2], None )
            else:
                log.error(u"Unknown notification type {}".format(notification_type))
                success = None
        else:
            if notification_type == "telegram":
                success = action.sendTelegramPhoto(url,"*" + header + "*: " + message)
            elif notification_type == "pushover":
                #sendMessage(String message, @Nullable String title, @Nullable String sound, @Nullable String url, @Nullable String urlTitle, @Nullable String attachment, @Nullable String contentType, @Nullable Integer priority, @Nullable String device, @Nullable Duration ttl)
                success = action.sendMessage(message, header, mapped_sound, None, None, url, None, mapped_priority, notification_config[2], None )
            else:
                log.error(u"Unknown notification type {}".format(notification_type))
                success = None

        if not success and success is not None and retry < 5:
            waiting_time = retry * 5
            log.info(u"Failed to send message '{}: {}'. Retry in {} seconds.".format(header, message, waiting_time))
            time.sleep(waiting_time)
            success = NotificationHelper._sendNotification(notification_config, notification_type, mapped_sound, mapped_priority, action, header, message, url, retry + 1)

        return bool(success)

    @staticmethod
    def sendNotification(priority, header, message, url=None, recipients = None):
        chars = {
            u"_": u"\\_"
        }
        for k,v in chars.iteritems():
            message = message.replace(k,v)

        if recipients is None:
            recipients = []
            for userName in userConfigs:
                if not userConfigs[userName]["notification_config"]:
                    continue
                recipients.append(userName)

        for recipient in recipients:
            notification_config = userConfigs[recipient]["notification_config"]
            notification_type = notification_config[0]
            notification_thing = notification_config[1]

            action = actions.get(notification_type, notification_thing)

            if action is None:
                log.warn(u"No Action found, Type: '{}', Thing: '{}'".format(notification_type, notification_thing))
                continue

            if notification_type == "pushover":
                # mapping to pushover priorities
                if priority == NotificationHelper.PRIORITY_INFO:
                    mapped_priority = 0
                    mapped_sound = "magic"
                elif priority == NotificationHelper.PRIORITY_NOTICE:
                    mapped_priority = 0
                    mapped_sound = "gamelan"
                elif priority == NotificationHelper.PRIORITY_WARN or priority == NotificationHelper.PRIORITY_ERROR:
                    mapped_priority = 1
                    mapped_sound = "intermission"
                else:
                    mapped_priority = 2
                    mapped_sound = "echo"
            else:
                mapped_priority = 0
                mapped_sound = None

            success = NotificationHelper._sendNotification(notification_config, notification_type, mapped_sound, mapped_priority, action, header, message, url)
            if not success:
                caller = getframeinfo(stack()[1][0])
                log.error(u"Failed to send message '{}: {}' from {}:{}".format(header, message, caller.filename, caller.lineno))

    @staticmethod
    def sendNotificationToAllAdmins(priority, header, message, url=None):
        recipients = []
        for userName in userConfigs:
            if not userConfigs[userName]["notification_config"] or not userConfigs[userName]["is_admin"]:
                continue
            recipients.append(userName)
        NotificationHelper.sendNotification(priority, header, message, url, recipients)

def getLanguage():
    return language
