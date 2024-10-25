# -*- coding: utf-8 -*-
"""
Created on Mon Feb 22 12:10:07 2023

@author: Nádia Carvalho
"""

class NoMeterError(Exception):
    def __init__(self, arg):
        self.args = arg

    def __str__(self):
        return repr(self.value) # type: ignore

#parsing failed
class ParseError(Exception):
    def __init__(self, arg):
        self.args = arg

    def __str__(self):
        return repr(self.value) # type: ignore
