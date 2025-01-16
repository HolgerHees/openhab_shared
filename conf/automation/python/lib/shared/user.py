import java

from openhab import logger, Registry
from configuration import userConfigs


Java_OnOffType = java.type("org.openhab.core.library.types.OnOffType")

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
            stateItem = Registry.getItem(userConfigs[userName]["state_item"])
            if stateItem.getState() != Java_OnOffType.ON:
                continue
            usernames[userName] = stateItem
        return usernames

    @staticmethod
    def getStateItem(userName):
        return Registry.getItem(userConfigs[userName]["state_item"])

    @staticmethod
    def getName(userName):
        return userConfigs[userName]["name"]
