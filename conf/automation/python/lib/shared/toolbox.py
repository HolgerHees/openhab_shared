from openhab import Registry

from datetime import datetime, timedelta


class NotInitialisedException(Exception):
    pass

class ToolboxHelper:
    @staticmethod
    def getFilteredGroupMember(group_or_group_name, state):
        group_member = Registry.resolveItem(group_or_group_name).getAllMembers()
        if isinstance(state, list):
            return list(filter(lambda child: child.getState() in state, group_member))
        else:
            return list(filter(lambda child: child.getState() == state, group_member))

    @staticmethod
    def getPersistedEntry(item_or_item_name, at_time):
        entry = Registry.resolveItem(item_or_item_name).getPersistence("jdbc").persistedState(at_time)
        if entry is None:
            raise NotInitialisedException("Item history for {} before {} not found".format(ToolboxHelper._resolveItemName(item_or_item_name),at_time))
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
    def getAllStatesSince(item_or_item_name, at_time):
        return Registry.resolveItem(item_or_item_name).getPersistence("jdbc").getAllStatesSince(at_time)


    #@staticmethod # deprecated since openhab 5
    #def getLastChange(item_or_item_name):
    #    persistence = Registry.resolveItem(item_or_item_name).getPersistence("jdbc")
    #    last_change = persistence.lastUpdate()
    #    if last_change is None:
    #        previous_state = persistence.previousState() # https://community.openhab.org/t/item-persistence-lastupdate-not-always-working/158534
    #        if previous_state is None:
    #            raise NotInitialisedException("Item lastChange for {} not found".format(ToolboxHelper._resolveItemName(item_or_item_name)))
    #        last_change = previous_state.getTimestamp()
    #    return last_change

    #@staticmethod # deprecated since openhab 5
    #def getLastUpdate(item_or_item_name):
    #    last_update = Registry.resolveItem(item_or_item_name).getPersistence().lastUpdate()
    #    if last_update is None:
    #        return datetime.now().astimezone()
    #        #raise NotInitialisedException("Item lastUpdate for '" + item_or_item_name + "' not found")
    #    return last_update

    @staticmethod
    def getMaximumSince(item_or_item_name, at_time):
        entry = Registry.resolveItem(item_or_item_name).getPersistence("jdbc").maximumSince(at_time)
        if entry is None:
            raise NotInitialisedException("Item max state for {} before {} not found".format(ToolboxHelper._resolveItemName(item_or_item_name),at_time))
        return entry.getState()

    @staticmethod
    def getMinimumSince(item_or_item_name, at_time):
        entry = Registry.resolveItem(item_or_item_name).getPersistence("jdbc").minimumSince(at_time)
        if entry is None:
            raise NotInitialisedException("Item min state for {} before {} not found".format(ToolboxHelper._resolveItemName(item_or_item_name),at_time))
        return entry.getState()

    @staticmethod
    def getStableMinMaxState(item_or_item_name, time_slot, end_time = None):
        return Registry.resolveItem(item_or_item_name).getPersistence("jdbc").getStableMinMaxState(time_slot, end_time)

    @staticmethod
    def getStableState(item_or_item_name, time_slot, end_time = None):
        return Registry.resolveItem(item_or_item_name).getPersistence("jdbc").getStableState(time_slot, end_time)

    @staticmethod
    def isMember(item_or_item_name, group_name):
        group_names = Registry.getItem(item_or_item_name).getGroupNames()
        return group_name in group_names

    @staticmethod
    def _resolveItemName(item_or_item_name):
        if isinstance(item_or_item_name, str):
            return item_or_item_name
        return item_or_item_name.getName()
