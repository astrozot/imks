# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
from collections import OrderedDict as ODict
from fractions import Fraction
import numpy as np
from ply import lex, yacc
import re

# from IPython.core.debugger import Pdb
# Pdb().set_trace()

try:
    # noinspection PyCompatibility
    basestring
except NameError:
    # noinspection PyShadowingBuiltins
    basestring = str

try:
    from mpmath.ctx_mp_python import mpnumeric
except ImportError:
    mpnumeric = float

from .spelling import *

#####################################################################
# Numerical service functions


def almost_equal(x, y=0, eps=1e-7):
    """Check if two numbers are almost equal.

    :param float x:  the first number to check
    :param float y:  the second number to check [0]
    :param eps:      the checking tolerance [1e-7]
    :rtype bool:
    """
    return abs(x - y) < eps


def fraction(x, max_den=10000000):
    """Convert a float into a fraction, with a given maximum denominator.

    :param float x:      number to convert
    :param int max_den:  maximum denominator accepted
    :rtype (int, int):
    """
    f = Fraction(x).limit_denominator(max_den)
    return f.numerator, f.denominator


#####################################################################
# Unit errors definition

class UnitError(Exception):
    """Abstract class for general unit exceptions."""
    pass


class UnitParseError(UnitError):
    """Class for unit parsing errors."""
    def __init__(self, expression, message, lineno=None):
        self.expression = expression
        self.message = message
        self.lineno = lineno

    def __str__(self):
        if self.lineno:
            return "Unit error for `%s' at line %d: %s" % \
                   (self.expression, self.lineno, self.message)
        else:
            return "Unit error for `%s': %s" % \
                   (self.expression, self.message)


class UnitCompatibilityError(UnitError):
    """Class for unit compability exceptions."""
    def __init__(self, u1, u2, where=None):
        import traceback
        self.u1 = u1
        self.u2 = u2
        if where and where > 2:
            self.fn = where
        else:
            self.fn = traceback.extract_stack()[-2][2]
        if self.fn == "check_units" or self.fn == "check_pure":
            self.fn = traceback.extract_stack()[-3][2]

    def __str__(self):
        return "%s incompatible with %s in %s" % \
               (str(self.u1) or "[]", str(self.u2) or "[]", self.fn)


class UnitAbsoluteError(Exception):
    """Class for exceptions related to absolute units."""
    def __init__(self, a1, a2, where=None):
        import traceback
        self.a1 = "absolute" if a1 is not False else "relative"
        self.a2 = "absolute" if a2 is not False else "relative"
        if where and where > 2:
            self.fn = where
        else:
            self.fn = traceback.extract_stack()[-2][2]
        if self.fn == "check_units" or self.fn == "check_pure":
            self.fn = traceback.extract_stack()[-3][2]

    def __str__(self):
        return "%s unit incompatible with %s unit in %s" % \
               (self.a1, self.a2, self.fn)


#####################################################################
# Documentation functions

def make_object_w_doc(value, doc="", source=""):
    """Defines an object with a documentation string.

    Works by creating a new class that inherits all attributes of the original
    object. Needed for base objects that allow no attributes (for example
    tuples).
    """
    c = type(value.__class__.__name__ + "_w_doc",
             (value.__class__,),
             {"__doc__": doc, "__source__": source,
              "__reduce__": lambda s: (make_object_w_doc, (value, doc, source))})
    return c(value)


make_object_w_doc.__safe_for_unpickling__ = True


def extract_name(doc):
    """Extract the name from the documentation of a unit."""
    return doc.splitlines()[0].lower().replace(" ", "-")


def unit_parser(unit):
    """General parser for units.

    :param str unit: the string to parse
    :return (Value, UnitTree): the full result of the parsing

    The parse tries to parse first simple units, such as 'm/s^', then verbose
    ones, such as 'meter per second squared'.
    """
    try:
        unitlex.verbose = unityacc.verbose = False
        res = unityacc.parse(unit, lexer=unitlex)
    except UnitParseError:
        try:
            unitlex.verbose = unityacc.verbose = True
            res = unityacc.parse(unit, lexer=unitlex)
        finally:
            unitlex.verbose = unityacc.verbose = False
    return res


class Doc(object):
    tdict = {}

    def __init__(self, doc="", source=""):
        """A class o generate documentation strings.

        :param str doc:  documentation string
        :param source:   source string
        """
        self.doc = doc
        self.source = source

    def __rand__(self, x):
        """Operator overload for Doc objects.

        The operator makes it possible to do something like
        >>> m = Value(80, "kg") | Doc("Average mass of a person.")

        :param Any x:  Variable to annotate
        :return Any:   x annotated

        If x is a basic type that cannot be extended with the __doc__ attribute,
        this function returns a new copy of x generated with `make_object_w_doc`.
        """
        try:
            if self.doc:
                x.__doc__ = self.doc
            if self.source:
                x.__source__ = self.source
        except AttributeError:
            x = make_object_w_doc(x, self.doc, self.source)
        return x


#####################################################################
# Main classes

class UnitTree(tuple):
    """A unit tree representation.

    The general structure is

    ((unit1, exponent1), (unit2, exponent2), ...)

    where unit is either a string (i.e. a leaf of the parsing tree)
    or a UnitTree itself. This second form allows one to represent
    trees that contains parentheses: kg / (km/s)^2 would be represented
    as

    (("kg", 1), ((("km", 1), ("s", -1)), 2))
    """
    def __new__(cls, obj=()):
        """Overrides constructor for immutable type.

        :param Tuple[Tuple[Union[str, UnitTree], float]] obj:  UnitTree description
        """
        return super(UnitTree, cls).__new__(cls, obj)

    @classmethod
    def simple(cls, name, exp=1):
        """Return a simple UnitTree with a single unit.

        :param str name:  Name of the unit
        :param int exp:   Exponent [1]
        :return UnitTree:
        """
        return cls(((name, exp),))

    def __bool__(self):
        """Check if a unit is zero, i.e. if it represent a pure number."""
        for u, e in self:
            if bool(u) and e != 0:
                return True
        return False

    def __nonzero__(self):
        """Python 2 compatibility method that calls __bool__."""
        return self.__bool__()

    def __neg__(self):
        return UnitTree(((b, -e) for b, e in self))

    def __add__(self, t):
        """Sum of unit trees, i.e. product of quantities.

        :param UnitTree t:  tree to add
        """
        return UnitTree(super(UnitTree, self).__add__(t))

    def __sub__(self, t):
        """Sum of unit trees, i.e. product of quantities.

        :param UnitTree t:  tree to subtract
        """
        return UnitTree(super(UnitTree, self).__add__(-t))

    def __mul__(self, f):
        """Multiplication of a unit, i.e. exponentiation.

        :param float f:  exponent"""
        if len(self) == 1 and self[0][1] == 1:
            return UnitTree(((self[0][0], f),))
        elif f == 1:
            return self
        else:
            return UnitTree(((self, f),))
        # return UnitTree(((b, e*f) for b, e in self))

    def to_value(self):
        """Convert a UnitTree to the Value it represents.

        :return Value:  value represented by the UnitTree
        """
        global user_ns
        r = Value(1.0)
        for u, e in self:
            if e == 0:
                continue
            if isinstance(u, UnitTree):
                r = r * u.to_value() ** e
            else:
                if u[0] == '"':
                    x = user_ns[u[1:-1]]
                else:
                    x = unit_parser(u)[0]
                r = r * x ** e
        return r

    def remove_variable_units(self):
        """Remove double quoted units.

        Returns a tuple (f, u), where f is a scalar factor that represents the
        deleted units, and u the new unit with double quotes removed as a
        UnitTree.

        :return UnitTree:  New UnitTree without units
        """
        global user_ns
        factor = 1
        new_unit = []
        for k, v in self:
            if isinstance(k, UnitTree):
                factor1, new_unit1 = k.remove_variable_units()
                if new_unit1:
                    new_unit.append((new_unit1, v))
                factor *= factor1 ** v
            elif k[0] == '"' == k[-1]:
                factor *= user_ns[k[1:-1]] ** v
            else:
                new_unit.append((k, v))
        return factor, UnitTree(new_unit)

    def show(self, latex=False, verbose=False, singular=False):
        """

        :param bool latex:    If true, the output follow the LaTeX style
        :param bool verbose:  If true, units are shown in verbose mode (e.g.
                              "meters per second"
        :param bool singular: If true, do not use plurals in verbose mode
        :return str:          The converted UnitTree
        """
        unit = []
        negpow = None
        first = True
        for u, e in self:
            space_like = False
            if almost_equal(e):
                continue
            if isinstance(u, basestring):
                if u[0] == '"' == u[-1]:
                    continue
                if latex:
                    if u[0] == "'" == u[-1]:
                        base = r"\mathbf{%s}" % u[1:-1]
                    else:
                        base = r"\mathrm{%s}" % u
                else:
                    if u[0] == "'" == u[-1] or not verbose:
                        base = u
                    else:  # thus verbose and no quotes
                        iu = isunit(u) or isunit(u, True)
                        base = (extract_name(prefixes[iu[0]].__doc__) if iu[0] else "") + \
                               (extract_name(units[iu[1]].__doc__) if iu[1] else "")
                        space_like = iu[1] in space_units
                        if first and not singular:   # First unit!
                            base = plural(base)
                if base.find(' ') >= 0 or base.find('^') >= 0 or \
                        base.find('/') >= 0:
                    base = '(' + base + ')'
            elif isinstance(u, UnitTree):
                base = u.show(latex=latex, verbose=verbose, singular=not first)
                if len(u) > 1 or e != 1:
                    base = '(' + base + ')'
                elif isinstance(u[0][0], basestring):
                    space_like = isunit(u[0][0])[1] in space_units
            # Ok, the base is not set; concentrate on the exponent
            first = False
            if almost_equal(e, 1):
                unit.append(base)
                if negpow is None:
                    negpow = False
            else:
                p, q = fraction(e)
                if verbose:
                    if p < 0:
                        if negpow is None:
                            unit.append("inverse")
                        elif negpow is False:
                            unit.append("per")
                        p = -p
                        negpow = True
                    else:
                        negpow = False
                    if almost_equal(q, 1):
                        if p == 1:
                            unit.append(base)
                        elif p == 2:
                            if space_like:
                                unit.append("square %s" % base)
                            else:
                                unit.append("%s squared" % base)
                        elif p == 3:
                            if space_like:
                                unit.append("cubic %s" % base)
                            else:
                                unit.append("%s cubed" % base)
                        else:
                            unit.append("%s to the %s" % (base, number_to_ordinal(p, short=verbose is not True)))
                    else:
                        if verbose is True:
                            unit.append("%s to %s %s" % (base, number_to_cardinal(p),
                                                         number_to_ordinal(q, numerator=p)))
                        else:
                            unit.append("%s to the %d/%s" % (base, p, number_to_ordinal(q, short=True)))
                elif latex:
                    if almost_equal(q, 1):
                        unit.append("%s{}^{%d}" % (base, p))
                    else:
                        unit.append("%s{}^{%d/%d}" % (base, p, q))
                else:
                    if almost_equal(q, 1):
                        unit.append("%s^%d" % (base, p))
                    else:
                        unit.append("%s^%d/%d" % (base, p, q))
        if len(unit) == 0 or (len(unit) == 1 and not unit[0]):
            return ""
        elif len(unit) == 1 and unit[0][0] == '(' and unit[0][-1] == ')':
            return unit[0][1:-1]
        else:
            if latex:
                return r"\,".join(unit)
            else:
                return " ".join(unit)


class Unit(np.ndarray):
    """A unit representation.

    Units are stored as simple vectors of real numbers, where each element is
    the exponent of the corresponding base unit. For example, if the base
    units are 'm', 's', 'kg', the unit

    [1, -2, 0]

    would represent an acceleration [m/s^2].
    """

    def __new__(cls, *args, **kwargs):
        """Build a new unit following the arguments

        :param Union(str, np.ndarray, List[float]) args:  Unit specification
        :param kwargs:  Unused
        :return Unit:   Newly created unit
        """
        shape = len(baseunits)
        obj = np.zeros(shape).view(cls)
        if len(args) == 0:
            return obj
        if len(args) == 1 and isinstance(args[0], basestring):
            if not re.match(r"^[ \t]*$", args[0]):
                tmp = unit_parser(args[0])[0]
                if isinstance(tmp, tuple):
                    obj += tmp[1].unit
                else:
                    obj += tmp.unit
        elif len(args) == 1 and isinstance(args[0], np.ndarray):
            np.copyto(obj, args[0])
        else:
            tmp = np.array(*args)
            np.copyto(obj, tmp)
        return obj

    def __array_finalize__(self, obj):
        if obj is None:
            return

    def show(self, *args, **kwargs):
        lst = tuple((baseunits[n], e) for n, e in enumerate(self) if e != 0)
        return UnitTree(lst).show(*args, **kwargs)

    def __bool__(self):
        """Check if a unit is non zero, i.e. if it represents a non-pure number."""
        return np.asscalar(np.any(self))

    def __eq__(self, obj):
        return not bool(self - obj)

    def __ne__(self, obj):
        return bool(self - obj)

    def __nonzero__(self):
        """Python 2 compatibility method that calls __bool__."""
        return self.__bool__()

    def __str__(self):
        unit = []
        for n, e in enumerate(self):
            if not almost_equal(e, 0):
                s = baseunits[n]
                if not almost_equal(e, 1):
                    s += "^%g" % e
                unit.append(s)
        return "[" + " ".join(unit) + "]"


class Value(np.ndarray):

    def __new__(cls, value, unit=None, **kw):
        """

        :param value:
        :param unit:
        :param absolute:
        :param original:
        :return:
        """
        obj = np.asanyarray(value).view(cls)
        # add the new attributes to the instance
        if unit is None:
            unit = getattr(value, "unit", Unit())
        absolute = kw.get("absolute", getattr(value, "absolute", False))
        original = kw.get("original", False)
        showunit = kw.get("showunit", getattr(value, "showunit", None))
        showprefix = kw.get("showprefix", getattr(value, "showprefix", None))
        if not isinstance(unit, Unit):
            if isinstance(unit, np.ndarray):
                unit = Unit(unit)
            elif isinstance(unit, basestring):
                if not re.match(r"^[ \t]*$", unit):
                    value, tree = unit_parser(unit)
                    obj *= value.view(np.ndarray)
                    unit = value.unit
                    absolute = kw.get("absolute", value.absolute)
                    if original:
                        showunit = tree
        obj.unit = unit
        obj.absolute = absolute
        obj.showunit = showunit
        obj.showprefix = showprefix
        return obj

    def __array_finalize__(self, obj):
        if obj is None:
            return
        self.unit = getattr(obj, 'unit', Unit())
        self.absolute = getattr(obj, 'absolute', False)
        self.showunit = getattr(obj, 'showunit', None)

    @property
    def value(self):
        return np.asarray(self)

    @value.setter
    def value(self, x):
        np.copyto(self, x)

    def __array_prepare__(self, array, context=None):
        # FIXME: Implement using context = [ufunc, *args, 0?]
        results = super(Value, self).__array_prepare__(array, context)
        return results

    def check_units(self, y, where=None):
        global tolerant
        u0 = self.unit
        if isinstance(y, Value):
            u1 = y.unit
            if u0 != u1 and (not tolerant or (self.value != 0 and y.value != 0)):
                if where:
                    raise UnitCompatibilityError(u0, u1, where)
                raise UnitCompatibilityError(u0, u1)
        else:
            self.check_pure(where=where)
        return u0

    def check_pure(self, where=None):
        global tolerant
        value = self.value
        unit = self.unit
        if bool(unit) and (not tolerant or value != 0):
            if where:
                raise UnitCompatibilityError(unit, Unit(), where)
            raise UnitCompatibilityError(unit, Unit())
        return value

    def set_units(self, us):
        """Return a new Value with a different default display unit.

        :param tuple(str) us:  Tuple of units or prefixes that needs to be used
                               when displaying the value
        :rtype Value:          New value with the `showunit` and `showprefix` set
        """
        # We could also use functools.lru_cache instead of cachedat, but it would be
        # probably not as efficient in our situation; also requires python > 3.5
        global cachedat, sortunits, formats, user_ns
        nunits = 0   # num. of units in us
        nvalues = 0  # num. of value'd units in us
        s = Value(self)
        s.showprefix = []
        # If us is just a single format, use it and return
        if len(us) == 1 and us[0] in formats:
            s.showunit = formats[us[0]]
            return s
        # Filter all non-units parts of us, leaving only real units
        oldus = us
        us = []
        for u in oldus:
            if u[-1] == "*":
                if u == "*":
                    s.showprefix.extend(prefixes.keys())
                else:
                    if u[0:-1] not in prefixes:
                        raise UnitParseError(u, "unknown prefix")
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
                if iu and iu[1] == "":
                    s.showprefix.append(u)
                else:
                    nunits += 1
                    us.append(u)
        # Now us contains units or values and no naked prefixes
        us = tuple(us)
        oldus = us
        try:
            m, newus, newvs = cachedat[us]
        except KeyError:
            # Split units and values
            us = []  # list of units, as UnitTree's
            vs = []  # list of values, w/o quotes
            for u in oldus:
                if u[0] in ("'", '"') and u[0] == u[-1]:
                    us.append(UnitTree.simple(u))
                    vs.append(user_ns[u[1:-1]])
                else:
                    up = unit_parser(u)
                    us.append(up[1])
                    vs.append(up[0])
            try:
                if len(us) == 1 and not bool(self.unit) and \
                        not bool(vs[0].unit):
                    s.showunit = us[0]
                    return s
            except ValueError:
                pass
            maxrank = False
            if len(us) == 0:
                maxrank = True
            elif len(us) <= len(baseunits):
                m = np.array([v.unit for v in vs])
                if abs(np.linalg.det(np.dot(m, m.T))) > 1e-7:
                    maxrank = True
            if maxrank:
                newus = us
                newvs = vs
                us = [UnitTree.simple(u) for u in baseunits]
                vs = [units[baseunits[n]] for n, _ in enumerate(baseunits)]
                n = 0
                while len(newus) < len(baseunits):
                    m = np.array([v.unit for v in newvs + [vs[n]]])
                    if abs(np.linalg.det(np.dot(m, m.T))) > 1e-7:
                        newus.append(us[n])
                        newvs.append(vs[n])
                    n += 1
                m = np.array([v.unit for v in newvs])
                cachedat[tuple(oldus)] = (m, newus, newvs)
            else:
                # Check if we are requested a particular unit in a natural system
                # This does not get to the cache, so we always get here!
                if nunits == 1 and nvalues > 0 and not isinstance(us[0], basestring):
                    tmp = Value(1.0, oldus[0].replace('"', "'")).set_units([oldus[0]])
                    out = (self / tmp).set_units(oldus[1:])
                    out.showunit += tmp.showunit
                    out.unit += tmp.unit
                    out.value *= tmp.value
                    return out
                # Deal with a pure number in the other cases: no transformation is done
                if not bool(self.unit):
                    s.showunit = None
                    return s
                # General simple case
                newuvs = zip(us, vs)
                uvs = ODict(newuvs)
                res = None
                for l in range(len(uvs)):
                    g = s.find_compatible(uvs, level=l + 1)
                    try:
                        res = next(g)
                        break
                    except StopIteration:
                        pass
                if res:
                    if sortunits:
                        s.showunit = UnitTree(sorted(res, key=lambda x: x[1] < 0))
                    else:
                        s.showunit = res
                else:
                    s.showunit = None
                # FIXME: remove_variable_units now has a different interface!
                # return s.remove_variable_units()
                return s
        r = zip(newus, np.linalg.solve(m.T, np.array(s.unit)))
        if sortunits:
            r = sorted(r, key=lambda x: x[1] < 0)
        s.showunit = sum((u*e for u, e in r if e != 0), UnitTree())
        # FIXME: remove_variable_units now has a different interface!
        # return s.remove_variable_units()
        return s

    def find_compatible(self, d=None, level=1):
        # Fixme: goes to Unit
        import itertools
        if d is None:
            d = units
        if level == 0:
            for k, v in d.items():
                if isinstance(v, Value) and v.unit == self.unit:
                    yield k
        else:
            ks = d.keys()
            u0 = np.array(self.unit)
            for c in itertools.combinations(ks, abs(level)):
                js = []
                mat = np.zeros(shape=(len(baseunits), abs(level)))
                residuals = 1.0
                for l, cu in enumerate(c):
                    if isinstance(d[cu], tuple):
                        u = d[cu][0].unit
                    else:
                        u = d[cu].unit
                    js.append(cu)
                    mat[:, l] = np.array(u)
                try:
                    if level > 0:
                        x, residuals, rank, sv = np.linalg.lstsq(mat, u0)
                    else:
                        x = np.ones(abs(level), 1)
                except ValueError:
                    continue
                if np.sum(residuals) < 1e-7 and min(map(abs, x)) > 1e-5:
                    yield sum((u * e for u, e in zip(js, x) if e != 0), UnitTree())

    def show(self, latex=False, verbose=False):
        global defaultsystem
        tilde = ""
        mytilde = r"\sim\!" if latex else "~"
        if self.showunit is not None:
            if callable(self.showunit):
                return self.showunit(self, latex=latex, verbose=verbose)
            if self.absolute is not False:
                u0 = self.showunit.to_value()
                if u0.absolute is not False:
                    value = (self.value + self.absolute) / u0.value - u0.absolute
                else:
                    value = self.value / u0.value
            else:
                u0 = self.showunit.to_value()
                if u0.absolute is not False:
                    tilde = mytilde
                    u0.absolute = False
                value = self.value / u0.value
            unit = self.showunit
        elif defaultsystem and self.unit:
            return Value(self).set_units(defaultsystem.args).show(latex=latex, verbose=verbose)
        else:
            value = self.value
            unit = self.unit
        if self.showprefix:
            myunit = None
            myexp = 1  # This is redundant, but avoids an inspection warning
            for u, e in unit:
                if isinstance(u, basestring) and e != 0:
                    myunit = u
                    myexp = e
                    break
            if myunit is not None:
                fprefix = isunit(myunit)[0]
                if fprefix:
                    value = value * prefixes[fprefix] ** myexp
            else:
                myunit = "" if prefixonly else "*"
                myexp = 1
                fprefix = ""
                unit = UnitTree.simple(myunit)
            avalue = abs(value)
            dexes = [(k, avalue / prefixes[k] ** myexp)
                     for k in self.showprefix
                     if prefixes[k] ** myexp <= avalue and
                     (myunit != "" or k not in units)]
            if not dexes:
                dexes = [(k, -avalue / prefixes[k] ** myexp)
                         for k in self.showprefix
                         if myunit != "" or k not in units]
            dex, best = min(dexes, key=lambda x: x[1])
            if dex:
                value = value / prefixes[dex] ** myexp
            unit = UnitTree(((k, v) if k != myunit else
                             (dex + myunit[len(fprefix):], v)
                             for k, v in unit))
        u = unit.show(latex=latex, verbose=verbose)
        if u:
            u = "[" + u + "]"
        if latex:
            if hasattr(value, "_repr_latex_"):
                v = value._repr_latex_()
            else:
                v = str(value)
                v.replace("e", r"\times 10^{%s}")
                v = v.replace("+/-", r" \pm ")
            if v[0] == '$' and v[-1] == '$':
                v = v[1:-1]
        else:
            v = str(value)
        if (v.find(r"+/-") >= 0 or v.find(r"\pm") >= 0) and v.find("(") < 0 and u:
            v = "(" + v + ")"
        if latex:
            return "$" + tilde + v + u + "$"
        else:
            return tilde + v + u

    def __repr__(self):
        return self.show(verbose=verbose)

    def __str__(self):
        return self.show(verbose=verbose)

    # noinspection PyUnusedLocal
    def _repr_pretty_(self, p, cycle):
        if self.showunit is not None and callable(self.showunit):
            p.text(self.showunit(self, pretty=True))
        else:
            p.text(str(self))

    def _repr_latex_(self):
        return self.show(latex=True, verbose=verbose)

    def __coerce__(self, y):
        if y.__class__ != Value:
            y = Value(y)
        return self, y

    # Standard binary operators

    def __add__(self, y):
        if not isinstance(y, Value):
            y = Value(y)
        unit = self.check_units(y)
        if self.absolute is not False and y.absolute is not False:
            raise UnitAbsoluteError(self.absolute, y.absolute)
        return Value(self.value + y.value, unit,
                     absolute=self.absolute or y.absolute)

    def __sub__(self, y):
        if not isinstance(y, Value):
            y = Value(y)
        unit = self.check_units(y)
        offset = (self.absolute or 0.0) - (y.absolute or 0.0)
        absolute = int(self.absolute is not False) - int(y.absolute is not False)
        if absolute < 0:
            raise UnitAbsoluteError(self.absolute, y.absolute)
        if absolute:
            return Value(self.value - y.value, unit, absolute=offset)
        else:
            return Value(self.value - y.value + offset, unit)

    def __mul__(self, y):
        if not isinstance(y, Value):
            y = Value(y)
        absolute = False
        if self.absolute is not None and not bool(y.unit):
            absolute = self.absolute
        elif y.absolute is not None and not bool(self.unit):
            absolute = y.absolute
        return Value(self.value * y.value, self.unit + y.unit, absolute=absolute)

    def __div__(self, y):
        if not isinstance(y, Value):
            y = Value(y)
        absolute = False
        if self.absolute is not None and not bool(y.unit):
            absolute = self.absolute
        return Value(self.value / y.value, self.unit - y.unit, absolute=absolute)

    def __truediv__(self, y):
        if not isinstance(y, Value):
            y = Value(y)
        return Value(self.value / y.value, self.unit - y.unit)

    def __floordiv__(self, y):
        if not isinstance(y, Value):
            y = Value(y)
        return Value(self.value // y.value, self.unit - y.unit)

    def __divmod__(self, y):
        if not isinstance(y, Value):
            y = Value(y)
        unit = self.unit - y.unit
        if hasattr(np, "divmod"):
            # noinspection PyUnresolvedReferences
            d, m = np.divmod(self.value, y.value)
        else:
            d = self.value / y.value
            m = self.value % y.value
        return Value(d, unit), Value(m, unit)

    def __pow__(self, y, modulo=None):
        if not isinstance(y, Value):
            y = Value(y)
        yvalue = y.check_pure()
        if y == 1:
            return self
        return Value(np.power(self.value, yvalue, modulo), self.unit * yvalue)

    def __round__(self, n=None):
        return Value(np.round(self.value, n), self.unit, absolute=self.absolute)

    def __and__(self, y):
        if isinstance(y, Doc):
            return y.__rand__(self)
        else:
            return self.value & y.value

    def __or__(self, y):
        if isinstance(y, System):
            return y.__ror__(self)
        elif not isinstance(y, Value):
            y = Value(y)
        return self.value | y.value

    def __xor__(self, y):
        return self.value ^ y.value

    # Comparison operators

    def __lt__(self, y):
        if not isinstance(y, Value):
            y = Value(y)
        self.check_units(y)
        return self.value < y.value

    def __le__(self, y):
        if not isinstance(y, Value):
            y = Value(y)
        self.check_units(y)
        return self.value <= y.value

    def __gt__(self, y):
        if not isinstance(y, Value):
            y = Value(y)
        self.check_units(y)
        return self.value > y.value

    def __ge__(self, y):
        if not isinstance(y, Value):
            y = Value(y)
        self.check_units(y)
        return self.value >= y.value

    def __eq__(self, y):
        if not isinstance(y, Value):
            y = Value(y)
        self.check_units(y)
        return self.value == y.value

    def __ne__(self, y):
        if not isinstance(y, Value):
            y = Value(y)
        self.check_units(y)
        return self.value != y.value

    def __bool__(self):
        return bool(self.value)

    def __nonzero__(self):
        """Python 2 compatibility method that calls __bool__."""
        return self.__bool__()

    # Reverse methods

    __radd__ = __add__

    def __rsub__(self, y):
        if not isinstance(y, Value):
            y = Value(y)
        unit = self.check_units(y)
        offset = (y.absolute or 0.0) - (self.absolute or 0.0)
        absolute = int(y.absolute is not False) - int(self.absolute is not False)
        if absolute < 0:
            raise UnitAbsoluteError(y.absolute, self.absolute)
        if absolute:
            return Value(y.value - self.value, unit, absolute=offset)
        else:
            return Value(y.value - self.value + offset, unit)

    __rmul__ = __mul__

    def __rdiv__(self, y):
        if not isinstance(y, Value):
            y = Value(y)
        return Value(y.value / self.value, y.unit - self.unit)

    __rtruediv__ = __rdiv__

    def __rfloordiv__(self, y):
        if not isinstance(y, Value):
            y = Value(y)
        return Value(y.value // self.value, y.unit - self.unit)

    def __rmod__(self, y):
        if not isinstance(y, Value):
            y = Value(y)
        return Value(y.value % self.value, y.unit - self.unit)

    def __rdivmod__(self, y):
        if not isinstance(y, Value):
            y = Value(y)
        unit = y.unit - self.unit
        if hasattr(np, "divmod"):
            # noinspection PyUnresolvedReferences
            d, m = np.divmod(y.value, self.value)
        else:
            d = y.value / self.value
            m = y.value % self.value
        return Value(d, unit), Value(m, unit)

    def __rpow__(self, y, **kwargs):
        value = self.check_pure()
        if not isinstance(y, Value):
            y = Value(y)
        return Value(np.power(y.value, value), y.unit * value)

    __rand__ = __and__

    __ror__ = __or__

    __rxor__ = __xor__

    # Unary operators

    def __pos__(self):
        return self

    def __neg__(self):
        if self.absolute is not False:
            return Value(-self.value, self.unit, absolute=-self.absolute)
        else:
            return Value(-self.value, self.unit)

    def __abs__(self):
        return Value(abs(self.value), self.unit)

    def __invert__(self):
        if self.absolute is not False:
            return Value(self.value + self.absolute, self.unit)
        else:
            return Value(self.value, self.unit, absolute=0)

    def __int__(self):
        return int(self.check_pure())

    def __long__(self):
        # This should be long in Python 2: however it is so seldom used that
        # we can safely put int for both Python 2 and 3. Problems are
        # expected only in Python 2 for very large integers.
        return int(self.check_pure())

    def __index__(self):
        import operator
        return operator.index(self.check_pure())

    def __trunc__(self):
        return Value(np.trunc(self.value), self.unit)

    def __float__(self):
        return float(self.check_pure())

    def __complex__(self):
        return self.check_pure().astype(complex)

    # noinspection PyUnusedLocal
    def _mpmath_(self, *args, **kwargs):
        from mpmath import mpmathify
        return mpmathify(self.check_pure())

    def __oct__(self):
        return oct(np.asscalar(self.check_pure()))

    def __hex__(self):
        return hex(np.asscalar(self.check_pure()))


class System(object):
    def __init__(self, *args):
        global systems
        self.args = []
        self.repr = []
        self.doc = ""
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
                if quote == "'":
                    tmp = [a.replace("\"", "'") for a in tmp]
                if quote == '"':
                    tmp = [a.replace("'", "\"") for a in tmp]
                self.args.extend(tmp)
                if sarg[0] == "*" or sarg[-1] == "*":
                    self.args.append("*")
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
            result = expr.set_units(self.args)
        else:
            result = Value(expr).set_units(self.args)
        self.doc = doc
        if doc:
            return doc.__rand__(result)
        else:
            return result

    def __and__(self, y):
        if isinstance(y, Doc):
            self.doc = y
            return self
        elif isinstance(y, System):
            res = System()
            res.args = self.args + y.args
            return res
        else:
            raise TypeError("Unsupported operand types for &: 'System' and '%s'"
                            % y.__class__.__name__)


######################################################################
# Currency symbols

# Extracted from: http://en.wikipedia.org/wiki/List_of_circulating_currencies
currency_symbols = {
    'AED': u'د.إ',
    'AFN': u'؋',
    'BDT': u'৳',
    'BGN': u'лв',
    'BHD': u'.د.ب',
    'CNY': u'元',
    'CRC': u'₡',
    'CZK': u'Kč',
    'DZD': u'د.ج',
    'EGP': u'ج.م',
    'ERN': u'Nfk',
    'EUR': u'€',
    'GBP': u'£',
    'GEL': u'ლ',
    'GHS': u'₵',
    'ILS': u'₪',
    'IQD': u'ع.د',
    'IRR': u'﷼',
    'JOD': u'د.ا',
    'JPY': u'¥',
    'KES': u'Sh',
    'KHR': u'៛',
    'KRW': u'₩',
    'KWD': u'د.ك',
    'LAK': u'₭',
    'LBP': u'ل.ل',
    'LKR': u'රු',
    'LYD': u'ل.د',
    'MAD': u'د.م.',
    'MKD': u'ден',
    'MNT': u'₮',
    'NGN': u'₦',
    'OMR': u'ر.ع.',
    'PHP': u'₱',
    'PLN': u'zł',
    'PYG': u'₲',
    'QAR': u'ر.ق',
    'RSD': u'дин',
    'RUB': u'руб.',
    'SAR': u'ر.س',
    'SYP': u'ل.س',
    'THB': u'฿',
    'TND': u'د.ت',
    'UAH': u'₴',
    'USD': u'$',
    'VND': u'₫',
    'YER': u'﷼'}


######################################################################
# Unit Lexer

reserved = {
    'square': 'SQUARE',
    'cubic': 'CUBIC',
    'squared': 'SQUARED',
    'cubed': 'CUBED',
    'per': 'PER',
    'inverse': 'INVERSE',
    'to': 'TO',
    'the': 'THE',
    'over': 'OVER'
}

# List of token names.   This is always required
tokens = (
    'UNIT',
    'NUMERAL',
    'ORDINAL',
    'FLOAT',
    'NUMDIV',
    'UNITDIV',
    'POW',
    'DOT',
    'LPAREN',
    'RPAREN',
    'QUOTE'
    ) + tuple(reserved.values())

# Regular expression rules for simple tokens
t_NUMDIV = r'/(?=[ \t]*\d)'
t_UNITDIV = r'/(?=[ \t]*\D)'
t_POW = r'\^'
t_DOT = r'\.'
t_LPAREN = r'\('
t_RPAREN = r'\)'
t_QUOTE = r"\'"

# The way units are defined here, they can contain dashes in their name, but not digits
unit_regex = u"([^\\W\\d]+(-[^\\W\\d]+)*|°\\w*|\\$|" + \
             u"|".join([re.escape(_v_) for _v_ in currency_symbols.values()]) + u")"


# A unit, or also a keyword in verbose mode
@lex.TOKEN(unit_regex)
def t_UNIT(t):
    if t.lexer.verbose:
        if t.value in reserved:
            t.type = reserved.get(t.value)
        else:
            try:
                v = cardinal_to_number(t.value)
                t.type = 'NUMBER'
                t.value = v
            except ValueError:
                try:
                    v = ordinal_to_number(t.value, fraction=True)
                    t.type = 'ORDINAL'
                    t.value = v
                except ValueError:
                    pass
    return t


def t_ORDINAL(t):
    r"""(?P<number>[-+]?\d+)(?P<suffix>st|nd|rd|th)"""
    if t.lexer.verbose:
        try:
            t.value = Fraction(int(t.lexer.lexmatch.group("number")), 1) * 1.0
            return t
        except ValueError:
            raise UnitParseError(t.value, "number conversion failed", t.lineno)
    else:
        raise UnitParseError(t.value, "ordinals not allowed in this context", t.lineno)


def t_FLOAT(t):
    r"""[-+]?\d+\.\d+"""
    try:
        t.value = float(t.value)
    except ValueError:
        raise UnitParseError(t.value, "number conversion failed", t.lineno)
    return t


# A regular expression for numbers and ordinals
def t_NUMERAL(t):
    r"""([-+]?\d+)"""
    try:
        t.value = Fraction(int(t.value), 1) * 1.0
    except ValueError:
        raise UnitParseError(t.value, "number conversion failed", t.lineno)
    return t


# Define a rule so we can track line numbers
def t_newline(t):
    r"""\n+"""
    t.lineno += len(t.value)


# A string containing ignored characters (spaces and tabs)
t_ignore = " *\t"


# Error handling rule
def t_error(t):
    raise UnitParseError(t.value[0], "illegal character", t.lineno)


# Build the lexer
unitlex = lex.lex(reflags=re.UNICODE)
unitlex.verbose = False


######################################################################
# Unit Parser

def p_expression(p):
    """expression : expression1
                  | INVERSE expression1
                  | expression UNITDIV expression1
                  | expression PER expression1
    """
    if len(p) == 2:
        p[0] = p[1]
    elif len(p) == 3:
        a = p[2][0]
        if isinstance(a, tuple):
            a = a[1]
        p[0] = (1 / a, -p[2][1])
    else:
        a = p[1][0]
        b = p[3][0]
        if isinstance(a, tuple):
            a = a[1]
        if isinstance(b, tuple):
            b = b[1]
        p[0] = (a / b, p[1][1] - p[3][1])


def p_expression1(p):
    """expression1 : expression1 POW exponent
                   | expression1 POW LPAREN exponent RPAREN
                   | unit_exp
                   | expression1 expression1
                   | expression1 DOT expression1
                   | unit
    """
    if len(p) == 2:
        p[0] = p[1]
    elif len(p) == 3:
        a = p[1][0]
        b = p[2][0]
        if isinstance(a, tuple):
            a = a[1]
        if isinstance(b, tuple):
            b = b[1]
        p[0] = (a * b, p[1][1] + p[2][1])
        return
    elif len(p) == 4 and p[2] == '.':
        a = p[1][0]
        b = p[3][0]
        if isinstance(a, tuple):
            a = a[1]
        if isinstance(b, tuple):
            b = b[1]
        p[0] = (a * b, p[1][1] + p[3][1])
    elif len(p) == 4 and p[2] == '^':
        a = p[1][0]
        if isinstance(a, tuple):
            a = a[1]
        p[0] = (a ** p[3], p[1][1] * p[3])
    else:
        a = p[1][0]
        if isinstance(a, tuple):
            a = a[1]
        p[0] = (a ** p[4], p[1][1] * p[4])


def p_expression1_verbose(p):
    """expression1 : SQUARE expression1
                   | expression1 SQUARED
                   | CUBIC expression1
                   | expression1 CUBED
                   | expression1 TO THE verbose_exponent
    """
    if len(p) == 3:
        if p[1] == 'square':
            x = p[2]
            n = 2
        elif p[2] == 'squared':
            x = p[1]
            n = 2
        elif p[1] == 'cubic':
            x = p[2]
            n = 3
        else:   # must be p[2] == 'cubed'
            x = p[1]
            n = 3
    else:
        x = p[1]
        n = p[4]
    a = x[0]
    if isinstance(a, tuple):
        a = a[1]
    p[0] = (a ** n, x[1] * n)


def p_expression_group(p):
    """expression1 : LPAREN expression RPAREN"""
    p[0] = p[2]


def p_exponent(p):
    """exponent : NUMERAL NUMDIV NUMERAL
                | NUMERAL
                | FLOAT
    """
    if len(p) == 4:
        # p[0] = Fraction(p[1], p[3])
        p[0] = p[1] / p[3]
    else:
        p[0] = p[1]


def p_verbose_exponent(p):
    """verbose_exponent : ORDINAL
                        | NUMERAL ORDINAL
                        | NUMERAL NUMDIV NUMERAL
                        | NUMERAL NUMDIV ORDINAL
                        | NUMERAL OVER NUMERAL
    """
    if len(p) == 4:
        # p[0] = Fraction(p[1], p[3])
        p[0] = p[1] / p[3]
    elif len(p) == 3:
        # p[0] = Fraction(p[1], p[2])
        p[0] = p[1] / p[2]
    else:
        p[0] = p[1]


def p_unit_exp(p):
    """unit_exp : unit NUMERAL
                | unit FLOAT"""
    a = p[1][0]
    if isinstance(a, tuple):
        a = a[1]
    p[0] = (a ** p[2], p[1][1] * p[2])


def p_unit(p):
    """unit : UNIT
            | QUOTE UNIT QUOTE
    """
    global prefixonly, user_ns
    if p[1] == "'":
        variables = user_ns
        if p[2] in variables:
            p[0] = (variables[p[2]], UnitTree.simple("'" + p[2] + "'"))
        else:
            raise UnitParseError(p[2], "unrecognized special unit")
        return
    ku = isunit(p[1], p.parser.verbose)
    if ku:
        k, u = ku
        if k:
            k1 = prefixes[k]
        else:
            k1 = 1
        if u:
            u1 = units[u]
        else:
            u1 = 1
        if p.parser.verbose:
            new_name = p[1]
        else:
            new_name = k + u
        p[0] = (k1 * u1, UnitTree.simple(new_name))
    else:
        raise UnitParseError(p[1], "unrecognized unit")


def p_error(p):
    value = getattr(p, "value", "")
    while 1:
        tok = unityacc.token()             # Get the next token
        if not tok:
            break
    unityacc.restart()
    raise UnitParseError(value, "syntax error")


unityacc = yacc.yacc(write_tables=0, debug=0)
unityacc.verbose = False


######################################################################
# General use functions

def newbaseunit(name, doc=""):
    global baseunits, units, cachedat
    if name in baseunits:
        raise ValueError("Base unit %s already defined" % name)
    baseunits.append(name)
    n_bases = len(baseunits)
    u = np.zeros(n_bases)
    u[-1] = 1
    v = Value(1.0, Unit(u))
    v.__doc__ = doc
    units[name] = v
    verbose_name = extract_name(doc) if doc else name
    verbose_units[verbose_name] = name
    verbose_units[plural(verbose_name)] = name
    # Fix all other units
    for k, u in units.items():
        uu = u.unit
        units[k].unit = Unit(np.hstack((uu, np.zeros(n_bases - len(uu)))))
    for k, u in prefixes.items():
        uu = u.unit
        prefixes[k].unit = Unit(np.hstack((uu, np.zeros(n_bases - len(uu)))))
    cachedat = {}


def newbasecurrency(name, doc=""):
    global cachedat
    from . import currencies
    currencies.basecurrency = name
    newbaseunit(name, doc)


def newprefix(name, value, doc="", source=""):
    global prefixes, verbose_prefixes, cachedat
    v = Value(value)
    v.check_pure()
    v.unit = Unit()                     # Just in case tolerant is True...
    v.__doc__ = doc
    if source:
        v.__source__ = source
    prefixes[name] = v
    verbose_prefixes[extract_name(doc) if doc else name] = name
    cachedat = {}


def delprefix(name):
    global prefixes
    del prefixes[name]
    for k, v in verbose_prefixes.items():
        if v == name:
            del verbose_prefixes[k]


def newunit(name, value, doc="", source=""):
    global units, verbose_units, cachedat
    if not isinstance(value, (int, float, Value, tuple, mpnumeric)):
        raise ValueError("The unit %s must be a simple value or a tuple" % name)
    if isinstance(value, tuple):
        if len(value) != 2:
            raise ValueError("The absolute unit `%s` is not a 2-tuple" % name)
        z, v = Value(value[0]), Value(value[1])
        v.check_units(z)
        v.absolute = z.value
    else:
        v = Value(value)
    if name == "m" or v.unit == units["m"].unit:
        space_units.append(name)
    v = v & Doc(doc)
    if source:
        v.__source__ = source
    units[name] = v
    verbose_units[extract_name(doc) if doc else name] = name
    verbose_name = extract_name(doc) if doc else name
    verbose_units[verbose_name] = name
    verbose_units[plural(verbose_name)] = name
    cachedat = {}


def delunit(name):
    global units
    del units[name]
    for k, v in verbose_units.items():
        if v == name:
            del verbose_units[k]


def newsystem(name, value, doc=""):
    global systems, cachedat
    v = System(*value)
    v.__doc__ = doc
    systems[name] = v
    cachedat = {}


def delsystem(name):
    global systems
    del systems[name]


isunit_re = re.compile('^' + unit_regex + '$', re.UNICODE)


def isunit(fullname, verbose=False):
    global prefixonly
    match = isunit_re.match(fullname)
    if match:
        name = match.group(0)
    else:
        name = fullname
    if verbose:
        if name in verbose_units:
            return "", verbose_units[name]
        elif prefixonly and name in verbose_prefixes:
            return verbose_prefixes[name], ""
        elif name[-1] == "*" and not name[0:-1] in verbose_prefixes:
            return verbose_prefixes[name[0:-1]], ""
        else:
            ks = [k for k in verbose_prefixes.keys()
                  if k == name[:len(k)]]
            for k in ks:
                u = name[len(k):]
                if u in verbose_units:
                    return verbose_prefixes[k], verbose_units[u]
    else:
        if name in units:
            return "", name
        elif prefixonly and name in prefixes:
            return name, ""
        elif name[-1] == "*" and not name[0:-1] in prefixes:
            return name[0:-1], ""
        else:
            ks = [k for k in prefixes.keys() if k == name[:len(k)]]
            for k in ks:
                u = name[len(k):]
                if u in units:
                    return k, u
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

# Should we print out units using verbose strings (such as meter per
# square second) or standard SI notation (such as m s^-2)?
verbose = False

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
verbose_units = ODict()
space_units = ["m"]
prefixes = ODict()
verbose_prefixes = ODict()
systems = ODict()
formats = ODict()
defaultsystem = None
cachedat = {}
newprefix('', Value(1.0))
user_ns = {}


def load_variables(namespace):
    global baseunits, units, prefixes, systems, formats, defaultsystem, user_ns
    namespace['Doc'] = Doc
    namespace['Unit'] = Unit
    namespace['Value'] = Value
    namespace['System'] = System
    namespace['UnitError'] = UnitError
    namespace['baseunits'] = baseunits
    namespace['units'] = units
    namespace['prefixes'] = prefixes
    namespace['systems'] = systems
    namespace['formats'] = formats
    namespace['defaultsystem'] = defaultsystem
    namespace['verbose'] = lambda x: x.show(verbose=True)
    # TODO: remove next line
    namespace['parser'] = unit_parser
    user_ns = namespace


def save_variables(namespace):
    global baseunits, units, prefixes, systems, formats, defaultsystem, user_ns
    baseunits = namespace['baseunits']
    units = namespace['units']
    prefixes = namespace['prefixes']
    systems = namespace['systems']
    formats = namespace['formats']
    defaultsystem = namespace['defaultsystem']
    user_ns = namespace


def reset():
    global baseunits, units, space_units, prefixes, systems, formats, defaultsystem, \
      cachedat
    baseunits = []
    units = ODict()
    space_units = ["m"]
    prefixes = ODict()
    systems = ODict()
    formats = ODict()
    defaultsystem = None
    cachedat = {}
    newprefix('', Value(1.0))
