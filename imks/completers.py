__all__ = ["imks_value_completer", "imks_svalue_completer",
           "imks_at_completer", "imks_dict_completer",
           "imks_load_imks_ext", "imks_imks_completer",
           "imks_date_completer"]

import readline
from itertools import chain
from IPython.core.error import TryNext
import re
from unidecode import unidecode

from . import units, currencies, calendars
from .config import *


def _retrieve_obj(name, context):
    # we don't want to call any functions, but I couldn't find a robust regex
    # that filtered them without unintended side effects. So keys containing
    # "(" will not complete.
    try:
        assert "(" not in name
    except AssertionError:
        raise ValueError()

    try:
        # older versions of IPython:
        obj = eval(name, context.shell.user_ns)
    except AttributeError:
        # as of IPython-1.0:
        obj = eval(name, context.user_ns)
    return obj


class ImksCompleter(object):
    @staticmethod
    def is_ascii(text):
        try:
            str(text)
        except UnicodeEncodeError:
            return False
        return True

    def get_prefixes(self, text):
        return filter(lambda x: x.startswith(text) and self.is_ascii(x),
                      units.prefixes.keys())

    def get_units(self, text):
        us = units.units.keys()
        if config["complete_currencies"] is False or \
                (config["complete_currencies"] is not True and text.lower() == text):
            us = set(us) - set(currencies.currencydict.keys())
        return filter(lambda x: x.startswith(text) and self.is_ascii(x),
                      us)

    def get_systems(self, text):
        return filter(lambda x: x.startswith(text) and self.is_ascii(x),
                      units.systems.keys())

    def get_prefunits(self, text):
        us = units.units.keys()
        if config["complete_currencies"] is False or \
                (config["complete_currencies"] is not True and text.lower() == text):
            us = set(us) - set(currencies.currencydict.keys())
        ps = list(filter(lambda x: (x.startswith(text) or text.startswith(x)) and
                         self.is_ascii(x), units.prefixes.keys()))
        length = len(text)
        # Note that below we do not explicitely add us, since the null prefix
        # is a valid prefix and is already in the list ps.  We do instead add
        # the list of prefixes, as the null unit is not included in us.
        r = filter(lambda x: x.startswith(text) and self.is_ascii(x),
                   [p for p in ps if len(p) >= length] +
                   [p + u for u in us for p in ps if len(p) <= length])
        return r

    @staticmethod
    def get_quotes(text, cs):
        ds = [unidecode(c) for c in cs]
        if text == "" or text[0] == '"':
            r = ['"' + d + '"' for d in ds]
        else:
            r = ["'" + d + "'" for d in ds]
        rx = "[- \t\n@()\[\]+-/*^|&=<>,]"
        m = len(re.findall(rx, text))
        if m == 0:
            r = [c for c in r if c.startswith(text)]
        else:
            r = [re.split(rx, c, maxsplit=m)[-1] for c in r
                 if c.startswith(text)]
        # Check if we are in a notebook
        import sys
        from io import IOBase
        if not isinstance(sys.stderr, IOBase):
            return [x if x[0] != '"' and x[0] != "'" else x[1:] for x in r]
        else:
            return r


imks_completer = ImksCompleter()

re_space_match = re.compile(r"[][ \t\n@()+-/*^|&=<>,]+")

re_value_match = re.compile(r"(?:.*=)?(\d+(?:\.\d*)?(?:[eE][-+]?\d*)?\s*)(?:\[)")


# noinspection PyUnusedLocal
def imks_value_completer(self, event):
    # event has command, line, symbol, text_until_cursor
    # self._ofind(base) has obj, parent, isalias, namespace, found, ismagic
    m = re_value_match.split(event.text_until_cursor)
    u = m[-1]  # full unit
    if u.find("]") >= 0:
        return []  # unit specification closed already
    v = re_space_match.split(u)[-1]  # last unit (or generally last word of u)
    readline.set_completer_delims(" \t\n@()[]+-/*^|&=<>,")
    return imks_completer.get_prefunits(v)


re_svalue_match = re.compile(r"(?:.*=)?(\d+(?:\.\d*)?(?:[eE][-+]?\d*)?\s*)(?: )")


# noinspection PyUnusedLocal
def imks_svalue_completer(self, event):
    m = re_svalue_match.split(event.text_until_cursor)
    u = m[-1]  # full unit
    if u.find("[") >= 0:
        raise TryNext  # unit specification with [...]
    v = re_space_match.split(u)[-1]  # last unit (or generally last word of u)
    readline.set_completer_delims(" \t\n@()[]+-/*^|&=<>,")
    return imks_completer.get_prefunits(v)


re_unit_match = re.compile(r"\[([^]]*)\]\s*,?\s*")


# noinspection PyUnusedLocal
def imks_at_completer(self, event):
    # event has command, line, symbol, text_until_cursor
    # self._ofind(base) has obj, parent, isalias, namespace, found, ismagic
    parts = event.text_until_cursor.split("@")
    if len(parts) != 2:
        raise TryNext
    us = parts[1]  # unit or system part
    vs = re_unit_match.split(us)[-1]  # last unit or system
    v = re_space_match.split(vs)[-1]
    readline.set_completer_delims(" \t\n@()[]+-/*^|&=<>,")
    return chain(imks_completer.get_systems(v), imks_completer.get_prefunits(v))


re_item_match = re.compile(r".*(\b(?!\d)\w\w*(\[[^\]]+\])*)\[((?P<s>['\"])(?!.*(?P=s)).*)$")


def imks_dict_completer(self, event):
    m = re_item_match.split(event.text_until_cursor)
    if len(m) < 3:
        if event.text_until_cursor[-1] == "[":
            return ['"']
        else:
            return []
    base, item = m[1], m[3]
    try:
        obj = _retrieve_obj(base, self)
    except:
        return []
    items = obj.keys()
    readline.set_completer_delims(" \t\n@()[]+-/*^|&=<>,")
    return imks_completer.get_quotes(item, items)


# noinspection PyUnusedLocal
def imks_load_imks_ext(self, event):
    return ["constants", "currencies", "calendars", "geolocation", "jpl",
            "wiki", "wolfram"]


# noinspection PyUnusedLocal
def imks_imks_completer(self, event):
    words = re.split(r"\s+", event.text_until_cursor)
    opts = "ha:e:u:s:k:t:c:m:M:p:o:d:"
    argopt = None
    for word in words[:-1]:
        if argopt:
            argopt = None
        if word[0] == "-" and len(word) == 2:
            i = opts.find(word[1])
            if i >= 0:
                if len(opts) > i + 1 and opts[i + 1] == ":":
                    argopt = word[1]
                    opts = opts[:i] + opts[i + 2:]
                else:
                    argopt = None
                    opts = opts[:i] + opts[i + 1:]
    if argopt == "c":
        return ["math", "mpmath", "fpmath", "numpy", "umath", "soerp", "mcerp"]
    elif argopt == "o":
        return ["0", "1", "2"]
    elif argopt == "d":
        return [c.calendar for c in calendars.calendars]
    elif argopt in ["p", "m", "M"]:
        return []
    elif argopt:
        return ["on", "off"]
    else:
        return ["on", "off"] + ["-" + o for o in opts if o != ":"]


def imks_date_completer(self, event):
    text = event.text_until_cursor
    n = len(text) - 1
    quote = None
    while n >= 0:
        c = text[n]
        if (c == '"' or c == "'") and quote is None:
            quote = n
            break
        n -= 1
    n -= 1
    nargs = 1
    npar1 = 0
    npar2 = 0
    npar3 = 0
    quot1 = 0
    quot2 = 0
    name = ""
    while n >= 0:
        c = text[n]
        if c == ")":
            npar1 += 1
        elif c == "(":
            npar1 -= 1
            if npar1 == -1 and npar2 == 0 and npar3 == 0 and \
                    quot1 == 0 and quot2 == 0:
                m = re.match(r".*(\b(?!\d)\w\w*\b)$", text[0:n])
                if m:
                    name = m.group(1)
                else:
                    name = None
                break
        elif c == "," and npar1 == 0 and npar2 == 0 and npar3 == 0 and \
                quot1 == 0 and quot2 == 0:
            nargs += 1
        elif c == "]":
            npar2 += 1
        elif c == "[":
            npar2 -= 1
        elif c == "}":
            npar3 += 1
        elif c == "{":
            npar3 -= 1
        elif c == '"':
            quot1 = 1 - quot1
        elif c == "'":
            quot2 = 1 - quot2
        n -= 1
    try:
        obj = _retrieve_obj(name, self)
    except:
        return []
    if not issubclass(obj, calendars.CalDate):
        return TryNext
    item = text[quote:]
    if nargs == 1:
        readline.set_completer_delims(" \t\n@()[]+-/*^|&=<>,")
        return imks_completer.get_quotes(item, ["today", "tomorrow",
                                                "yesterday", "now"])
    else:
        names = list(getattr(obj, list(obj.dateparts.keys())[nargs - 1] + "names", []))
        if nargs == obj.holidayarg + 1 and obj.holidays:
            names.extend(obj.holidays.keys())
        names = [name for name in names if name != ""]
        names.sort()
        readline.set_completer_delims(" \t\n@()[]+-/*^|&=<>,")
        return imks_completer.get_quotes(item, names)
