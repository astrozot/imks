# -*- coding: utf-8 -*-

import token, tokenize, re
import units, units_fpmath
from collections import deque

try:
	from io import StringIO
except ImportError:
	from cStringIO import StringIO

config = {"banner": True,
          "enabled": True,
          "auto_brackets": True,
          "standard_exponent": True,
          "unicode": False,
          "engine": "",
          "sort_units": units.sortunits,
          "unit_tolerant": units.tolerant,
          "prefix_only": units.prefixonly,
          "show_errors": units.showerrors,
          "digits": 15,
          "min_fixed": None,
          "max_fixed": None}
engine = "ufloat"
engine_unloader = None
lazyvalues = set()

re_date = re.compile(r"(\d+(\.\d+){2,})([ ]+\d\d?:\d\d?:\d\d?(\.\d*)?|[ ]+\d\d?:\d\d?(\.\d*)?|[ ]+\d\d?(\.\d*)?)?")
def utf2ascii(s):
    global config
    if not config["unicode"]: return s
    r = ""
    for c in s:
        e = c.encode("utf")
        if len(e) == 1: r += e
        elif c == u'±': r += '+/-'
        else: r += "_uTf_" + "_".join(["%x" % ord(x) for x in e])
    return r


re_utf_encoding = re.compile(r"_uTf((?:_[a-fA-F0-9][a-fA-F0-9])+)")
def ascii2utf(s):
    global config
    if not config["unicode"]: return s
    r = u""
    trunks = re_utf_encoding.split(s)
    normal = True
    for trunk in trunks:
        if normal:
            r += trunk
        else:
            e = ""
            for h in trunk[1:].split("_"):
                e += chr(string.atoi(h, 16))
            r += e.decode("utf")
        normal = not normal
    return r

def offset_token(t, delta=0, gamma=0):
    return (t[0], t[1], (t[2][0]+gamma, t[2][1]+delta),
                (t[3][0]+gamma, t[3][1]+delta), t[4])

def offset_tokens(ts, delta=0, gamma=0):
    return ts.__class__(offset_token(t, delta, gamma) for t in ts)

def change_token(t, value):
    return (t[0], value, (t[2][0], t[2][1]), (t[3][0], t[3][1]), t[4])

def unit_quote(queue):
    u = tokenize.untokenize(offset_tokens(queue, 0, -queue[0][2][0]+1)).strip()
    if u.find('"') < 0: return u'"' + u + u'"'
    elif u.find("'") < 0: return u"'" + u + u"'"
    else: return u'"""' + u + u'"""'
    

def unit_create(substatus, queue, brackets=False):
    string = queue[0][-1]
    if substatus == 0:
        if brackets:
            u = unit_quote(queue[2:-1])
            l1, c1 = queue[0][2]
            l2, c2 = queue[0][3]
            value = queue[0][1]
            if value.find(".") < 0 and value.find("e") < 0:
                value = value + ".0"
                c2 = c2 + 2
            offset = c2 + 7 + len(u) - queue[-2][3][1]
            return [(tokenize.NAME, u"Value", (l1, c1), (l1, c1+5), string),
                    (tokenize.OP, u'(', (l1, c1+5), (l1, c1+6), string),
                    (tokenize.NUMBER, value, (l1, c1+6), (l2, c2+6), string),
                    (tokenize.OP, u',', (l2, c2+6), (l2, c2+7), string),
                    (tokenize.STRING, u, (l2, c2+7), (l2, c2+7+len(u)), string),
                    (tokenize.OP, u')', (l2, c2+7+len(u)), (l2, c2+8+len(u)), string)], \
                    offset
        else:
            u = unit_quote(queue[1:])
            l1, c1 = queue[0][2]
            l2, c2 = queue[0][3]
            value = queue[0][1]
            if value.find(".") < 0 and value.find("e") < 0:
                value = value + ".0"
                c2 = c2 + 2
            offset = c2 + 7 + len(u) - queue[-1][3][1]
            return [(tokenize.NAME, u"Value", (l1, c1), (l1, c1+5), string),
                    (tokenize.OP, u'(', (l1, c1+5), (l1, c1+6), string),
                    (tokenize.NUMBER, value, (l1, c1+6), (l2, c2+6), string),
                    (tokenize.OP, u',', (l2, c2+6), (l2, c2+7), string),
                    (tokenize.STRING, u, (l2, c2+7), (l2, c2+7+len(u)), string),
                    (tokenize.OP, u')', (l2, c2+7+len(u)), (l2, c2+8+len(u)), string)], \
                    offset
    else:
        if brackets:
            u = unit_quote(queue[1:-1])
            l1, c1 = queue[0][2]
            offset = c1 + len(u) - queue[-1][3][1]
            return [(tokenize.STRING, u, (l1, c1), (l1, c1+len(u)), string)], \
                   offset
        else:
            u = unit_quote(queue)
            l1, c1 = queue[0][2]
            offset = c1 + len(u) - queue[-1][3][1]
            return [(tokenize.STRING, u, (l1, c1), (l1, c1+len(u)), string)], \
                   offset

def unit_transformer(tokens):
    global config
    if not config["enabled"]: return tokens

    # fix multiline issue
    # tokens = list(filter(lambda t: t[0] != tokenize.NL, tokens))
    
    # First, check if there are uncertainties combinations
    if engine == "ufloat":
        newtoks = []
        ntokens = len(tokens)
        n = 0
        while n < ntokens:
            c0 = tokens[n][0]
            if c0 == tokenize.NUMBER:
                if n < ntokens - 4 and \
                  tokens[n+1][0] == tokenize.OP and tokens[n+1][1] == "+" and \
                  tokens[n+2][0] == tokenize.OP and tokens[n+2][1] == "/" and \
                  tokens[n+3][0] == tokenize.OP and tokens[n+3][1] == "-" and \
                  tokens[n+4][0] == tokenize.NUMBER:
                    # check if we are using the (a +/- b)[exp] syntax
                    if n > 0 and n < ntokens - 5 and \
                      tokens[n-1][0] == tokenize.OP and tokens[n-1][1] == "(" and \
                      tokens[n+5][0] == tokenize.OP and tokens[n+5][1] == ")":
                      # OK, we might be using it, check if this is a function
                      # call
                        if n <= 1 or tokens[n-2][0] != tokenize.NAME:
                            # not a function call: we need to remove the
                            # parentheses; check if the exponent is following
                            newtoks.pop()
                            if n < ntokens - 6 and \
                              tokens[n+6][0] == tokenize.NAME and \
                              len(tokens[n+6][1]) >= 2 and \
                              tokens[n+6][1][0].lower() == "e" and \
                              tokens[n+6][1][1].isdigit():
                                # Get all digits after "e": the rest might be a
                                # unit specification
                                i = 2
                                t1 = tokens[n+6]
                                s = t1[1]
                                while i < len(s) and s[i].isdigit(): i = i+1
                                tokens[n+6] = (t1[0], s[0:i], t1[2],
                                               (t1[3][0], t1[2][1] + i), t1[4])
                                t = (tokenize.NUMBER,
                                     tokenize.untokenize(tokens[n-1:n+7]),
                                     tokens[n-1][2], tokens[n+6][3],
                                     tokens[n][4])
                                newtoks.append(t)
                                if len(s.rstrip()) > i:
                                    t1 = (t1[0], s[i:], (t1[2][0], t1[2][1]+i),
                                          t1[3], t1[4])
                                    tokens[n+6] = t1
                                    n = n -1
                                n = n + 7
                                continue
                            elif (n < ntokens - 8 and \
                              tokens[n+6][0] == tokenize.NAME and \
                              tokens[n+6][1].lower() == "e" and \
                              tokens[n+7][0] == tokenize.OP and \
                              tokens[n+7][1] in ["+", "-"] and \
                              tokens[n+8][0] == tokenize.NUMBER):
                                t = (tokenize.NUMBER,
                                     tokenize.untokenize(tokens[n-1:n+9]),
                                     tokens[n-1][2], tokens[n+8][3],
                                     tokens[n][4])
                                newtoks.append(t)
                                n = n + 9
                                continue
                            else:
                                # The parentheses are not needed: remove them!
                                t = (tokenize.NUMBER,
                                     tokenize.untokenize(tokens[n:n+5]),
                                     tokens[n-1][2], tokens[n+4][3],
                                     tokens[n][4])
                                newtoks.append(t)
                                n = n + 6
                                continue
                    t = (tokenize.NUMBER, tokenize.untokenize(tokens[n:n+5]),
                         tokens[n][2], tokens[n+4][3], tokens[n][4])
                    newtoks.append(t)
                    n = n + 5
                    continue
                if n < ntokens - 3 and \
                  tokens[n+1][0] == tokenize.OP and tokens[n+1][1] == "(" and \
                  tokens[n+2][0] == tokenize.NUMBER and \
                  tokens[n+3][0] == tokenize.OP and tokens[n+3][1] == ")":
                  # using the 1.234(5) notation: verify the possible presence
                  # of an exponent

                    if n < ntokens - 4 and \
                      tokens[n+4][0] == tokenize.NAME and \
                      len(tokens[n+4][1]) >= 2 and \
                      tokens[n+4][1][0].lower() == "e" and \
                      tokens[n+4][1][1].isdigit():
                        # Get all digits after "e": the rest might be a
                        # unit specification
                        i = 2
                        t1 = tokens[n+4]
                        s = t1[1]
                        while i < len(s) and s[i].isdigit(): i = i+1
                        tokens[n+4] = (t1[0], s[0:i], t1[2],
                                       (t1[3][0], t1[2][1] + i), t1[4])
                        t = (tokenize.NUMBER,
                             tokenize.untokenize(tokens[n:n+5]),
                             tokens[n][2], tokens[n+4][3],
                             tokens[n][4])
                        newtoks.append(t)
                        if len(s.rstrip()) > i:
                            t1 = (t1[0], s[i:], (t1[2][0], t1[2][1]+i),
                                  t1[3], t1[4])
                            tokens[n+4] = t1
                            n = n - 1
                        n = n + 5
                        continue
                    elif n < ntokens - 6 and \
                      tokens[n+4][0] == tokenize.NAME and \
                      tokens[n+4][1].lower() == "e" and \
                      tokens[n+5][0] == tokenize.OP and \
                      tokens[n+5][1] in ["+", "-"] and \
                      tokens[n+6][0] == tokenize.NUMBER:
                        t = (tokenize.NUMBER,
                             tokenize.untokenize(tokens[n:n+7]),
                             tokens[n][2], tokens[n+6][3],
                             tokens[n][4])
                        newtoks.append(t)
                        n = n + 7
                        continue
                    else:
                        t = (tokenize.NUMBER, tokenize.untokenize(tokens[n:n+4]),
                             tokens[n][2], tokens[n+3][3], tokens[n][4])
                        newtoks.append(t)
                        n = n + 4
                        continue
            newtoks.append(tokens[n])
            n = n + 1
        tokens = newtoks
    # Now scan for lazy values
    global lazyvalues
    newtoks = []
    ntokens = len(tokens)
    n = 0
    offset = 0
    while n < ntokens:
        t = offset_token(tokens[n], offset)
        if t[0] == tokenize.NAME and t[1] in lazyvalues:
            newtoks.append(t)
            newtoks.append((tokenize.OP, "(", t[3], (t[3][0], t[3][1]+1), t[4]))
            newtoks.append((tokenize.OP, ")", (t[3][0], t[3][1]+1),
                            (t[3][0], t[3][1]+2), t[4]))
            offset += 2
        else:
            newtoks.append(t)
        n = n + 1
    tokens = newtoks
    # Now proceed
    newtoks = []                        # Transformed tokens
    queue = []                          # Queue used to store partial units
    status = 0                          # General status
    substatus = 0                       # Substatus: before (0) or after (1) @
    offset = 0                          # Current offset of the tokens
    reset = False                       # Do a reset after a newline
    for tt in tokens:                   # Feed loop
        if True and tt[1] == "~":      # Debug me! @@@
            import pdb
            pdb.set_trace()
            continue
        if reset:
            status = 0
            substatus = 0 
            offset = 0
            reset = False
        if tt[0] in (tokenize.NEWLINE, tokenize.NL):
            reset = True
        tokens1 = deque([offset_token(tt, offset)])
        while tokens1:                  # Internal loop
            t = tokens1.popleft()
            codex, value, p1, p2, string = t
            if codex == tokenize.OP and value == "@" and not queue:
                substatus = 1
                status = 1
            if codex == tokenize.N_TOKENS:
                comment = value[1:].strip()
                if len(comment) > 0 and comment[0] in "'\"" and comment[-1] == comment[0]:
                    comment = comment.encode('latin-1').decode('unicode_escape')
                    codex = tokenize.OP
                    value = "&"
                    l1, c1 = p1
                    t = codex, value, p1, (l1, c1+1), string
                    lc = len(comment)
                    tokens1.extend([t,
                                    (tokenize.NAME, "Doc", (l1, c1+2), (l1, c1+5),
                                     string),
                                     (tokenize.OP, "(", (l1, c1+5), (l1, c1+6), string),
                                     (tokenize.STRING, comment, (l1, c1+6),
                                     (l1, c1+6+lc), string),
                                     (tokenize.OP, ")", (l1, c1+6+lc), (l1, c1+7+lc),
                                      string)])
                    continue
            if status <= 0:                 # ...
                if codex == tokenize.NUMBER and substatus == 0:
                    status = 1
                    queue.append(t)
                else:
                    newtoks.append(t)
            elif status == 1:               # ...12 or ... @
                if codex == tokenize.OP and value == "[":
                    status = 2
                    queue.append(t)
                elif config["auto_brackets"] and codex == tokenize.NAME and \
                    (units.isunit(ascii2utf(value)) or substatus == 1):
                    status = 3
                    queue.append(t)
                elif config["auto_brackets"] and value == "*" and \
                    substatus == 1:
                    status = 1
                    queue.append(t)
                elif substatus == 1 and value == "@":
                    value == "|"
                    l1, c1 = t[3]
                    s = t[-1]
                    offset += 8             # This is OK, tokens1 should be empty now!
                    newtoks.extend([change_token(t, "|"), 
                                    (tokenize.NAME, u"System", (l1,c1+1), (l1,c1+7), s),
                                    (tokenize.OP, u"(", (l1,c1+7), (l1,c1+8), s)])
                else:
                    newtoks.extend(queue)
                    queue = []
                    tokens1.appendleft(t)
                    if substatus == 1:
                        l1, c1 = t[3]
                        s = t[-1]
                        newtoks.append((tokenize.OP, u")", (l1,c1+1), (l1,c1+2), s))
                        substatus = 0
                        offset += 1
                        tokens1 = offset_tokens(tokens1, 2)
                    status = 0
            elif status == 2:               # ...12[ or ... @[
                if codex == tokenize.OP and value == "]":
                    status = 0
                    queue.append(t)
                    queue, delta = unit_create(substatus, queue, True)
                    newtoks.extend(queue)
                    if substatus == 1:
                        delta += 1
                        newtoks.append(offset_token(change_token(t, ")"), delta))
                        substatus = 0
                    offset += delta
                    tokens1 = offset_tokens(tokens1, delta)
                    queue = []
                elif substatus == 1 and codex == tokenize.OP and \
                    (value == "," or value == "|"):
                    queue.append(change_token(t, "]"))
                    queue, delta = unit_create(substatus, queue, True)
                    newtoks.extend(queue)
                    newtoks.append(offset_token(change_token(t, ","), delta + 1))
                    queue = [offset_token(change_token(t, "["), delta + 2)]
                    offset += delta + 3
                    tokens1 = offset_tokens(tokens1, delta + 4)
                else:
                    queue.append(t)
            elif status == 3:               # ...12 m or ... @ m
                if codex == tokenize.NAME and units.isunit(ascii2utf(value)):
                    queue.append(t)
                elif codex == tokenize.OP and value == "/":
                    status = 4
                    queue.append(t)
                elif codex == tokenize.OP and value == "^":
                    status = 5
                    queue.append(t)
                elif codex == tokenize.OP and value == ".":
                    status = 8
                    queue.append(t)
                else:
                    queue, delta = unit_create(substatus, queue)
                    newtoks.extend(queue)
                    tokens1.appendleft(t)
                    offset += delta
                    tokens1 = offset_tokens(tokens1, delta+1)
                    if substatus == 1:
                        col = queue[-1][3][1]
                        tokens1.appendleft((tokenize.OP, ")",
                                           (t[2][0], col),
                                           (t[2][0], col+1), t[4]))
                        substatus = 0
                        offset += 1
                    status = 0
                    queue = []
            elif status == 4 or status == 8: # ...12 m / or ...12 m.
                if codex == tokenize.NAME:
                    # Mmh, found a name after a / in a possible unit specification.
                    # Is it really a possible unit or not?  Check...
                    if units.isunit(ascii2utf(value)):
                        # It is a unit, use it
                        status = 3
                        queue.append(t)
                        continue
                # We did not find a name after a / or the name was not a valid
                # unit.  Put everything back!
                status = 0
                t0 = queue[-1]
                queue = queue[0:-1]
                queue, delta = unit_create(substatus, queue)
                newtoks.extend(queue)
                if substatus == 1:
                    tokens1.appendleft(offset_token(t, 1))
                    tokens1.appendleft((tokenize.OP, ")", (t[2][0], t[2][1]),
                                       (t[2][0], t[2][1]+1), t[4]))
                    substatus = 0
                else:
                    tokens1.appendleft(t)
                tokens1.appendleft(t0)
                offset += delta
                tokens1 = offset_tokens(tokens1, delta)
                queue = []
            elif status == 5:               # 12 m^
                if codex == tokenize.NUMBER:
                    status = 6
                    queue.append(t)
                elif codex == tokenize.OP and (value == "-" or value == "+"):
                    status = 7
                    queue.append(t)
                else:
                    status = 0
                    t0 = queue[-1]
                    queue = queue[0:-1]
                    queue, delta = unit_create(substatus, queue)
                    newtoks.extend(queue)
                    if substatus == 1:
                        tokens1.appendleft(offset_token(t, 1))
                        tokens1.appendleft((tokenize.OP, ")", (t[2][0], t[2][1]),
                                            (t[2][0], t[2][1]+1), t[4]))
                        substatus = 0
                    else:
                        tokens1.appendleft(t)
                    tokens1.appendleft(t0)
                    offset += delta
                    tokens1 = offset_tokens(tokens1, delta)
                    queue = []
            elif status == 6:               # 12 m^2 or 12 m^-2
                if codex == tokenize.NAME and units.isunit(ascii2utf(value)):
                    queue.append(t)
                    status = 3
                elif codex == tokenize.OP and value == "/":
                    status = 4
                    queue.append(t)
                elif codex == tokenize.OP and value == ".":
                    status = 8
                    queue.append(t)
                else:
                    status = 0
                    queue, delta = unit_create(substatus, queue)
                    newtoks.extend(queue)
                    if substatus == 1:
                        tokens1.appendleft(offset_token(t, 1))
                        tokens1.appendleft((tokenize.OP, ")", (t[2][0], t[2][1]),
                                            (t[2][0], t[2][1]+1), t[4]))
                        substatus = 0
                    else:
                        tokens1.appendleft(t)
                    offset += delta
                    tokens1 = offset_tokens(tokens1, delta)
                    queue = []
                continue
            elif status == 7:               # 12 m^-
                if codex == tokenize.NUMBER:
                    status = 6
                    queue.append(t)
                    continue
                else:
                    status = 0
                    t0 = queue[-1]
                    queue = queue[0:-1]
                    queue, delta = unit_create(substatus, queue)
                    newtoks.extend(queue)
                    if substatus == 1:
                        tokens1.appendleft(offset_token(t, 1))
                        tokens1.appendleft((tokenize.OP, ")", (t[2][0], t[2][1]),
                                            (t[2][0], t[2][1]+1), t[4]))
                        substatus = 0
                    else:
                        tokens1.appendleft(t)
                    tokens1.appendleft(t0)
                    tokens1.appendleft(t)
                    tokens1.appendleft(t)
                    offset += delta
                    tokens1 = offset_tokens(tokens1, delta)
                    queue = []
            else:
                newtoks.append(t)
    if substatus == 0:
        result = newtoks
        # Fix for problem w/ tokenize.ENDMARKER
        if result[-1][0] == tokenize.ENDMARKER and len(result) >= 2:
            l1, c1 = result[-2][3]
            result = result[0:-1]
            result.append((tokenize.ENDMARKER, "",  (l1, c1), (l1, c1+1), result[-1][-1]))
    else:
        result = newtoks
    if config["standard_exponent"]:
        result = [(codex, u"**", p1, p2, string) if codex == tokenize.OP and value == "^"
                  else (codex, value, p1, p2, string) \
                  for codex, value, p1, p2, string in result]
    if config["unicode"]:
        uresult = []
        offset = 0
        for t in result:
            t = offset_token(t, offset)
            if t[0] == tokenize.STRING:
                old = t[1]
                new = ascii2utf(old)
                if new[0] != "u": new = "u" + new
                delta = len(new) - len(old)
                offset += delta
                t = (t[0], new, t[2], (t[3][0], t[3][1] + delta), t[4])
            uresult.append(t)
            if t[0] in (tokenize.NEWLINE, tokenize.NL):
                offset = 0
        result = uresult
    if engine:
        uresult = []
        offset = 0
        for t in result:
            t = offset_token(t, offset)
            if t[0] == tokenize.NUMBER and \
              (t[1].find(".") >= 0 or t[1].find("e") >= 0 or \
               t[1].find("E") >= 0 or \
               t[1].find("/") >= 0 or t[1].find("(") >= 0):
                l1, c1 = t[2]
                l2, c2 = t[3]
                le = len(engine)
                uresult.extend([(tokenize.NAME, engine, t[2], (l1, c1+le), t[4]),
                                (tokenize.OP, u"(", (l1, c1+le), (l1, c1+le+1), t[4]),
                                (tokenize.STRING, '"' + t[1] + '"', (l1, c1+le+1),
                                 (l2, c2+le+3), t[4]),
                                (tokenize.OP, u")", (l2, c2+le+3), (l2, c2+le+4), t[4])])
                offset += le + 4
            else:
                uresult.append(t)
            if t[0] in (tokenize.NEWLINE, tokenize.NL):
                offset = 0
        result = uresult
    # @@@ print tokenize.untokenize(result)
    # @@@ print result
    return result


def magic_transformer(tokens):
    global config
    if not config["enabled"]: return tokens

    # fix multiline issue
    # tokens = list(filter(lambda t: t[0] != tokenize.NL, tokens))
    
    # check if there is a newline followed by a %
    newline = True
    trigger = []
    newtokens = []
    for t in tokens:
        if newline:
            if t[0] == tokenize.OP and t[1] == "%":
                trigger.append(t)
                newline = False
                continue
        if t[0] in (tokenize.NEWLINE, tokenize.NL):
            if trigger:
                l0, c0 = trigger[0][2]
                trigger = offset_tokens(trigger, -c0-1, -l0+1)
                s = repr(tokenize.untokenize(trigger[1:]).strip())
                newtokens.extend(
                    [(tokenize.NAME, u"run_magic", (l0, c0), (l0, c0+9), t[4]),
                     (tokenize.OP, u"(", (l0, c0+9), (l0, c0+10), t[4]),
                     (tokenize.STRING, s, (l0, c0+10), (l0, c0+10+len(s)), t[4]),
                     (tokenize.OP, u")", (l0, c0+10+len(s)), (l0, c0+11+len(s)), t[4]),
                     (tokenize.NEWLINE, u"\n", (l0, c0+11+len(s)), (l0, c0+12+len(s)),
                          t[4])])
                trigger = []
            else:
                newtokens.append(t)
            newline = True
        else:
            if trigger:
                trigger.append(t)
            else:
                newtokens.append(t)
            newline = False
    return newtokens


######################################################################
# Engines and related initialization functions

def math_engine(ns):
    import units_math
    global engine, engine_unloader
    if engine_unloader: engine_unloader(ns)
    units_math.load(ns)
    engine = "ufloat"
    engine_unloader = units_math.unload

def mpmath_engine(ns):
    import units_mpmath
    global engine, engine_unloader
    if engine_unloader: engine_unloader(ns)
    units_mpmath.load(ns)
    ns["mp"].pretty = True
    engine = "ufloat"
    engine_unloader = units_mpmath.unload

def fpmath_engine(ns):
    import units_fpmath
    global engine, engine_unloader
    if engine_unloader: engine_unloader(ns)
    units_fpmath.load(ns)
    ns["fp"].pretty = True
    engine = "ufloat"
    engine_unloader = units_fpmath.unload

def numpy_engine(ns):
    import units_numpy
    global engine, engine_unloader
    if engine_unloader: engine_unloader(ns)
    units_numpy.load(ns)
    ns["mp"].pretty = True
    engine = "ufloat"
    engine_unloader = units_numpy.unload

def umath_engine(ns):
    import units_umath
    from uncertainties import ufloat_fromstr
    global engine, engine_unloader
    if engine_unloader: engine_unloader(ns)
    units_umath.load(ns)
    engine = "ufloat"
    engine_unloader = units_umath.unload

def soerp_engine(ns):
    import units_soerp
    from uncertainties import ufloat_fromstr
    global engine, engine_unloader
    if engine_unloader: engine_unloader(ns)
    units_soerp.load(ns)
    engine = "ufloat"
    engine_unloader = units_soerp.unload

def mcerp_engine(ns):
    import units_mcerp
    from uncertainties import ufloat_fromstr
    global engine, engine_unloader
    if engine_unloader: engine_unloader(ns)
    units_mcerp.load(ns)
    engine = "ufloat"
    engine_unloader = units_mcerp.unload


###########################################

def printtoken(type, token, srow_scol, erow_ecol, line): # for testing
    srow, scol = srow_scol
    erow, ecol = erow_ecol
    print ("%d,%d-%d,%d:\t%s\t%s" % \
           (srow, scol, erow, ecol, tokenize.tok_name[type], repr(token)))

def pt(us):
    if type(us) in (str, unicode):
        tokens = tokenize.generate_tokens(StringIO(us.rstrip()).readline)
    else:
        tokens = us
    last = False
    for t in tokens:
        if t[0] == tokenize.ENDMARKER and last:
            t = (tokenize.NEWLINE, '\n', last[3], (last[3][0], last[3][1]+1), t[4])
        printtoken(*t)
        last = t
    return
           
def i(us):
    tokens = tokenize.generate_tokens(StringIO(us.strip()).readline)
    newtokens = []
    last = False
    for t in tokens:
        if t[0] == tokenize.ENDMARKER and last:
            t = (tokenize.NEWLINE, '\n', last[3], (last[3][0], last[3][1]+1), t[4])
        newtokens.append(t)
        printtoken(*t)
        last = t
    newtokens = unit_transformer(magic_transformer(list(newtokens)))
    print ("=======================================")
    for t in newtokens:
        printtoken(*t)
    print(tokenize.untokenize(newtokens))

def ev(us):
    tokens = tokenize.generate_tokens(StringIO(us.strip()).readline)
    newtokens = unit_transformer(magic_transformer(list(tokens)))
    s = tokenize.untokenize(newtokens)
    print(m.shell.ev(s))
    
def ev(us):
    tokens = tokenize.generate_tokens(StringIO(us.strip()).readline)
    newtokens = unit_transformer(magic_transformer(list(tokens)))
    s = tokenize.untokenize(newtokens)
    print(m.shell.ev(s))

###############################################################################

class Shell(object):
    def __init__(self):
        self.user_ns = {}
        self.user_global_ns = {"run_magic": lambda s: self.run_magic(s)}

    def ev(self, expr):
        """Evaluate python expression expr in user namespace.

        Returns the result of evaluation
        """
        return eval(expr, self.user_global_ns, self.user_ns)

    def ex(self, cmd):
        """Execute a normal python statement in user namespace."""
        print(cmd)
        exec(cmd, self.user_global_ns, self.user_ns)
    
    def run_magic(self, line):
        s = line.split(" ")
        return self.run_line_magic(s[0], " ".join(s[1:]))

    def run_line_magic(self, magic_name, line):
        """Execute the given line magic.

        Parameters
        ----------
        magic_name : str
          Name of the desired magic function, without '%' prefix.

        line : str
          The rest of the input line as a single string.
        """
        fn = self.magics[magic_name]
        if fn is None:
            raise ValueError('Magic `%s` not found' % magic_name)
        else:
            # Note: no variable expansion here!
            result = fn(line)
            return result

    def find_user_code(self, target, *args, **kwargs):
        with open(target, "rt", encoding="utf-8") as f:
            return f.read()

    def run_cell(self, code):
        tokens = tokenize.generate_tokens(StringIO(code.rstrip()).readline)
        newtokens = unit_transformer(magic_transformer(list(tokens)))
        s = tokenize.untokenize(newtokens)
        self.ex(s)
        
import sys, os, shlex, getopt

magics = {}

def magics_class(cls):
    """Class decorator for all subclasses of the main Magics class.

    Any class that subclasses Magics *must* also apply this decorator, to
    ensure that all the methods that have been decorated as line/cell magics
    get correctly registered in the class instance.  This is necessary because
    when method decorators run, the class does not exist yet, so they
    temporarily store their information into a module global.  Application of
    this class decorator copies that global data to the class instance and
    clears the global.

    Obviously, this mechanism is not thread-safe, which means that the
    *creation* of subclasses of Magic should only be done in a single-thread
    context.  Instantiation of the classes has no restrictions.  Given that
    these classes are typically created at IPython startup time and before user
    application code becomes active, in practice this should not pose any
    problems.
    """
    global magics
    cls.registered = True
    cls.magics = magics
    magics = {}
    return cls


def line_magic(func):
    magics[func.__name__] = func.__name__
    return func


class Magics(object):
    # Dict holding all command-line options for each magic.
    options_table = None
    # Dict for the mapping of magic names to methods, set by class decorator
    magics = None
    # Flag to check that the class decorator was properly applied
    registered = False
    # Instance of IPython shell
    shell = None


    def __init__(self, shell=None, **kwargs):
        if not(self.__class__.registered):
            raise ValueError('Magics subclass without registration - '
                             'did you forget to apply @magics_class?')
        self.options_table = {}
        # The method decorators are run when the instance doesn't exist yet, so
        # they can only record the names of the methods they are supposed to
        # grab.  Only now, that the instance exists, can we create the proper
        # mapping to bound methods.  So we read the info off the original names
        # table and replace each method name by the actual bound method.
        # But we mustn't clobber the *class* mapping, in case of multiple instances.
        if shell is None:
            self.shell = Shell()
        else:
            self.shell = shell
        class_magics = self.magics
        self.magics = {}
        for magic_name, meth_name in class_magics.items():
            if isinstance(meth_name, str):
                # it's a method name, grab it
                self.magics[magic_name] = getattr(self, meth_name)
            else:
                # it's the real thing
                self.magics[magic_name] = meth_name
        self.shell.magics = self.magics

    def arg_err(self,func):
        """Print docstring if incorrect arguments were passed"""
        print('Error in arguments:')
        print(oinspect.getdoc(func))

    def parse_options(self, arg_str, opt_str, *long_opts, **kw):
        """Parse options passed to an argument string.

        The interface is similar to that of :func:`getopt.getopt`, but it
        returns a :class:`~IPython.utils.struct.Struct` with the options as keys
        and the stripped argument string still as a string.

        arg_str is quoted as a true sys.argv vector by using shlex.split.
        This allows us to easily expand variables, glob files, quote
        arguments, etc.

        Parameters
        ----------

        arg_str : str
          The arguments to parse.

        opt_str : str
          The options specification.

        mode : str, default 'string'
          If given as 'list', the argument string is returned as a list (split
          on whitespace) instead of a string.

        list_all : bool, default False
          Put all option values in lists. Normally only options
          appearing more than once are put in a list.

        posix : bool, default True
          Whether to split the input line in POSIX mode or not, as per the
          conventions outlined in the :mod:`shlex` module from the standard
          library.
        """

        # inject default options at the beginning of the input line
        caller = sys._getframe(1).f_code.co_name
        arg_str = '%s %s' % (self.options_table.get(caller,''),arg_str)

        mode = kw.get('mode','string')
        if mode not in ['string','list']:
            raise ValueError('incorrect mode given: %s' % mode)
        # Get options
        list_all = kw.get('list_all',0)
        posix = kw.get('posix', os.name == 'posix')
        strict = kw.get('strict', True)

        # Check if we have more than one argument to warrant extra processing:
        odict = {}  # Dictionary with options
        args = arg_str.split()
        if len(args) >= 1:
            # If the list of inputs only has 0 or 1 thing in it, there's no
            # need to look for options
            argv = shlex.split(arg_str, posix, strict)
            # Do regular option processing
            try:
                opts,args = getopt.getopt(argv, opt_str, long_opts)
            except getopt.GetoptError as e:
                raise UsageError('%s ( allowed: "%s" %s)' % (e.msg,opt_str,
                                        " ".join(long_opts)))
            for o,a in opts:
                if o.startswith('--'):
                    o = o[2:]
                else:
                    o = o[1:]
                try:
                    odict[o].append(a)
                except AttributeError:
                    odict[o] = [odict[o],a]
                except KeyError:
                    if list_all:
                        odict[o] = [a]
                    else:
                        odict[o] = a

        # Prepare opts,args for return
        if mode == 'string':
            args = ' '.join(args)

        return odict,args


######################################################################

@magics_class
class imks_magic(Magics):
    re_doc = re.compile(r'([^#]+)\s*#\s*"(.*)(?<!\\)"\s*')

    def split_command_doc(self, line):
        m = re.match(self.re_doc, line)
        if m:
            doc = m.group(2).strip(' ')
            doc = doc.encode('latin-1').decode('unicode_escape')
            line = m.group(1)
        else: doc = ""
        return (line, doc)

    @classmethod
    def imks_doc(cls):
        """Activate and deactivate iMKS, and set iMKS options.

        Options:
          -h           show an help page on iMKS
          -a <on|off>  auto brackets for units [%s]
          -e <on|off>  allow the use of the caret (^) as an exponent (**) [%s]
          -u <on|off>  allow the use of unicode characters [%s]
          -t <on|off>  toggle the zero-value tolerance.  When enabled, zero values
                       are sum-compatible with any unit [%s]
          -s <on|off>  toggle the sorting of compound units.  When enabled, compound
                       units are sorted to show first positive units [%s]
          -k <on|off>  toggle the use of prefixes without units.  When enabled, one
                       can enter quantities such as 1[k] to indicate 1000 [%s]
          -c <name>    specify the engine for mathematical calculations: must be one
                       of math, mpmath, fpmath, numpy, umath, soerp, mcerp [%s]
          -o <0|1|2>   ignore errors on outputs (0), use them only to set the number
                       of significant digits (1), or show them (2) [%d]
          -d <cal>     default calendar to interpret dates (XXXX.YY.ZZ [HH[:MM[:SS]]])
                       [%s]
                       
        Options for the mpmath engine: 
          -p <digits>  set the number of digits to use for calculations [%d]
          -m <min>     specify the minimum digits for fixed notation [%s]
          -M <max>     specify the maximum digits for fixed notation: outside the
                       range indicated by -m min and -M max the exponential notation
                       is used.  To force a fixed format always, use min=-inf and
                       max=+inf; to force an exponential format always, use min=max
                       [%s]

        An additional <on|off> argument enable or disable imks altogether [%s].
        """
        global config
        imks_magic.__dict__["imks"].__doc__ = imks_magic.imks_doc.__doc__ % \
            ("on" if config["auto_brackets"] else "off",
             "on" if config["standard_exponent"] else "off",
             "on" if config["unicode"] else "off",
             "on" if config["unit_tolerant"] else "off",
             "on" if config["sort_units"] else "off",
             "on" if config["prefix_only"] else "off",
             config["engine"], config["show_errors"],
             config.get("default_calendar", "none"),
             config["digits"], config["min_fixed"], config["max_fixed"],
             "on" if config["enabled"] else "off")


    @line_magic
    def imks(self, args):
        def imks_print(s):
            if units.units or len(units.prefixes) > 1:
                print(s)
                
        global config
        opts, name = self.parse_options(args, 'ha:e:u:s:k:t:c:m:M:p:o:d:')
        if name in ["on", "1", "yes"]:
            config["enabled"] = True
            imks_print("iMKS enabled")
        elif name in ["off", "0", "no"]:
            config["enabled"] = False
            imks_print("iMKS disabled")
        elif len(args) == 0:
            config["enabled"] = not config["enabled"]
            imks_print("iMKS %s" % ("enabled" if config["enabled"] \
                                    else "disabled"))
        if "h" in opts:
            page.page(__doc__)
            imks_magic.imks_doc()
        if "a" in opts:
            if opts["a"] in ["on", "1", "yes"]:
                config["auto_brackets"] = True
                imks_print("Auto brackets enabled")
            elif opts["a"] in ["off", "0", "no"]:
                config["auto_brackets"] = False
                imks_print("Auto brackets disabled")
            else:
                print("Incorrect argument.  Use on/1 or off/0")
        if "e" in opts:
            if opts["e"] in ["on", "1", "yes"]:
                config["standard_exponent"] = True
                imks_print("Standard exponent (^) enabled")
            elif opts["e"] in ["off", "0", "no"]:
                config["standard_exponent"] = False
                imks_print("Standard exponent (^) disabled")
            else:
                imks_print("Incorrect argument.  Use on/1 or off/0")
        if "u" in opts:
            if opts["u"] in ["on", "1", "yes"]:
                config["unicode"] = True
                imks_print("Unicode enabled")
            elif opts["u"] in ["off", "0", "no"]:
                config["unicode"] = False
                imks_print("Unicode disabled")
            else:
                print("Incorrect argument.  Use on/1 or off/0")
        if "s" in opts:
            if opts["s"] in ["on", "1", "yes"]:
                config["sort_units"] = units.sortunits = True
                imks_print("Compound units are sorted")
            elif opts["s"] in ["off", "0", "no"]:
                config["sort_units"] = units.sortunits = False
                imks_print("Compound units are not sorted")
            else:
                print("Incorrect argument.  Use on/1 or off/0")        
        if "k" in opts:
            if opts["k"] in ["on", "1", "yes"]:
                config["prefix_only"] = units.prefixonly = True
                imks_print("Prefix without unit accepted")
            elif opts["k"] in ["off", "0", "no"]:
                config["prefix_only"] = units.prefixonly = False
                imks_print("Prefix without unit not accepted")
            else:
                print("Incorrect argument.  Use on/1 or off/0")        
        if "t" in opts:
            if opts["t"] in ["on", "1", "yes"]:
                config["unit_tolerant"] = units.tolerant = True
                imks_print("Zero-value tolerance enabled")
            elif opts["t"] in ["off", "0", "no"]:
                config["unit_tolerant"] = units.tolerant = False
                imks_print("Zero-value tolerance disabled")
            else:
                print("Incorrect argument.  Use on/1 or off/0")
        if "c" in opts:
            if opts["c"] in ["math", "mpmath", "fpmath", "numpy",
                             "umath", "soerp", "mcerp"]:
                globals()[opts["c"] + "_engine"](globals())
            else:
                print("Incorrect argument: must be math, mpmath, fpmath, numpy, umath, soerp, or mcerp.")
                return
            imks_print("iMKS math engine: %s.  Consider doing a %%reset." % opts["c"])
            config["engine"] = opts["c"]
        if "o" in opts:
            if opts["o"] == "0":
                config["show_errors"] = units.showerrors = 0
                imks_print("Errors ignored")
            elif opts["o"] == "1":
                config["show_errors"] = units.showerrors = 1
                imks_print("Errors not shown")
            elif opts["o"] == "2":
                config["show_errors"] = units.showerrors = 2
                imks_print("Errors shown")
            else:
                print("Incorrect argument: must be 0, 1, or 2")
                return
        if "p" in opts:
            self.shell.user_ns["mp"].dps = config["digits"] = int(opts["p"])
            imks_print("Precision set to %d digits" % config["digits"])
        if "m" in opts or "M" in opts:
            import units_mpmath
            if "m" in opts:
                config["min_fixed"] = units_mpmath.min_fixed = \
                    eval(opts["m"], self.shell.user_ns)
            elif "M" in opts:
                config["max_fixed"] = units_mpmath.max_fixed = \
                    eval(opts["M"], self.shell.user_ns)
            imks_print("Fixed range:", units_mpmath.min_fixed, ":", \
                        units_mpmath.max_fixed)
        if "d" in opts:
            import calendars
            calnames = [c.calendar for c in calendars.calendars]
            if opts["d"] in calnames:
                config["default_calendar"] = opts["d"]
            else: print("Unkown calendar %s" % opts["d"])
            imks_print("Default calendar set to %s" % opts["d"])
        self.imks_doc()

    @line_magic
    def load_imks(self, arg):
        """Load one ore more imks modules."""
        import os, os.path
        ip = self.shell
        modules = arg.split(",")
        for module in modules:
            code = None
            filename = module.strip()
            if os.path.splitext(filename)[1] == "":
                filename += ".txt"
            try:
                code = ip.find_user_code(filename, py_only=True)
            except:
                if not os.path.isabs(filename):
                    try:
                        filename = os.path.join(os.environ["HOME"], ".imks",
                                                filename)
                        code = ip.find_user_code(filename, py_only=True)
                    except:
                        pass
            if code:
                ip.run_cell(code)
            else:
                raise ImportError("Could not find imks file named %s" %
                                  module.strip())

    @line_magic
    def load_imks_ext(self, arg):
        """Load one ore more imks extensions.

        Currently, the following extensions are recognized:
          calendars     allow the use of multiple calendars
          constants     load a large list of constants from the NIST database
                        and set the const dictionary accordingly
          currencies    load a large list of currencies from the database
                        openexchangerates.org and define them as units
          geolocation   define two functions, set/get_geolocation to handle
                        geographical locations
          jpl           load planetary data from the SSD JPL database
          wiki          search through Wikipedia infoboxes"""
        import os, os.path
        ip = self.shell
        oldkeys = set(ip.user_ns.keys())
        oldunits = set(units.units.keys())
        exts = arg.split()
        silent = False
        for ext in exts:
            if ext == "-s": silent = True
            elif ext == "calendars":
                global config
                calendars.loadcalendars(ip)
                config["default_calendar"] = "Gregorian"
            elif ext == "geolocation":
                import geolocation
                ip.user_ns["get_geolocation"] = geolocation.get_geolocation
                ip.user_ns["set_geolocation"] = geolocation.set_geolocation
            elif ext == "constants":
                import constants
                constants.loadconstants(engine=eval(engine,
                                                        self.shell.user_global_ns,
                                                        self.shell.user_ns))
                self.shell.user_ns["const"] = constants.constants
            elif ext == "jpl":
                import jpl
                planets, moons = jpl.loadJPLconstants(engine=eval(engine,
                                                        self.shell.user_global_ns,
                                                        self.shell.user_ns))
                self.shell.user_ns["planets"] = planets
                self.shell.user_ns["moons"] = moons
                self.shell.user_ns["minorplanet"] = \
                    lambda name: jpl.load_minor(name)
            elif ext == "currencies":
                if ip.user_ns.has_key("openexchangerates_id"):
                    app_id = self.shell.user_ns["openexchangerates_id"]
                else: app_id = ""
                currencies.currencies(app_id)
            elif ext == "wiki" or ext == "wikipedia":
                import wiki
                wiki.ip = self.shell
                wiki.unit_transformer = unit_transformer
                wiki.command_transformer = command_transformer
                self.shell.user_ns["wiki"] = wiki.wiki
            else: q("Unknown extension `%s'." % ext)
        newkeys = set(ip.user_ns.keys())
        newunits = set(units.units.keys())
        if not silent:
            from textwrap import wrap
            if newkeys != oldkeys:
                diff = list(newkeys - oldkeys)
                diff.sort()
                print("\n  ".join(wrap("New definitions: %s." % (u", ".join(diff)))))
            if newunits != oldunits:
                diff = list(newunits - oldunits)
                diff.sort()
                print("\n  ".join(wrap("New units: %s." % (u", ".join(diff)))))

    def checkvalidname(self, arg):
        if re.search(r"[0-9]", arg):
            raise NameError("Invalid name \"%s\"" % arg)
                
    @line_magic
    def newbaseunit(self, arg):
        """Define a new base unit.

        Usage:
          %newbaseunit name [# "Documentation string"]

        Since base units are the fundamental building blocks of a unit system,
        a base unit definition is typically the first operation performed in a iMKS
        configuration file (see for example Startup.imks).  Note that a base unit,
        being a fundamental block used for all calculations, cannot be deleted.

        See also:
          %newbasecurrency, %newunit, %newprefix"""
        command, doc = self.split_command_doc(arg)
        self.checkvalidname(command)
        units.newbaseunit(command.strip(), doc=doc)
        return
        
    @line_magic
    def newbasecurrency(self, arg):
        """Define a new base currency.

        Usage:
          %newbasecurrency name [# "Documentation string"]

        A base currency is the main currency used for currency conversions.  It is
        important to define it, since all exchange rates are calculated using the
        base currency as reference currency.  Note that a base currency is also a
        base unit; as such, it cannot be deleted.

        See also:
          %newbaseunit, %newunit, %newprefix"""
        command, doc = self.split_command_doc(arg)
        self.checkvalidname(command)
        units.newbasecurrency(command.strip(), doc=doc)
        return

    @line_magic
    def newprefix(self, arg):
        """Define a new prefix.

        Usage:
          %newprefix name=[aliases=]value [# "Documentation string"]

        A prefix is used before a unit to build a prefixed unit: for example, the
        unit km is understood as k+m, i.e. the prefix k=1000 times the unit m=meter.
        The value of a prefix must always be a pure number; moreover, fractional
        prefixes (such as m=1/1000) should be entered in the mpmath engine using
        the fraction function (this ensures that the prefix is always computed at
        the required accuracy).

        See also:
          %delprefix, %newunit, %delunit."""
        command, doc = self.split_command_doc(arg)
        tmp = command.split("=")
        names, value = tmp[:-1], tmp[-1]
        print("PREFIX: %s", ", ".join(names))
        tokens = tokenize.generate_tokens(StringIO(value.strip()).readline)
        walue = self.shell.ev(tokenize.untokenize(
            unit_transformer([t for t in tokens])))
        for name in names:
            self.checkvalidname(name)
            units.newprefix(name.strip(), walue, doc=doc, source=value.strip())
        return

    @line_magic
    def delprefix(self, arg):
        """Delete a prefix previously defined using the %newprefix magic.

        Usage:
          %delprefix name"""
        units.delprefix(arg.strip())
        return

    @line_magic
    def newunit(self, arg):
        """Define a new unit.

        Usage:
          %newunit name=[aliases=]value [# "Documentation string"]

        After its definition, a unit can be used for any physical quantity.  If
        value evaluates to a 2-tuple, the unit is understood as an absolute
        unit: in this case the two elements of the tuple must have the same
        unit, and must represent the zero-point and the offset.  This technique
        can also be used with base units, to make them absolute:

        > %newunit Celsius=(273.15[K], 1[K])
        > %newunit K=(0[K], 1[K])

        A unit can be deleted using the %delunit magic."""
        command, doc = self.split_command_doc(arg)
        tmp = command.split("=")
        names, value = tmp[:-1], tmp[-1]
        tokens = tokenize.generate_tokens(StringIO(value.strip()).readline)
        evalue = self.shell.ev(tokenize.untokenize(
            unit_transformer([t for t in tokens])))
        for name in names:
            self.checkvalidname(name)
            units.newunit(name.strip(), evalue, doc=doc, source=value.strip())
        return

    @line_magic
    def delunit(self, arg):
        """Delete a unit previously defined using the %newunit magic.

        Usage:
          %delunit name"""
        units.delunit(arg.strip())
        return

    @line_magic
    def newsystem(self, arg):
        """Define a new unit system.
        
        Usage:
          %newsystem name=[aliases=]u1 | u2 | ... [# "Documentation string"]

        where u1,u2,... is a list of unit specifications.  A unit system is a
        convenient way to specify a set of units that will be used together in unit
        conversions with the @ operator.  This operator is able to find out the
        combination of units among the ones provided, that can recreate the unit
        specified in its left operand.  In this respect, the unit system can be used
        in two different ways:

        - If all units of a unit system are independent (that is, none of the units
          of the unit system can be expressed in terms of the other units), it is
          intended that the units in the system MUST be used, in a suitable
          combination, to produce the requested unit.

        - Alternatively, there might be multiple possible solutions, i.e.
          multiple combinations of units in the system, that can recreate the
          requested unit.  In this case, the @ operator will find the combination
          that will result in the lower number of combined system units, giving
          priority to the units entered first in the system.

        As an example, say we define two systems

        > %newsystem one=[m | s]
        > %newsystem two=[m | s | km/hour]

        If we then type
        > c @ one
        we will obtain c in units of [m s^-1], a combination of the two provided
        units.  Instead
        > c @ two
        will use as a unit [km hour^-1], since this is a unit entered in the system
        and as such it is privileged over the combination [m s^-1] (which instead
        requires the use of two different units entered).
        
        A unit system can be deleted using the %delsystem magic."""
        command, doc = self.split_command_doc(arg)
        tmp = command.split("=")
        names, value = tmp[:-1], tmp[-1]
        values = [value.strip("[] ") for value in value.split("|")] 
        for name in names:
            self.checkvalidname(name)
            units.newsystem(name.strip(), values, doc=doc)
        return
        
    @line_magic
    def delsystem(self, arg=""):
        """Delete a unit system previously defined using the %newsystem magic.

           Usage:
             %delsystem name"""
        units.delsystem(arg.strip())
        return

    @line_magic
    def defaultsystem(self, arg):
        """Set the default unit system for value representations.
        
        Usage:
          %defaultsystem system

        where system is a previously define unit system or a list of units
        separated by | as in %newsystem.  Do not use any argument to unset the
        default unit system."""
        if len(arg) == 0:
            units.defaultsystem = None
        else:
            units.defaultsystem = units.System(*[v.strip("[] ")
                                                 for v in arg.split("|")])
            units.cachedat = {}

    @line_magic
    def let(self, arg):
        """Define a variable.

        Usage:
          %let name=[aliases=]value [# "Documentation string"]

        The advantage of using let over a simple assignment is that the entire
        variable definition is retained and can be queried when inspecting the
        variable."""
        command, doc = self.split_command_doc(arg)
        tmp = command.split("=")
        names, value = tmp[:-1], tmp[-1]
        tokens = tokenize.generate_tokens(StringIO(value.strip()).readline)
        evalue = self.shell.ev(tokenize.untokenize(
            unit_transformer([t for t in tokens])))
        evalue = evalue & units.Doc(doc, value)
        try:
            evalue.__source__ = value.strip()
        except AttributeError:
            pass
        for name in names:
            self.shell.user_ns[name.strip()] = evalue
        return
            
    @line_magic
    def lazy(self, arg):
        """Define a general lazy value in terms of an expression.

        Usage:
          %lazy var=[aliases=]=expr  [# "Documentation string"]

        This magic defines the variable var to be the result of expression.  In
        contrast to standard variables, however, expr is not computed immediately:
        rather, it is evaluated only when var is used or displayed.

        This magic can be used similarly to %lazyvalue: the difference is that %lazy
        support any kind of variable, while %lazyvalue is limited to simple values.
        The mechanism used is also different: %lazy defines var to be a function with
        no argument, and include it to an internal list used to automatically add ()
        when parsing the input line; %lazyvalue uses the LazyValue python object (a
        child of Value)."""
        global lazyvalues
        command, doc = self.split_command_doc(arg)
        command = command.replace('"', '\\"').replace("'", "\\'")
        opts, command = self.parse_options(command, "1u")
        tmp = command.split("=")
        names, source = tmp[:-1], tmp[-1]
        lazyvalues.difference_update([name.strip() for name in names])
        value = "lambda : " + source
        tokens = tokenize.generate_tokens(StringIO(value.strip()).readline)
        s = tokenize.untokenize(unit_transformer(list(tokens)))
        value = self.shell.ev(s)
        for name in names:
            self.shell.user_ns[name.strip()] = value & units.Doc(doc, source)
            lazyvalues.add(name.strip())

    @line_magic
    def dellazy(self, arg):
        """Delete a previously defined lazy variable.

        Usage:
          %dellazy var

        This magic needs to be used only for variables defined through %lazy, and
        not for the ones defined through %lazyvalue (which can be deleted with the
        usual python del command, or by just overwriting them)."""
        global lazyvalues
        lazyvalues.difference_update([arg.strip()])
        del self.shell.user_ns[arg.strip()]
            
    @line_magic
    def lazyvalue(self, arg):
        """Define a variable lazily in terms of an expression.

        Usage:
          %lazyvalue [options] var=[aliases=]=expr  [# "Documentation string"]

        This magic defines the variable var to be the value of expression.  In contrast
        to standard variables, however, expr is not computed immediately: rather, it is
        evaluated only when var is used or displayed.  Among other uses, this allows
        one to define variables with a arbitrary precision (in the sense that the
        precision used when calculating the variable is the one set at real time), or
        variables that depend dynamically on other external variables.  Note that this
        magic only works for simple values: for more complicated combination, please
        use the %lazy magic.

        Options:
          -u   Evaluate the expression unit each time (by default, the value of the
               expression is recomputed each time it is needed, but the unit is
               computed only once, the first time variable is calculated)
          -1   Evaluate the entire expression (unit and value) only once, the first
               time the variable is calculated

        See also %lazy, %lazyunit, and %lazyprefix."""
        command, doc = self.split_command_doc(arg)
        command = command.replace('"', '\\"').replace("'", "\\'")
        opts, command = self.parse_options(command, "1u")
        tmp = command.split("=")
        names, value = tmp[:-1], tmp[-1]
        value = "lambda : " + value
        tokens = tokenize.generate_tokens(StringIO(value.strip()).readline)
        value = self.shell.ev(tokenize.untokenize(
            unit_transformer([t for t in tokens])))
        lvalue = units.LazyValue(value, once="1" in opts, unit_once="u" not in opts)
        for name in names:
            self.shell.user_ns[name.strip()] = lvalue

    @line_magic
    def lazyprefix(self, arg):
        """Define a prefix lazily in terms of an expression.

        Usage:
          %lazyprefix [options] var=[aliases=]=expr  [# "Documentation string"]

        Similar to %lazy, but used to define a lazy prefix (see also %lazyunit).

        Options: 
         -1   Evaluate the entire expression only once, the first time the prefix is
               used"""
        command, doc = self.split_command_doc(arg)
        opts, command = self.parse_options(command, "1")
        tmp = command.split("=")
        names, value = tmp[:-1], tmp[-1]
        walue = "lambda : " + value
        tokens = tokenize.generate_tokens(StringIO(walue.strip()).readline)
        walue = self.shell.ev(tokenize.untokenize(
            unit_transformer([t for t in tokens])))
        lvalue = units.LazyValue(walue, once="1" in opts, unit_once=True)
        for name in names:
            self.checkvalidname(name)
            units.newprefix(name.strip(), lvalue, doc=doc, source=value.strip())

    @line_magic
    def lazyunit(self, arg):
        """Define a unit lazily in terms of an expression.

        Usage:
          %lazyunit [options] var=[aliases=]=expr  [# "Documentation string"]

        Similar to %lazy, but used to define a lazy unit (see also %lazyprefix).

        Options:
          -1   Evaluate the entire expression only once, the first time the unit is
               used"""
        command, doc = self.split_command_doc(arg)
        opts, command = self.parse_options(command, "1")
        tmp = command.split("=")
        names, value = tmp[:-1], tmp[-1]
        walue = "lambda : " + value
        tokens = tokenize.generate_tokens(StringIO(walue.strip()).readline)
        walue = self.shell.ev(tokenize.untokenize(
            unit_transformer([t for t in tokens])))
        lvalue = units.LazyValue(walue, once="1" in opts, unit_once=True)
        for name in names:
            self.checkvalidname(name)
            units.newunit(name.strip(), lvalue, doc=doc, source=value.strip())

    @line_magic
    def newtransformer(self, arg):
        """Define a new input transformer.

           Usage:
             %newtransformer name="regex":transformer

           where name is the name of the new input transformer (only used as a key for
           %deltransformer), regexp is a regular expression using the named groups, and
           transformer is a function used to perform the input transformation."""
        command, doc = self.split_command_doc(arg)
        i = command.find("=")
        if i < 0: raise SyntaxError("equal sign not found")
        name, value = command[0:i], command[i+1:]
        quotes = re.split(r'(?<!\\)\"', value)
        regex = quotes[1]
        trans = quotes[2]
        if trans[0] != ':': raise SyntaxError("column sign not found")
        cregex = re.compile(regex)
        self.checkvalidname(name)
        config["intrans"][name] = (cregex, trans[1:].strip()) & \
            units.Doc(doc, regex + " : " + trans[1:])
        return

    @line_magic
    def deltransformer(self, arg=""):
        """Delete an input transformer previously defined using %newtransformer.

           Usage:
             %deltransformer name"""
        del config["intrans"][arg.strip()]
        return

    @line_magic
    def newformat(self, arg):
        """Define a new output format.

           Usage:
             %newformat name=transformer

           where name is the name of the new output transformer (only used as a key for
           %deltformat) and transformer is a function used to generate the output."""
        command, doc = self.split_command_doc(arg)
        i = command.find("=")
        if i < 0: raise SyntaxError("equal sign not found")
        name, value = command[0:i], command[i+1:]
        self.checkvalidname(name)
        units.formats[name] = eval(value, self.shell.user_ns) & units.Doc(doc, value)
        return

    @line_magic
    def delformat(self, arg=""):
        """Delete a format previously defined using %newformat.

           Usage:
             %delformat name"""
        del units.formats[arg.strip()]
        return

    @line_magic
    def uinfo(self, args):
        """Provide detailed information about an imks-related object.

        Usage:
          %uinfo [options] name

        Options:
          -a   Apropos mode: does search within documentation strings
          -y   Parsing mode: show how a prefix + unit is parsed
          -u   Search among units
          -c   Search among currencies
          -p   Search among prefixes
          -s   Search among unit systems
          -t   Search among input transformers
          -f   Search among output formats
          -x   Extended search: include variables
          -i   For wildcard searches, ignore the case"""
        global config
        opts, name = self.parse_options(args, "ayupstfxci")
        if name == "":
            self.shell.run_line_magic("imks", "-h")
            return
        u0 = dict([(k, w) for k, w in units.units.iteritems()
                   if k in units.baseunits])
        u1 = dict([(k, w) for k, w in units.units.iteritems()
                   if k not in units.baseunits and k not in currencies.basecurrency \
                   and k not in currencies.currencydict])
        c0 = dict([(k, w) for k, w in units.units.iteritems()
                   if k in currencies.basecurrency])
        c1 = dict([(k, w) for k, w in units.units.iteritems()
                    if k not in currencies.basecurrency and \
                       k in currencies.currencydict])
        namespaces = []
        if 's' in opts:
            namespaces.append(("Unit systems", units.systems))
        if 'u' in opts:
            namespaces.extend([("Base units", u0),
                               ("Units", u1)])
        if 'c' in opts:
            namespaces.extend([("Base currencies", c0),
                               ("Currencies", c1)])
        if 'p' in opts:
            namespaces.append(("Prefixes", units.prefixes))
        if 't' in opts:
            namespaces.append(("Input Transformers", config["intrans"]))
        if 'f' in opts:
            namespaces.append(("Output Formats", units.formats))
        if not namespaces:
            namespaces = [("Unit systems", units.systems),
                          ("Base units", u0),
                          ("Base currencies", c0),
                          ("Units", u1),
                          ("Currencies", c1),
                          ("Prefixes", units.prefixes),
                          ("Input Transformers", config["intrans"]),
                          ("Output Formats", units.formats)]
        if 'x' in opts:
            namespaces.append(("Variables", self.shell.user_ns))
        if 'a' in opts:
            name = name.upper()
            shown = False
            for n, d in namespaces:
                f = [k for k,v in d.iteritems() \
                     if unicode(getattr(v, "__doc__", "")).upper().find(name) >= 0]
                if f:
                    if not shown: print(name)
                    print("%s: %s" % (n, ", ".join(f)))
                    shown = True
            if not shown:
                print("Nothing found")
            return
        if 'y' in opts:
            res = units.isunit(name)
            if res:
                print("%s parsed as prefix(%s) + unit(%s)" % (name, res[0], res[1]))
            else: print("%s is not a valid unit with prefix")
            return
        if '*' in name:
            psearch = self.shell.inspector.psearch
            d = dict(namespaces)
            try:
                psearch(name, d, d.keys(), ignore_case='i' in opts)
            except:
                self.shell.showtraceback()

        else:
            goodones = [n for n,ns in enumerate(namespaces)
                        if name in ns[1]]
            if goodones:
                if len(goodones) > 1: spaces = "  "
                else: spaces = ""
                res = []
                for goodone in goodones:
                    namespace = namespaces[goodone]
                    obj = namespace[1][name]
                    if len(goodones) > 1:
                        fields = [(namespace[0].upper(), "")]
                    else: fields = []
                    fields.extend([(spaces + "Type", obj.__class__.__name__),
                                   (spaces + "String Form", str(obj)),
                                   (spaces + "Namespace", namespace[0])])
                    if hasattr(obj, "__source__"):
                        fields.append((spaces + "Definition", obj.__source__))
                    fields.append((spaces + "Docstring", obj.__doc__ or
                                   "<no docstring>"))
                    if hasattr(obj, "__timestamp__"):
                        fields.append((spaces + "Timestamp",
                                       obj.__timestamp__ or "<no timestamp>"))
                    res.append(self.shell.inspector._format_fields(fields,13+len(spaces)))
                page.page("\n\n".join(res))
            else:
                res = units.isunit(name)
                if res:
                    print("%s parsed as prefix(%s) + unit(%s)" % (name, res[0], res[1]))
                else: print("Object `%s` not found" % name)
        return

    @line_magic
    def compatible(self, args):
        """Check units or variables compatible with a given value or unit.

        By default, the function checks both units and variables, but this can be
        changed using the appropriate flag.

        Flags:
        -u         Check only units
        -U list    When checking units consider only units in the quoted list
        -v         Check only variables
        -V list    When checking variables consider only the ones in the quoted list
        -l level   Search combined units containing level number of simple units
                   (default: level=1).  Use a negative level to search only for
                   direct compatibilities (without exponent).  Use level=0 to search
                   for aliases (identical units or variables).

        Examples:
        %compatible g
        %compatible -l 3 -v -V "c, G, hbar" [s]
        """
        import sys 
        opts, us = self.parse_options(args, "uU:vV:l:")
        level = int(opts.get("l", 1))
        if us[0] == '[' and us[-1] == ']':
            r = units.Value(1, us.strip("[] "))
        else:
            tokens = tokenize.generate_tokens(StringIO(us.strip()).readline)
            r = self.shell.ev(tokenize.untokenize(
                unit_transformer([t for t in tokens])))
        if "v" not in opts:
            print("Compatible units:", end='')
            found = False
            if "U" in opts:
                where = ODict()
                for k in opts["U"].split(","):
                    k1 = k.strip(" []")
                    if k1 in units.systems:
                        for k2 in units.systems[k1].repr:
                            k3 = k2.strip(" []")
                            tmp = units.unityacc.parse(k3, lexer=units.unitlex)
                            where[str(tmp[1]).strip(" []")] = tmp[0]
                    else:
                        tmp = units.unityacc.parse(k1, lexer=units.unitlex)
                        where[str(tmp[1]).strip(" []")] = tmp[0]
            else:
                where = units.units
            for u in r.findCompatible(where, level=level):
                print(unicode(u), end='')
                found = True
                sys.stdout.flush()
            if not found: print("None")
            else: print()
        if "u" not in opts:
            print("Compatible values:", end='')
            found = False
            if "V" in opts:
                where = ODict([(k.strip(), self.shell.user_ns[k.strip()])
                                for k in opts["V"].split(",")])
            else:
                where = self.shell.user_ns
            where = ODict([(k,v) for k,v in where.iteritems()
                           if isinstance(v, units.Value)])
            for u in r.findCompatible(where, level=level):
                uu = unicode(u).strip("[] ")
                if not found: print (uu, end='')
                else: print(chr(8) + ",", uu, end='')
                found = True
                sys.stdout.flush()
            if not found: print("None")
            else: print()

    @line_magic
    def reset(self, args):
        """Reset the iMKS session.

        This does a full reset: the engine, however, is left unchanged."""
        global lazyvalues, config
        import gc
        # this code is from IPython
        ip = self.shell
        ip.reset(new_session=False)
        gc.collect()
        # load new symbols
        units.reset()
        lazyvalues = set()
        units.load_variables(ip)
        # math engine: this is not reset!
        globals()[config["engine"] + "_engine"](ip)
        # input transformers
        config["intrans"] = {}
        # active true float division
        exec(ip.compile("from __future__ import division", "<input>", "single"), ip.user_ns)
        # check if currencies are loaded
        if hasattr(currencies, "reset"): currencies.reset()
        # load Startup
        ip.run_line_magic("load_imks", "Startup")
        # reprint the welcome message
        if config["banner"]:
            print("Welcome to iMKS 1.3 - © Marco Lombardi 2017")
            print("Type %imks -h or ! for help.")



# units.load_variables(globals())
# math_engine(globals())

# print(i(u"1[m]"))

m=imks_magic()
units_fpmath.load(m.shell.user_global_ns)
units.load_variables(m.shell.user_global_ns)
m.load_imks('Startup-ios')
