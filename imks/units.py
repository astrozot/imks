# -*- coding: utf-8 -*-

from __future__ import division
from collections import OrderedDict as ODict
import traceback, re, types, mpmath
from mpmath import mpmathify, mp
from mpmath.libmp import to_str, mpc_to_str
from .xdict import xdict

def make_object_w_doc(value, doc="", source=""):
    c = type(value.__class__.__name__ + "_w_doc",
             (value.__class__,),
             {"__doc__": doc, "__source__": source,
              "__reduce__": lambda s: (make_object_w_doc, (value, doc, source))})
    return c(value)
make_object_w_doc.__safe_for_unpickling__ = True

class Doc(object):
    tdict = {}
    def __init__(self, doc="", source=""):
        self.doc = doc
        self.source = source

    def __rand__(self, x):
        try:
            if self.doc: x.__doc__ = self.doc
            if self.source: x.__source__ = self.source
        except AttributeError:
            x = make_object_w_doc(x, self.doc, self.source)
        return x


class UnitError(Exception):
    def __init__(self, u):
        self.u1 = u[0]
        self.u2 = u[1]
        if len(u) > 2: self.fn = u[2]
        else: self.fn = traceback.extract_stack()[-2][2]
        if self.fn == "checkUnits" or self.fn == "checkPure":
            self.fn = traceback.extract_stack()[-3][2]
        
    def __str__(self):
        return "%s incompatible with %s in %s" % \
               (str(self.u1) or "[]", str(self.u2) or "[]", self.fn)


class Unit(ODict):
    """A unit representation.

    Units are stored as ordered dictionaries where the key represent a simple
    unit, and the value is the exponent.  Two representations are used:

    1. Keys can be simple integers, indicating the respective baseunit: this is the
       normal form for units.

    2. Keys can be tuples of the format ((u1, exp1), (u2, exp2), ...): this form is
       used for unit transformations and is interpreted as (u1^exp1 u2^exp2 ...)."""

    def __init__(self, *args, **kw):
        if len(args) == 1 and isinstance(args[0], str):
            unit = Unit()
            if not re.match(r"^[ \t]*$", args[0]):
                tmp = unityacc.parse(args[0], lexer=unitlex)[0]
                if isinstance(tmp, tuple):
                    unit += tmp[1].unit
                else:
                    unit += tmp.unit
            ODict.__init__(self, unit)
        else:
            ODict.__init__(self, *args, **kw)
    
    def toList(self):
        """Return a list representation of the unit.

        This function should only be called for units stored in normal form."""
        r = [0] * len(baseunits)
        for n, u in self.items():
            r[n] = u
        return r
    
    def toTuple(self):
        """Return a tuple representation of the unit.

        This function should *not* be called for units stored in normal form."""
        return tuple(x for x in self.items())

    def __bool__(self):
        """Check if a unit is zero, i.e. if it represent a pure number."""
        for n, u in self.items():
            if u != 0: return True
        return False

    def __eq__(self, y):
        s = set(self.keys() | y.keys())
        for n in s:
            if self.get(n, 0) != y.get(n, 0): return False
        return True

    def __ne__(self, y):
        return not self.__eq__(y)

    def sort(self):
        pos = []
        neg = []
        for u, n in self.items():
            if n > 0: pos.append((u, n))
            elif n < 0: neg.append((u, n))
        return Unit(pos + neg)

    def getValue(self):
        global user_ns
        v = Value(1.0)
        for n, u in self.items():
            if u == 0: continue
            if isinstance(n, str):
                if n[0] != "'" or n[-1] != "'": continue
                v *= user_ns[n[1:-1]] ** u
        return v
        
    def show(self, latex=False):
        unit = []
        if mp.prec < 53:
            lastprec = mp.prec
            mp.prec = 53
        else: lastprec = False
        for n, u in self.items():
            if u == 0: continue
            if isinstance(n, str):
                if n[0] == '"' and n[-1] == '"': continue
                if latex:
                    if n[0] == n[-1] and n[0] == "'": base = r"\mathbf{%s}" % n[1:-1]
                    else: base = r"\mathrm{%s}" % n
                else: base = n
                if base.find(' ') >= 0 or base.find('^') >= 0 or \
                    base.find('/') >= 0:
                    base = '(' + base + ')'
            elif isinstance(n, tuple):
                base = Unit(ODict(n)).show(latex=latex).strip(" []")
                if len(n) > 1 or mpmath.chop(n[0][1] - 1) != 0:
                    base = '(' + base + ')'
            else:
                if latex: base = r"\mathrm{%s}" % baseunits[n]
                else: base = baseunits[n]
            base = ''.join(re.sub(r"\s*/\s*", "/", base))
            base = ''.join(re.sub(r"\s*\^\s*", "^", base))
            # if latex: base = r"\mathrm{%s}" % re.sub(r"\s+", "\,", base)
            if mpmath.chop(u - 1) == 0: unit.append(base)
            elif mpmath.chop(u) != 0:
                pq = mpmath.pslq([-1, u], tol=1e-5)
                if pq: p, q = pq
                else: p, q = mpmath.pslq([-1, u], tol=1e-5, maxcoeff=10**20)
                if q < 0:
                    p = -p
                    q = -q
                if latex:
                    if mpmath.chop(abs(q) - 1) == 0:
                        unit.append("%s{}^{%d}" % (base, p))
                    else:
                        unit.append("%s{}^{%d/%d}" % (base, p, q))
                else:
                    if mpmath.chop(abs(q) - 1) == 0:
                        unit.append("%s^%d" % (base, p))
                    else:
                        unit.append("%s^%d/%d" % (base, p, q))
        if lastprec: mp.prec = lastprec
        if len(unit) == 0 or (len(unit) == 1 and not unit[0]): return ""
        elif len(unit) == 1 and unit[0][0] == '(' and unit[0][-1] == ')':
            return "[%s]" % unit[0][1:-1]
        else:
            if latex: return "[%s]" % r"\,".join(unit)
            else: return "[%s]" % " ".join(unit)
            
    def __str__(self):
        return self.show()

    def _repr_latex_(self):
        return '$' + self.show(latex=True) + '$'

    def __add__(self, y):
        r = self.copy()
        for n in y:
            r[n] = r.get(n, 0) + y[n]
        return r

    def __sub__(self, y):
        r = self.copy()
        for n in y:
            r[n] = r.get(n, 0) - y[n]
        return r

    def __mul__(self, y):
        r = Unit()
        for n, u in self.items():
            r[n] = u * mpmathify(y)
        return r

    def __div__(self, y):
        r = Unit()
        for n, u in self.items():
            r[n] = u / mpmathify(y)
        return r

    def __truediv__(self, y):
        return self.__div__(y)

    def __radd__(self, y):
        return self.__add__(y)

    def __rsub__(self, y):
        return y.__sub__(self)
    
    def __rmul__(self, y):
        return self.__mul__(y)

    def __rdiv__(self, y):
        return self.__mul__(1.0/y)

    def __rtruediv__(self, y):
        return self.__rdiv__(y)


from mpmath.ctx_mp_python import mpnumeric
class Value(mpnumeric):
    def __new__(cls, *args, **kw):
        """The new function"""
        return object.__new__(cls)
        
    def __init__(self, value, unit={}, absolute=None, original=False):
        if isinstance(value, Value):
            self.value = value.value
            self.unit = value.unit
            self.absolute = bool(value.absolute or absolute)
            self.showunit = value.showunit
            self.showprefix = value.showprefix
            self.offset = value.offset
        else:
            self.value = value
            self.unit = Unit()
            self.absolute = bool(absolute)
            self.showunit = None
            self.showprefix = False
            self.offset = 0
        if isinstance(unit, str):
            if not re.match(r"^[ \t]*$", unit): 
                tmp, uparse = unityacc.parse(unit, lexer=unitlex)
                if isinstance(tmp, tuple):
                    self.value *= tmp[1].value
                    if absolute is None or self.absolute:
                        self.value += tmp[0].value
                        self.absolute = True
                    self.offset = tmp[0].value
                    self.unit += tmp[1].unit
                else:
                    self.value *= tmp.value
                    self.unit += tmp.unit
                if original:
                    self.showunit = Unit({uparse.toTuple(): 1.0})
        else:
            self.unit += Unit(unit)

    def checkUnits(self, y, where=None):
        global tolerant
        u0 = self.unit
        if isinstance(y, Value):
            u1 = y.unit
            if u0 != u1 and (not tolerant or (self.value != 0 and y.value != 0)):
                if where: raise UnitError((u0, u1, where))
                raise UnitError((u0, u1))
        else:
            self.checkPure(where=where)
        return u0

    def checkPure(self, where=None):
        global tolerant
        value = self.value
        unit = self.unit
        if bool(unit) and (not tolerant or value != 0):
            if where: raise UnitError((unit, Unit(), where))
            raise UnitError((unit, Unit()))
        return value

    def removeVariableUnits(self):
        """Remove double quoted units from the showunit part of a Value, also changing the
        value."""
        global user_ns
        variables = None
        f = Value(1)
        newshowunit = Unit()
        for k,v in self.showunit.items():
            if k[0] == '"' and k[-1] == '"':
                if variables is None: variables = user_ns
                f *= variables[k[1:-1]] ** v
            else:
                newshowunit[k] = v
        r = self / f
        r.showunit = newshowunit
        r.showprefix = self.showprefix
        r.absolute = self.absolute
        r.offset = self.offset / f
        return r

    def setUnits(self, us):
        """Return a new Value with a different default display unit."""
        global cachedat, sortunits, formats, user_ns
        nunits = 0
        nvalues = 0
        s = Value(self)
        s.showprefix = []
        if len(us) == 1 and us[0] in formats:
            s.showunit = formats[us[0]]
            return s
        oldus = us
        us = []
        for u in oldus:
            if u[-1] == "*":
                if u == "*":
                    s.showprefix.extend(prefixes.keys())
                else:
                    if u[0:-1] not in prefixes:
                        raise ValueError("Unknown prefix %s" % u[0:-1])
                    s.showprefix.append(u[0:-1])
            elif u == ".":
                s.showprefix.append("")
            elif u[0] in ("'", '"') and u[0] == u[-1]:
                us.append(u)
                nvalues += 1
            else:
                if u[0] == "*":
                    s.showprefix.extend(prefixes.keys())
                    u = u[1:]
                iu = isunit(u)
                if iu and iu[1] == "": s.showprefix.append(u)
                else:
                    nunits += 1
                    us.append(u)
        us = tuple(us)
        oldus = us
        try:
            m, newus, newvs = cachedat[tuple(us)]
        except KeyError:
            us = []
            vs = []
            for u in oldus:
                if u[0] in ("'", '"') and u[0] == u[-1]:
                    us.append(u)
                    vs.append(user_ns[u[1:-1]])
                else:
                    up = unityacc.parse(u, lexer=unitlex)
                    us.append(up[1])
                    # Take care of absolute units
                    if isinstance(up[0], tuple): vs.append(up[0][1])
                    else: vs.append(up[0])
            try:
                if len(us) == 1 and not bool(self.unit) and \
                    not bool(vs[0].unit):
                    s.showunit = us[0]
                    return s
            except ValueError:
                pass
            maxrank = False
            if len(us) == 0: maxrank = True
            elif len(us) <= len(baseunits):
                m = mpmath.matrix([v.unit.toList() for v in vs])
                if abs(mpmath.det(m * m.transpose())) > mpmath.mp.eps:
                    maxrank = True
            if maxrank:
                us = us + [Unit(ODict([(u, 1)])) for u in baseunits]
                vs = vs + [Value(1, Unit(ODict([(n, 1)])))
                           for n,_ in enumerate(baseunits)]
                newus = []
                newvs = []
                n = 0
                while len(newus) < len(baseunits):
                    m = mpmath.matrix([v.unit.toList() for v in newvs + [vs[n]]])
                    if abs(mpmath.det(m * m.transpose())) > mpmath.mp.eps:
                        newus.append(us[n])
                        newvs.append(vs[n])
                    n = n + 1
                m = mpmath.matrix([v.unit.toList() for v in newvs])
                cachedat[tuple(oldus)] = (m, newus, newvs)
            else:
                # Check if we are requested a particular unit in a natural system
                if nunits == 1 and nvalues > 0 and not isinstance(us[0], str):
                    tmp = Value(1, oldus[0]).setUnits([oldus[0]])
                    out = (self / tmp).setUnits(oldus[1:])
                    out.showunit += tmp.showunit
                    out.unit += tmp.unit
                    out.value *= tmp.value
                    return out
                # Deal with a pure number in the other cases: no transformation is done
                if not bool(self.unit):
                    s.showunit = None
                    return s
                # General simple case
                newuvs = zip([u if isinstance(u, str) else u.toTuple()
                              for u in us], vs)
                uvs = ODict(newuvs)
                res = None
                for l in range(len(uvs)):
                    g = s.findCompatible(uvs, level=l+1)
                    try:
                        res = next(g)
                        break
                    except StopIteration:
                        pass
                if res:
                    if sortunits: s.showunit = res.sort()
                    else: s.showunit = res
                else: s.showunit = None
                return s.removeVariableUnits()
        r = mpmath.lu_solve(m.transpose(), mpmath.matrix(s.unit.toList()))
        uvs = Unit(ODict([(u if isinstance(u, str) else u.toTuple(), v)
                         for u, v in zip(newus, r.transpose().tolist()[0])]))
        if sortunits: s.showunit = uvs.sort()
        else: s.showunit = uvs
        return s.removeVariableUnits()

    def findCompatible(self, d=None, level=1):
        import itertools
        if d is None: d = units
        if level == 0:
            for k,v in d.items():
                if isinstance(v, Value) and v.unit == self.unit and \
                  abs(v - self).value == 0:
                    yield k
        else:
            ks = d.keys()
            nk = len(ks)
            u0 = mpmath.matrix(self.unit.toList())
            for c in itertools.combinations(ks, abs(level)):
                js = []
                M = mpmath.matrix(len(baseunits), abs(level))
                for l,cu in enumerate(c):
                    if isinstance(d[cu], tuple): u = d[cu][0].unit.toList()
                    else: u = d[cu].unit.toList()
                    js.append(cu)
                    M[:, l] = mpmath.matrix(u)
                try:
                    if level > 0: x = mpmath.lu_solve(M, u0)
                    else: x = mpmath.ones(abs(level), 1)
                    r = mpmath.norm(M*x - u0)
                except ValueError:
                    continue
                if r < mpmath.eps and min(map(abs, x)) > 1e-5:
                    u = Unit(ODict(zip(js, x)))
                    yield u
        
    def __repr__(self):
        return self.__str__()

    def __str__(self):
        global defaultsystem
        tilde = ""
        if self.showunit is not None:
            if callable(self.showunit):
                return self.showunit(self)
            if self.absolute:
                at = str(self.showunit).strip(" []")
                u0 = Value(0, at)
                if not u0.absolute:
                    tilde = "~"
                    u0 = ~u0
                u1 = Value(1, at, absolute=True)
                value = ((self - u0) / (u1 - u0)).value
            else:
                u0 = Value(1, str(self.showunit).strip(" []"))
                if u0.absolute:
                    tilde = "~"
                    u0 = ~u0
                value = (self / u0).value
            unit = self.showunit
        elif defaultsystem and self.unit:
            return str(Value(self).setUnits(defaultsystem.args))
        else:
            value = self.value
            unit = self.unit
            u0 = Value(0, str(self.unit).strip(" []"))
            if (u0.absolute ^ self.absolute): tilde = "~"
        if self.showprefix:
            myunit = None
            for u,e in unit.items():
                if len(u) == 1 and u[0][1] == 1 and e != 0:
                    myunit = u[0][0]
                    myexp  = e
                    break
            if myunit is not None:
                fprefix = isunit(myunit)[0]
                if fprefix:
                    value = value * prefixes[fprefix]**myexp
            else:
                myunit = "" if prefixonly else "*"
                myexp = 1
                fprefix = ""
                unit = Unit([(((myunit, 1),), 1)])
            avalue = abs(value)
            dexes = [(k, avalue / prefixes[k]**myexp)
                     for k in self.showprefix \
                     if prefixes[k]**myexp <= avalue and \
                        (myunit != "" or k not in units)]
            if not dexes:
                dexes = [(k, -avalue / prefixes[k]**myexp)
                         for k in self.showprefix
                         if myunit != "" or k not in units]
            dex, best = min(dexes, key=lambda x: x[1])
            if dex: value = value / prefixes[dex]**myexp
            unit = Unit([(k,v) if k != ((myunit, 1),) else
                         (((dex + myunit[len(fprefix):], 1),), v)
                         for k,v in unit.items()])
        v = str(value)
        u = str(unit)
        if v.find(r"+/-") >= 0 and v.find("(") < 0 and u: v = "(" + v + ")"
        return tilde + v + u

    def _repr_pretty_(self, p, cycle):
        if self.showunit is not None and callable(self.showunit):
            p.text(self.showunit(self, pretty=True))
        else:
            p.text(str(self))

    def _repr_latex_(self):
        global defaultsystem
        tilde = ""
        mytilde = r"\sim\!"
        if self.showunit is not None:
            if callable(self.showunit):
                return self.showunit(self, latex=True)
            if self.absolute:
                at = str(self.showunit).strip(" []")
                u0 = Value(0, at)
                if not u0.absolute:
                    tilde = mytilde
                    u0 = ~u0
                u1 = Value(1, at, absolute=True)
                value = (self - u0) / (u1 - u0)
            else:
                u0 = Value(1, str(self.showunit).strip(" []"))
                if u0.absolute:
                    tilde = mytilde
                    u0 = ~u0
                value = self / u0
            unit = self.showunit
        elif defaultsystem and self.unit:
            return Value(self).setUnits(defaultsystem.args)._repr_latex_()
        else:
            value = self.value
            unit = self.unit
            u0 = Value(0, str(self.unit).strip(" []"))
            if (u0.absolute ^ self.absolute): tilde = mytilde
        if self.showprefix:
            myunit = None
            for u,e in unit.items():
                if len(u) == 1 and u[0][1] == 1 and e != 0:
                    myunit = u[0][0]
                    myexp  = e
                    break
            if myunit is not None:
                fprefix = isunit(myunit)[0]
                if fprefix:
                    value = value * prefixes[fprefix]**myexp
            else:
                myunit = "" if prefixonly else "*"
                myexp = 1
                fprefix = ""
                unit = Unit([(((myunit, 1),), 1)])
            avalue = abs(value)
            dexes = [(k, avalue / prefixes[k]**myexp)
                     for k in self.showprefix \
                     if prefixes[k]**myexp <= avalue and \
                        (myunit != "" or k not in units)]
            if not dexes:
                dexes = [(k, -avalue / prefixes[k]**myexp)
                         for k in self.showprefix
                         if myunit != "" or k not in units]
            dex, best = min(dexes, key=lambda x: x[1])
            if dex: value = value / prefixes[dex]**myexp
            unit = Unit([(k,v) if k != ((myunit, 1),) else
                         (((dex + myunit[len(fprefix):], 1),), v)
                         for k,v in unit.items()])
        u = unit.show(latex=True)
        if u: u = r"\," + u
        if hasattr(value, "_repr_latex_"): v = value._repr_latex_()
        else:
            v = str(value)
            i = v.find("e")
            if i >= 0: v = r"$%s \times 10^{%s}$" % (v[0:i], v[i+1:])
            v = v.replace("+/-", r" \pm ")
        if v[0] == '$' and v[-1] == '$': v = v[1:-1]
        if v.find(r"\pm") >= 0 and v.find("(") < 0 and u: v = "(" + v + ")"
        return "$" + tilde + v + u + "$"

    def __coerce__(self, y):
        if y.__class__ != Value: y = Value(y)
        return (self, y)

    # Standard binary operators

    def __add__(self, y):
        if not isinstance(y, Value): y = Value(y)
        unit = self.checkUnits(y)
        if self.absolute and y.absolute:
            raise ValueError("Cannot add two absolute values")
        return Value(self.value + y.value, unit,
                     absolute=self.absolute or y.absolute)

    def __sub__(self, y):
        if not isinstance(y, Value): y = Value(y)
        unit = self.checkUnits(y)
        if not self.absolute and y.absolute:
            raise ValueError("Cannot subtract an absolute value from a relative one")
        return Value(self.value - y.value, unit,
                     absolute=self.absolute and not y.absolute)
    
    def __mul__(self, y):
        if not isinstance(y, Value): y = Value(y)
        return Value(self.value * y.value, self.unit + y.unit)

    def __div__(self, y):
        if not isinstance(y, Value): y = Value(y)
        return Value(self.value / y.value, self.unit - y.unit)

    def __truediv__(self, y):
        if not isinstance(y, Value): y = Value(y)
        return Value(self.value / y.value, self.unit - y.unit)

    def __floordiv__(self, y):
        if not isinstance(y, Value): y = Value(y)
        return Value(floor(self.value / y.value), self.unit - y.unit)

    def __divmod__(self, y):
        if not isinstance(y, Value): y = Value(y)
        unit = self.unit - y.unit
        d, m = divmod(self.value, y.value)
        return (Value(d, unit), Value(m, unit))

    def __pow__(self, y, modulo=None):
        if not isinstance(y, Value): y = Value(y)
        yvalue = y.checkPure()
        return Value(pow(self.value, yvalue, modulo), self.unit * yvalue)

    def __round__(self, n=None):
        return Value(round(self.value, n), self.unit, absolute=self.absolute)

    def __and__(self, y):
        if isinstance(y, Doc): return y.__rand__(self)
        else: return self.value & y.value

    def __or__(self, y):
        if isinstance(y, System): return y.__ror__(self)
        elif not isinstance(y, Value): y = Value(y)
        return self.value | y.value

    def __xor__(self, y):
        return self.value ^ y.value

    # Comparison operators

    def __lt__(self, y):
        if not isinstance(y, Value): y = Value(y)
        self.checkUnits(y)
        return self.value < y.value

    def __le__(self, y):
        if not isinstance(y, Value): y = Value(y)
        self.checkUnits(y)
        return self.value <= y.value

    def __gt__(self, y):
        if not isinstance(y, Value): y = Value(y)
        self.checkUnits(y)
        return self.value > y.value

    def __ge__(self, y):
        if not isinstance(y, Value): y = Value(y)
        self.checkUnits(y)
        return self.value >= y.value

    def __eq__(self, y):
        if not isinstance(y, Value): y = Value(y)
        self.checkUnits(y)
        return self.value == y.value

    def __ne__(self, y):
        if not isinstance(y, Value): y = Value(y)
        self.checkUnits(y)
        return self.value != y.value

    def __bool__(self):
        return bool(self.value)

    # Reverse methods

    __radd__ = __add__

    def __rsub__(self, y):
        if not isinstance(y, Value): y = Value(y)
        unit = self.checkUnits(y)
        if not self.absolute and y.absolute:
            raise ValueError("Cannot subtract an absolute value from a relative one")
        return Value(y.value - self.value, unit,
                     absolute=y.absolute and not self.absolute)

    __rmul__ = __mul__

    def __rdiv__(self, y):
        if not isinstance(y, Value): y = Value(y)
        return Value(y.value / self.value, y.unit - self.unit)

    __rtruediv__ = __rdiv__

    def __rfloordiv__(self, y):
        if not isinstance(y, Value): y = Value(y)
        return Value(floor(y.value / self.value), y.unit - self.unit)

    def __rmod__(self, y):
        if not isinstance(y, Value): y = Value(y)
        return Value(y.value % self.value, y.unit - self.unit)

    def __rdivmod__(self, y):
        if not isinstance(y, Value): y = Value(y)
        unit = y.unit - self.unit
        d, m = divmod(y.value, self.value)
        return (Value(d, unit), Value(m, unit))

    def __rpow__(self, y):
        value = self.checkPure()
        if not isinstance(y, Value): y = Value(y)
        return Value(pow(y.value, value), y.unit * value)

    __rand__ = __and__

    __ror__ = __or__

    __rxor__ = __xor__

    # Unary operators

    def __pos__(self):
        return self

    def __neg__(self):
        if self.absolute:
            return Value(self.offset*2 - self.value, self.unit, absolute=True)
        else:
            return Value(-self.value, self.unit)

    def __abs__(self):
        return Value(abs(self.value), self.unit)

    def __invert__(self):
        if self.absolute:
            return Value(self.value - self.offset, self.unit, absolute=False)
        else:
            return Value(self.value + self.offset, self.unit, absolute=True)

    def __int__(self):
        return int(self.checkPure())

    def __long__(self):
        return long(self.checkPure())

    def __index__(self):
        import operator
        return operator.index(self.checkPure())

    def __trunc__(self):
        return Value(self.value.__trunc__(), self.unit)

    def __float__(self):
        return float(self.checkPure())

    def __complex__(self):
        return complex(self.checkPure())

    def _mpmath_(self, prec, rounding):
        return mpmathify(self.checkPure())

    def __oct__(self):
        return oct(self.checkPure())

    def __hex__(self):
        return hex(self.checkPure())

class System(object):
    def __init__(self, *args):
        global systems
        self.args = []
        self.repr = []
        self.doc  = ""
        for arg in args:
            sarg = arg.strip("[] ")
            self.repr.append(sarg)
            ssarg = sarg.strip("*")
            if len(ssarg) > 0 and ssarg[0] in ('"', "'") and ssarg[0] == ssarg[-1] and \
              ssarg[1:-1].find(ssarg[0]) < 0:
                sssarg = ssarg[1:-1]
                quote = ssarg[0]
            else:
                sssarg = ssarg
                quote = ""
            if sssarg in systems:
                tmp = systems[sssarg].args
                if quote == "'": tmp = [a.replace("\"", "'") for a in tmp]
                if quote == '"': tmp = [a.replace("'", "\"") for a in tmp]
                self.args.extend(tmp)
                if sarg[0] == "*" or sarg[-1] == "*": self.args.append("*")
            else:
                self.args.append(sarg)
        self.args = tuple(self.args)

    def __repr__(self):
        return repr(["[" + u + "]" for u in self.repr])

    def _repr_latex_(self):
        return repr(["[" + u + "]" for u in self.repr])

    def __str__(self):
        return "[%s]" % ", ".join(self.repr)

    def __ror__(self, expr):
        doc = self.doc
        self.doc = None
        if isinstance(expr, (tuple, list)):
            result = expr.__class__(x | self for x in expr)
        elif isinstance(expr, dict):
            result = expr.__class__([(k, v | self) for k, v in expr.items()])
        elif isinstance(expr, Value):
            result = expr.setUnits(self.args)
        else:
            result = Value(expr).setUnits(self.args)
        self.doc = doc
        if doc: return doc.__rand__(result)
        else: return result

    def __and__(self, y):
        if isinstance(y, Doc):
            self.doc = y
            return self
        else: return self.value & y.value
            
class LazyValue(Value):
    """A variable whose value is calculated lazy when required."""
    def __init__(self, expression, globals=None, locals=None, once=False,
                 unit_once=True):
        if callable(expression): self.expression = expression
        else: self.expression = lambda: eval(expression, globals, locals)
        self._once = once
        self._unit_once = unit_once
        self._unit_set = False

    def __getattr__(self, attr):
        res = self.expression()
        if not isinstance(res, Value): res = Value(res)
        if self._once:
            self.value = res.value
            self._once = False
        if self._once or self._unit_once:
            self.unit = res.unit
            self.showunit = res.showunit
            self.showprefix = res.showprefix
            self.absolute = res.absolute
            self._unit_once = False
            self._unit_set = True
        elif self._unit_set and self.unit != res.unit:
            raise ValueError("Unit changed for lazy object from [%s] to [%s]" %
                            (str(self.unit).strip("[] "), str(res.unit).strip("[] ")))
        return getattr(res, attr)

######################################################################
# Unit Lexer

from ply import lex, yacc

# List of token names.   This is always required
tokens = (
    'UNIT',
    'NUMBER',
    'NUMDIV',
    'UNITDIV',
    'POW',
    'DOT',
    'LPAREN',
    'RPAREN',
    'QUOTE'
    )

# Regular expression rules for simple tokens
t_UNIT    = r'((°\w*|\w*(\$|¢|₥|₠|€|₣|₤|£|₧|₱|¥|৲|৳|૱|௹|฿|៛|﷼|₡|₢|₦|₨|₩|₪|₫|₭|₮|₯|₰|∞|∑)\B)|(?:(?!\d)\w)+\*?)'
t_NUMDIV  = r'/(?=[ \t]*\d)'
t_UNITDIV = r'/(?=[ \t]*\D)'
t_POW     = r'\^'
t_DOT     = r'\.'
t_LPAREN  = r'\('
t_RPAREN  = r'\)'
t_QUOTE   = r"\'"

# A regular expression rule with some action code
def t_NUMBER(t):
    r'[-+]?\d+(\.\d+)?'
    try:
        t.value = float(t.value)    
    except ValueError:
        raise ValueError("line %d: Number conversion failed for %s " % \
                         (t.lineno, t.value))
        t.value = 0
    return t

# Define a rule so we can track line numbers
def t_newline(t):
    r'\n+'
    t.lineno += len(t.value)

# A string containing ignored characters (spaces and tabs)
t_ignore  = " *\t"

# Error handling rule
def t_error(t):
    raise SyntaxError("Illegal character '%s' in unit '%s'" %
                      (t.value[0], t.lexer.lexdata))

# Build the lexer
unitlex = lex.lex(reflags=re.UNICODE)


######################################################################
# Unit Parser

def p_expression(p):
    '''expression : expression1
                  | expression1 UNITDIV expression1'''
    if len(p) == 2: p[0] = p[1]
    else:
        a = p[1][0]
        b = p[3][0]
        if isinstance(a, tuple): a = a[1]
        if isinstance(b, tuple): b = b[1]
        p[0] = (a / b, p[1][1] - p[3][1])

def p_expression1(p):
    '''expression1 : expression1 POW exponent
                   | unit_exp
                   | expression1 expression1
                   | expression1 DOT expression1
                   | unit'''
    if len(p) == 2: p[0] = p[1]
    elif len(p) == 3: 
        a = p[1][0]
        b = p[2][0]
        if isinstance(a, tuple): a = a[1]
        if isinstance(b, tuple): b = b[1]
        p[0] = (a * b, p[1][1] + p[2][1])
    elif len(p) == 4 and p[2] == '.':
        a = p[1][0]
        b = p[3][0]
        if isinstance(a, tuple): a = a[1]
        if isinstance(b, tuple): b = b[1]
        p[0] = (a * b, p[1][1] + p[3][1])        
    elif len(p) == 4 and p[2] == '^':
        a = p[1][0]
        if isinstance(a, tuple): a = a[1]
        p[0] = (a ** p[3], p[1][1] * p[3])

def p_expression_group(p):
    'expression1 : LPAREN expression RPAREN'
    p[0] = p[2]

def p_exponent(p):
    '''exponent : LPAREN NUMBER NUMDIV NUMBER RPAREN
                | NUMBER NUMDIV NUMBER
                | NUMBER'''
    if len(p) == 6:
        p[0] = mpmath.fraction(p[2], p[4])
    elif len(p) == 4:
        p[0] = mpmath.fraction(p[1], p[3])
    else:
        p[0] = p[1]

def p_unit_exp(p):
    'unit_exp : unit NUMBER'
    a = p[1][0]
    if isinstance(a, tuple): a = a[1]
    p[0] = (a ** p[2], p[1][1] * p[2])

def p_unit(p):
    '''unit : UNIT
            | QUOTE UNIT QUOTE'''
    global prefixonly, user_ns
    if p[1] == "'":
        variables = user_ns
        if p[2] in variables:
            p[0] = (variables[p[2]], Unit({"'" + p[2] + "'": 1}))
        else: raise ValueError("Unrecognized special unit '%s'" % p[2])
        return
    if p[1] in units:
        p[0] = (units[p[1]], Unit({p[1]: 1}))
    else:
        for n in range(1, len(p[1])):
            k = p[1][:n]
            u = p[1][n:]
            if k in prefixes and u in units:
                if isinstance(units[u], tuple):
                    p[0] = ((units[u][0], prefixes[k] * units[u][1]), Unit({p[1]: 1}))
                else:
                    p[0] = (prefixes[k] * units[u], Unit({p[1]: 1}))
                return
        if prefixonly and p[1] in prefixes:
            p[0] = (Value(prefixes[p[1]]), Unit({p[1]: 1}))
        elif p[1][-1] == "*" and p[1][0:-1] in prefixes:
            p[0] = (Value(prefixes[p[1][0:-1]]), Unit({p[1]: 1}))
        else: raise ValueError("Unrecognized unit %s" % p[1])


def p_error(p):
    while 1:
        tok = yacc.token()             # Get the next token
        if not tok: break
    yacc.restart()
    raise SyntaxError("unix syntax at '%s'" % p.value)
    
unityacc = yacc.yacc(write_tables=0, debug=0)

######################################################################
# General use functions

def newbaseunit(name, doc=""):
    global baseunits, units, cachedat
    if name in baseunits:
        raise ValueError("Base unit %s already defined" % name)
    v = Value(1, {len(baseunits): 1})
    v.__doc__ = doc
    units[name] = v
    baseunits.append(name)
    cachedat = {}

def newbasecurrency(name, doc=""):
    from . import currencies
    if name in baseunits:
        raise ValueError("base unit %s already known" % name)
    if currencies.basecurrency is not None:
        raise ValueError("base currency already defined (%s)", currencies.basecurrency)
    currencies.basecurrency = name
    v = Value(1, {len(baseunits): 1})
    v.__doc__ = doc
    units[name] = v
    baseunits.append(name)
    cachedat = {}


def newprefix(name, value, doc="", source=""):
    global prefixes, cachedat
    v = Value(value)
    v.checkPure()
    v.unit = Unit()                     # Just in case tolerant is True...
    if isinstance(value, LazyValue): v = value
    v.__doc__ = doc
    if source: v.__source__ = source
    prefixes[name] = v
    cachedat = {}

def delprefix(name):
    global prefixes
    del prefixes[name]

def newunit(name, value, doc="", source=""):
    global units, cachedat
    if isinstance(value, LazyValue):
        v = value
    else:
        if not isinstance(value, (int, float, Value, tuple, mpnumeric)):
            raise ValueError("The unit %s must be a simple value or a tuple" % name)
        if isinstance(value, tuple):
            if len(value) != 2:
                raise ValueError("The absolute unit `%s` is not a 2-tuple" % name)
            v = (Value(value[0]), Value(value[1]))
            v[0].checkUnits(value[1])
        else: v = Value(value)
    v = v & Doc(doc)
    if source: v.__source__ = source
    units[name] = v
    cachedat = {}

def delunit(name):
    global units
    del units[name]

def newsystem(name, value, doc=""):
    global systems, cachedat
    v = System(*value)
    v.__doc__ = doc
    systems[name] = v
    cachedat = {}

def delsystem(name):
    global systems
    del systems[name]

isunit_re = re.compile("[A-Za-z]+")
def isunit(fullname):
    global prefixonly
    match = isunit_re.match(fullname) 
    if match: name = match.group(0)
    else: name = fullname
    if name in units: return ("", name)
    elif prefixonly and name in prefixes:
        return (name, "")
    elif name[-1] == "*" and not name[0:-1] in prefixes:
        return (name[0:-1], "")
    else:
        ks = [k for k in prefixes.keys()
              if k == name[:len(k)]]
        for k in ks:
            u = name[len(k):]
            if u in units:
                return (k, u)
    return False


######################################################################
# Global variables

# The following parameter controls the so-called zero-value tolerance.
# When enabled, a zero value is sum-compatible with any value: thus
# one can perform operations such as 3[m] + 0[s] without raising any
# error message.  This is useful for functions such as sum: this way
# one can compute expressions such as sum([1[m], 2[m], 3[m]]) instead
# of the slight more complicated way sum([1[m], 2[m], 3[m]], 0[m]).
tolerant = True

# Do we accept a unit composed of a single prefix?  It should be
# probably avoided, especially if used with powers: 3k^2 shouldn't be
# written as 3M or better as 3e6?
prefixonly = True

# Should we sort compount units to display first units with positive
# exponents?
sortunits = True

# Should we show errors and if we do, how are we showing them?
# 0: ignore errors, 1: do not show errors, but use right number of digits
# 2: show errors with +/-
showerrors = 2

baseunits = []
units = ODict()
prefixes = ODict()
systems = ODict()
formats = ODict()
defaultsystem = None
cachedat = {}
newprefix("", 1)
user_ns = {}

def load_variables(ip):
    global baseunits, units, prefixes, systems, formats, defaultsystem, user_ns
    ip.user_ns['Doc'] = Doc
    ip.user_ns['Unit'] = Unit
    ip.user_ns['Value'] = Value
    ip.user_ns['System'] = System
    ip.user_ns['UnitError'] = UnitError
    ip.user_ns['baseunits'] = baseunits
    ip.user_ns['units'] = units
    ip.user_ns['prefixes'] = prefixes
    ip.user_ns['systems'] = systems
    ip.user_ns['formats'] = formats
    ip.user_ns['defaultsystem'] = defaultsystem
    user_ns = ip.user_ns

def save_variables(ip):
    global baseunits, units, prefixes, systems, formats, defaultsystem, user_ns
    baseunits = ip.user_ns['baseunits']
    units = ip.user_ns['units']
    prefixes = ip.user_ns['prefixes']
    systems = ip.user_ns['systems']
    formats = ip.user_ns['formats']
    defaultsystem = ip.user_ns['defaultsystem']
    user_ns = ip.user_ns
    
def reset():
    global baseunits, units, prefixes, systems, formats, defaultsystem, \
      cachedat
    baseunits = []
    units = ODict()
    prefixes = ODict()
    systems = ODict()
    formats = ODict()
    defaultsystem = None
    cachedat = {}
    newprefix("", 1)
    
