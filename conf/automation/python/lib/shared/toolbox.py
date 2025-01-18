from openhab import Registry
from openhab.services import get_service

from datetime import datetime, timedelta


class NotInitialisedException(Exception):
    pass

class ToolboxHelper:
    @staticmethod
    def getGroupMemberTrigger(clazz, group_or_group_name, state=None, trigger_name=None):
        triggers = []
        group_member = Registry.resolveItem(group_or_group_name).getAllMembers()
        for item in group_member:
            triggers.append(clazz(item.getName(), state=state, trigger_name=trigger_name))
        return triggers

    @staticmethod
    def getFilteredGroupMember(group_or_group_name, state):
        group_member = Registry.resolveItem(group_or_group_name).getAllMembers()
        if isinstance(state, list):
            return list(filter(lambda child: child.getState() in state, group_member))
        else:
            return list(filter(lambda child: child.getState() == state, group_member))

    @staticmethod
    def getPersistedEntry(item_or_item_name, at_time):
        entry = Registry.resolveItem(item_or_item_name).getPersistance("jdbc").persistedState(at_time)
        if entry is None:
            raise NotInitialisedException("Item history for {} before {} not found".format(TToolboxHelper._resolveItemName(item_or_item_name),at_time))
        return entry

    @staticmethod
    def getPersistedState(item_or_item_name, at_time):
        return ToolboxHelper.getPersistedEntry(item_or_item_name, at_time).getState()

    @staticmethod
    def getPreviousPersistedState(item_or_item_name):
        entry = ToolboxHelper.getPersistedEntry(item_or_item_name, datetime.now().astimezone())
        previousEntry = ToolboxHelper.getPersistedEntry(item_or_item_name, entry.getTimestamp() - timedelta(microseconds=1))
        return previousEntry.getState()

    @staticmethod
    def getLastChange(item_or_item_name):
        lastChange = Registry.resolveItem(item_or_item_name).getPersistance("jdbc").lastUpdate()
        if lastChange is None:
            raise NotInitialisedException("Item lastChange for {} not found".format(ToolboxHelper._resolveItemName(item_or_item_name)))
        return lastChange

    @staticmethod
    def getLastUpdate(item_or_item_name):
        last_update = Registry.resolveItem(item_or_item_name).getPersistance().lastUpdate()
        if last_update is None:
            return datetime.now().astimezone()
            #raise NotInitialisedException("Item lastUpdate for '" + item_or_item_name + "' not found")
        return last_update

    @staticmethod
    def getMaximumSince(item_or_item_name, at_time):
        entry = Registry.resolveItem(item_or_item_name).getPersistance("jdbc").maximumSince(at_time)
        if entry is None:
            raise NotInitialisedException("Item max state for {} before {} not found".format(ToolboxHelper._resolveItemName(item_or_item_name),at_time))
        return entry.getState()

    @staticmethod
    def getMinimumSince(item_or_item_name, at_time):
        entry = Registry.resolveItem(item_or_item_name).getPersistance("jdbc").minimumSince(at_time)
        if entry is None:
            raise NotInitialisedException("Item min state for {} before {} not found".format(ToolboxHelper._resolveItemName(item_or_item_name),at_time))
        return entry.getState()

    @staticmethod
    def getStableMinMaxState(item_or_item_name, time_slot, end_time = None):
        return Registry.resolveItem(item_or_item_name).getPersistance("jdbc").getStableMinMaxState(time_slot, end_time)

    @staticmethod
    def getStableState(item_or_item_name, time_slot, end_time = None):
        return Registry.resolveItem(item_or_item_name).getPersistance("jdbc").getStableState(time_slot, end_time)

    @staticmethod
    def isMember(item_or_item_name, group_name):
        group_names = Registry.getItem(item_or_item_name).getGroupNames()
        return group_name in group_names

    @staticmethod
    def _resolveItemName(item_or_item_name):
        if isinstance(item_or_item_name, str):
            return item_or_item_name
        return item_or_item_name.getName()
