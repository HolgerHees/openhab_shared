from openhab import logger
from configuration import userConfigs

import scope

import time


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
                logger.error("Unknown notification type {}".format(notification_type))
                success = None
        else:
            if notification_type == "telegram":
                success = action.sendTelegramPhoto(url,"*" + header + "*: " + message)
            elif notification_type == "pushover":
                #sendMessage(String message, @Nullable String title, @Nullable String sound, @Nullable String url, @Nullable String urlTitle, @Nullable String attachment, @Nullable String contentType, @Nullable Integer priority, @Nullable String device, @Nullable Duration ttl)
                success = action.sendMessage(message, header, mapped_sound, None, None, url, None, mapped_priority, notification_config[2], None )
            else:
                logger.error("Unknown notification type {}".format(notification_type))
                success = None

        if not success and success is not None and retry < 5:
            waiting_time = retry * 5
            logger.info("Failed to send message '{}: {}'. Retry in {} seconds.".format(header, message, waiting_time))
            time.sleep(waiting_time)
            success = NotificationHelper._sendNotification(notification_config, notification_type, mapped_sound, mapped_priority, action, header, message, url, retry + 1)

        return bool(success)

    @staticmethod
    def sendNotification(priority, header, message, url=None, recipients = None):
        chars = {
            "_": "\\_"
        }
        for k,v in chars.items():
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

            action = scope.actions.get(notification_type, notification_thing)

            if action is None:
                logger.warn("No Action found, Type: '{}', Thing: '{}'".format(notification_type, notification_thing))
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
                logger.error("Failed to send message '{}: {}' from {}:{}".format(header, message, caller.filename, caller.lineno))

    @staticmethod
    def sendNotificationToAllAdmins(priority, header, message, url=None):
        recipients = []
        for userName in userConfigs:
            if not userConfigs[userName]["notification_config"] or not userConfigs[userName]["is_admin"]:
                continue
            recipients.append(userName)
        NotificationHelper.sendNotification(priority, header, message, url, recipients)
