import numpy
from .units import Value
from .uparse import uparse


def numdoc(f):
    """Decorator to copy the mpmath __doc__ string."""
    f.__doc__ = getattr(numpy, f.__name__, {"__doc__": ""}).__doc__
    return f


@numdoc
def fabs(x):
    if isinstance(x, Value):
        return Value(numpy.fabs(x.value), x.unit)
    else:
        return numpy.fabs(x)


@numdoc
def sign(x):
    if isinstance(x, Value):
        return numpy.sign(x.value)
    else:
        return numpy.sign(x)


@numdoc
def real(x):
    if isinstance(x, Value):
        return Value(numpy.real(x.value), x.unit)
    else:
        return numpy.real(x)


@numdoc
def imag(x):
    if isinstance(x, Value):
        return Value(numpy.imag(x.value), x.unit)
    else:
        return numpy.imag(x)


@numdoc
def conj(x):
    if isinstance(x, Value):
        return Value(numpy.conj(x.value), x.unit)
    else:
        return numpy.conj(x)


# Powers and logarithms

@numdoc
def sqrt(x, **kwargs):
    if isinstance(x, Value):
        return Value(numpy.sqrt(x.value, **kwargs), x.unit / 2)
    else:
        return numpy.sqrt(x, **kwargs)


@numdoc
def square(x, **kwargs):
    if isinstance(x, Value):
        return Value(numpy.square(x.value, **kwargs), x.unit * 2)
    else:
        return numpy.square(x, **kwargs)


# Trigonometric functions

@numdoc
def arctan2(y, x):
    if isinstance(x, Value) or isinstance(y, Value):
        x1 = Value(x)
        y1 = Value(y)
        x1.check_units(y1)
        return numpy.arctan2(y1.value, x1.value)
    else:
        return numpy.arctan2(y, x)
        

def ufloat(s):
    """Convert a number in the format 12.2+/-0.3 into a Normal distribution."""
    v, u = uparse(s)
    return float(v)


######################################################################
# Load and unload functions

def value_getattr(self, attr):
    globs = globals()
    f = globs.get(attr, getattr(numpy, attr, None))
    if type(f) == numpy.ufunc:
        if callable(f) and type(self) == Value: 
            return lambda: f(self.check_pure(attr))
        else:
            return f
    elif f is not None:
        return lambda: f(self)
    else:
        raise AttributeError


def load(namespace):
    """Load all numpy defined functions, using when appropriate modified versions."""
    names = dir(numpy)
    globs = globals()
    setattr(Value, "__getattr__", value_getattr)
    for name in names:
        f = getattr(numpy, name)
        if type(f) == numpy.ufunc:
            namespace[name] = globs.get(name, f)
    namespace["numpy"] = numpy
    namespace["ufloat"] = ufloat


def unload(namespace):
    """Unload all numpy defined functions"""
    names = dir(numpy) + ["numpy", "ufloat"]
    for name in names:
        f = getattr(numpy, name)
        if type(f) == numpy.ufunc:
            try:
                del namespace[name]
            except KeyError:
                pass
