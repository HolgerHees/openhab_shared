from shared.jsr223 import scope

import uuid
import re

scriptExtension   = scope.get("scriptExtension")
scriptExtension.importPreset("RuleSupport")

TriggerBuilder = scope.get("TriggerBuilder")
Configuration = scope.get("Configuration")
Trigger = scope.get("Trigger")

from java.nio.file import StandardWatchEventKinds
ENTRY_CREATE = StandardWatchEventKinds.ENTRY_CREATE  # type: WatchEvent.Kind
ENTRY_DELETE = StandardWatchEventKinds.ENTRY_DELETE  # type: WatchEvent.Kind
ENTRY_MODIFY = StandardWatchEventKinds.ENTRY_MODIFY  # type: WatchEvent.Kind

def validate_uid(uid):
    if uid is None:
        uid = uuid.uuid1().hex
    else:
        uid = re.sub(r"[^A-Za-z0-9_-]", "_", uid)
        uid = "{}_{}".format(uid, uuid.uuid1().hex)
    if not re.match("^[A-Za-z0-9]", uid):# in case the first character is still invalid
        uid = "{}_{}".format("jython", uid)
    uid = re.sub(r"__+", "_", uid)
    return uid

class CronTrigger(Trigger):
    def __init__(self, cron_expression, trigger_name=None):
        trigger_name = validate_uid(trigger_name)
        configuration = {'cronExpression': cron_expression}
        self.trigger = TriggerBuilder.create().withId(trigger_name).withTypeUID("timer.GenericCronTrigger").withConfiguration(Configuration(configuration)).build()


class ItemStateUpdateTrigger(Trigger):
    def __init__(self, item_name, state=None, trigger_name=None):
        trigger_name = validate_uid(trigger_name)
        configuration = {"itemName": item_name}
        if state is not None:
            configuration["state"] = state
        self.trigger = TriggerBuilder.create().withId(trigger_name).withTypeUID("core.ItemStateUpdateTrigger").withConfiguration(Configuration(configuration)).build()


class ItemStateChangeTrigger(Trigger):
    def __init__(self, item_name, previous_state=None, state=None, trigger_name=None):
        trigger_name = validate_uid(trigger_name)
        configuration = {"itemName": item_name}
        if state is not None:
            configuration["state"] = state
        if previous_state is not None:
            configuration["previousState"] = previous_state
        self.trigger = TriggerBuilder.create().withId(trigger_name).withTypeUID("core.ItemStateChangeTrigger").withConfiguration(Configuration(configuration)).build()


class ItemCommandTrigger(Trigger):
    def __init__(self, item_name, command=None, trigger_name=None):
        trigger_name = validate_uid(trigger_name)
        configuration = {"itemName": item_name}
        if command is not None:
            configuration["command"] = command
        self.trigger = TriggerBuilder.create().withId(trigger_name).withTypeUID("core.ItemCommandTrigger").withConfiguration(Configuration(configuration)).build()


class ThingStatusUpdateTrigger(Trigger):
    def __init__(self, thing_uid, status=None, trigger_name=None):
        trigger_name = validate_uid(trigger_name)
        configuration = {"thingUID": thing_uid}
        if status is not None:
            configuration["status"] = status
        self.trigger = TriggerBuilder.create().withId(trigger_name).withTypeUID("core.ThingStatusUpdateTrigger").withConfiguration(Configuration(configuration)).build()


class ThingStatusChangeTrigger(Trigger):
    def __init__(self, thing_uid, previous_status=None, status=None, trigger_name=None):
        trigger_name = validate_uid(trigger_name)
        configuration = {"thingUID": thing_uid}
        if previous_status is not None:
            configuration["previousStatus"] = previous_status
        if status is not None:
            configuration["status"] = status
        self.trigger = TriggerBuilder.create().withId(trigger_name).withTypeUID("core.ThingStatusChangeTrigger").withConfiguration(Configuration(configuration)).build()


class ChannelEventTrigger(Trigger):
    def __init__(self, channel_uid, event=None, trigger_name=None):
        trigger_name = validate_uid(trigger_name)
        configuration = {"channelUID": channel_uid}
        if event is not None:
            configuration["event"] = event
        self.trigger = TriggerBuilder.create().withId(trigger_name).withTypeUID("core.ChannelEventTrigger").withConfiguration(Configuration(configuration)).build()


class GenericEventTrigger(Trigger):
    def __init__(self, event_source, event_types, event_topic="*/*", trigger_name=None):
        trigger_name = validate_uid(trigger_name)
        self.trigger = TriggerBuilder.create().withId(trigger_name).withTypeUID("core.GenericEventTrigger").withConfiguration(Configuration({
            "eventTopic": event_topic,
            "eventSource": event_source,
            "eventTypes": event_types
        })).build()


class ItemEventTrigger(Trigger):
    def __init__(self, event_types, item_name=None, trigger_name=None):
        trigger_name = validate_uid(trigger_name)
        self.trigger = TriggerBuilder.create().withId(trigger_name).withTypeUID("core.GenericEventTrigger").withConfiguration(Configuration({
            "eventTopic": "*/items/*",
            "eventSource": "/items/{}".format(item_name if item_name else ""),
            "eventTypes": event_types
        })).build()


class ThingEventTrigger(Trigger):
    def __init__(self, event_types, thing_uid=None, trigger_name=None):
        trigger_name = validate_uid(trigger_name)
        self.trigger = TriggerBuilder.create().withId(trigger_name).withTypeUID("core.GenericEventTrigger").withConfiguration(Configuration({
            "eventTopic": "*/things/*",
            "eventSource": "/things/{}".format(thing_uid if thing_uid else ""),
            "eventTypes": event_types
        })).build()


class StartupTrigger(Trigger):
    def __init__(self, trigger_name=None):
        trigger_name = validate_uid(trigger_name)
        self.trigger = TriggerBuilder.create().withId(trigger_name).withTypeUID("jsr223.StartupTrigger").withConfiguration(Configuration()).build()


class DirectoryEventTrigger(Trigger):
    def __init__(self, path, event_kinds=[ENTRY_CREATE, ENTRY_DELETE, ENTRY_MODIFY], watch_subdirectories=False, trigger_name=None):
        trigger_name = validate_uid(trigger_name)
        configuration = {
            'path': path,
            'event_kinds': str(event_kinds),
            'watch_subdirectories': watch_subdirectories,
        }
        self.trigger = TriggerBuilder.create().withId(trigger_name).withTypeUID("jsr223.DirectoryEventTrigger").withConfiguration(Configuration(configuration)).build()
