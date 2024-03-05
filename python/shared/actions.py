# -*- coding: utf-8 -*-

import sys
from shared.services import find_service

actions = find_service("org.openhab.core.model.script.engine.action.ActionService", None)

_MODULE = sys.modules[__name__]

for action in actions:
    action_class = action.actionClass
    name = str(action_class.simpleName)
    setattr(_MODULE, name, action_class)

from org.openhab.core.model.script.actions import Audio
from org.openhab.core.model.script.actions import Exec
from org.openhab.core.model.script.actions import HTTP
from org.openhab.core.model.script.actions import Log
from org.openhab.core.model.script.actions import Ping
from org.openhab.core.model.script.actions import ScriptExecution
from org.openhab.core.model.script.actions import Semantics
from org.openhab.core.model.script.actions import Transformation
from org.openhab.core.model.script.actions import Voice

STATIC_IMPORTS = [Audio, Exec, HTTP, Log, Ping, ScriptExecution, Semantics, Transformation, Voice]

for action in STATIC_IMPORTS:
    name = str(action.simpleName)
    setattr(_MODULE, name, action)
