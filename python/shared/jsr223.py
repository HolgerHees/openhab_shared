# -*- coding: utf-8 -*-

import sys
from org.osgi.framework import FrameworkUtil

def get_scope():
    depth = 1
    while True:
        try:
            frame = sys._getframe(depth)
            name = str(type(frame.f_globals))
            if name == "<type 'scope'>":
                return frame.f_globals
            depth += 1
        except ValueError:
            raise EnvironmentError("No JSR223 scope is available")

scope = get_scope()
