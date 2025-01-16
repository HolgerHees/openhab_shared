from shared.semantic.config.colors import ColorConfig
from shared.semantic.config.colors_de import ColorConfigTranslations

from shared.semantic.config.numbers import NumberConfig
from shared.semantic.config.numbers_de import NumberConfigTranslations

SemanticConfig = {
    "i18n": {
        "nothing_found": "Ich habe '{term}' nicht verstanden",
        "no_equipment_found_in_phrase": "Ich habe das Gerät in '{term}' nicht erkannt",
        "no_cmd_found_in_phrase": "Ich habe die Aktion in '{term}' nicht erkannt",
        "no_supported_cmd_in_phrase": "Die Aktion wird für das Gerät in '{term}' nicht unterstützt",
        "more_results": "und {count} weitere Ergebnisse.",
        "message_join_separator": " und ",
        "ok_message": "ok"
    },
    "answers": {
        "Temperature": { "answer": "Die Temperatur im {room} beträgt {state}", "unit": "°C" },
        "Humidity": { "answer": "Die Luftfeuchtigkeit im {room} beträgt {state}", "unit": "%" },
        "Default": { "answer": "{equipment} im {room} ist {state}" }
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
        "phrase_separator": " und ",
        "phrase_part_matcher": "(.*[^0-9a-zA-ZäÄöÖüÜ]+|^){}(.*|$)",
        "phrase_full_matcher": "(.*[^0-9a-zA-ZäÄöÖüÜ]+|^){}([^0-9a-zA-ZäÄöÖüÜ]+.*|$)",
        "phrase_sub": ["vorne","hinten","links","rechts","oben","unten"],
        "phrase_equipment": "eOther_Scenes",
    },
    "commands": {
        "READ": [
            { "value": "READ", "search": ["wie","wieviel","was","ist","sind"],
                "synonyms": {
                    "warm": "temperatur",
                    "kalt": "temperatur",
                    "feucht": "feuchtigkeit",
                    "trocken": "feuchtigkeit",
                    "luftfeuchtigkeit": "feuchtigkeit",
                }
            }
        ],
        "SWITCH": [
            { "value": "OFF", "search": ["aus","ausschalten","beenden","beende","deaktiviere","stoppe","stoppen"], "types": ["Switch","Dimmer","Color"], "tags": ["Power","Light"] },
            { "value": "ON", "search": ["on", "an","ein","einschalten","starten","aktiviere","aktivieren"], "types": ["Switch","Dimmer","Color"], "tags": ["Power","Light"] }
        ],
        "ROLLERSHUTTER": [
            { "value": "DOWN", "search": ["runter","schliessen"], "types": ["Rollershutter"], "tags": ["Control"] },
            { "value": "UP", "search": ["hoch","rauf","öffnen"], "types": ["Rollershutter"], "tags": ["Control"] }
        ],
        "PERCENT": [
            { "value": "REGEX", "search": ["([0-9a-zA-ZäÄöÖüÜ]+)[\\s]*(prozent|%)"], "types": ["Dimmer","Color"], "tags": ["Light"] }, # default, if search matches
            { "value": "REGEX", "search": ["([0-9a-zA-ZäÄöÖüÜ]+)[\\s]*(prozent|%)"], "types": ["Dimmer"], "tags": ["ColorTemperature"] }
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
            "warmweiss": "100",
            "weiss": "75",
            "tageslicht": "50",
            "kaltweiss": "0",
        },
        "COLOR": {}, # will be initialized later
        "PERCENT": {}, # will be initialized later
    }
} 
    
SemanticConfig["mappings"]["COLOR"] = {}
for color_name in ColorConfigTranslations:
    color_key = ColorConfigTranslations[color_name]
    SemanticConfig["mappings"]["COLOR"][color_name] = ColorConfig[color_key]

SemanticConfig["mappings"]["PERCENT"] = {}
for number_name in NumberConfigTranslations:
    number_key = NumberConfigTranslations[number_name]
    SemanticConfig["mappings"]["PERCENT"][number_name] = NumberConfig[number_key]

SemanticConfig["commands"]["COLOR"][0]["search"][0] = SemanticConfig["commands"]["COLOR"][0]["search"][0].format("|".join(SemanticConfig["mappings"]["COLOR"].keys()))
SemanticConfig["commands"]["COLOR_TEMPERATURE"][0]["search"][0] = SemanticConfig["commands"]["COLOR_TEMPERATURE"][0]["search"][0].format("|".join(SemanticConfig["mappings"]["COLOR_TEMPERATURE"].keys()))
