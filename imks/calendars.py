#!/usr/bin/env python
# -*- coding: utf-8 -*-

# TODO:
# 1. Clean everything!
# 2. Fix mnemonics for Chinese calendar (cycle not working)

import time
from collections import OrderedDict as ODict
from mpmath import mpmathify, floor
from unidecode import unidecode
from . import pycalcal as pcc
from .units import Value
from . import geolocation

try:
    from builtins import str as text
except ImportError:
    from __builtin__ import unicode as text


def caldoc(c):
    import re
    from textwrap import wrap
    keys = list(c.dateparts.keys())
    doc = """A date or datetime in the %s calendar.
    
A date in this calendar can be specified as using the following formats:
  1. A single integer, the date as a fixed number (number of days from 1 January 1 C.E.)
  2. A value with a time-like unit, with an integer number of days (number of days from 1 January 1 C.E.)
  3. The strings "today", "tomorrow", "yesterday", meaning the corresponding day
  4. A full date specification: (%s)
""" % (c.calendar, ", ".join(keys))
    if c.holidays:
        doc += """  4. A holiday specification: (%s, holiday)
""" % (", ".join(keys[0:c.holidayarg]))
    bounds = []
    for p in keys:
        _, min, max = c.dateparts[p]
        bounds.append("%s [%s, %s]" %
                      (p, "-inf" if min is None else min,
                       "+inf" if max is None else max))
    doc += """
The bounds for calendar parts are: %s.
""" % (", ".join(bounds))
    for p in keys:
        if hasattr(c, p + "names"):
            names = ["%s (%d)" % (v, n)
                     for n, v in enumerate(getattr(c, p + "names"))
                     if v != ""]
            doc += """
In the full date, the %s can be entered using the mnemonics: %s.
""" % (p, ", ".join(names))
    if c.holidays:
        names = ["%s (%s)" % (k, ".".join(map(str, v)) if isinstance(v, tuple)
                              else "variable") for k, v in c.holidays.items()]
        doc += """
The calendar has the following known holidays: %s.
""" % ", ".join(names)
    if getattr(c, "weekdays", None):
        doc += """
The weekdays are %s.
""" % ", ".join(c.weekdays)
    doc += ("Alternatively, the function can be used to represent an instant in the\n"
            "%s calendar. The possible formats are:\n"
            "  1. A single float, the date as a fixed number (days and fractions of days "
            "since 12:00:00 of 31 December 1 B.C.E.)\n"
            "  2. A value with a time-like unit (time since 12:00:00 of 31 December 1 B.C.E.)\n"
            "  3. The single string \"now\", meaning the current instant\n"
            "  4. Any of the other previous formats, followed by 1 to 3 arguments: "
            "hours, minutes, and seconds. Any of this argument can be a float\n\n"
            "In this calendar, the day start at %s.\n") % (c.calendar, c.daystart)
    d = c.__dict__.copy()
    doc = unidecode(text(doc))
    pars = []
    for par in doc.split("\n"):
        m = re.match(" *([1-9][-.)]|[-*]) *", par)
        if m:
            nl = "\n" + " "*len(m.group(0))
        else:
            nl = "\n"
        pars.append(nl.join(wrap(par)))
    d["__doc__"] = "\n".join(pars)
    return type(c.__name__, c.__bases__, d)


class CalDate(Value):
    """The base class for all calendar datetimes.

    Subclasses should define the following class attributes:
      calendar:   The name of the calendar.
      prefix:     The prefix of calendar-related functions in PyCalCal.
      dateparts:  An OrderedDict with the parts that compose a full calendar
                  date.  Each key is a date part (for example "year") and the
                  associated value is a triple composed by the associated
                  PyCalCal function to retrieve the datepart, the minimum
                  acceptable value, and the maximum acceptable value (use None
                  for no bound).  The dateparts keys are used by the class
                  __getattr__ to retrieve  the associate datepart: therefore, it
                  is important to use keys that are valid attributes names in
                  Python (in particular, no whitespaces!)
      holidays:   An OrderedDict with the known holidays for the calendar.
                  Keys are the holiday names, values are either a tuple that
                  represents part of a date, or a function that returns a tuple.
      holidayarg: The argument number of a holiday specification.  This typically
                  corresponds to the number of arguments necessary to specify a
                  year in a calendar.  For example, in the Gregorian calendar
                  a holiday is specified as (year, holiday), and therefore
                  holidayarg = 1 (year is argument 0 and holiday is argument 1).
      daystart:   When does a day start in the calendar.  Accepted values are
                  midnight, noon, sunset, sunrise, 6:00, or 18:00
      weeklen:    The length of a week.  This is almost always 7.

    A CalDate instance defines a number of important attributes:
      self.fixed:    The date in fixed format (number of days since 1 January
                     1 C.E.).  It is an integer if the instance is a simple date,
                     or a float if it is a datetime.  For datetimes, this quantity
                     always refers to a UTC datetime.
      self.date:     The date as represented internally by PyCalCal.  Typically
                     this is a tuple with all the dateparts.
      self.datetime: True if the instance is a datetime
      self.tz:       For a datetime instance, the associated timezone, if
                     specified; otherwise None.

    Additionally, since a CalDate instance is also a Value instance, the
    Value-associated attributes (self.value, self.unit, and self.absolute) are
    defined.
    """
    calendar = "Cal"                    # Name of the calendar
    prefix = ""                         # Prefix of functions in PyCalCal
    dateparts = ODict([                 # Parts of a date: name: (getter, min, max)
        ("year", (pcc.standard_year, None, None)),
        ("month", (pcc.standard_month, 1, 12)),
        ("day", (pcc.standard_day, 1, 31))])
    holidays = ODict()                  # dict of holidays
    holidayarg = 1                      # Which argument is the holiday name?
    daystart = "midnight"               # midnight, noon, sunset, sunrise, or time
    weeklen = 7                         # The length of a week

    def __init__(self, *opars, **kw):
        """Initialize an instance of the calendar (a date or a datetime).

        This function is generic enough to work with any implemented calendar.
        Parameters can be provided using different schemes:
          A CalDate instance: A copy of the instance (ev. in a different calendar).
          One integer:        A fixed date.
          One float or Value: A fixed datetime.  If Value is a pure number, it is
                              interpreted as if an implicit "day" were used.  The
                              final object is taken to be a datetime if the
                              associated fixed date is not integer.
          String "now":       The current instant (a datetime).
          String "today":     The current date.  An optional time specification can
                              follow, in which case the object is a datetime.
          Tuple:              The current date following the specification given
                              in the class dateparts attribute.  The date parts can
                              be entered as integers; additionally, if the class
                              defines a member parse_<datepart> (for example,
                              parse_months), the corresponding tuple element can
                              be a string parsed by that function; as a shortcut,
                              if the class defines a list <datepart>_names, the
                              corresponding mnemonic can be used.  The tuple can be
                              followed by a time specification (in which case the
                              object is a datetime).
          A holiday:          It is specified using holidayarg integer arguments,
                              which represent the year, and a string, which must
                              be a key in the holidays class dictionary.

        A time specification must be provided by using up to three additional
        arguments: hours, minutes, and seconds.  Each argument can be an integer
        or a float number.  A day is always taken to be composed by 24 hours.
        However, the day length will not be uniform if the time is measured from
        sunset or sunrise.

        The function also accept a number of keywords:
          datetime:
          tz:
        """
        # First, we call the parent constructor.  This fixes self.unit and
        # self.absolute; moreover, it provides a reference length for a day
        Value.__init__(self, mpmathify(1), "day", absolute=True)
        ref = self.value
        pars = list(opars)              # Parameters can be modified (holidays...)
        self.datetime = kw.get("datetime", None)
        self.tz = kw.get("tz", None)
        self.fixed = None
        if len(pars) >= 1 and isinstance(pars[0], str) and \
                pars[0] in ["today", "tomorrow", "yesterday"]:
            localtime = list(time.localtime()[0:6])
            now = GregorianDate(*localtime[0:3], datetime=True).fixed + \
                (((localtime[3] - 12)*60 + localtime[4])*60 + localtime[5]) \
                / 86400.0
            if pars[0] == "tomorrow":
                now += 1
            elif pars[0] == "yesterday":
                now -= 1
            now = self.__class__(now, datetime=True)
            now.recalc()
            pars = list(now.date) + pars[1:]
        if len(pars) == 1:              # It's a fixed date, a copy, or "now"
            if isinstance(pars[0], CalDate):
                self.fixed = pars[0].fixed
                if self.datetime is None:
                    self.datetime = pars[0].datetime
                if self.tz is None:
                    self.tz = pars[0].tz
            elif isinstance(pars[0], Value):
                if not pars[0].unit:
                    self.fixed = mpmathify(pars[0].value)
                else:
                    pars[0].check_units(self)
                    self.fixed = mpmathify(pars[0].value / ref)
                if self.datetime is None:
                    self.datetime = self.fixed != int(self.fixed)
                elif not self.datetime:
                    self.fixed = int(self.fixed)
            elif isinstance(pars[0], str):
                if pars[0] == "now":
                    localtime = list(time.localtime()[0:6])
                    now = GregorianDate(*localtime[0:3], datetime=True).fixed + \
                        (((localtime[3] - 12)*60 + localtime[4])*60 +
                         localtime[5]) / 86400.0
                    self.fixed = now
                    self.datetime = True
                else:
                    try:
                        self.fixed = mpmathify(pars[0])
                    except TypeError:
                        raise ValueError("Unrecognized date '%s'" % pars[0])
            else:
                self.fixed = pars[0]
                if self.datetime is None:
                    self.datetime = not isinstance(self.fixed, (int, long))
                    # @@@ self.datetime = self.fixed != int(self.fixed)
            if self.fixed is not None:
                self.value = self.fixed * ref
            self.date = None
            # @@@ self.value and all the rest
            return
        # Check possible holidays
        if len(pars) > self.holidayarg and \
                isinstance(pars[self.holidayarg], str):
            found = False
            for hk, hw in self.holidays.items():
                dpar = unidecode(text(pars[self.holidayarg])).lower()
                if unidecode(text(hk)).lower() == dpar:
                    found = True
                    if callable(hw):
                        h = hw(*pars[0:self.holidayarg])
                        if not isinstance(h, (tuple, list)):
                            h = self.__class__(h, datetime=False)
                            h.recalc()
                        pars = h.date + pars[self.holidayarg+1:]
                    else:
                        pars = pars[0:self.holidayarg] + list(hw) + \
                               pars[self.holidayarg+1:]
                    break
            if not found and len(pars) == self.holidayarg + 1 and \
                    len(pars) < len(self.dateparts):
                raise ValueError("Unknown holiday '%s' for %s calendar" %
                                 (pars[self.holidayarg], self.calendar))
        if len(pars) >= len(self.dateparts):
            if self.datetime is None:
                self.datetime = len(pars) > len(self.dateparts)
            for n, par in enumerate(self.dateparts.keys()):
                dummy, min, max = self.dateparts[par]
                # First check if we are using mnemonics
                if isinstance(pars[n], str):
                    parser = getattr(self, "parse_" + par, None)
                    if callable(parser):
                        pars[n] = parser(pars[n])
                    else:
                        parser = getattr(self, par + "names", None)
                        if parser:
                            parser = tuple(unidecode(text(a)).lower()
                                           for a in parser)
                            try:
                                pars[n] = parser.index(unidecode(text(pars[n])).lower())
                            except ValueError:
                                raise ValueError("%s: '%s' is not a valid %s name" %
                                                 (self.calendar, pars[n], par))
                        else:
                            ValueError("%s: no %s name known" %
                                       (self.calendar, par))
                # Now check boundaries
                par_n = int(pars[n])
                if min is not None and par_n < min:
                    raise ValueError("%s: value %d for %s is smaller than minimum acceptable (%d)" %
                                     (self.calendar, int(par_n), par, min))
                if max is not None and par_n > max:
                    raise ValueError("%s: value %d for %s is larger than maximum acceptable (%d)" %
                                     (self.calendar, par_n, par, max))
            # Finally perform the conversion using the PyCalCal functions
            self.date = getattr(pcc, self.prefix + "_date")(*[int(p) for p in pars[0:len(self.dateparts)]])
            self.fixed = getattr(pcc, "fixed_from_" + self.prefix)(self.date)
        else:
            raise ValueError("Wrong number of parameters passed to %s" %
                             self.calendar)
        # All the following is for datetimes
        daylength = 1.0  # The length of the current day in days...
        if self.datetime:
            # First we need to "massage" self.fixed: make it a float number,
            # and correct it for the daystart calendar attribute.
            self.fixed = mpmathify(self.fixed)
            rest = pars[len(self.dateparts):] + [0, 0, 0]
            rest0 = mpmathify(rest[0])  # Hours: used for sunset-sunrise calendars
            if self.daystart == "midnight":
                pass
            elif self.daystart == "noon":
                self.fixed += 0.5
            elif self.daystart == "6:00":
                self.fixed += 0.25
            elif self.daystart == "sunrise":
                f = sunrise(self.fixed)
                daylength = sunrise(self.fixed + 1) - f
                self.fixed += f - floor(f) - 0.5
            elif self.daystart == "sunset":
                f = sunset(self.fixed - 1)
                daylength = sunset(self.fixed) - f
                self.fixed += f - floor(f) - 0.5
            elif self.daystart == "sunrise-sunset":
                if rest0 < 12:
                    f = sunrise(self.fixed)
                    daylength = (sunset(self.fixed) - f)*2
                else:
                    f = sunset(self.fixed)
                    daylength = (sunrise(self.fixed + 1) - f)*2
                    pars[len(self.dateparts)] -= 12
                self.fixed += f - floor(f) - 0.5
            elif self.daystart == "sunset-sunrise":
                if rest0 < 12:
                    f = sunset(self.fixed - 1)
                    daylength = (sunrise(self.fixed) - f)*2
                else:
                    f = sunrise(self.fixed)
                    daylength = (sunset(self.fixed) - f)*2
                    pars[len(self.dateparts)] -= 12
                self.fixed += f - floor(f) - 0.5
        if len(pars) > len(self.dateparts):
            mins = [0, 0, 0]
            maxs = [24, 60, 60]
            names = ["hour", "minute", "second"]
            rest = pars[len(self.dateparts):] + [0, 0, 0]
            for n in [0, 1, 2]:
                if rest[n] < mins[n]:
                    raise ValueError("%s: value %d for %s is smaller than minimum acceptable (%d)" %
                                     (self.__class__.__name__, rest[n], names[n], mins[n]))
                if rest[n] >= maxs[n]:
                    raise ValueError("%s: value %d for %s is not smaller than maximum acceptable (%d)" %
                                     (self.__class__.__name__, rest[n], names[n], maxs[n]))
            f = mpmathify(rest[0])/24 + mpmathify(rest[1])/1440 + \
                mpmathify(rest[2])/86400
            self.fixed += f / daylength - 0.5
        # @@@ Timezone corrections
        self.value = Value(self.fixed, "day").value

    # Standard operations
    def __copy__(self):
        result = self.__class__(self.fixed)
        result.datetime = self.datetime
        result.date = self.date
        result.tz = self.tz
        return result
    copy = __copy__
    __deepcopy__ = __copy__

    # A.2. Sums and subtractions
    def __add__(self, y):
        if not isinstance(y, Value):
            y = Value(y)
        if not bool(y.unit):
            delta = y.value
            datetime = self.datetime or not isinstance(delta, (int, long))
        else:
            delta = y.value / Value(1, "day").value
            datetime = self.datetime or delta != floor(delta)
        if y.absolute:
            raise ValueError("Cannot add two absolute values")
        return self.__class__(self.fixed + delta, datetime=datetime,
                              tz=self.tz)

    def __sub__(self, y):
        if isinstance(y, Value):
            if not bool(y.unit):
                delta = y.value
                datetime = self.datetime or not isinstance(delta, (int, long))
            else:
                delta = y.value / Value(1, "day").value
                datetime = self.datetime or delta != floor(delta)
            absolute = not y.absolute
        elif isinstance(y, CalDate):
            delta = y.fixed
            absolute = False
            datetime = self.datetime or y.datetime
        else:
            delta = y
            datetime = self.datetime or not isinstance(delta, (int, long))
            absolute = True
        if absolute:
            return self.__class__(self.fixed - delta, datetime=datetime,
                                  tz=self.tz)
        else:
            return Value(self.fixed - delta, "day")
    __radd__ = __add__

    def __rsub__(self, y):
        return y.__sub__(self)
    
    # A.4. String operations
    def __repr__(self):
        return str(self)

    def _repr_latex_(self):
        return str(self)

    def __str__(self):
        return unidecode(self)

    def show(self):
        return self.calendar + "(" + ",".join(map(str, self.date)) + ")"

    def showtimeofday(self):
        if self.datetime is False:
            return ""
        fday = self.fixed - round(self.fixed)
        f = (fday + 0.5) * 24 + 0.5 / 3600
        h = floor(f)
        f = (f - h)*60
        m = floor(f)
        f = (f - m)*60
        s = floor(f)
        # f = (f - m)*1000
        # ms = floor(f)
        if h or m or s or self.datetime:
            return ", %02d:%02d:%02d" % (h, m, s)
        else:
            return ""

    # B. Data update and extraction
    def recalc(self):
        if not self.date:
            fixed = self.fixed
            if self.datetime:
                if self.daystart == "midnight":
                    pass
                elif self.daystart == "noon":
                    fixed -= 0.5
                elif self.daystart == "6:00":
                    fixed -= 0.25
                elif self.daystart == "sunrise":
                    for iter in [0, 1]:
                        f = sunrise(fixed)
                        fixed = self.fixed - (f - floor(f) - 0.5)
                elif self.daystart == "sunset":
                    for iter in [0, 1]:
                        f = sunset(fixed - 1)
                        fixed = self.fixed - (f - floor(f) - 0.5)
            self.date = getattr(pcc, self.prefix + "_from_fixed")(int(round(fixed)))
        return self

    def __dir__(self):
        names = ["realdate", "weekday"] + \
                self.dateparts.keys() + self.__dict__.keys()
        o = self.__class__
        while True:
            names = names + o.__dict__.keys()
            if o.__bases__:
                o = o.__bases__[0]
            else:
                break
        names.sort()
        return names

    def __getattr__(self, name):
        if name in self.dateparts.keys():
            self.recalc()
            return self.dateparts[name][0](self.date)
        elif name == 'realdate':
            self.recalc()
            return self.date
        elif name == 'weekday':
            if self.datetime:
                self.recalc()
                if self.daystart == 'noon':
                    offset = -1
                else:
                    offset = 0
                return pcc.day_of_week_from_fixed(int(round(self.fixed))
                                                  + offset)
            else:
                return pcc.day_of_week_from_fixed(int(round(self.fixed)))
        else:
            raise AttributeError("'%s' object has no attribute '%s'" %
                                 (self.calendar, name))

    # C. Year operations (use only the year of self)
    def is_leap_year(self):
        return getattr(pcc, "is_" + self.prefix + "_leap_year")(self.year)

    def year_begin(self):
        pass

    def year_end(self):
        pass

    def specialday(self, name):
        pass

    # D. Weekday operations
    def kday_on_or_before(self, k):
        return self - (self - k).weekday

    def kday_on_or_after(self, k):
        return (self + self.weeklen - 1).kday_on_or_before(k)

    def kday_before(self, k):
        return (self - 1).kday_on_or_before(k)

    def kday_after(self, k):
        return (self + self.weeklen).kday_on_or_before(k)

    def kday_nearest(self, k): 
        return (self + self.weeklen/2).kday_on_or_before(k)

    def kday_nth(self, k, n):
        if n > 0:
            if n == int(n):
                return self.weeklen*n + self.kday_on_or_before(k)
            else:
                return self.weeklen*int(n + 1) + self.kday_before(k)
        elif n < 0:
            if n == int(n):
                return self.weeklen*n + self.kday_on_or_after(k)
            else:
                return self.weeklen*int(n - 1) + self.kday_after(k)
        elif n == 0:
            return self.kday_nearest(k)


# JD Dates

class JDDate(CalDate):
    calendar = "JD"
    prefix = "jd"
    dateparts = ODict([
        ("jd", (lambda x: x[0], None, None))])

    def __init__(self, *pars, **kw):
        if len(pars) != 1:
            raise ValueError("Wrong number of parameters passed to %s" %
                             self.calendar)
        self.date = None
        if isinstance(pars[0], CalDate):
            self.fixed = pars[0].fixed
        elif kw.get("date", False) is False:
            self.fixed = pars[0]
        else:
            self.date = [int(pars[0])]
            self.fixed = pcc.fixed_from_jd(pars[0])
        self.weeklen = 7

    def recalc(self):
        if not self.date:
            self.date = (pcc.jd_from_fixed(self.fixed),)
        return self

    def __str__(self):
        return "JD%d" % self.date[0]

    def year_begin(self):
        raise NotImplemented

    def year_end(self):
        raise NotImplemented


# MJD Dates
class MJDDate(CalDate):
    calendar = "MJD"
    prefix = "mjd"
    dateparts = ODict([
        ("mjd", (lambda x: x[0], None, None))])

    def __init__(self, *pars, **kw):
        if len(pars) != 1:
            raise ValueError("Wrong number of parameters passed to %s" %
                             self.calendar)
        self.date = None
        if isinstance(pars[0], CalDate):
            self.fixed = pars[0].fixed
        elif kw.get("date", False) is False:
            self.fixed = pars[0]
        else:
            self.date = [int(pars[0])]
            self.fixed = pcc.fixed_from_mjd(pars[0])
        self.weeklen = 7

    def recalc(self):
        if not self.date:
            self.date = (pcc.mjd_from_fixed(self.fixed),)
        return self

    def __str__(self):
        return "MJD%d" % self.date[0]

    def year_begin(self):
        raise NotImplemented

    def year_end(self):
        raise NotImplemented


# Gregorian Dates
@caldoc
class GregorianDate(CalDate):
    calendar = "Gregorian"
    prefix = "gregorian"
    weekdays = ('Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 
                'Friday', 'Saturday')
    monthnames = ("", "January", "February", "March", "April", "May", "June", "July",
                  "August", "September", "October", "November", "December")
    holidays = ODict([
        ("New Year", (1, 1)),
        ("Epiphany", (1, 6)),
        ("Easter", pcc.easter),
        ("Septuagesima Sunday", lambda y: pcc.easter(y) - 63),
        ("Sexagesima Sunday", lambda y: pcc.easter(y) - 56),
        ("Shrove Sunday", lambda y: pcc.easter(y) - 49),
        ("Shrove Monday", lambda y: pcc.easter(y) - 48),
        ("Shrove Tuesday", lambda y: pcc.easter(y) - 47),
        ("Mardi Gras", lambda y: pcc.easter(y) - 47),
        ("Ash Wednesday", lambda y: pcc.easter(y) - 46),
        ("Passion Sunday", lambda y: pcc.easter(y) - 14),
        ("Palm Sunday", lambda y: pcc.easter(y) - 7),
        ("Holy Thursday", lambda y: pcc.easter(y) - 3),
        ("Good Friday", lambda y: pcc.easter(y) - 2),
        ("Rogation Sunday", lambda y: pcc.easter(y) + 35),
        ("Ascension Day", lambda y: pcc.easter(y) + 39),
        ("Pentecost", lambda y: pcc.easter(y) + 49),
        ("Whidmundy", lambda y: pcc.easter(y) + 50),
        ("Thrinity Sunday", lambda y: pcc.easter(y) + 56),
        ("Corpus Christi", lambda y: pcc.easter(y) + 60),
        ("Orthodox Easter", pcc.orthodox_easter),
        ("Orthodox Lent begin", lambda y: pcc.orthodox_easter(y) - 48),
        ("Fest of Orthodoxy", lambda y: pcc.orthodox_easter(y) - 42),
        ("Advent", lambda y: GregorianDate(y, 11, 30).kday_nearest(0)),
        ("Christmas", (12, 25))])

    def __str__(self):
        return "%s, %d %s %d%s" % (self.weekdays[self.weekday], self.day,
                                   self.monthnames[self.month], self.year,
                                   self.showtimeofday())

    def year_begin(self):
        return GregorianDate(self.year, 1, 1)

    def year_end(self):
        return GregorianDate(self.year, 12, 31)


# Julian Dates
@caldoc
class JulianDate(CalDate):
    calendar = "Julian"
    prefix = "julian"
    weekdays = ('Solis dies (Dies dominica)', 'Lunae dies (Feria secunda)',
                'Martis dies (Feria tertia)', 'Mercurii dies (Feria quarta)',
                'Iovis dies (Feria quinta)', 'Veneris dies (Feria Sexta)',
                'Saturni dies (Sabbatum)')
    monthnames = ("", "Januarius", "Februarius", "Mars", "Aprilis", "Maius", "Iunius",
                  "Julius", "Augustus", "September", "October", "November", "December")
    holidays = ODict([
        ("New Year", (1, 1)),
        ("Epiphany", (1, 6)),
        ("Easter", pcc.easter),
        ("Septuagesima Sunday", lambda y: pcc.easter(y) - 63),
        ("Sexagesima Sunday", lambda y: pcc.easter(y) - 56),
        ("Shrove Sunday", lambda y: pcc.easter(y) - 49),
        ("Shrove Monday", lambda y: pcc.easter(y) - 48),
        ("Shrove Tuesday", lambda y: pcc.easter(y) - 47),
        ("Mardi Gras", lambda y: pcc.easter(y) - 47),
        ("Ash Wednesday", lambda y: pcc.easter(y) - 46),
        ("Passion Sunday", lambda y: pcc.easter(y) - 14),
        ("Palm Sunday", lambda y: pcc.easter(y) - 7),
        ("Holy Thursday", lambda y: pcc.easter(y) - 3),
        ("Good Friday", lambda y: pcc.easter(y) - 2),
        ("Rogation Sunday", lambda y: pcc.easter(y) + 35),
        ("Ascension Day", lambda y: pcc.easter(y) + 39),
        ("Pentecost", lambda y: pcc.easter(y) + 49),
        ("Whidmundy", lambda y: pcc.easter(y) + 50),
        ("Thrinity Sunday", lambda y: pcc.easter(y) + 56),
        ("Corpus Christi", lambda y: pcc.easter(y) + 60),
        ("Orthodox Easter", pcc.orthodox_easter),
        ("Orthodox Lent begin", lambda y: pcc.orthodox_easter(y) - 48),
        ("Fest of Orthodoxy", lambda y: pcc.orthodox_easter(y) - 42),
        ("Advent", lambda y: GregorianDate(y, 11, 30).kday_nearest(0)),
        ("Christmas", (12, 25))])

    def __init__(self, *pars, **kw):
        CalDate.__init__(self, *pars, **kw)
        if len(pars) == 3:
            self.date = pcc.julian_date(*pars)
            self.fixed = pcc.fixed_from_julian(self.date)

    def __str__(self):
        if self.year > 0:
            era = "C.E."
        else:
            era = "B.C.E."
        return "%s, %d %s %d %s%s" % (self.weekdays[self.weekday], self.day,
                                      self.monthnames[self.month], abs(self.year), era,
                                      self.showtimeofday())

    def year_begin(self):
        return JulianDate(self.year, 1, 1)

    def year_end(self):
        return JulianDate(self.year, 12, 31)


# Roman (Julian) Dates
@caldoc
class RomanDate(CalDate):
    calendar = "Roman"
    prefix = "roman"                    # Prefix of functions in PyCalCal
    dateparts = ODict([
        ("year", (pcc.roman_year, None, None)),
        ("month", (pcc.roman_month, 1, 12)),
        ("event", (pcc.roman_event, 1, 3)),
        ("count", (pcc.roman_count, 1, 19)),
        ("leap", (pcc.roman_leap, 0, 1))])
    weekdays = ('Solis dies (Dies dominica)', 'Lunae dies (Feria secunda)',
                'Martis dies (Feria tertia)', 'Mercurii dies (Feria quarta)',
                'Iovis dies (Feria quinta)', 'Veneris dies (Feria Sexta)',
                'Saturni dies (Sabbatum)')
    monthnamesacc = ("", "Ianuarias", "Februarias", "Martias", "Aprilias", "Maias",
                     "Iunias", "Iulias", "Augustas", "Septembres", "Octobres",
                     "Novembres", "Decembres")
    monthnamesabl = ("", "Ianuariis", "Februariis", "Martiis", "Aprilibus", "Maiis",
                     "Iuniis", "Iuliis", "Augustis", "Septembribus", "Octobribus",
                     "Novembribus", "Decembribus")
    eventsacc = ("Kalendas", "Nonas", "Idus")
    eventsabl = ("Kalendis", "Nonis", "Idibus")

    def __init__(self, *pars, **kw):
        CalDate.__init__(self, *pars, **kw)
        if len(pars) == 5:
            self.date = pcc.roman_date(*pars)
            self.fixed = pcc.fixed_from_julian(self.date)

    def __str__(self):
        if self.leap:
            count = "a.d. bis vi "
        else: 
            count = ["", "pridie ", "a.d. iii ", "a.d. iv ", "a.d. v ", "a.d. vi ",
                     "a.d. vii ", "a.d. viii ", "a.d. ix ", "a.d. x ", "a.d. xi ",
                     "a.d. xii ", "a.d. xiii ", "a.d. xiv ", "a.d. xv ", "a.d. xvi ",
                     "a.d. xvii ", "a.d. xviii ", "a.d. xix ", "a.d. xx "][self.count-1]
        if count == "":
            event = self.eventsabl[self.event-1] + " " + self.monthnamesabl[self.month]
        else:
            event = count + self.eventsacc[self.event-1] + " " + \
                    self.monthnamesacc[self.month]
        return "%s, %s %d A.U.C.%s" % (self.weekdays[self.weekday], event,
                                       pcc.auc_year_from_julian_year(self.year),
                                       self.showtimeofday())

    def is_leap_year(self):
        return pcc.is_julian_leap_year(self.year)

    def year_begin(self):
        return RomanDate(self.year, 1, 1)

    def year_end(self):
        return RomanDate(self.year, 12, 31)


# Egyptian Dates
@caldoc
class EgyptianDate(CalDate):
    calendar = "Egyptian"
    prefix = "egyptian"
    dateparts = ODict([
        ("year", (pcc.standard_year, None, None)),
        ("month", (pcc.standard_month, 1, 13)),
        ("day", (pcc.standard_day, 1, 30))])
    weekdays = ('Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 
                'Friday', 'Saturday')
    monthnames = ("", "First of Akhet (Thoth)", "Second of Akhet (Phaophi)",
                  "Third of Akhet (Athyr)", "Fourth of Akhet (Choiak)",
                  "First of Peret (Tybi)", "Second of Peret (Mechir)",
                  "Third of Peret (Phamenoth)", "Fourth of Peret (Pharmuthi)",
                  "First of Shemu (Pachon)", "Second of Shemu (Payni)",
                  "Third of Shemu (Epiphi)", "Fourth of Shemu (Mesori)",
                  "Epagomenae")

    def __str__(self):
        return "%d %s %d%s" % (self.day, self.monthnames[self.month], self.year,
                               self.showtimeofday())

    def is_leap_year(self):
        return False

    def year_begin(self):
        return EgyptianDate(self.year, 1, 1)

    def year_end(self):
        return EgyptianDate(self.year, 13, 5)


# Armenian Dates
@caldoc
class ArmenianDate(CalDate):
    calendar = "Armenian"
    prefix = "armenian"
    dateparts = ODict([
        ("year", (pcc.standard_year, None, None)),
        ("month", (pcc.standard_month, 1, 13)),
        ("day", (pcc.standard_day, 1, 31))])
    weekdays = ('Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 
                'Friday', 'Saturday')
    monthnames = ("", "Nawasardi", "Hori", "Sahimi", u"Trē", "K`aloch", "Arach",
                  "Mehekani", "Areg", "Ahekani", "Mareri", "Margach", "Hrotich",
                  "Epagomenae")

    def __str__(self):
        return "%d %s %d%s" % (self.day, self.monthnames[self.month], self.year,
                               self.showtimeofday())

    def is_leap_year(self):
        return False

    def year_begin(self):
        return ArmenianDate(self.year, 1, 1)

    def year_end(self):
        return ArmenianDate(self.year, 13, 5)


# ISO Dates
@caldoc
class ISODate(CalDate):
    calendar = "ISO"
    prefix = "iso"
    dateparts = ODict([
        ("year", (pcc.iso_year, None, None)),
        ("week", (pcc.iso_week, 1, 53)),
        ("day", (pcc.iso_day, 1, 7))])
    weekdays = ('Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 
                'Friday', 'Saturday')

    def __str__(self):
        return "%s, week %d, %d%s" % (self.weekdays[self.weekday], self.week,
                                      self.year, self.showtimeofday())

    def is_leap_year(self):
        return pcc.is_iso_long_year(self.year)

    def year_begin(self):
        return ISODate(self.year, 1, 1)

    def year_end(self):
        if self.is_leap_year():
            return ISODate(self.year, 53, 7)
        else:
            return ISODate(self.year, 52, 7)


# Coptic Dates
@caldoc
class CopticDate(CalDate):
    calendar = "Coptic"
    prefix = "coptic"
    dateparts = ODict([
        ("year", (pcc.standard_year, None, None)),
        ("month", (pcc.standard_month, 1, 13)),
        ("day", (pcc.standard_day, 1, 31))])
    weekdays = (u"Tkyriakē", "Pesnau", "Pshament", "Peftoou", "Ptiou", "Psoou",
                "Psabbaton")
    monthnames = ("", "Thoout", "Paope", u"Athōr", "Koiak", u"Tōbe", "Meshir",
                  "Paremotep", "Parmoute", "Pashons", u"Paōne", u"Epēp", u"Mesorē",
                  u"Epagomenē")
    daystart = "sunset"              # midnight, noon, sunset, sunrise

    def __str__(self):
        return "%s, %d %s %d%s" % (self.weekdays[self.weekday], self.day,
                                   self.monthnames[self.month], self.year,
                                   self.showtimeofday())

    def year_begin(self):
        return CopticDate(self.year, 1, 1)

    def year_end(self):
        return CopticDate(self.year, 12, 31)
        

# Ethiopic Dates
@caldoc
class EthiopicDate(CalDate):
    calendar = "Ethiopic"
    prefix = "ethiopic"
    dateparts = ODict([
        ("year", (pcc.standard_year, None, None)),
        ("month", (pcc.standard_month, 1, 13)),
        ("day", (pcc.standard_day, 1, 31))])
    weekdays = (u"Iḥud", "Sanyo", "Maksanyo", "Rob", u"H̱amus", "Arb", u"Kidāmmē")
    monthnames = ("", "Maskaram", "Teqemt", u"H̱edār", u"Tākhśāś", u"Ṭer", u"Hakātit",
                  u"Magābit", u"Miyāzyā", "Genbot", u"Sanē", u"Ḥamlē", u"Naḥasē",
                  u"Pāguemēn")
    daystart = "sunset"              # midnight, noon, sunset, sunrise

    def __str__(self):
        return "%s, %d %s %d%s" % (self.weekdays[self.weekday], self.day,
                                   self.monthnames[self.month], self.year,
                                   self.showtimeofday())

    def year_begin(self):
        return EthiopicDate(self.year, 1, 1)

    def year_end(self):
        return EthiopicDate(self.year, 12, 31)


# Islamic Dates
@caldoc
class IslamicDate(CalDate):
    calendar = "Islamic"
    prefix = "islamic"
    dateparts = ODict([
        ("year", (pcc.standard_year, None, None)),
        ("month", (pcc.standard_month, 1, 12)),
        ("day", (pcc.standard_day, 1, 30))])
    weekdays = (u"Yawm al-aḥad", "Yawm al-ithnayna", u"Yawm ath-thalāthā'",
                u"Yawm al-arba`ā'", u"Yawm al-ẖamīs", "Yawm al-jumu`ah",
                "Yawm as-sabt")
    monthnames = ("", u"Muḥarram", u"Ṣafar", u"Rabī` I", u"Rabī` II", u"Jumādā I",
                  u"Jumādā II", "Rajab", u"Sha`bān", u"Ramaḍān", u"Shawwāl",
                  u"Dhu al-Qa'da", u"Dhu al-Ḥijja")
    holidays = ODict([
        ("New Year", (1, 1)),
        (u"Ashūrā'", (1, 10)),
        (u"Muwlid an-Nabī", (3, 12)),
        (u"Lailat-al-Mi`rāj", (7, 27)),
        (u"`Īd-al-Fiṭr", (10, 1)),
        (u"`Īd-al-'Aḍḥā", (12, 10))])
    daystart = "sunset"              # midnight, noon, sunset, sunrise

    def __str__(self):
        return u"%s, %d %s %d%s" % (self.weekdays[self.weekday], self.day,
                                    self.monthnames[self.month], self.year,
                                    self.showtimeofday())

    def year_begin(self):
        return IslamicDate(self.year, 1, 1)

    def year_end(self):
        return IslamicDate(self.year + 1, 1, 1) - 1

    
# Hebrew Dates
def hebrew_ta_anit_esther(year):
    d = pcc.fixed_from_hebrew(pcc.hebrew_date(year,
                                              pcc.last_month_of_hebrew_year(year), 14))
    if pcc.day_of_week_from_fixed(d) == 0:
        d -= 2
    return d


def hebrew_fast_day(year, month, day):
    d = pcc.fixed_from_hebrew(pcc.hebrew_date(year, month, day))
    if pcc.day_of_week_from_fixed(d) == 6:
        d += 1
    return d


def hebrew_yom_ha_shoah(year):
    d = pcc.fixed_from_hebrew(pcc.hebrew_date(year, 1, 27))
    if pcc.day_of_week_from_fixed(d) == 0:
        d += 1
    return d


def hebrew_yom_ha_zikkaron(year):
    iyyar4 = pcc.fixed_from_hebrew(pcc.hebrew_date(year, pcc.IYYAR, 4))
    if pcc.day_of_week_from_fixed(iyyar4) in [pcc.THURSDAY, pcc.FRIDAY]:
        return pcc.kday_before(pcc.WEDNESDAY, iyyar4)
    elif pcc.SUNDAY == pcc.day_of_week_from_fixed(iyyar4):
        return iyyar4 + 1
    else:
        return iyyar4


@caldoc
class HebrewDate(CalDate):
    calendar = "Hebrew"
    prefix = "hebrew"
    dateparts = ODict([
        ("year", (pcc.standard_year, None, None)),
        ("month", (pcc.standard_month, 1, 13)),
        ("day", (pcc.standard_day, 1, 30))])
    weekdays = ("Yom rishon", "Yom sheni", "Yom shelishi", "Yom revi`i",
                u"Yom ḥamishi", "Yom shishi", "Yom shabbat")
    monthnames = ("", "Nisan", "Iyyar", "Sivan", "Tammuz", "Av", "Elul", "Tishri",
                  u"Marḥeshvan", "Kislev", "Tevet", "Shevat", "Adar", "Adar II")    
    holidays = ODict([
        ("Rosh ha-Shanah", (7, 1)),
        ("Yom Kippur", (7, 10)),
        ("Sukkot", (7, 15)),
        ("Hoshana Rabba", (7, 21)),
        (u"Shemini Aẓaret", (7, 22)),
        (u"Simḥat Torah", (7, 23)),
        ("Passover", (1, 15)),
        ("Ending of passover", (1, 21)),
        ("Shavuot", (3, 6)),
        ("Purim", lambda y:
         pcc.fixed_from_hebrew(pcc.hebrew_date(y, pcc.last_month_of_hebrew_year(y),
                                               14))),
        # Fast days
        ("Tzom Gedaliah", lambda y: hebrew_fast_day(y, 7, 3)),
        ("Tzom Tevet", lambda y: hebrew_fast_day(y, 10, 10)),
        ("Ta'anit Esther", hebrew_ta_anit_esther),
        ("Tzom Tammuz", lambda y: hebrew_fast_day(y, 4, 17)),
        ("Tishah be-Av", lambda y: hebrew_fast_day(y, 5, 9)),
        ("Yom ha-Shoah", hebrew_yom_ha_shoah),
        ("Yom ha-Zikkaron", hebrew_yom_ha_zikkaron)])
    # Go ahead p. 136 with "Ta'anit Esther"
    daystart = "sunset"               # midnight, noon, sunset, sunrise

    def __str__(self):
        return u"%s, %d %s %d%s" % (self.weekdays[self.weekday], self.day,
                                    self.monthnames[self.month], self.year,
                                    self.showtimeofday())

    def year_begin(self):
        return HebrewDate(pcc.hebrew_new_year(self.year))

    def year_end(self):
        return HebrewDate(pcc.hebrew_new_year(self.year + 1)) - 1
    

# Mayan Long Count Dates
@caldoc
class MayanLongCountDate(CalDate):
    calendar = "MayanLongCount"
    prefix = "mayan_long_count"
    dateparts = ODict([
        ("baktun", (pcc.mayan_baktun, None, None)),
        ("katun", (pcc.mayan_katun, 0, 19)),
        ("tun", (pcc.mayan_tun, 0, 17)),
        ("uinal", (pcc.mayan_uinal, 0, 19)),
        ("kin", (pcc.mayan_kin, 0, 19))])

    def __str__(self):
        return u"%d.%d.%d.%d.%d%s" % (self.baktun, self.katun, self.tun, self.uinal,
                                      self.kin, self.showtimeofday())

    def is_leap_year(self):
        return False

    def year_begin(self):
        return MayanLongCountDate(self.baktun, 0, 0, 0, 0)

    def year_end(self):
        if self.is_leap_year():
            return MayanLongCountDate(self.year, 12, 30)
        else:
            return MayanLongCountDate(self.baktun, 19, 19, 17, 19)

    
# Old Hindu Lunar Date
@caldoc
class OldHinduLunarDate(CalDate):
    calendar = "OldHinduLunar"
    prefix = "old_hindu_lunar"
    dateparts = ODict([
        ("year", (pcc.old_hindu_lunar_year, None, None)),
        ("month", (pcc.old_hindu_lunar_month, 1, 12)),
        ("leap", (pcc.old_hindu_lunar_leap, 0, 1)),
        ("day", (pcc.old_hindu_lunar_day, 1, 30))])
    weekdays = (u"Ravivāra", u"Somavāra", u"Maṅglavāra", u"Budhavāra",
                u"Bṛihaspatvāra", u"Śukravāra", u"Śanivāra")
    monthnames = ("", "Caitra", u"Vaiśākha", u"Jyeṣṭha", u"Āṣāḍha", u"Śrāvaṇa",
                  u"Bhādrapada", u"Āśvina", u"Kārtika", u"Mārgaśīrṣa", u"Pauṣa",
                  u"Māgha", u"Phālguna")
    daystart = "6:00"              # midnight, noon, sunset, sunrise

    def __str__(self):
        if self.leap:
            added = " adhika"
        else:
            added = ""
        return "%s, %d %s%s %d%s" % (self.weekdays[self.weekday], self.day,
                                     self.monthnames[self.month], added, self.year,
                                     self.showtimeofday())

    def year_begin(self):
        return OldHinduLunarDate(self.year, 1, self.is_leap_year(), 1)

    def year_end(self):
        raise NotImplemented


# Old Hindu Solar Date
@caldoc
class OldHinduSolarDate(CalDate):
    calendar = "OldHinduSolar"
    prefix = "old_hindu_solar"
    weekdays = (u"Ravivāra", u"Somavāra", u"Maṅglavāra", u"Budhavāra",
                u"Bṛihaspatvāra", u"Śukravāra", u"Śanivāra")
    monthnames = ("", u"Meṣa", u"Vṛṣabha", "Mithuna", "Karka", u"Siṃha", u"Kanyā",
                  u"Tulā", u"Vṛścika", u"Dhanus", "Makara", u"Mīna")
    daystart = "6:00"              # midnight, noon, sunset, sunrise

    def __str__(self):
        return "%s, %d %s %d%s" % (self.weekdays[self.weekday], self.day,
                                   self.monthnames[self.month], self.year,
                                   self.showtimeofday())

    def year_begin(self):
        return OldHinduSolarDate(self.year, 1, 1)

    def year_end(self):
        return OldHinduSolarDate(self.year + 1, 1, 1) - 1


# Persian Dates
@caldoc
class PersianDate(CalDate):
    calendar = "Persian"
    prefix = "persian"
    weekdays = (u"Yek-shanbēh", u"Do-shanbēh", u"Se-shanbēh",
                u"Chār-shanbēh", u"Panj-shanbēh", u"Jom`ēh", u"Shanbēh")
    monthnames = ("", u"Farvardīn", u"Ordībehesht", u"Xordād", u"Tīr", u"Mordād",
                  u"Shahrīvar", u"Mehr", u"Ābān", u"Ābān", u"Āzar", "Dey",
                  "Bahman", "Esfand")
    holidays = ODict([
        ("Naz Ruz", (1, 1))])
    daystart = "noon"

    def __init__(self, *pars, **kw):
        CalDate.__init__(self, *pars, **kw)
        if len(pars) == 3:
            self.date = pcc.persian_date(*pars)
            self.fixed = pcc.fixed_from_persian(self.date)

    def __str__(self):
        return "%s, %d %s %d%s" % (self.weekdays[self.weekday], self.day,
                                   self.monthnames[self.month], self.year,
                                   self.showtimeofday())

    def recalc(self):
        if not self.date:
            self.date = pcc.persian_from_fixed(self.fixed)
        return self

    def is_leap_year(self):
        return (self.year_end() - self.year_begin()) == 365

    def year_begin(self):
        return PersianDate(self.year, 1, 1)

    def year_end(self):
        year = self.year + 1
        if year == 0:
            year = 1
        return PersianDate(year, 1, 1) - 1


# Bahai Dates
@caldoc
class BahaiDate(CalDate):
    calendar = "Bahai"
    prefix = "bahai"
    dateparts = ODict([
        ("major", (pcc.bahai_major, None, None)),
        ("cycle", (pcc.bahai_cycle, 1, 19)),
        ("year", (pcc.bahai_year, 1, 19)), 
        ("month", (pcc.bahai_month, 0, 19)),
        ("day", (pcc.bahai_day, 1, 19))])
    weekdays = (u"Jamāl", u"Kamāl", u"Fiḍāl", u"`Idāl", u"Istijlāl",
                u"Istiqlāl", u"Jalāl")
    daynames = (u"Bahā", u"Jalāl", u"Jamāl", u"`Aẓamat", u"Nūr", u"Raḥmat", u"Kalimāt",
                u"Kamāl", u"Asmā", u"`Izzat", u"Mashīyyat", u"`Ilm", u"Qudrat",
                u"Qawl", u"Masā'il", u"Sharaf", u"Sulṭān", u"Mulk", u"`Alā")
    monthnames = (u"Ayyām-i-Hā",  # This is month 0!
                  u"Bahā", u"Jalāl", u"Jamāl", u"`Aẓamat", u"Nūr", u"Raḥmat", u"Kalimāt",
                  u"Kamāl", u"Asmā", u"`Izzat", u"Mashīyyat", u"`Ilm", u"Qudrat",
                  u"Qawl", u"Masā'il", u"Sharaf", u"Sulṭān", u"Mulk", u"`Alā")
    yearnames = (u"Alif", u"Bā'", u"Āb", u"Dāl", u"Bāb", u"Vāv", u"Abad", u"Jād",
                 u"Bahā'", u"Ḥubb", u"Bahhāj", u"Javāb", u"Aḥad", u"Vahhāb", u"Vidād",
                 u"Badī'", u"Bahī", u"Abhā", u"Vāḥid")
    holidays = ODict([
        (u"Feast of Naz-Rūz", (1, 1)),
        (u"Feast of Riḍvān", (2, 13)),
        (u"Riḍvān 9", (2, 29)),
        (u"Riḍvān 12", (3, 5)),
        (u"Declaration of the Bāb", (4, 7)),
        (u"Ascension of Bahā'u'llāh", (4, 13)),
        (u"Martyrdom of the Bāb", (6, 16)),
        (u"Birth of the Bāb", (12, 5)),
        (u"Birth of Bahā'i'llāh", (13, 9)),
        (u"Birth of `Abdu'l-Bahā", (4, 7)),
        (u"Ascension of `Abdu'l-Bahā", (14, 6))])
    holidayarg = 3
    daystart = "sunset"

    def __str__(self):
        return "%s, day (%d) %s, month (%d) %s, year (%d) %s, cycle %d%s" % \
               (self.weekdays[self.weekday], self.day, self.daynames[self.day - 1],
                self.month, self.monthnames[self.month],
                self.year, self.yearnames[self.year-1], self.cycle,
                self.showtimeofday())

    def is_leap_year(self):
        return (self.year_end() - self.year_begin()) == 365

    def year_begin(self):
        return BahaiDate(self.major, self.cycle, self.year, 1, 1)

    def year_end(self):
        return BahaiDate(self.major, self.cycle, self.year, 19, 19)


# Chinese Dates
@caldoc
class ChineseDate(CalDate):
    calendar = "Chinese"
    prefix = "chinese"
    dateparts = ODict([
        ("cycle", (pcc.chinese_cycle, None, None)),
        ("year", (pcc.chinese_year, 1, 60)),
        ("month", (pcc.chinese_month, 1, 12)),
        ("leap", (pcc.chinese_leap, 0, 1)),
        ("day", (pcc.chinese_day, 1, 31))])
    stems = (u"Jiă", u"Yĭ", u"Bĭng", u"Dīng", u"Wù", u"Jĭ", u"Gēng", u"Xīn",
             u"Rén", u"Guĭ")
    branches = (u"Zĭ", u"Chŏu", u"Yín", u"Măo", u"Chén", u"Sì", u"Wŭ", u"Wèi",
                u"Shēn", u"Yŏu", u"Xū", u"Hài")
    holidays = ODict([
        ("New Year", (1, 0, 1)),
        ("Lantern Festival", (1, 0, 15)),
        ("Dragon Festival", (5, 0, 5)),
        (u"Qĭqiăo", (7, 0, 7)),
        ("Hungry Ghosts", (7, 0, 15)),
        ("Mid-AUtumn Festival", (8, 0, 15)),
        ("Double-Ninth Festival", (9, 0, 9))])

    def __str__(self):
        year = self.year
        year_name = pcc.chinese_year_name(year)
        year_name = self.stems[pcc.chinese_stem(year_name)-1] + "-" + \
            self.branches[pcc.chinese_branch(year_name)-1]
        month = self.month
        if self.leap:
            month_name = "leap"
        else:
            month_name = pcc.chinese_month_name(month, year)
            month_name = self.stems[pcc.chinese_stem(month_name)-1] + "-" + \
                self.branches[pcc.chinese_branch(month_name)-1]
        day = self.day
        day_name = pcc.chinese_day_name(day)
        day_name = self.stems[pcc.chinese_stem(day_name)-1] + "-" + \
            self.branches[pcc.chinese_branch(day_name)-1]
        return "Cycle %d, year %d (%s), month %d (%s), day %d (%s)%s" % \
            (self.cycle, year, year_name, month, month_name, day, day_name,
             self.showtimeofday())

    def is_leap_year(self):
        raise NotImplemented

    def year_begin(self):
        return ChineseDate(pcc.chinese_new_year_on_or_before(self.fixed))

    def year_end(self):
        raise NotImplemented


ChineseDate.yearnames = ('',) + tuple(ChineseDate.stems[pcc.amod(n, 10)-1] +
                                      ChineseDate.branches[pcc.amod(n, 12)-1]
                                      for n in range(1, 60))
ChineseDate.monthnames = ChineseDate.yearnames
ChineseDate.daynames = ChineseDate.yearnames


# Hindu Lunar Date
@caldoc
class HinduLunarDate(CalDate):
    calendar = "HinduLunar"
    prefix = "hindu_lunar"
    dateparts = ODict([
        ("year", (pcc.hindu_lunar_year, None, None)),
        ("month", (pcc.hindu_lunar_month, 1, 12)),
        ("leap_month", (pcc.hindu_lunar_leap_month, 0, 1)),
        ("day", (pcc.hindu_lunar_day, 1, 30)),
        ("leap_day", (pcc.hindu_lunar_leap_day, 0, 1))])
    weekdays = (u"Ravivāra", u"Somavāra", u"Maṅglavāra", u"Budhavāra",
                u"Bṛihaspatvāra", u"Śukravāra", u"Śanivāra")
    monthnames = ("", "Caitra", u"Vaiśākha", u"Jyeṣṭha", u"Āṣāḍha", u"Śrāvaṇa",
                  u"Bhādrapada", u"Āśvina", u"Kārtika", u"Mārgaśīrṣa", u"Pauṣa",
                  u"Māgha", u"Phālguna")
    daystart = "sunrise"

    def __str__(self):
        if self.leap_month:
            leap_month = " adhika"
        else:
            leap_month = ""
        if self.leap_day:
            leap_day = " adhika"
        else:
            leap_day = ""
        return "%s, %d%s %s%s %d%s" % (self.weekdays[self.weekday], self.day, leap_day,
                                       self.monthnames[self.month], leap_month,
                                       self.year, self.showtimeofday())

    def year_begin(self):
        raise NotImplemented

    def year_end(self):
        raise NotImplemented


# Hindu Solar Date
@caldoc
class HinduSolarDate(CalDate):
    calendar = "HinduSolar"
    prefix = "hindu_solar"
    dateparts = ODict([
        ("year", (pcc.standard_year, None, None)),
        ("month", (pcc.standard_month, 1, 12)),
        ("day", (pcc.standard_day, 1, 32))])
    weekdays = (u"Ravivāra", u"Somavāra", u"Maṅglavāra", u"Budhavāra",
                u"Bṛihaspatvāra", u"Śukravāra", u"Śanivāra")
    monthnames = ("", "Caitra", u"Vaiśākha", u"Jyeṣṭha", u"Āṣāḍha", u"Śrāvaṇa",
                  u"Bhādrapada", u"Āśvina", u"Kārtika", u"Mārgaśīrṣa", u"Pauṣa",
                  u"Māgha", u"Phālguna")
    daystart = "sunrise"

    def __str__(self):
        return "%s, %d %s %d%s" % (self.weekdays[self.weekday], self.day,
                                   self.monthnames[self.month], self.year,
                                   self.showtimeofday())

    def year_begin(self):
        return HinduSolarDate(self.year, 1, 1)

    def year_end(self):
        return HinduSolarDate(self.year + 1, 1, 1) - 1


# Tibetan Date
@caldoc
class TibetanDate(CalDate):
    calendar = "Tibetan"
    prefix = "tibetan"
    dateparts = ODict([
        ("year", (pcc.tibetan_year, None, None)),
        ("month", (pcc.tibetan_month, 1, 12)),
        ("leap_month", (pcc.tibetan_leap_month, 0, 1)),
        ("day", (pcc.tibetan_day, 1, 30)),
        ("leap_day", (pcc.tibetan_leap_day, 0, 1))])
    weekdays = ("gza' nyi ma", "gza' zla ba", "gza' mig dmar", "gza' lhag pa",
                "gza' phur bu", "gza' pa sangs", "gza' spen pa")
    monthnames = ("", "dbo", "nag pa", "sa ga", "snron", "chu stod", "gro bzhin",
                  "khrums", "tha skar", "smin drug", "mgo", "rgyal", "mchu")
    elements = ("shing", "me", "sa", "lcags", "chu")
    totems = ("bya ba", "glang", "stag", "yos", "'brug", "sbrul",
              "rta", "lug", "spre'u", "khyi", "phag")

    def __str__(self):
        if self.leap_month:
            leap_month = "(leap) "
        else:
            leap_month = ""
        if self.leap_day:
            leap_day = "(leap) "
        else:
            leap_day = ""
        return "%s, %s%d %s%s %d%s" % (self.weekdays[self.weekday], leap_day, self.day,
                                       leap_month, self.monthnames[self.month],
                                       self.year, self.showtimeofday())

    def year_begin(self):
        return TibetanDate(pcc.losar(self.year))

    def year_end(self):
        return TibetanDate(pcc.losar(self.year + 1)) - 1


calendars = (JDDate, MJDDate, GregorianDate, JulianDate, RomanDate, EgyptianDate,
             ArmenianDate, ISODate, CopticDate, EthiopicDate, IslamicDate,
             HebrewDate, MayanLongCountDate, OldHinduLunarDate, OldHinduSolarDate,
             PersianDate, BahaiDate, ChineseDate, HinduLunarDate, HinduSolarDate,
             TibetanDate)

defaultcalendar = "Gregorian"


######################################################################

def sunrise(date, location=None):
    """Computes the approximate sunrise time.

    This function returns the approximate sunrise time for a given location (by
    default, the current location).  The output has the same format of the input
    date, that is a calendar datetime, or a fixed number."""
    if location is None:
        location = geolocation.location
    if isinstance(date, CalDate):
        return date.__class__(pcc.sunrise(round(date.fixed), location) - 0.5)
    else:
        return pcc.sunrise(round(date), location) - 0.5
        

def sunset(date, location=None):
    """Computes the approximate sunset time.

    This function returns the approximate sunset time for a given location (by
    default, the current location).  The output has the same format of the input
    date, that is a calendar datetime, or a fixed number."""
    if location is None:
        location = geolocation.location
    if isinstance(date, CalDate):
        return date.__class__(pcc.sunset(round(date.fixed), location) - 0.5)
    else:
        return pcc.sunset(round(date), location) - 0.5


def moonrise(date, location=None):
    """Computes the approximate moonrise time.

    This function returns the approximate sunrise time for a given location (by
    default, the current location).  The output has the same format of the input
    date, that is a calendar datetime, or a fixed number."""
    if location is None:
        location = geolocation.location
    if isinstance(date, CalDate):
        return date.__class__(pcc.moonrise(round(date.fixed), location) - 0.5)
    else:
        return pcc.moonrise(round(date), location) - 0.5


def loadcalendars(ip):
    for cal in calendars:
        ip.user_ns[cal.calendar] = cal
    ip.user_ns["sunrise"] = sunrise
    ip.user_ns["sunset"] = sunset
    ip.user_ns["moonrise"] = moonrise
