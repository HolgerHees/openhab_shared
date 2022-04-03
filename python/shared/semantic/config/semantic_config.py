# -*- coding: utf-8 -*-
from colors import ColorConfig

from numbers import NumberConfig

SemanticConfig = {
    "i18n": {
        "nothing_found": u"I didn't understand '{term}'",
        "no_equipment_found_in_phrase": u"I did not found the equipment in '{term}'",
        "no_cmd_found_in_phrase": u"I didn't recognize the action in '{term}'",
        "no_supported_cmd_in_phrase": u"The action is not supported for the equipment in '{term}'",
        "more_results": u"and {count} other results.",
        "message_join_separator": u" and ",
        "ok_message": "ok"
    },
    "answers": {
        "Temperature": u"The temperature in the {room} is {state} °C",
        "Humidity": u"The humidity in the {room} is {state} %",
        #"Light": u"The light in the {room} is {state}",
        "Default": u"{equipment} in the {room} is {state}"
    },
    "states": {
        "ON": "on",
        "OFF": "off",
        "UP": "up",
        "DOWN": "down",
        "OPEN": "open",
        "CLOSED": "closed"
    },
    "main": {
        "replacements": [ [ u"ß", u"ss" ] ], # character cleanups
        "phrase_separator": " abd ",
        "phrase_part_matcher": u"(.*[^0-9a-zA-ZäÄöÖüÜ]+|^){}(.*|$)",
        "phrase_full_matcher": u"(.*[^0-9a-zA-ZäÄöÖüÜ]+|^){}([^0-9a-zA-ZäÄöÖüÜ]+.*|$)",
        "phrase_sub": ["front","back","left","right","top","bottom"],
        "phrase_equipment": "eOther_Scenes",
    },
    "commands": {
        "SWITCH": [
            { "value": "OFF", "search": ["off", "switch off", "terminate", "terminated", "disabled", "stop", "stoped" ], "types": ["Switch","Dimmer","Color"], "tags": ["Power","Light"] },
            { "value": "ON", "search": ["on", "switch on", "start", "activate", "activated"], "types": ["Switch","Dimmer","Color"], "tags": ["Power","Light"] }
        ],
        "ROLLERSHUTTER": [
            { "value": "DOWN", "search": ["down","close"], "types": ["Rollershutter"], "tags": ["Control"] },
            { "value": "UP", "search": ["up","open"], "types": ["Rollershutter"], "tags": ["Control"] }
        ],
        "PERCENT": [
            { "value": "REGEX", "search": [u"([0-9a-zA-ZäÄöÖüÜ]+)[\\s]*(percent|%)"], "types": ["Dimmer","Color"], "tags": ["Light"] }, # default, if search matches
            { "value": "REGEX", "search": [u"([0-9a-zA-ZäÄöÖüÜ]+)[\\s]*(percent|%)"], "types": ["Dimmer"], "tags": ["ColorTemperature"] }
        ],
        "COLOR": [
            { "value": "REGEX", "search": [u"({})"], "types": ["Color"], "tags": ["Light"] }
        ],
        "COLOR_TEMPERATURE": [
            { "value": "REGEX", "search": [u"({})"], "types": ["Dimmer"], "tags": ["ColorTemperature"] }
        ],
        "READ": [ 
            { "value": "READ", "search": ["how","how much","what","is","are"],
                "synonyms": {
                    "warm": "temperature",
                    "cold": "temperature",
                    "wet": "humidity",
                    "dry": "humidity",
                    "humidity": "humidity",
                }
            } 
        ]
    },
    "mappings": {      
        "COLOR_TEMPERATURE": {
            u"warm white": "100",
            u"white": "75",
            u"daylight": "50",
            u"cold white": "0",
        },
        "COLOR": {}, # will be initialized later
        "PERCENT": {}, # will be initialized later
    }
} 
    
SemanticConfig["mappings"]["COLOR"] = {}
for color_key in ColorConfig:
    SemanticConfig["mappings"]["COLOR"][color_key] = ColorConfig[color_key]

SemanticConfig["mappings"]["PERCENT"] = {}
for number_key in NumberConfig:
    SemanticConfig["mappings"]["PERCENT"][number_key] = NumberConfig[number_key]

SemanticConfig["commands"]["COLOR"][0]["search"][0] = SemanticConfig["commands"]["COLOR"][0]["search"][0].format("|".join(SemanticConfig["mappings"]["COLOR"].keys()))
SemanticConfig["commands"]["COLOR_TEMPERATURE"][0]["search"][0] = SemanticConfig["commands"]["COLOR_TEMPERATURE"][0]["search"][0].format("|".join(SemanticConfig["mappings"]["COLOR_TEMPERATURE"].keys()))
