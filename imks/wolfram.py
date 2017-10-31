# -*- coding: utf-8 -*-

try:
    from urllib import request, error
except:
    import urllib2 as request
    error = request

import json
import re

from .units import Value
from .config import *

namespace = None
app_id = ""
timeout = 5


def short_answer(query, verbose=False):
    if namespace:
        engine = namespace.get(internals["engine"], float)
    else:
        engine = float
    url = "http://api.wolframalpha.com/v1/result?appid=%s&i=%s&units=metric" % \
        (app_id, request.quote(query))
    if verbose:
        print(url)
    response = request.urlopen(url, timeout=timeout).read()
    result = response.decode('utf-8').strip()
    result = result.replace(u"×10^", "e")
    result = result.split()
    if len(result) == 0:
        try:
            return engine(result)
        except ValueError:
            return result
    value = engine(result[0])
    unit = " ".join(result[1:])
    return Value(value, unit, original=True)


def wolfram(query, verbose=False):
    if namespace:
        engine = namespace.get(internals["engine"], float)
    else:
        engine = float
    url = "https://api.wolframalpha.com/v2/query?format=plaintext&output=JSON" \
          "&includepodid=Value&includepodid=Result&appid=%s&input=%s" \
          % (app_id, request.quote(query))
    if verbose:
        print(url)
    response = request.urlopen(url, timeout=timeout).read()
    result = json.loads(response.decode('utf-8').strip())
    result = result['queryresult']
    if result['success']:
        if 'pods' not in result:
            return None
        out = {}
        for pod in result['pods']:
            for subpod in pod['subpods']:
                try:
                    lines = subpod['plaintext'].replace(u"×10^", "e").splitlines()
                    for line in lines:
                        if '|' in line:
                            line = line.split("|")
                            key = line[0].strip()
                            value = line[1]
                        else:
                            key = ''
                            value = line
                        v = value.split('(')[0].strip()
                        w = v.split()
                        try:
                            v = Value(engine(w[0]), w[1], original=True)
                        except ValueError:
                            pass
                        if key not in out:
                            out[key] = v
                except (KeyError, ValueError):
                    pass
        if out:
            if len(out) == 1:
                return list(out.values())[0]
            else:
                return out
    return None

