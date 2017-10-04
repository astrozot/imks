# -*- coding: utf-8 -*-

import uncertainties
import uncertainties.umath as umath
import math
from .units import Value
from . import units

def umathdoc(f):
    "Decorator to copy the uncertainties.umath __doc__ string."
    f.__doc__ = getattr(umath, f.__name__, {"__doc__": ""}).__doc__
    return f

@umathdoc
def atan2(y, x):
    if isinstance(x, Value) or isinstance(y, Value):
        x1 = Value(x)
        y1 = Value(y)
        x1.checkUnits(y1)
        return umath.atan2(y1.value, x1.value)
    else:
        return umath.atan2(y, x)

@umathdoc
def ceil(x):
    if isinstance(x, Value): return Value(umath.ceil(x.value), x.unit)
    else: return umath.ceil(x)

@umathdoc
def copysign(x, y):
    if isinstance(x, Value) or isinstance(y, Value):
        x1 = Value(x)
        y1 = Value(y)
        return Value(umath.copysign(x1.value, y1.value), x1.unit)
    else:
        return umath.copysign(x, y)
    
@umathdoc
def fabs(x):
    if isinstance(x, Value): return Value(umath.fabs(x.value), x.unit)
    else: return umath.fabs(x)

@umathdoc
def floor(x):
    if isinstance(x, Value): return Value(umath.floor(x.value), x.unit)
    else: return umath.floor(x)

@umathdoc
def fmod(x, y):
    if isinstance(x, Value) or isinstance(y, Value):
        x1 = Value(x)
        y1 = Value(y)
        return Value(umath.fmod(x1.value, y1.value), x1.units - y1.units)
    else:
        return umath.fmod(x, y)

@umathdoc
def hypot(x, y):
    return sqrt(x*x + y*y)

@umathdoc
def isinf(x):
    if isinstance(x, Value): return umath.isinf(x.value)
    else: return umath.isinf(x)

@umathdoc
def isnan(x):
    if isinstance(x, Value): return umath.isnan(x.value)
    else: return umath.isnan(x)

@umathdoc
def modf(x):
    if isinstance(x, Value):
        a, b = umath.modf(x.value)
        return (Value(a, x.unit), Value(b, x.unit))
    else: return umath.modf(x)

@umathdoc
def pow(x, y):
    return x**y

@umathdoc
def sqrt(x):
    if isinstance(x, Value): return Value(umath.sqrt(x.value), x.unit / 2)
    else: return umath.sqrt(x)

def fraction(q, p):
    """Given Python integers `(p, q)`, return the fraction p/q."""
    if isinstance(q, Value) or isinstance(p, Value):
        q1 = Value(q)
        p1 = Value(p)
        return Value(float(q1.value) / float(p1.value),
                     q1.unit - p1.unit)
    else:
        return Value(float(q) / float(p))

def mconvert(f):
    "Decorator for generic one-argument functions"
    g = lambda x: f(x.checkPure(f.__name__)) \
      if isinstance(x, Value) else f(x)
    g.__doc__ = f.__doc__
    return g

def ufloat(s):
    """Convert a number in the format 12.2+/-0.3 into a quantity with error."""
    if s.find("+/-") >= 0 or s.find("(") >= 0 or s.find(u"±") >= 0:
        return uncertainties.ufloat_fromstr(s)
    else: return float(s)

ufloat_str = uncertainties.AffineScalarFunc.__str__
def ufloat_repr(self):
    if units.showerrors == 0: return str(self.nominal_value)
    elif units.showerrors == 1:
        s = ufloat_str(self)
        i = s.find(r")")
        if i >= 0:
            e = s[i+1:]
            s = s[1:i]
        else: e = ""
        i = s.find(r"+/-")
        if i >= 0: return s[0:i] + e
        else: return s + e
    else: return ufloat_str(self)
            
def ufloat_repr_latex(self):
    s = "${" + ufloat_repr(self).replace("+/-", "} \pm {") + "}$"
    return s.replace("e", r"} \times 10^{")

######################################################################
# Load and unload functions

def load(ip):
    "Load all math defined functions, using when appropriate modified versions."
    names = dir(umath)
    globs = globals()
    for name in names:
        if name[0] != '_':
            ip.user_ns[name] = globs.get(name, mconvert(getattr(umath, name)))
    ip.user_ns["fraction"] = fraction
    ip.user_ns["ufloat"] = ufloat
    ip.user_ns["pi"] = math.pi
    ip.user_ns["e"] = math.e
    uncertainties.AffineScalarFunc.__repr__ = uncertainties.AffineScalarFunc.__str__
    uncertainties.AffineScalarFunc.__repr__ = ufloat_repr
    uncertainties.AffineScalarFunc.__str__ = ufloat_repr
    uncertainties.AffineScalarFunc._repr_latex_ = ufloat_repr_latex

def unload(ip):
    "Unload all math defined functions"
    names = dir(umath) + ["fraction", "ufloat", "pi", "e"]
    for name in names:
        if name[0] != '_':
            try:
                del ip.user_ns[name]
            except KeyError:
                pass

