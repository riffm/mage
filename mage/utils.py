# -*- coding: utf-8 -*-

import sys
from os import path


class cached_property(object):
    '''Turns decorated method into caching property (method is called once on
    first access to property).'''

    def __init__(self, method, name=None):
        self.method = method
        self.name = name or method.__name__
        self.__doc__ = method.__doc__

    def __get__(self, inst, cls):
        if inst is None:
            return self
        result = self.method(inst)
        setattr(inst, self.name, result)
        return result
