# -*- coding: utf-8 -*-

from __future__ import division
from collections import OrderedDict as ODict
import traceback, re, types, mpmath
from mpmath import mpmathify, mp
from mpmath.libmp import to_str, mpc_to_str
from xdict import xdict

class Doc(object):
    tdict = {}
    def __init__(self, s=""):
        self.doc = s

    def __rand__(self, x):
        try:
            x.__doc__ = self.doc
        except AttributeError:
            # The standard type does not allow __doc__: create a new derived
            # type, if this has not done already
            if x.__class__ not in self.tdict:
                self.tdict[x.__class__] = type(x.__class__.__name__ + "_w_doc",
                                               (x.__class__,), {})
            x = self.tdict[x.__class__](x)
            x.__doc__ = self.doc
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
        if len(args) == 1 and isinstance(args[0], (str, unicode)):
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
        for n, u in self.iteritems():
            r[n] = u
        return r
    
    def toTuple(self):
        """Return a tuple representation of the unit.

        This function should *not* be called for units stored in normal form."""
        return tuple(x for x in self.iteritems())

    def __nonzero__(self):
        """Check if a unit is zero, i.e. if it represent a pure number."""
        for n, u in self.iteritems():
            if u != 0: return True
        return False

    def __eq__(self, y):
        s = set(self.keys() + y.keys())
        for n in s:
            if self.get(n, 0) != y.get(n, 0): return False
        return True

    def __ne__(self, y):
        return not self.__eq__(y)

    def sort(self):
        pos = []
        neg = []
        for u, n in self.iteritems():
            if n > 0: pos.append((u, n))
            elif n < 0: neg.append((u, n))
        return Unit(pos + neg)
        
    def show(self, latex=False):
        unit = []
        if mp.prec < 53:
            lastprec = mp.prec
            mp.prec = 53
        else: lastprec = False
        for n, u in self.iteritems():
            if u == 0: continue
            if isinstance(n, (str, unicode)):
                base = n
                if base.find(' ') >= 0 or base.find('^') >= 0 or \
                    base.find('/') >= 0:
                    base = '(' + base + ')'
            elif isinstance(n, tuple):
                base = Unit(ODict(n)).show(latex=latex).strip(" []")
                if len(n) > 1 or mpmath.chop(n[0][1] - 1) != 0:
                    base = '(' + base + ')'
            else: base = baseunits[n]
            base = ''.join(re.sub(r"\s*/\s*", "/", base))
            base = ''.join(re.sub(r"\s*\^\s*", "^", base))
            if latex:
                base = r"\mathrm{%s}" % re.sub(r"\s+", "\,", base)
                if mpmath.chop(u - 1) == 0:
                    unit.append(base)
                elif mpmath.chop(u) != 0:
                    p, q = mpmath.pslq([-1, u], tol=1e-5)
                    if q < 0:
                        p = -p
                        q = -q
                    if mpmath.chop(abs(q) - 1) == 0:
                        unit.append("%s{}^{%d}" % (base, p))
                    else: unit.append("%s{}^{%d/%d}" % (base, p, q))
            else:
                if mpmath.chop(u - 1) == 0: unit.append(base)
                elif mpmath.chop(u) != 0:
                    pq = mpmath.pslq([-1, u], tol=1e-5)
                    if pq: p, q = pq
                    else: p,q = mpmath.pslq([-1, u], tol=1e-5, maxcoeff=10**20)
                    if q < 0:
                        p = -p
                        q = -q
                    if mpmath.chop(abs(q) - 1) == 0:
                        unit.append("%s^%d" % (base, p))
                    else: unit.append("%s^%d/%d" % (base, p, q))
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
        for n, u in self.iteritems():
            r[n] = u * mpmathify(y)
        return r

    def __div__(self, y):
        r = Unit()
        for n, u in self.iteritems():
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
    def __new__(*args, **kw):
        """The new function"""
        return object.__new__(*args, **kw)
        
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
        if isinstance(unit, (str, unicode)):
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
        u1 = y.unit
        if u0 != u1 and (not tolerant or (self.value != 0 and y.value != 0)):
            if where: raise UnitError((u0, u1, where))
            raise UnitError((u0, u1))
        return u0

    def checkPure(self, where=None):
        global tolerant
        value = self.value
        unit = self.unit
        if bool(unit) and (not tolerant or value != 0):
            if where: raise UnitError((unit, Unit(), where))
            raise UnitError((unit, Unit()))
        return value

    def setUnits(self, us):
        """Return a new Value with a different default display unit."""
        global cachedat, sortunits
        s = Value(self)    
        s.showprefix = []
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
            else:
                if u[0] == "*":
                    s.showprefix.extend(prefixes.keys())
                    u = u[1:]
                iu = isunit(u)
                if not iu: raise ValueError("Unknown unit %s" % u)
                if iu[1] == "": s.showprefix.append(u)
                else: us.append(u)
        us = tuple(us)
        oldus = us
        try:
            m, newus = cachedat[tuple(us)]
        except KeyError:
            us = [unityacc.parse(u, lexer=unitlex)[1] for u in us]
            try:
                if len(us) == 1 and not bool(self.unit) and \
                    not bool(Value(1, unicode(us[0]).strip("[] ")).unit):
                    s.showunit = us[0]
                    return s
            except ValueError:
                pass
            maxrank = False
            if len(us) == 0: maxrank = True
            elif len(us) <= len(baseunits):
                m = mpmath.matrix([Value(1, unicode(v).strip("[] ")).unit.toList()
                                   for v in us])
                if abs(mpmath.det(m * m.transpose())) > mpmath.mp.eps:
                    maxrank = True
            if maxrank:
                us = us + [Unit(ODict([(u, 1)])) for u in baseunits]
                newus = []
                n = 0
                while len(newus) < len(baseunits):
                    m = mpmath.matrix([Value(1, unicode(v).strip("[] ")).unit.toList()
                                       for v in newus + [us[n]]])
                    if abs(mpmath.det(m * m.transpose())) > mpmath.mp.eps:
                        newus.append(us[n])
                    n = n + 1
                m = mpmath.matrix([Value(1, unicode(v).strip("[] ")).unit.toList()
                                   for v in newus])
                cachedat[tuple(oldus)] = (m, newus)
            else:
                if not bool(self.unit):
                    s.showunit = None
                    return s
                newus = []
                for u in us:
                    newus.append((u.toTuple(), Value(1, unicode(u).strip("[] "))))
                us = ODict(newus)
                res = None
                for l in range(len(us)):
                    g = s.findCompatible(us, level=l+1)
                    try:
                        res = g.next()
                        break
                    except StopIteration:
                        pass
                if res:
                    if sortunits: s.showunit = res.sort()
                    else: s.showunit = res
                else: s.showunit = None
                return s
        r = mpmath.lu_solve(m.transpose(), mpmath.matrix(s.unit.toList()))
        us = Unit(ODict([(u.toTuple(), v)
                         for u, v in zip(newus, r.transpose().tolist()[0])]))
        if sortunits: s.showunit = us.sort()
        else: s.showunit = us
        return s

    def findCompatible(self, d=None, level=1):
        import itertools
        if d is None: d = units
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
        return unicode(self)

    def __unicode__(self):
        global defaultsystem
        tilde = ""
        if self.showunit is not None:
            if self.absolute:
                at = unicode(self.showunit).strip(" []")
                u0 = Value(0, at)
                if not u0.absolute:
                    tilde = "~"
                    u0 = ~u0
                u1 = Value(1, at, absolute=True)
                value = (self - u0) / (u1 - u0)
            else:
                u0 = Value(1, unicode(self.showunit).strip(" []"))
                if u0.absolute:
                    tilde = "~"
                    u0 = ~u0
                value = self / u0
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
            for u,e in unit.iteritems():
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
                         for k,v in unit.iteritems()])
        return tilde + str(value) + unicode(unit)

    def _repr_pretty_(self, p, cycle):
        p.text(unicode(self))

    def _repr_latex_(self):
        global defaultsystem
        tilde = ""
        mytilde = r"\sim\!"
        if self.showunit is not None:
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
            for u,e in unit.iteritems():
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
                         for k,v in unit.iteritems()])
        u = unit.show(latex=True)
        if u: u = r"\," + u
        v = str(value)
        i = v.find("e")
        if i >= 0:
            return "$" + tilde + v[0:i] + r" \times 10^{" + v[i+1:] + "}" + u + "$"
        else: 
            return "$" + tilde + str(value) + u + "$"

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
        return Value(self.value < y.value, {})

    def __le__(self, y):
        if not isinstance(y, Value): y = Value(y)
        self.checkUnits(y)
        return Value(self.value <= y.value, {})

    def __gt__(self, y):
        if not isinstance(y, Value): y = Value(y)
        self.checkUnits(y)
        return Value(self.value > y.value, {})

    def __ge__(self, y):
        if not isinstance(y, Value): y = Value(y)
        self.checkUnits(y)
        return Value(self.value >= y.value, {})

    def __eq__(self, y):
        if not isinstance(y, Value): y = Value(y)
        self.checkUnits(y)
        return Value(self.value == y.value, {})

    def __ne__(self, y):
        if not isinstance(y, Value): y = Value(y)
        self.checkUnits(y)
        return Value(self.value != y.value, {})

    def __nonzero__(self):
        return bool(self.value)

    def __cmp__(self, y):
        self.checkUnits(y)
        return cmp(self.value, y.value)

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
            ssarg = sarg.strip("*")
            self.repr.append(sarg)
            if systems.has_key(ssarg):
                self.args.extend(systems[ssarg].args)
                if sarg[0] == "*" or sarg[-1] == "*": self.args.append("*")
            else:
                self.args.append(sarg)
        self.args = tuple(self.args)

    def __repr__(self):
        return repr(["[" + u + "]" for u in self.repr])

    def _repr_latex_(self):
        return repr(["[" + u + "]" for u in self.repr])

    def __str__(self):
        return repr(self)

    def __ror__(self, expr):
        doc = self.doc
        self.doc = None
        if isinstance(expr, (tuple, list)):
            result = expr.__class__(x | self for x in expr)
        elif isinstance(expr, dict):
            result = expr.__class__([(k, v | self) for k, v in expr.iteritems()])
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

import lex

# List of token names.   This is always required
tokens = (
    'UNIT',
    'NUMBER',
    'NUMDIV',
    'UNITDIV',
    'POW',
    'DOT',
    'LPAREN',
    'RPAREN'
    )

# Regular expression rules for simple tokens
t_UNIT    = ur'((°\w*|\w*(\$|¢|₥|₠|€|₣|₤|£|₧|₱|¥|৲|৳|૱|௹|฿|៛|﷼|₡|₢|₦|₨|₩|₪|₫|₭|₮|₯|₰|∞|∑)\B)|(?:(?!\d)\w)+\*?)'
t_NUMDIV  = r'/(?=[ \t]*\d)'
t_UNITDIV = r'/(?=[ \t]*\D)'
t_POW     = r'\^'
t_DOT     = r'\.'
t_LPAREN  = r'\('
t_RPAREN  = r'\)'

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
    '''expression : expression POW exponent
                  | unit_exp
                  | expression expression
                  | expression DOT expression
                  | expression UNITDIV expression
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
    else:
        a = p[1][0]
        b = p[3][0]
        if isinstance(a, tuple): a = a[1]
        if isinstance(b, tuple): b = b[1]
        p[0] = (a / b, p[1][1] - p[3][1])

def p_expression_group(p):
    'expression : LPAREN expression RPAREN'
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
    'unit : UNIT'
    global prefixonly
    if units.has_key(p[1]):
        p[0] = (units[p[1]], Unit({p[1]: 1}))
    else:
        ks = [k for k in prefixes.keys() if k == p[1][:len(k)]]
        for k in ks:
            u = p[1][len(k):]
            if units.has_key(u):
                if isinstance(units[u], tuple):
                    p[0] = ((units[u][0], prefixes[k] * units[u][1]), Unit({p[1]: 1}))
                else:
                    p[0] = (prefixes[k] * units[u], Unit({p[1]: 1}))
                return
        if prefixonly and prefixes.has_key(p[1]):
            p[0] = (Value(prefixes[p[1]]), Unit({p[1]: 1}))
        elif p[1][-1] == "*" and prefixes.has_key(p[1][0:-1]):
            p[0] = (Value(prefixes[p[1][0:-1]]), Unit({p[1]: 1}))
        else: raise ValueError("Unrecognized unit %s" % p[1])

    

def p_error(p):
    while 1:
        tok = yacc.token()             # Get the next token
        if not tok: break
    yacc.restart()
    raise SyntaxError("unix syntax at '%s'" % p.value)
    
import yacc
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
    import currencies
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
    if units.has_key(name): return ("", name)
    elif prefixonly and prefixes.has_key(name):
        return (name, "")
    elif name[-1] == "*" and not prefixes.has_key(name[0:-1]):
        return (name[0:-1], "")
    else:
        ks = [k for k in prefixes.keys()
              if k == name[:len(k)]]
        for k in ks:
            u = name[len(k):]
            if units.has_key(u):
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

baseunits = []
units = ODict()
prefixes = ODict()
systems = ODict()
defaultsystem = None
cachedat = {}
newprefix("", 1)

def load_variables(ip):
    global baseunits, units, prefixes, systems
    ip.user_ns['Doc'] = Doc
    ip.user_ns['Unit'] = Unit
    ip.user_ns['Value'] = Value
    ip.user_ns['System'] = System
    ip.user_ns['baseunits'] = baseunits
    ip.user_ns['units'] = units
    ip.user_ns['prefixes'] = prefixes
    ip.user_ns['systems'] = systems
    ip.user_ns['defaultsystem'] = defaultsystem

def reset():
    global baseunits, units, prefixes, systems, defaultsystem, cachedat
    baseunits = []
    units = ODict()
    prefixes = ODict()
    systems = ODict()
    defaultsystem = None
    cachedat = {}
    newprefix("", 1)
    
