import mpmath
from .units import Value
from .uparse import uparse

def mpdoc(f):
    "Decorator to copy the mpmath __doc__ string."
    f.__doc__ = getattr(mpmath, f.__name__, {"__doc__": ""}).__doc__
    return f

@mpdoc
def fraction(q, p):
    if isinstance(q, Value) or isinstance(p, Value):
        q1 = Value(q)
        p1 = Value(p)
        return Value(float(q1.value) / float(p1.value),
                     q1.unit - p1.unit)
    else:
        return Value(float(q) / float(p))

@mpdoc
def fabs(x):
    if isinstance(x, Value): return Value(mpmath.fp.fabs(x.value), x.unit)
    else: return mpmath.fp.fabs(x)

@mpdoc
def sign(x):
    if isinstance(x, Value): return mpmath.fp.sign(x.value)
    else: return mpmath.fp.sign(x)

@mpdoc
def re(x):
    if isinstance(x, Value): return Value(mpmath.fp.re(x.value), x.unit)
    else: return mpmath.fp.re(x)

@mpdoc
def im(x):
    if isinstance(x, Value): return Value(mpmath.fp.im(x.value), x.unit)
    else: return mpmath.fp.im(x)

@mpdoc
def arg(x):
    if isinstance(x, Value): return mpmath.fp.arg(x.value)
    else: return mpmath.fp.arg(x)

@mpdoc
def conj(x):
    if isinstance(x, Value): return Value(mpmath.fp.conj(x.value), x.unit)
    else: return mpmath.fp.conj(x)

# Powers and logarithms

@mpdoc
def sqrt(x, **kwargs):
    if isinstance(x, Value): return Value(mpmath.fp.sqrt(x.value, **kwargs), x.unit / 2)
    else: return mpmath.fp.sqrt(x, **kwargs)

@mpdoc
def cbrt(x, **kwargs):
    if isinstance(x, Value): return Value(mpmath.fp.cbrt(x.value, **kwargs), x.unit / 3)
    else: return mpmath.fp.cbrt(x, **kwargs)

@mpdoc
def root(x, n, k=0):
    if isinstance(x, Value): return Value(mpmath.fp.root(x.value, n, k), x.unit / n)
    else: return mpmath.fp.root(x, n, k)

# Trigonometric functions

@mpdoc
def atan2(y, x):
    if isinstance(x, Value) or isinstance(y, Value):
        x1 = Value(x)
        y1 = Value(y)
        x1.checkUnits(y1)
        return mpmath.fp.atan2(y1.value, x1.value)
    else:
        return mpmath.fp.atan2(y, x)
        
# Polynomials

@mpdoc
def polyval(coeffs, x, derivative=False):
    if not coeffs:
        return mpmath.fp.zero
    p = Value(coeffs[0])
    q = Value(cmpmath.fp.zero)
    for c in coeffs[1:]:
        if derivative:
            q = p + x*q
        p = c + x*p
    if derivative:
        return p, q
    else:
        return p

# Root-finding

@mpdoc
def polyroots(coeffs, maxsteps=50, cleanup=True, extraprec=10, error=False):
    p = Value(coeffs[0])
    q = Value(coeffs[1])
    u = q.unit - p.unit
    v = q.unit
    k = [p.value]
    for c in coeffs[1:]:
        c = Value(c)
        c.checkUnits(Value(1, v))
        k.append(c.value)
        v = v + u
    return map(lambda z: Value(z, u),
               mpmath.fp.polyroots(k, maxsteps, cleanup, extraprec, error))

@mpdoc
def findroot(f, x0, solver=mpmath.calculus.optimization.Secant, tol=None,
             verbose=False, verify=True, **kwargs):
    if isinstance(x0, Value):
        u = x0.unit
        f1 = lambda v: f(Value(v, u)).value
        x1 = x0.value
        res = mpmath.fp.findroot(f1, x1, solver=solver, tol=tol, verbose=verbose,
                                 verify=verify, **kwargs)
        return Value(res, u)
    else:
        return mpmath.fp.findroot(f, x0, solver=solver, tol=tol, verbose=verbose,
                                  verify=verify, **kwargs)

@mpdoc
def multiplicity(f, root, tol=None, maxsteps=10, **kwargs):
    if isinstance(root, Value):
        u = root.unit
        f1 = lambda v: f(Value(v, u)).value
        root1 = root.value
        return Value(mpmath.fp.multiplicity(f1, root1, tol, maxsteps, **kwargs))
    else:
        return mpmath.fp.multiplicity(f, root, tol, maxsteps, **kwargs)
    
# Sums, limits

@mpdoc
def nsum(f, *intervals, **options):
    x = []
    intervals1 = []
    for interval in intervals:
        min, max = Value(interval[0]), Value(interval[1])
        intervals1.append([min.value, max.value])
        min.checkUnit(max.unit)
        if isinf(min):
            if isinf(max): x0 = Value(0, min.unit)
            else: x0 = max
        else:
            if isinf(max): x0 = min
            else: x0 = (min + max) * 0.5
        x.append(x0)
    fu = Value(f(*x0)).unit
    f1 = lambda *args: Value(f(*map(Value, args))).value
    return Value(mpmath.fp.nsum(f1, *intervals1, **options), fu)

@mpdoc
def sumem(f, interval, tol=None, reject=10, integral=None, adiffs=None,
          bdiffs=None, verbose=False, error=False, _fast_abort=False):
    min, max = Value(interval[0]), Value(interval[1])
    interval1 = [min.value, max.value]
    min.checkUnit(max.unit)
    if isinf(min):
        if isinf(max): x1 = Value(0, min.unit)
        else: x1 = max
    else:
        if isinf(max): x1 = min
        else: x1 = (min + max) * 0.5
    fu = Value(f(x1)).unit
    f1 = lambda arg: Value(f(Value(arg))).value
    return Value(mpmath.fp.sumem(f1, interval1, tol, reject, integral, adiffs,
                              bdiffs, verbose, error, _fast_abort), fu)

@mpdoc
def sumap(f, interval, integral=None, error=False):
    min, max = Value(interval[0]), Value(interval[1])
    interval1 = [min.value, max.value]
    min.checkUnit(max.unit)
    if isinf(min):
        if isinf(max): x1 = Value(0, min.unit)
        else: x1 = max
    else:
        if isinf(max): x1 = min
        else: x1 = (min + max) * 0.5
    fu = Value(f(x1)).unit
    f1 = lambda arg: Value(f(Value(arg))).value
    return Value(mpmath.fp.sumap(f1, interval1, integral, error))

def ufloat(s):
    """Convert a number in the format 12.2+/-0.3 into a Normal distribution."""
    v, u = uparse(s)
    return float(v)

######################################################################
# Load and unload functions

def load(namespace):
    "Load all mpmath defined functions, using when appropriate modified versions."
    names = dir(mpmath)
    globs = globals()
    for name in names:
        if hasattr(mpmath.fp, name):
            namespace[name] = globs.get(name, getattr(mpmath.fp, name))
    namespace["fp"] = mpmath.fp
    namespace["fraction"] = fraction
    namespace["ufloat"] = ufloat
    namespace["fp"].pretty = True

def unload(namespace):
    "Unload all mpmath defined functions"
    names = dir(mpmath) + ["fraction", "fp", "ufloat"]
    for name in names:
        if hasattr(mpmath.mp, name):
            try:
                del namespace[name]
            except KeyError:
                pass
        
