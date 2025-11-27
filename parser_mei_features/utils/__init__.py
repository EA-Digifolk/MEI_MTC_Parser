# -*- coding: utf-8 -*-
"""
Created on Mon Feb 13 15:05:28 2023

@author: Nádia Carvalho
"""
from .error_classes import NoMeterError, ParseError

signs = {2: '++', 1: '+', 0: '=', -1: '-', -2: '--'}


def isDigit(x):
    """
    Check if x is a digit
    """
    try:
        float(x)
        return True
    except ValueError:
        return False


def sign_thresh(x, thresh=0):
    """
    Return the sign of x
    """
    if thresh != 0 and x <= -thresh:
        return -2
    elif x < 0:
        return -1
    elif thresh != 0 and x >= thresh:
        return 2
    elif x > 0:
        return 1
    else:
        return 0

def get_one_degree_change(x1, x2, const_add=0.0):
    res = None
    x1 += const_add
    x2 += const_add
    if x1 == x2: return 0.0
    if (x1+x2) != 0 and x1 >= 0 and x2 >= 0:
        res = float(abs(x1-x2)) / float (x1 + x2)
    return res

def has_meter(stream):
    """
    Get the time signature from a stream
    """
    time_signature = stream.recurse().getElementsByClass('TimeSignature')
    if not time_signature:
        return False
    mixedmetercomments = [c.comment for c in stream.getElementsByClass(
        'GlobalComment') if c.comment.startswith('Mixed meters:')]
    if len(mixedmetercomments) > 0:
        return False
    return True
