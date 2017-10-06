import numpy
from .units import Value
from .uparse import uparse

def numdoc(f):
    "Decorator to copy the mpmath __doc__ string."
    f.__doc__ = getattr(numpy, f.__name__, {"__doc__": ""}).__doc__
    return f

@numdoc
def fabs(x):
    if isinstance(x, Value): return Value(numpy.fabs(x.value), x.unit)
    else: return numpy.fabs(x)

@numdoc
def sign(x):
    if isinstance(x, Value): return numpy.sign(x.value)
    else: return numpy.sign(x)

@numdoc
def real(x):
    if isinstance(x, Value): return Value(numpy.real(x.value), x.unit)
    else: return numpy.real(x)

@numdoc
def imag(x):
    if isinstance(x, Value): return Value(numpy.imag(x.value), x.unit)
    else: return numpy.imag(x)

@numdoc
def conj(x):
    if isinstance(x, Value): return Value(numpy.conj(x.value), x.unit)
    else: return numpy.conj(x)

# Powers and logarithms

@numdoc
def sqrt(x, **kwargs):
    if isinstance(x, Value): return Value(numpy.sqrt(x.value, **kwargs), x.unit / 2)
    else: return numpy.sqrt(x, **kwargs)

@numdoc
def square(x, **kwargs):
    if isinstance(x, Value): return Value(numpy.square(x.value, **kwargs), x.unit * 2)
    else: return numpy.square(x, **kwargs)

# Trigonometric functions

@numdoc
def arctan2(y, x):
    if isinstance(x, Value) or isinstance(y, Value):
        x1 = Value(x)
        y1 = Value(y)
        x1.checkUnits(y1)
        return numpy.arctan2(y1.value, x1.value)
    else:
        return numpy.arctan2(y, x)
        
# Polynomials

# @numdoc
# def polyval(coeffs, x, derivative=False):
#     if not coeffs:
#         return mpmath.fp.zero
#     p = Value(coeffs[0])
#     q = Value(cmpmath.fp.zero)
#     for c in coeffs[1:]:
#         if derivative:
#             q = p + x*q
#         p = c + x*p
#     if derivative:
#         return p, q
#     else:
#         return p

# # Root-finding

# @numdoc
# def polyroots(coeffs, maxsteps=50, cleanup=True, extraprec=10, error=False):
#     p = Value(coeffs[0])
#     q = Value(coeffs[1])
#     u = q.unit - p.unit
#     v = q.unit
#     k = [p.value]
#     for c in coeffs[1:]:
#         c = Value(c)
#         c.checkUnits(v)
#         k.append(c.value)
#         v = v + u
#     return map(lambda z: Value(z, u),
#                mpmath.fp.polyroots(k, maxsteps, cleanup, extraprec, error))

# @numdoc
# def findroot(f, x0, solver=mpmath.calculus.optimization.Secant, tol=None,
#              verbose=False, verify=True, **kwargs):
#     if isinstance(x0, Value):
#         u = x0.unit
#         f1 = lambda v: f(Value(v, u)).value
#         x1 = x0.value
#         res = mpmath.fp.findroot(f1, x1, solver=solver, tol=tol, verbose=verbose,
#                                  verify=verify, **kwargs)
#         return Value(res, u)
#     else:
#         return mpmath.fp.findroot(f, x0, solver=solver, tol=tol, verbose=verbose,
#                                   verify=verify, **kwargs)

# @numdoc
# def multiplicity(f, root, tol=None, maxsteps=10, **kwargs):
#     if isinstance(root, Value):
#         u = root.unit
#         f1 = lambda v: f(Value(v, u)).value
#         root1 = root.value
#         return Value(mpmath.fp.multiplicity(f1, root1, tol, maxsteps, **kwargs))
#     else:
#         return mpmath.fp.multiplicity(f, root, tol, maxsteps, **kwargs)
    
# # Sums, limits

# @numdoc
# def nsum(f, *intervals, **options):
#     x = []
#     intervals1 = []
#     for interval in intervals:
#         min, max = Value(interval[0]), Value(interval[1])
#         intervals1.append([min.value, max.value])
#         min.checkUnit(max.unit)
#         if isinf(min):
#             if isinf(max): x0 = Value(0, min.unit)
#             else: x0 = max
#         else:
#             if isinf(max): x0 = min
#             else: x0 = (min + max) * 0.5
#         x.append(x0)
#     fu = Value(f(*x0)).unit
#     f1 = lambda *args: Value(f(*map(Value, args))).value
#     return Value(mpmath.fp.nsum(f1, *intervals1, **options), fu)

# @numdoc
# def sumem(f, interval, tol=None, reject=10, integral=None, adiffs=None,
#           bdiffs=None, verbose=False, error=False, _fast_abort=False):
#     min, max = Value(interval[0]), Value(interval[1])
#     interval1 = [min.value, max.value]
#     min.checkUnit(max.unit)
#     if isinf(min):
#         if isinf(max): x1 = Value(0, min.unit)
#         else: x1 = max
#     else:
#         if isinf(max): x1 = min
#         else: x1 = (min + max) * 0.5
#     fu = Value(f(x1)).unit
#     f1 = lambda arg: Value(f(Value(arg))).value
#     return Value(mpmath.fp.sumem(f1, interval1, tol, reject, integral, adiffs,
#                               bdiffs, verbose, error, _fast_abort), fu)

# @numdoc
# def sumap(f, interval, integral=None, error=False):
#     min, max = Value(interval[0]), Value(interval[1])
#     interval1 = [min.value, max.value]
#     min.checkUnit(max.unit)
#     if isinf(min):
#         if isinf(max): x1 = Value(0, min.unit)
#         else: x1 = max
#     else:
#         if isinf(max): x1 = min
#         else: x1 = (min + max) * 0.5
#     fu = Value(f(x1)).unit
#     f1 = lambda arg: Value(f(Value(arg))).value
#     return Value(mpmath.fp.sumap(f1, interval1, integral, error))

def ufloat(s):
    """Convert a number in the format 12.2+/-0.3 into a Normal distribution."""
    v, u = uparse(s)
    return float(s)

######################################################################
# Load and unload functions

def Value_getattr(self, attr):
    globs = globals()
    f = globs.get(attr, getattr(numpy, attr, None))
    if type(f) == numpy.ufunc:
        if callable(f) and type(self) == Value: 
            return lambda : f(self.checkPure(attr))
        else:
            return f
    elif f is not None:
        return lambda : f(self)
    else:
        raise AttributeError

def load(ip):
    "Load all numpy defined functions, using when appropriate modified versions."
    names = dir(numpy)
    globs = globals()
    setattr(Value, "__getattr__", Value_getattr)
    for name in names:
        f = getattr(numpy, name)
        if type(f) == numpy.ufunc:
            ip.user_ns[name] = globs.get(name, f)
    ip.user_ns["numpy"] = numpy
    ip.user_ns["ufloat"] = ufloat

def unload(ip):
    "Unload all numpy defined functions"
    names = dir(numpy) + ["numpy", "ufloat"]
    for name in names:
        f = getattr(numpy, name)
        if type(f) == numpy.ufunc:
            try:
                del ip.user_ns[name]
            except KeyError:
                pass
        
