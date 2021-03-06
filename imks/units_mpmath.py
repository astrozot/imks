import mpmath
from .units import Value
from .uparse import uparse

_round = round


def mpdoc(f):
    """Decorator to copy the mpmath __doc__ string."""
    f.__doc__ = getattr(mpmath, f.__name__, {"__doc__": ""}).__doc__
    return f


def unitier(f):
    """Decorator to use Value's (with units put back) in normal functions."""
    def f_new(x):
        if isinstance(x, Value):
            return Value(f_orig(x.value), x.unit)
        else:
            return f_orig(x)
    if isinstance(f, str):
        name = f
    else:
        name = f.__name__
    f_orig = getattr(mpmath, name)
    f_new.__doc__ = f_orig.__doc__
    return f_new


def purifier(f):
    """Decorator to use Value's (with units ignored) in normal functions."""
    def f_new(x):
        if isinstance(x, Value):
            return f_orig(x.value)
        else:
            return f_orig(x)
    if isinstance(f, str):
        name = f
    else:
        name = f.__name__
    f_orig = getattr(mpmath, name)
    f_new.__doc__ = f_orig.__doc__
    return f_new


@mpdoc
def fraction(q, p):
    if isinstance(q, Value) or isinstance(p, Value):
        q1 = Value(q)
        p1 = Value(p)
        return Value(mpmath.fraction(int(q1.value), int(p1.value)),
                     q1.unit - p1.unit)
    else:
        return mpmath.fraction(int(q), int(p))


# Powers and logarithms

@mpdoc
def sqrt(x, **kwargs):
    if isinstance(x, Value):
        return Value(mpmath.sqrt(x.value, **kwargs), x.unit / 2)
    else:
        return mpmath.sqrt(x, **kwargs)


@mpdoc
def cbrt(x, **kwargs):
    if isinstance(x, Value):
        return Value(mpmath.cbrt(x.value, **kwargs), x.unit / 3)
    else:
        return mpmath.cbrt(x, **kwargs)


@mpdoc
def root(x, n, k=0):
    if isinstance(x, Value):
        return Value(mpmath.root(x.value, n, k), x.unit / n)
    else:
        return mpmath.root(x, n, k)


# Trigonometric functions

@mpdoc
def atan2(y, x):
    if isinstance(x, Value) or isinstance(y, Value):
        x1 = Value(x)
        y1 = Value(y)
        x1.check_units(y1)
        return mpmath.atan2(y1.value, x1.value)
    else:
        return mpmath.atan2(y, x)


# Polynomials

@mpdoc
def polyval(coeffs, x, derivative=False):
    if not coeffs:
        return mpmath.mp.zero
    p = Value(coeffs[0])
    q = Value(mpmath.mp.zero)
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
        c.check_units(Value(1, v))
        k.append(c.value)
        v = v + u
    return map(lambda z: Value(z, u),
               mpmath.polyroots(k, maxsteps, cleanup, extraprec, error))


@mpdoc
def findroot(f, x0, solver='secant', tol=None, verbose=False, verify=True,
             **kwargs):
    if isinstance(x0, Value):
        u = x0.unit
        f1 = lambda v: f(Value(v, u)).value
        x1 = x0.value
        res = mpmath.findroot(f1, x1, solver=solver, tol=tol, verbose=verbose,
                              verify=verify, **kwargs)
        return Value(res, u)
    else:
        return mpmath.findroot(f, x0, solver=solver, tol=tol, verbose=verbose,
                               verify=verify, **kwargs)


@mpdoc
def multiplicity(f, root, tol=None, maxsteps=10, **kwargs):
    if isinstance(root, Value):
        u = root.unit
        f1 = lambda v: f(Value(v, u)).value
        root1 = root.value
        return Value(mpmath.multiplicity(f1, root1, tol, maxsteps, **kwargs))
    else:
        return mpmath.multiplicity(f, root, tol, maxsteps, **kwargs)


# Sums, limits

@mpdoc
def nsum(f, *intervals, **options):
    x = []
    intervals1 = []
    for interval in intervals:
        min, max = Value(interval[0]), Value(interval[1])
        intervals1.append([min.value, max.value])
        min.check_units(max.unit)
        if mpmath.isinf(min):
            if mpmath.isinf(max):
                x0 = Value(0, min.unit)
            else:
                x0 = max
        else:
            if mpmath.isinf(max):
                x0 = min
            else:
                x0 = (min + max) * 0.5
        x.append(x0)
    fu = Value(f(*x)).unit
    f1 = lambda *args: Value(f(*map(Value, args))).value
    return Value(mpmath.nsum(f1, *intervals1, **options), fu)


@mpdoc
def sumem(f, interval, tol=None, reject=10, integral=None, adiffs=None,
          bdiffs=None, verbose=False, error=False, _fast_abort=False):
    min, max = Value(interval[0]), Value(interval[1])
    interval1 = [min.value, max.value]
    min.check_units(max.unit)
    if mpmath.isinf(min):
        if mpmath.isinf(max):
            x1 = Value(0, min.unit)
        else:
            x1 = max
    else:
        if mpmath.isinf(max):
            x1 = min
        else:
            x1 = (min + max) * 0.5
    fu = Value(f(x1)).unit
    f1 = lambda arg: Value(f(Value(arg))).value
    return Value(mpmath.sumem(f1, interval1, tol, reject, integral, adiffs,
                 bdiffs, verbose, error, _fast_abort), fu)


@mpdoc
def sumap(f, interval, integral=None, error=False):
    min, max = Value(interval[0]), Value(interval[1])
    interval1 = [min.value, max.value]
    min.check_units(max.unit)
    if mpmath.isinf(min):
        if mpmath.isinf(max):
            x1 = Value(0, min.unit)
        else:
            x1 = max
    else:
        if mpmath.isinf(max):
            x1 = min
        else:
            x1 = (min + max) * 0.5
    fu = Value(f(x1)).unit
    f1 = lambda arg: Value(f(Value(arg))).value
    return Value(mpmath.sumap(f1, interval1, integral, error), fu)


@mpdoc
def plot(f, xlim=(-5, 5), ylim=None, points=200, file=None, dpi=None,
         singularities=(), axes=None):
    import pylab
    min, max = Value(xlim[0]), Value(xlim[1])
    min.check_units(max)
    if min.showunit:
        xfact = Value(1, str(min.showunit).strip("[] ")).value
    else:
        xfact = 1
    xlim1 = [min.value / xfact, max.value / xfact]
    if type(f) == list:
        y0 = Value(f[0](min))
        for fi in f:
            y0.check_units(Value(fi(min)))
    else:
        y0 = Value(f(min))
    if y0.showunit:
        yfact = Value(1, str(y0.showunit).strip("[] ")).value
    else:
        yfact = 1
    if type(f) == list:
        f1 = [(lambda arg: (Value(fi(Value(arg * xfact, min.unit))).value
                            / yfact)) for fi in f]
    else:
        f1 = lambda arg: (Value(f(Value(arg * xfact, min.unit))).value / yfact)
    if file:
        axes = None
    fig = None
    if not axes:
        import pylab
        fig = pylab.figure()
        axes = fig.add_subplot(111)
    mpmath.plot(f1, xlim=xlim1, ylim=ylim, points=points, file=file, dpi=dpi,
                singularities=singularities, axes=axes)
    axes.set_xlabel("x " + str(min.showunit or min.unit))
    axes.set_ylabel("f(x) " + str(y0.unit))
    if fig:
        if file:
            pylab.savefig(file, dpi=dpi)
        else:
            pylab.show()

def ufloat(s):
    """Convert a number in the format 12.2+/-0.3 into a Normal distribution."""
    v, u = uparse(s)
    return mpmath.mpmathify(v)


######################################################################
# Load and unload functions

old_mpf_str = None
min_fixed = None
max_fixed = None


def new_mpf_str(s):
    from mpmath.libmp import to_str
    global min_fixed, max_fixed
    return to_str(s._mpf_, s.context._str_digits,
                  min_fixed=min_fixed, max_fixed=max_fixed)


def load(namespace):
    """Load all mpmath defined functions, using when appropriate modified versions."""
    global old_mpf_str
    names = dir(mpmath)
    globs = globals()
    purifiers = ['sign', 'arg', 'isinf', 'isnan', 'isnormal', 'isfinite', 'isint']
    unitiers = ['fabs', 'ceils', 'floor', 'frac', 'nint', 're', 'im', 'conj']
    for name in names:
        if hasattr(mpmath.mp, name) or name == 'mp':
            if name in globs:
                namespace[name] = globs[name]
            elif name in purifiers:
                namespace[name] = purifier(name)
            elif name in unitiers:
                namespace[name] = unitier(name)
            else:
                namespace[name] = getattr(mpmath, name)
    x = mpmath.mpf(1)
    old_mpf_str = x.__class__.__str__
    x.__class__.__str__ = new_mpf_str
    namespace["ufloat"] = ufloat
    namespace["round"] = namespace["nint"]
    namespace["mp"].pretty = True


def unload(namespace):
    """Unload all mpmath defined functions."""
    global old_mpf_str
    names = dir(mpmath) + ["ufloat"]
    x = mpmath.mpf(1)
    x.__class__.__str__ = old_mpf_str
    old_mpf_str = None
    for name in names:
        if hasattr(mpmath.mp, name):
            try:
                del namespace[name]
            except KeyError:
                pass
    namespace["round"] = _round
