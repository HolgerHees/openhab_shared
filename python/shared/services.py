# -*- coding: utf-8 -*-

import sys
from org.osgi.framework import FrameworkUtil

from shared.jsr223 import scope

scriptExtension   = scope.get("scriptExtension")

_BUNDLE = FrameworkUtil.getBundle(type(scriptExtension))
BUNDLE_CONTEXT = _BUNDLE.getBundleContext() if _BUNDLE else None
REGISTERED_SERVICES = {}

def get_service(class_or_name):
    if BUNDLE_CONTEXT:
        classname = class_or_name.getName() if isinstance(class_or_name, type) else class_or_name
        ref = BUNDLE_CONTEXT.getServiceReference(classname)
        return BUNDLE_CONTEXT.getService(ref) if ref else None
    else:
        return None

def find_service(class_name, service_filter):
    if BUNDLE_CONTEXT:
        references = BUNDLE_CONTEXT.getServiceReferences(class_name, service_filter)
        if references:
            return [BUNDLE_CONTEXT.getService(reference) for reference in references]
        else:
            return []
    else:
        return None
