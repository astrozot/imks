import re
import tokenize
from collections import deque
from io import StringIO
from . import units


re_date = re.compile(r"(\d+(\.\d+){2,})([ ]+\d\d?:\d\d?:\d\d?(\.\d*)?|[ ]+\d\d?:\d\d?(\.\d*)?|[ ]+\d\d?(\.\d*)?)?")


######################################################################
# Token utilities

def offset_token(t, delta=0, gamma=0):
    return t[0], t[1], (t[2][0]+gamma, t[2][1]+delta), \
           (t[3][0]+gamma, t[3][1]+delta), t[4]


def offset_tokens(ts, delta=0, gamma=0):
    return ts.__class__(offset_token(t, delta, gamma) for t in ts)


def change_token(t, value):
    return t[0], value, (t[2][0], t[2][1]), (t[3][0], t[3][1]), t[4]


######################################################################
# Magic transformer: used only by the standalone version of imks

def magic_transformer(tokens):
    from .config import config
    if not config["enabled"]:
        return tokens
        
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
        if t[0] in (tokenize.NEWLINE, tokenize.NL, tokenize.ENDMARKER):
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
            if t[0] != tokenize.DEDENT:
                newline = False
    return newtokens


######################################################################
# Command transformer: works on strings and does, e.g., date input

def command_transformer(line):
    from .config import config
    if not config["enabled"]:
        return line
    if line and line[-1] == '!':
        if len(line) > 1 and line[-2] == '!':
            line = "%uinfo -a " + line[:-2]
        else:
            line = "%uinfo " + line[:-1]
    if config.get("default_calendar", None):
        replaces = []
        for m in re_date.finditer(line):
            datetime = [e.strip() for e in m.group(1).split(".")]
            if m.group(3):
                datetime.extend([e.strip() for e in m.group(3).split(":")])
            replaces.insert(0, ("%s(%s)" % (config["default_calendar"],
                                            ",".join(datetime)),
                                m.start(), m.end()))
        for what, start, end in replaces:
            line = line[:start] + what + line[end:]
    for r, t in config["intrans"].values():
        replaces = []
        for m in r.finditer(line):
            args = m.groupdict()
            reps = ['"%s": %s' % arg for arg in args.items()
                    if arg[1] is not None]
            replaces.insert(0, ("%s(**{%s})" % (t, ", ".join(reps)),
                                m.start(), m.end()))
        for what, start, end in replaces:
            line = line[:start] + what + line[end:]
    return line


######################################################################
# Unit transformer: works on tokens and does all the job

def unit_quote(queue):
    u = tokenize.untokenize(queue).replace('\\', '').replace('\n', ' ').strip()
    if u.find('"') < 0:
        return u'"' + u + u'"'
    elif u.find("'") < 0:
        return u"'" + u + u"'"
    else:
        return u'"""' + u + u'"""'
    

def unit_create(substatus, queue, brackets=False):
    string = queue[0][-1]
    if substatus == 0:
        if brackets:
            unit_part = queue[2:-1]
        else:
            unit_part = queue[1:]
        u = unit_quote(unit_part)
        l1, c1 = queue[0][2]
        l2, c2 = queue[0][3]
        value = queue[0][1]
        if value.find(".") < 0 and value.find("e") < 0:
            value = value + ".0"
            c2 = c2 + 2
        offset = c2 + 8 + len(u) - queue[-1][3][1]
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
    from .config import config, internals
    if not config["enabled"]:
        return tokens
    engine = internals["engine"]
    
    # fix multi-line issue
    tokens = list(filter(lambda x: x[0] != tokenize.NL, tokens))

    # DEBUG ONLY:
    # for t in tokens:
    #    print(t)
    
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
                    if 0 < n < ntokens - 5 and \
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
                                while i < len(s) and s[i].isdigit():
                                    i = i+1
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
                                    n = n - 1
                                n = n + 7
                                continue
                            elif n < ntokens - 8 and \
                                    tokens[n+6][0] == tokenize.NAME and \
                                    tokens[n+6][1].lower() == "e" and \
                                    tokens[n+7][0] == tokenize.OP and \
                                    tokens[n+7][1] in ["+", "-"] and \
                                    tokens[n+8][0] == tokenize.NUMBER:
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
                        while i < len(s) and s[i].isdigit():
                            i = i+1
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
    # Now proceed
    newtoks = []                        # Transformed tokens
    queue = []                          # Queue used to store partial units
    status = 0                          # General status
    substatus = 0                       # Substatus: before (0) or after (1) @
    offset = 0                          # Current offset of the tokens
    reset = False                       # Do a reset after a newline
    for tt in tokens:                   # Feed loop
        if False and tt[1] == "~":      # Debug me! @@@
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
                        (units.isunit(value) or substatus == 1):
                    status = 3
                    queue.append(t)
                elif config["auto_brackets"] and value == "*" and \
                        substatus == 1:
                    status = 1
                    queue.append(t)
                elif substatus == 1 and value == "@":
                    value = "|"
                    l1, c1 = t[3]
                    s = t[-1]
                    offset += 7             # This is OK, tokens1 is empty now
                    newtoks.extend([change_token(t, value),
                                    (tokenize.NAME, u"System", (l1, c1), (l1, c1+6), s),
                                    (tokenize.OP, u"(", (l1, c1+6), (l1, c1+7), s)])
                else:
                    newtoks.extend(queue)
                    queue = []
                    tokens1.appendleft(t)
                    if substatus == 1:
                        l1, c1 = t[3]
                        s = t[-1]
                        newtoks.append((tokenize.OP, u")", (l1, c1+1), (l1, c1+2), s))
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
                if codex == tokenize.NAME and units.isunit(value):
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
                    tokens1 = offset_tokens(tokens1, delta)
                    if substatus == 1:
                        col = queue[-1][3][1]
                        tokens1 = offset_tokens(tokens1, 1)
                        tokens1.appendleft((tokenize.OP, ")",
                                           (t[2][0], col),
                                           (t[2][0], col+1), t[4]))
                        substatus = 0
                        offset += 1
                    status = 0
                    queue = []
            elif status == 4 or status == 8:  # ...12 m / or ...12 m.
                if codex == tokenize.NAME:
                    # Mmh, found a name after a / in a possible unit specification.
                    # Is it really a possible unit or not?  Check...
                    if units.isunit(value):
                        # It is a unit, use it
                        status = 3
                        queue.append(t)
                        continue
                # We did not find a name after a / or the name was not a valid
                # unit.  Put everything back!
                status = 0
                t0 = queue.pop()
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
                if codex == tokenize.NAME and units.isunit(value):
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
        if len(result) >= 2 and result[-1][0] == tokenize.ENDMARKER:
            l1, c1 = result[-2][3]
            result = result[0:-1]
            result.append((tokenize.ENDMARKER, "",  (l1, c1), (l1, c1+1), result[-1][-1]))
    else:
        result = newtoks
    if config["standard_exponent"]:
        result = [(codex, u"**", p1, p2, string) if codex == tokenize.OP and value == "^"
                  else (codex, value, p1, p2, string)
                  for codex, value, p1, p2, string in result]
    if engine:
        uresult = []
        offset = 0
        for t in result:
            t = offset_token(t, offset)
            if t[0] == tokenize.NUMBER and \
                (t[1].find(".") >= 0 or t[1].find("e") >= 0 or
                 t[1].find("E") >= 0 or
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
    # @@@DEBUG
    # for t in result:
    #     print(t)
    return result


######################################################################
# Transformer wrappers

try:
    unicode
except NameError:
    # noinspection PyShadowingBuiltins
    unicode = str


def transform(code):
    # We should probably add a command_transformer call here?
    tokens = tokenize.generate_tokens(StringIO(unicode(code.strip())).readline)
    return tokenize.untokenize(unit_transformer(list(tokens)))
