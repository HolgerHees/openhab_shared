import sys
from core import osgi

actions = osgi.find_services("org.openhab.core.model.script.engine.action.ActionService", None)

_MODULE = sys.modules[__name__]

for action in actions:
    action_class = action.actionClass
    name = str(action_class.simpleName)
    setattr(_MODULE, name, action_class)

from org.openhab.core.model.script.actions import Exec
from org.openhab.core.model.script.actions import HTTP
from org.openhab.core.model.script.actions import Ping
from org.openhab.core.model.script.actions import ScriptExecution
from org.openhab.core.model.script.actions import Log

STATIC_IMPORTS = [Exec, HTTP, Log, Ping, ScriptExecution]

for action in STATIC_IMPORTS:
    name = str(action.simpleName)
    setattr(_MODULE, name, action)
