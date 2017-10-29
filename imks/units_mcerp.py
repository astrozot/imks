# -*- coding: utf-8 -*-

import mcerp
import mcerp.umath as umath
import math
import uncertainties
from .units import Value
from . import units


def umathdoc(f):
    "Decorator to copy the uncertainties.umath __doc__ string."
    f.__doc__ = getattr(umath, f.__name__, {"__doc__": ""}).__doc__
    return f


@umathdoc
def ceil(x):
    if isinstance(x, Value):
        return Value(umath.ceil(x.value), x.unit)
    else:
        return umath.ceil(x)


@umathdoc
def fabs(x):
    if isinstance(x, Value):
        return Value(umath.fabs(x.value), x.unit)
    else:
        return umath.fabs(x)


@umathdoc
def floor(x):
    if isinstance(x, Value):
        return Value(umath.floor(x.value), x.unit)
    else:
        return umath.floor(x)


@umathdoc
def hypot(x, y):
    return sqrt(x*x + y*y)


@umathdoc
def pow(x, y):
    return x**y


@umathdoc
def sqrt(x):
    if isinstance(x, Value):
        return Value(umath.sqrt(x.value), x.unit / 2)
    else:
        return umath.sqrt(x)


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
    """Decorator for generic one-argument functions."""
    g = lambda x: f(x.check_pure(f.__name__)) \
        if isinstance(x, Value) else f(x)
    g.__doc__ = f.__doc__
    return g


def ufloat(s):
    """Convert a number in the format 12.2+/-0.3 into a Normal distribution."""
    if s.find("+/-") >= 0 or s.find("(") >= 0 or s.find(u"±") >= 0:
        u = uncertainties.ufloat_fromstr(s)
        return mcerp.N(u.nominal_value, u.std_dev)
    else:
        return float(s)


def ufloat_repr(self):
    if units.showerrors == 0:
        return str(self.mean)
    elif units.showerrors == 1:
        u = uncertainties.ufloat(self.mean, math.sqrt(self.var))
        s = str(u)
        i = s.find(r"+/-")
        if i >= 0:
            return s[0:i]
        else:
            return s
    else:
        u = uncertainties.ufloat(self.mean, math.sqrt(self.var))
        return str(u)


def ufloat_repr_latex(self):
    s = "${" + ufloat_repr(self).replace("+/-", "} \pm {") + "}$"
    return s.replace("e", r"} \times 10^{")


######################################################################
# Load and unload functions

def load(namespace):
    """Load all math defined functions, using when appropriate modified versions."""
    globs = globals()
    names = ["Beta", "Bradford", "Burr", "ChiSquared", "Chi2", "Erf",
             "Erlang", "Exponential", "Exp", "ExtValueMax", "EVMax",
             "ExtValueMin", "EVMin", "Fisher", "F", "Gamma", "LogNormal",
             "LogN", "Normal", "N", "Pareto", "Pareto2", "PERT",
             "StudentT", "Triangular", "Tri", "Uniform", "Weibull", "Weib",
             "Bernoulli", "Bern", "Binomial", "B", "Geometric", "G",
             "Hypergeometric", "H", "Poisson", "Pois"]
    for name in names:
        if name[0] != '_':
            namespace[name] = globs.get(name, mconvert(getattr(mcerp, name)))
    names = dir(umath)
    for name in names:
        if name[0] != '_':
            namespace[name] = globs.get(name, mconvert(getattr(umath, name)))
    mcerp.UncertainVariable.__repr__ = mcerp.UncertainFunction.__repr__ = \
        ufloat_repr
    mcerp.UncertainVariable.__str__ = mcerp.UncertainFunction.__str__ = \
        ufloat_repr
    mcerp.UncertainVariable._repr_latex_ = \
        mcerp.UncertainFunction._repr_latex_ = ufloat_repr_latex
    namespace["fraction"] = fraction
    namespace["ufloat"] = ufloat
    namespace["pi"] = math.pi
    namespace["e"] = math.e


def unload(namespace):
    """Unload all math defined functions."""
    names = dir(mcerp) + dir(umath) + ["fraction", "ufloat", "pi", "e"]
    for name in names:
        if name[0] != '_':
            try:
                del namespace[name]
            except KeyError:
                pass
