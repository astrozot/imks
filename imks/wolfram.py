# -*- coding: utf-8 -*-

try:
    from urllib import request, error
except:
    import urllib2 as request
    error = request

import json
import re

from .units import Value, UnitParseError
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
    """Perform a full Wolfram Alpha query and return the main results.

    This function queries Wolfram Alpha for a simple string and produces
    an output according to the results. The output is converted into a
    dimensional quantity (Value) if possible. Moreover, if several
    independent outputs are returned by Wolfram Alpha, the function returns
    a dictionary.

    The function requires that app_id from this module is set. Additionally,
    the user namespace, if available, is used to convert string representations
    of numbers into quantities. If unavailable, the float function is used
    instead.

    Examples:
        wolfram("earth mass")
        wolfram("mean ocean depth")
        wolfram("sun surface temperature")
        """
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
    result = json.loads(response.decode("utf-8").strip())
    result = result["queryresult"]
    if result["success"]:
        if "pods" not in result:
            return None
        out = {}
        for pod in result['pods']:
            if verbose:
                print("\n%s" % pod["title"])
            for subpod in pod["subpods"]:
                try:
                    lines = subpod["plaintext"].replace(u"×10^", "e").splitlines()
                    for line in lines:
                        if verbose:
                            print(" ", line)
                        if '|' in line:
                            line = line.split("|")
                            key = line[0].strip()
                            value = line[1]
                        else:
                            key = ""
                            value = line
                        v = value.split('  ')[0].strip()
                        w = v.split()
                        try:
                            v = Value(engine(w[0]), " ".join(w[1:]), original=True)
                        except (ValueError, UnitParseError):
                            pass
                        if key not in out:
                            out[key] = [v]
                        else:
                            out[key].append(v)
                except KeyError:
                    pass
        new_out = {}
        for k, vs in out.items():
            # Now make sure all units found are equivalent
            us = {}
            for v in vs:
                if isinstance(v, Value):
                    u = tuple(v.unit.to_list())
                    if u in us:
                        us[u].append(v)
                    else:
                        us[u] = [v]
            # Find out the version with the most identical units
            best_len = 0
            best_val = None
            for u, v in us.items():
                if len(v) > best_len:
                    best_val = v[0]
            new_out[k] = best_val
        if new_out:
            if len(new_out) == 1:
                return list(new_out.values())[0]
            else:
                return new_out
    return None
