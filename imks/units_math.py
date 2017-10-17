import math
from .units import Value
from .uparse import uparse

_round = round

def mathdoc(f):
    "Decorator to copy the math __doc__ string."
    f.__doc__ = getattr(math, f.__name__, {"__doc__": ""}).__doc__
    return f

@mathdoc
def atan2(y, x):
    if isinstance(x, Value) or isinstance(y, Value):
        x1 = Value(x)
        y1 = Value(y)
        x1.checkUnits(y1)
        return math.atan2(y1.value, x1.value)
    else:
        return math.atan2(y, x)

@mathdoc
def ceil(x):
    if isinstance(x, Value): return Value(math.ceil(x.value), x.unit)
    else: return math.ceil(x)

@mathdoc
def copysign(x, y):
    if isinstance(x, Value) or isinstance(y, Value):
        x1 = Value(x)
        y1 = Value(y)
        return Value(math.copysign(x1.value, y1.value), x1.unit)
    else:
        return math.copysign(x, y)
    
@mathdoc
def fabs(x):
    if isinstance(x, Value): return Value(math.fabs(x.value), x.unit)
    else: return math.fabs(x)

@mathdoc
def floor(x):
    if isinstance(x, Value): return Value(math.floor(x.value), x.unit)
    else: return math.floor(x)

@mathdoc
def fmod(x, y):
    if isinstance(x, Value) or isinstance(y, Value):
        x1 = Value(x)
        y1 = Value(y)
        return Value(math.fmod(x1.value, y1.value), x1.units - y1.units)
    else:
        return math.fmod(x, y)

@mathdoc
def hypot(x, y):
    return sqrt(x*x + y*y)

@mathdoc
def isinf(x):
    if isinstance(x, Value): return math.isinf(x.value)
    else: return math.isinf(x)

@mathdoc
def isnan(x):
    if isinstance(x, Value): return math.isnan(x.value)
    else: return math.isnan(x)

@mathdoc
def modf(x):
    if isinstance(x, Value):
        a, b = math.modf(x.value)
        return (Value(a, x.unit), Value(b, x.unit))
    else: return math.modf(x)

@mathdoc
def pow(x, y):
    return x**y

@mathdoc
def round(x):
    if isinstance(x, Value): return Value(_round(x.value), x.unit)
    else: return _round(x)

@mathdoc
def sqrt(x):
    if isinstance(x, Value): return Value(math.sqrt(x.value), x.unit / 2)
    else: return math.sqrt(x)

def fraction(q, p):
    """Given Python integers `(p, q)`, return the fraction p/q."""
    if isinstance(q, Value) or isinstance(p, Value):
        q1 = Value(q)
        p1 = Value(p)
        return Value(float(q1.value) / float(p1.value),
                     q1.unit - p1.unit)
    else:
        return Value(float(q) / float(p))

def ufloat(s):
    """Convert a number in the format 12.2+/-0.3 into a Normal distribution."""
    v, u = uparse(s)
    return float(v)

######################################################################
# Load and unload functions

def load(namespace):
    "Load all math defined functions, using when appropriate modified versions."
    names = dir(math)
    globs = globals()
    for name in names:
        if name[0] != '_':
            namespace[name] = globs.get(name, getattr(math, name))
    namespace["round"] = round
    namespace["fraction"] = fraction
    namespace["ufloat"] = ufloat

def unload(namespace):
    "Unload all math defined functions"
    names = dir(math) + ["fraction", "ufloat", "round"]
    for name in names:
        if name[0] != '_':
            try:
                del namespace[name]
            except KeyError:
                pass
    namespace["round"] = _round
