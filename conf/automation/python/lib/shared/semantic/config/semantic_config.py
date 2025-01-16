from shared.semantic.config.colors import ColorConfig
from shared.semantic.config.numbers import NumberConfig

SemanticConfig = {
    "i18n": {
        "nothing_found": "I didn't understand '{term}'",
        "no_equipment_found_in_phrase": "I did not found the equipment in '{term}'",
        "no_cmd_found_in_phrase": "I didn't recognize the action in '{term}'",
        "no_supported_cmd_in_phrase": "The action is not supported for the equipment in '{term}'",
        "more_results": "and {count} other results.",
        "message_join_separator": " and ",
        "ok_message": "ok"
    },
    "answers": {
        "Temperature": { "answer": "The temperature in the {room} is {state}", "unit": "°C" },
        "Humidity": { "answer": "The humidity in the {room} is {state}", "unit": "%" },
        #"Light": { "answer": "The light in the {room} is {state}"  },
        "Default": { "answer": "{equipment} in the {room} is {state}" }
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
        "replacements": [ [ "ß", "ss" ] ], # character cleanups
        "phrase_separator": " and ",
        "phrase_part_matcher": "(.*[^0-9a-zA-ZäÄöÖüÜ]+|^){}(.*|$)",
        "phrase_full_matcher": "(.*[^0-9a-zA-ZäÄöÖüÜ]+|^){}([^0-9a-zA-ZäÄöÖüÜ]+.*|$)",
        "phrase_sub": ["front","back","left","right","top","bottom"],
        "phrase_equipment": "eOther_Scenes",
    },
    "commands": {
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
        ],
        "SWITCH": [
            { "value": "OFF", "search": ["off", "switch off", "terminate", "terminated", "disabled", "stop", "stoped" ], "types": ["Switch","Dimmer","Color"], "tags": ["Power","Light"] },
            { "value": "ON", "search": ["on", "switch on", "start", "activate", "activated"], "types": ["Switch","Dimmer","Color"], "tags": ["Power","Light"] }
        ],
        "ROLLERSHUTTER": [
            { "value": "DOWN", "search": ["down","close"], "types": ["Rollershutter"], "tags": ["Control"] },
            { "value": "UP", "search": ["up","open"], "types": ["Rollershutter"], "tags": ["Control"] }
        ],
        "PERCENT": [
            { "value": "REGEX", "search": ["([0-9a-zA-ZäÄöÖüÜ]+)[\\s]*(percent|%)"], "types": ["Dimmer","Color"], "tags": ["Light"] }, # default, if search matches
            { "value": "REGEX", "search": ["([0-9a-zA-ZäÄöÖüÜ]+)[\\s]*(percent|%)"], "types": ["Dimmer"], "tags": ["ColorTemperature"] }
        ],
        "COLOR": [
            { "value": "REGEX", "search": ["({})"], "types": ["Color"], "tags": ["Light"] }
        ],
        "COLOR_TEMPERATURE": [
            { "value": "REGEX", "search": ["({})"], "types": ["Dimmer"], "tags": ["ColorTemperature"] }
        ]
    },
    "mappings": {      
        "COLOR_TEMPERATURE": {
            "warm white": "100",
            "white": "75",
            "daylight": "50",
            "cold white": "0",
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
