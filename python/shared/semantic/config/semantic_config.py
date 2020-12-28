# -*- coding: utf-8 -*-
from colors import ColorConfig
from colors_de import ColorConfigTranslations

from numbers import NumberConfig
from numbers_de import NumberConfigTranslations

SemanticConfig = {
    "i18n": {
        "nothing_found": u"Ich habe '{term}' nicht verstanden",
        "no_equipment_found_in_phrase": u"Ich habe das Gerät in '{term}' nicht erkannt",
        "no_cmd_found_in_phrase": u"Ich habe die Aktion in '{term}' nicht erkannt",
        "no_supported_cmd_in_phrase": u"Die Aktion wird für das Gerät in '{term}' nicht unterstützt",
        "more_results": u"und {count} weitere Ergebnisse.",
        "message_join_separator": u" und ",
        "ok_message": "ok"
    },
    "answers": {
        "Temperature": u"Die Temperatur im {room} beträgt {state} °C",
        "Humidity": u"Die Luftfeuchtigkeit im {room} beträgt {state} %",
        #"Light": u"Das Licht im {room} ist {state}",
        "Default": u"{equipment} im {room} ist {state}"
    },
    "states": {
        "ON": "an",
        "OFF": "aus",
        "UP": "oben",
        "DOWN": "unten",
        "OPEN": "offen",
        "CLOSED": "geschlossen"
    },
    "main": {
        "replacements": [ [ u"ß", u"ss" ] ], # character cleanups
        "phrase_separator": " und ",
        "phrase_part_matcher": u"(.*[^0-9a-zA-ZäÄöÖüÜ]+|^){}(.*|$)",
        "phrase_full_matcher": u"(.*[^0-9a-zA-ZäÄöÖüÜ]+|^){}([^0-9a-zA-ZäÄöÖüÜ]+.*|$)",
        "phrase_sub": ["vorne","hinten","links","rechts","oben","unten"],
        "phrase_equipment": "eOther_Scenes",
    },
    "commands": {
        "SWITCH": [
            { "value": "OFF", "search": ["aus","ausschalten","beenden","beende","deaktiviere","stoppe","stoppen"], "types": ["Switch","Dimmer","Color"], "tags": ["Power","Light"] },
            { "value": "ON", "search": ["an","ein","einschalten","starten","aktiviere","aktivieren"], "types": ["Switch","Dimmer","Color"], "tags": ["Power","Light"] }
        ],
        "ROLLERSHUTTER": [
            { "value": "DOWN", "search": ["runter","schliessen"], "types": ["Rollershutter"], "tags": ["Control"] },
            { "value": "UP", "search": ["hoch","rauf","öffnen"], "types": ["Rollershutter"], "tags": ["Control"] }
        ],
        "PERCENT": [
            { "value": "REGEX", "search": [u"([0-9a-zA-ZäÄöÖüÜ]+)[\\s]*(prozent|%)"], "types": ["Dimmer","Color"], "tags": ["Light"] }, # default, if search matches
            { "value": "REGEX", "search": [u"([0-9a-zA-ZäÄöÖüÜ]+)[\\s]*(prozent|%)"], "types": ["Dimmer"], "tags": ["ColorTemperature"] }
        ],
        "COLOR": [
            { "value": "REGEX", "search": [u"({})"], "types": ["Color"], "tags": ["Light"] }
        ],
        "COLOR_TEMPERATURE": [
            { "value": "REGEX", "search": [u"({})"], "types": ["Dimmer"], "tags": ["ColorTemperature"] }
        ],
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
        ]
    },
    "mappings": {      
        "COLOR_TEMPERATURE": {
            u"warmweiss": "100",
            u"weiss": "75",
            u"tageslicht": "50",
            u"kaltweiss": "0",
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
