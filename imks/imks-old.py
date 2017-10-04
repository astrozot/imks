# -*- coding: utf-8 -*-

"""
iMKS -- An advanced physical quantity calculator
================================================

iMKS is an IPython extension to allows the use of physical quantities
(Value's) in mathematical expressions.  A physical quantity is simply a number
(typically, a float number) followed by a unit specification.  Within iMKS,
one can use physical quantities in normal expressions: the result will be a
physical quantity with the correct unit.

Main Features
-------------

* Allow the use of physical quantities in mathematical expressions and
  performs consistency checks (so that, for example, an error is generated if
  one tries to add a length with a time)

* Unit systems make it easy to perform conversions of physical quantities in
  different units.  A unit system provides a list of units that should be
  used, alone or in combination, to represent physical values.  Large unit
  systems are effectively useful to define preferences in unit
  representations.

* Completely modular: one can define base units, prefixes, derived units, and
  unit systems using magic commands.  Definitions can be stored in an external
  file for reuse.

* Currencies are considered as physical units.  Automatically retrieves a
  large list of currencies and exchange rates from openexchangerates.org and
  stores them in a file for offline use.

* A list of physical constants can be retrieved from the NIST server
  http://physics.nist.gov/constants and are available as variable in
  interactive mode.

* Add autocompletion for units and constants.

* Allow the use of documentation strings for all quantities (base units,
  prefixes, units, unit systems, and values) using the ... # "doc string"
  notation.

* Optionally allow the use of the standard exponent (caret, ^) in mathematical
  expressions in addition to the Python notation (**).  Also, optionally allow
  the use of unicode characters in identifiers, units, and prefixes.

* Physical quantities are displayed in a proper way (using the LaTeX notation)
  in the notebook.

* Several mathematical engines can be used: the standard Python math module,
  mpmath, fpmath (mpmath with fixed point arithmetics), and numpy.  The
  engines are used to perform calculations involving mathematical functions.


Use of iMKS
-----------

iMKS extends the standard Python syntax in several ways:

* Physical quantities can be entered using the format 9.8[m s^-2] or
  9.8[m/s^2], i.e. with a number followed by a unit specification in
  brackets.  In simple cases, quantities can also be entered without the
  brackets: 9.8 m/s^2 or 9.8 m s^-2.  This shorter notation however can
  generate ambiguities when the quantity is exponentiated (2m^2 is 2[m^2],
  while 2[m]^2 is 4[m^2]).

* A unit specification follows a standard notation: it is a space-separated
  list of prefixed units followed by an optional exponent.  A prefixed unit is
  a unit with a prefix, such as [km] = prefix k + simple unit m.  The
  exponent in the unit must be a simple number or a fraction: it cannot
  involve any other term (for example, [km^a] is not a valid unit, while
  [km^2/3] is).

* Physical quantities can be used in expression with the standard operators.
  
* The result of an expression can be converted into a different unit by using
  the @ operator:

  > 12[m] + 3[cm] @ [km] --> 0.01203[km]

  Multiple units can be used after the @ operator: in that case, they are
  combined as necessary to obtain the requested quantity

  > 72[km/hour] @ [m], [s] --> 20.0[m s^-1]

  When the quantity can be represented using multiple combinations, the
  shorter one is used (i.e., the one that involves the smallest number of
  elements in the list at the right of the @ operator):

  > 72[km/hour] @ [m], [s], [mph] --> 44.738725841088[mph]

* Unit systems are just list of units that can be used after the @ operator:

  > 23[km/hour] @ SI


Configuration file
------------------

When launched, iMKS load definitions from the configuration file
Startup.imks.  This file is searched in the current directory, and if not
found in the ~/.imks directory.  The file should contain the standard
definitions that one is likely to need for any computation.  Typically the
file uses the following magic commands:

%newbaseunit <name>
  Define a new base unit.  Base units are the building blocks for all
  subsequent units definitions.  A base unit does not have a value: for
  example, one cannot express a meter in any other unit if no unit of length
  is known.

%newprefix <name>=<expression>
  Define a new prefix.  The <expression> value evaluate to a simple number.

%newunit <name>=<expression>
  Define a new unit.  <expression> should evaluate to a Value'd number.

%newsystem <name>=[u1], [u2], ...
  Define a new unit system.  A unit system is simply a list of units.

%defaultsystem <name>
  Set the unit system to use in case no @ is used.

Other magic commands
--------------------

%delprefix <name>, %delunit <name>, %delsystem <name>
  Delete a previously define prefix, unit, or unit system

%lazy <name>=<expression>
  Define the variable <name> as <expression> lazily: that is, <expression> is
  evaluated only when <name> is used or displayed.

%compatible <stuff>
  Find out the known variables or units that are compatible to <stuff>.
  <stuff> can be either a unit (in brackets) or an expression

%load_imks <filename>
  Load an external <filename> with definitions in iMKS format.

%load_imks_ext <filename>
  Load an imks extension.

%uinfo <name>
  Display an help page for a prefix, unit, or unit system.  This is the
  equivalent of %pinfo (which works for objects in the user namespace).  A short
  notation for %uinfo <name> is <name>! (i.e., the name of an imks object followed
  by the exclamation mark).


Internals
---------

Internally, iMKS works by converting an input string into Python expressions.
The following rules are used:

* Physical quantities are converted into Value's:

  > 72[km hour^-1] --> Value(72,"km hour^-1")

* The @ operator is converted into the | operator, and what follows is put in
  a unit System:

  > 72[km hour^-1] @ [m], [s] --> Value(72,"km hour^-1") | System("m", "s")

* Value and System are defined in units.py, and for these objects the standard
  operators are redefined to include tracking of physical units.

* If necessary, one can directly use the Value and System objects to make more
  complicated expressions.
"""

from IPython.utils.traitlets import List, Int, Any, Unicode, CBool, Bool, Instance
from IPython.core.inputtransformer import (CoroutineInputTransformer, 
                                           StatelessInputTransformer,
                                           TokenInputTransformer,
                                           _strip_prompts)
from IPython.core import inputsplitter as isp
from IPython.core import inputtransformer as ipt
from collections import OrderedDict as ODict
import token, tokenize, re
import units
from lazy import lazy_import

@lazy_import
def currencies():
  import currencies
  return currencies

@lazy_import
def calendars():
  import calendars
  return calendars

imks_enabled = True
auto_brackets = True
standard_exponent = True
use_unicode = True
engine = None
engine_unloader = None
debug = False

######################################################################
# Magic functions

from IPython.core.magic import Magics, magics_class, line_magic
from IPython.core import page
from IPython.core.magic_arguments import (argument, magic_arguments,
    parse_argstring)

@magics_class
class imks_magic(Magics):
    re_doc = re.compile(r'([^#]+)\s*#\s*"([^"]*)"\s*')

    def split_command_doc(self, line):
        m = re.match(self.re_doc, line)
        if m:
            doc = m.group(2).strip(' ')
            line = m.group(1)
        else: doc = ""
        return (line, doc)

    @line_magic
    def imks(self, args):
        """Activate and desactivate imks.

        Options:
          -h           show an help page on iMKS
          -a <on|off>  auto brackets for units
          -e <on|off>  allow the use of the caret (^) as an exponent (**)
          -u <on|off>  allow the use of unicode characters
          -t <on|off>  toggle the zero-value tolerance.  When enabled, zero values
                       are sum-compatible with any unit.
          -c <name>    specify the engine for mathematical calculations: must be one
                       of math, mpmath, fpmath, numpy
          -m min       specify the minimim digits for fixed notation
          -M max       specify the maximum digits for fixed notation: outside the
                       range indicated by -m min and -M max the exponential notation
                       is used.  To force a fixed format always, use min=-inf and
                       max=+inf; to force an exponential format always, use min=max

        An additional <on|off> argument enable or disable imks altoghether.
        """
        global auto_brackets, standard_exponent, use_unicode, imks_enabled
        opts, name = self.parse_options(args, 'ha:e:u:t:c:m:M:')
        if name in ["on", "1", "yes"]:
            imks_enabled = True
            print "iMKS enabled"
        elif name in ["off", "0", "no"]:
            imks_enabled = False
            print "iMKS disabled"
        elif len(args) == 0:
            imks_enabled = not imks_enabled
            print "iMKS %s" % ("enabled" if imks_enabled else "disabled")
        if "h" in opts:
            page.page(__doc__)
            return 
        if "a" in opts:
            if opts["a"] in ["on", "1", "yes"]:
                auto_brackets = True
                print "Auto brackets enabled"
            elif opts["a"] in ["off", "o", "no"]:
                auto_brackets = False
                print "Auto brackets disabled"
            else:
                print "Incorrect argument.  Use on/1 or off/0"
        if "e" in opts:
            if opts["e"] in ["on", "1", "yes"]:
                standard_exponent = True
                print "Standard exponent (^) enabled"
            elif opts["e"] in ["off", "o", "no"]:
                standard_exponent = False
                print "Standard exponent (^) disabled"
            else:
                print "Incorrect argument.  Use on/1 or off/0"
        if "u" in opts:
            if opts["u"] in ["on", "1", "yes"]:
                use_unicode = True
                print "Unicode enabled"
            elif opts["u"] in ["off", "o", "no"]:
                use_unicode = False
                print "Unicode disabled"
            else:
                print "Incorrect argument.  Use on/1 or off/0"
        if "t" in opts:
            if opts["t"] in ["on", "1", "yes"]:
                units.tolerant = True
                print "Zero-value tolerance enabled"
            elif opts["t"] in ["off", "o", "no"]:
                units.tolerant = False
                print "Zero-value tolerance disabled"
            else:
                print "Incorrect argument.  Use on/1 or off/0"
        if "c" in opts:
            if opts["c"] == "math": math_engine(self.shell)
            elif opts["c"] == "mpmath": mpmath_engine(self.shell)
            elif opts["c"] == "fpmath": fpmath_engine(self.shell)
            elif opts["c"] == "numpy": numpy_engine(self.shell)
            else:
                print "Incorrect argument: must be math, mpmath, fpmath, or numpy."
                return
            print "iMKS math engine: %s" % opts["c"]
        if "m" in opts or "M" in opts:
            import units_mpmath
            if "m" in opts:
                units_mpmath.min_fixed = eval(opts["m"], self.shell.user_ns)
            elif "M" in opts:
                units_mpmath.max_fixed = eval(opts["M"], self.shell.user_ns)
            print "Fixed range:", units_mpmath.min_fixed, ":", \
                units_mpmath.max_fixed

    @line_magic
    def load_imks(self, arg):
        """Load one ore more imks modules."""
        import os, os.path
        ip = self.shell
        modules = arg.split(",")
        for module in modules:
            code = None
            filename = module.strip()
            if os.path.splitext(filename)[1] == "":
                filename += ".imks"
            try:
                code = ip.find_user_code(filename, py_only=True)
            except:
                if not os.path.isabs(filename):
                    try:
                        filename = os.path.join(os.environ["HOME"], ".mks",
                                                filename)
                        code = ip.find_user_code(filename, py_only=True)
                    except:
                        pass
            if code:
                ip.run_cell(code)
            else:
                raise ImportError("Could not find imks file named %s" %
                                  module.strip())

    @line_magic
    def load_imks_ext(self, arg):
        """Load one ore more imks extensions.

        Currently, the following extensions are recognized:
          constants
          currencies
          calendars
          geolocation"""
        import os, os.path
        ip = self.shell
        exts = arg.split(",")
        for ext in exts:
            if ext == "calendars":
                calendars.loadcalendars(ip)
            elif ext == "geolocation":
                import geolocation
                ip.user_ns["get_geolocation"] = geolocation.get_geolocation
                ip.user_ns["set_geolocation"] = geolocation.set_geolocation
            elif ext == "constants":
                import constants
                constants.loadconstants(engine=eval(engine, self.shell.user_ns))
                self.shell.user_ns["const"] = constants.constants
            elif ext == "currencies":
                if ip.user_ns.has_key("openexchangerates_id"):
                    app_id = self.shell.user_ns["openexchangerates_id"]
                else: app_id = ""
                currencies.currencies(app_id)
            else: print "Unknown extension `%s'." % ext

    @line_magic
    def newbaseunit(self, arg):
        """Define a new base unit.

        Usage:
          %newbaseunit name [# "Documentation string"]

        Since base units are the fundamental building blocks of a unit system,
        a base unit definition is typically the first operation performed in a iMKS
        configuration file (see for example Startup.imks).  Note that a base unit,
        being a fundamental block used for all calculations, cannot be deleted.

        See also:
          %newbasecurrency, %newunit, %newprefix"""
        command, doc = self.split_command_doc(arg)
        units.newbaseunit(command.strip(), doc=doc)
        return
        
    @line_magic
    def newbasecurrency(self, arg):
        """Define a new base currency.

        Usage:
          %newbasecurrency name [# "Documentation string"]

        A base currency is the main currency used for currency conversions.  It is
        important to define it, since all exchange rates are calculated using the
        base currency as reference currency.  Note that a base currency is also a
        base unit; as such, it cannot be deleted.

        See also:
          %newbaseunit, %newunit, %newprefix"""
        command, doc = self.split_command_doc(arg)
        units.newbasecurrency(command.strip(), doc=doc)
        return

    @line_magic
    def newprefix(self, arg):
        """Define a new prefix.

        Usage:
          %newprefix name=value [# "Documentation string"]

        A prefix is used before a unit to build a prefixed unit: for example, the
        unit km is understood as k+m, i.e. the prefix k=1000 times the unit m=meter.
        The value of a prefix must always be a pure number; moreover, fractional
        prefixes (such as m=1/1000) should be entered in the mpmath engine using
        the fraction function (this ensures that the prefix is always computed at
        the required accuracy).

        See also:
          %delprefix, %newunit, %delunit."""
        import cStringIO
        command, doc = self.split_command_doc(arg)
        names, value = command.split("=")
        tokens = tokenize.generate_tokens(cStringIO.StringIO(value.strip()).readline)
        value = self.shell.ev(tokenize.untokenize(
            unit_transformer([t for t in tokens])))
        units.newprefix([name.strip() for name in names.split(",")], value, doc=doc)
        return

    @line_magic
    def delprefix(self, arg):
        """Delete a prefix previously defined using the %newprefix magic.

        Usage:
          %delprefix name"""
        units.delprefix(arg.strip())
        return

    @line_magic
    def newunit(self, arg):
        """Define a new unit.

        Usage:
          %newunit name=value [# "Documentation string"]

        After its definition, a unit can be used for any physical quantity.  A unit
        can be deleted using the %delunit magic."""
        import cStringIO
        command, doc = self.split_command_doc(arg)
        names, value = command.split("=")
        tokens = tokenize.generate_tokens(cStringIO.StringIO(value.strip()).readline)
        value = self.shell.ev(tokenize.untokenize(
            unit_transformer([t for t in tokens])))
        units.newunit([name.strip() for name in names.split(",")], value, doc=doc)
        return

    @line_magic
    def delunit(self, arg):
        """Delete a unit previously defined using the %newunit magic.

        Usage:
          %delunit name"""
        units.delunit(arg.strip())
        return


    @line_magic
    def newsystem(self, arg):
        """Define a new unit system.
        
        Usage:
          %newsystem name=u1,u2,... [# "Documentation string"]

        where u1,u2,... is a list of unit specifications.  A unit system is a
        convenient way to specify a set of units that will be used together in unit
        conversions with the @ operator.  This operator is able to find out the
        combination of units among the ones provided, that can recreate the unit
        specified in its left operand.  In this respect, the unit system can be used
        in two different ways:

        - If all units of a unit system are independent (that is, none of the units
          of the unit system can be expressed in terms of the other units), it is
          intended that the units in the system MUST be used, in a suitable
          combination, to produce the requested unit.

        - Alternatively, there might be multiple possible solutions, i.e.
          multiple combinations of units in the system, that can recreate the
          requested unit.  In this case, the @ operator will find the combination
          that will result in the lower number of combined system units, giving
          priority to the units entered first in the system.

        As an example, say we define two systems

        > %newsystem one=[m],[s]
        > %newsystem two=[m],[s],[km/hour]

        If we then type
        > c @ one
        we will obtain c in units of [m s^-1], a combintation of the two provided
        units.  Instead
        > c @ two
        will use as a unit [km hour^-1], since this is a unit entered in the system
        and as such it is priviledged over the combination [m s^-1] (which instead
        requires the use of two different units entered).
        
        A unit system can be deleted using the %delsystem magic."""
        command, doc = self.split_command_doc(arg)
        names, values = command.split("=")
        units.newsystem([name.strip() for name in names.split(",")],
                        [value.strip("[] ") for value in values.split(",")], doc=doc)
        
        return
        
    @line_magic
    def delsystem(self, arg=""):
        """Delete a unit system previously defined using the %newsystem magic.

           Usage:
             %delsystem name"""
        units.delsystem(arg.strip())
        return

    @line_magic
    def defaultsystem(self, arg):
        """Set the default unit system for value representations.
        
        Usage:
          %defaultsystem name
          %defaultsystem [u1], [u2],...

        where name is a previously define unit system and u1,u2,... is a list of
        unit specifications.  Do not use any argument to unset the default unit
        system."""
        if len(arg) == 0:
            units.defaultsystem = None
        elif len(arg.split(",")) == 1:
            units.defaultsystem = units.systems[arg]
        else:
            units.defaultsystem = \
                units.System(*(a.strip("[] ") for a in arg.split(",")))
            units.cachedat = {}

    @line_magic
    def lazy(self, arg):
        """Define a variable lazily in terms of an expression.

        %lazy var=expr defines the variable var to be the value of expression.  In
        contranst to standard variable, however, expr is not computed immediately:
        rather, it is evaluated only when var is used ore displayed.  This allows
        one to define variable with a arbitrary precision (in the sense that the
        precision used when calculating the variable is the one set at real time),
        or variables that depends dynamically on other external variables.

        Options:
          -u   Evaluate the expression unit each time (by default, the value of the
               expression is recomputed each time it is needed, but the unit is
               computed only once, the first time variable is calculated)
          -1   Evaluate the entire expression (unit and value) only once, the first
               time the variable is calculated"""
        import cStringIO
        command, doc = self.split_command_doc(arg)
        opts, command = self.parse_options(command, "1u")
        name, value = command.split("=")
        value = "lambda : " + value
        tokens = tokenize.generate_tokens(cStringIO.StringIO(value.strip()).readline)
        value = self.shell.ev(tokenize.untokenize(
            unit_transformer([t for t in tokens])))
        self.shell.user_ns[name] = units.LazyValue(value, once="1" in opts,
                                                   unit_once="u" not in opts)


    @line_magic
    def uinfo(self, args):
        """Provide detailed information about an imks-related object.

        Usage:
          %uinfo [-u|-p|-s] [-i] name

        Options:
          -a   Apropos mode: does search within documentation strings
          -x   Extended mode: show how a prefix + unit is parsed
          -u   Search among the units and currencies
          -p   Search among the prefixes
          -s   Search among the unit systems
          -i   For wildcard searches, ignore the case"""
        opts, name = self.parse_options(args, 'axsupi')
        u0 = dict([(k, w) for k, w in units.units.iteritems()
                   if k in units.baseunits])
        u1 = dict([(k, w) for k, w in units.units.iteritems()
                   if k not in units.baseunits and k not in currencies.basecurrency \
                   and k not in currencies.currencydict])
        c0 = dict([(k, w) for k, w in units.units.iteritems()
                   if k in currencies.basecurrency])
        c1 = dict([(k, w) for k, w in units.units.iteritems()
                    if k not in currencies.basecurrency and \
                       k in currencies.currencydict])
        if 's' in opts:
            namespaces[('Unit systems', units.systems)]
        elif 'u' in opts:
            namespaces = [('Base units', u0),
                          ('Base currencies', c0),
                          ('Units', u1),
                          ('Currencies', c1)]
        elif 'p' in opts:
            namespaces = [('Prefixes', units.prefixes)]
        else:
            namespaces = [('Unit systems', units.systems),
                          ('Base units', u0),
                          ('Base currencies', c0),
                          ('Units', u1),
                          ('Currencies', c1),
                          ('Prefixes', units.prefixes)]
        if 'a' in opts:
            name = name.upper()
            print name
            for n, d in namespaces:
                f = [k for k,v in d.iteritems() \
                     if v.__doc__.upper().find(name) >= 0]
                if f:
                    print "%s: %s" % (n, ", ".join(f))
            return
        if 'x' in opts:
            res = units.isunit(name)
            if res:
                print "%s parsed as prefix(%s) + unit(%s)" % (name, res[0], res[1])
            else: print "%s is not a valid unit with prefix"
            return
        if '*' in name:
            psearch = self.shell.inspector.psearch
            d = dict(namespaces)
            try:
                psearch(name, d, d.keys(), ignore_case='i' in opts)
            except:
                self.shell.showtraceback()

        else:
            if reduce(lambda x, y: x or y, [name in d for _,d in namespaces]):
                self.shell._inspect("pinfo", name, namespaces)
            else:
                res = units.isunit(name)
                if res:
                    print "%s parsed as prefix(%s) + unit(%s)" % (name, res[0], res[1])
                else: print "Object `%s` not found" % name
        return

    @line_magic
    def compatible(self, args):
        """Check units or variables compatible with a given value or unit.

        By default, the function checks both units and variables, but this can be
        changed using the appropriate flag.

        Flags:
        -u         Check only units
        -U list    When checking units consider only units in the quoted list
        -v         Check only variables
        -V list    When checking variables consider only the ones in the quoted list
        -l level   Search combinened units containing level number of simple units
                   (default: level=1).  Use a negative level to search only for
                   direct compatibilities (without exponent)

        Examples:
        %compatible g
        %compatible -l 3 -v -V "c, G, hbar" [s]
        """
        import sys, cStringIO
        opts, us = self.parse_options(args, 'uU:vV:l:')
        level = int(opts.get("l", 1))
        if "s" in opts: level = -level
        if us[0] == '[' and us[-1] == ']':
            r = units.Value(1, us.strip("[] "))
        else:
            tokens = tokenize.generate_tokens(cStringIO.StringIO(us.strip()).readline)
            r = self.shell.ev(tokenize.untokenize(
                unit_transformer([t for t in tokens])))
        if "v" not in opts:
            print "Compatible units:",
            found = False
            if "U" in opts:
                where = ODict([(k.strip(" []"), units.units[k.strip(" []")])
                                for k in opts["U"].split(",")])
            else:
                where = units.units
            for u in r.findCompatible(where, level=level):
                print unicode(u),
                found = True
                sys.stdout.flush()
            if not found: print "None"
            else: print
        if "u" not in opts:
            print "Compatible values:",
            found = False
            if "V" in opts:
                where = ODict([(k.strip(), self.shell.user_ns[k.strip()])
                                for k in opts["V"].split(",")])
            else:
                where = self.shell.user_ns
            where = ODict([(k,v) for k,v in where.iteritems()
                           if isinstance(v, units.Value)])
            for u in r.findCompatible(where, level=level):
                uu = unicode(u).strip("[] ")
                if not found: print uu,
                else: print chr(8) + ",", uu,
                found = True
                sys.stdout.flush()
            if not found: print "None"
            else: print

######################################################################
# Input transformers
import string

def utf2ascii(s):
    global use_unicode
    if not use_unicode: return s
    r = ""
    for c in s:
        e = c.encode("utf")
        if len(e) == 1: r += e
        else: r += "_uTf_" + "_".join(["%x" % ord(x) for x in e])
    return r


re_utf_encoding = re.compile(r"_uTf((?:_[a-fA-F0-9][a-fA-F0-9])+)")
def ascii2utf(s):
    global use_unicode
    if not use_unicode: return s
    r = u""
    trunks = re_utf_encoding.split(s)
    normal = True
    for trunk in trunks:
        if normal:
            r += trunk
        else:
            e = ""
            for h in trunk[1:].split("_"):
                e += chr(string.atoi(h, 16))
            r += e.decode("utf")
        normal = not normal
    return r

            
def command_transformer(line):
    global use_unicode
    if not imks_enabled: return line
    if line and line[-1] == '!': line = "%uinfo " + line[:-1]
    if use_unicode: line = utf2ascii(line)
    return line
input_command_transformer = StatelessInputTransformer.wrap(command_transformer)

def offset_token(t, delta):
    return (t[0], t[1], (t[2][0], t[2][1] + delta), (t[3][0], t[3][1]+delta), t[4])

def unit_create(sstatus, queue, brackets=False):
    string = queue[0][-1]
    if sstatus == 0:
        if brackets:
            u = u'"' + tokenize.untokenize(queue[2:-1]).strip() + u'"'
            l1, c1 = queue[0][2]
            l2, c2 = queue[0][3]
            offset = c2 + 8 + len(u) - queue[-2][3][1]
            return [(token.NAME, u'Value', (l1, c1), (l1, c1+5), string),
                    (token.OP, u'(', (l1, c1+5), (l1, c1+6), string),
                    (queue[0][0], queue[0][1], (l1, c1+6), (l2, c2+6), string),
                    (token.OP, u',', (l2, c2+6), (l2, c2+7), string),
                    (token.STRING, u, (l2, c2+7), (l2, c2+7+len(u)), string),
                    (token.OP, u')', (l2, c2+7+len(u)), (l2, c2+8+len(u)), string)], \
                    offset
        else:
            u = u'"' + tokenize.untokenize(queue[1:]).strip() + u'"'
            l1, c1 = queue[0][2]
            l2, c2 = queue[0][3]
            offset = c2 + 8 + len(u) - queue[-1][3][1]
            return [(token.NAME, u'Value', (l1, c1), (l1, c1+5), string),
                    (token.OP, u'(', (l1, c1+5), (l1, c1+6), string),
                    (queue[0][0], queue[0][1], (l1, c1+6), (l2, c2+6), string),
                    (token.OP, u',', (l2, c2+6), (l2, c2+7), string),
                    (token.STRING, u, (l2, c2+7), (l2, c2+7+len(u)), string),
                    (token.OP, u')', (l2, c2+7+len(u)), (l2, c2+8+len(u)), string)], \
                    offset
    else:
        if brackets:
            u = u'"' + tokenize.untokenize(queue[1:-1]).strip() + u'"'
            l1, c1 = queue[0][2]
            offset = c1 + len(u) - queue[-1][3][1]
            return [(token.STRING, u, (l1, c1), (l1, c1+len(u)), string)], \
                   offset
        else:
            u = u'"' + tokenize.untokenize(queue).strip() + u'"'
            l1, c1 = queue[0][2]
            offset = c1 + len(u) - queue[-1][3][1]
            return [(token.STRING, u, (l1, c1), (l1, c1+len(u)), string)], \
                   offset

def unit_transformer(tokens):
    if not imks_enabled: return tokens
    newtoks = [[], []]                  # Transformed tokens before/after @
    queue = []                          # Queue used to store partial units
    status = 0                          # General status
    sstatus = 0                         # 0: normal expr; 1: what comes after @
    offset = 0                          # Current offset of the tokens
    flag = False                        # To switch the sstatus
    for tt in tokens:                  # Feed loop
        tokens1 = [offset_token(tt, offset)]
        while tokens1:                  # Internal loop
            t = tokens1.pop()           # tokens1 is in reverse order!
            if flag:
                if newtoks[0][-1][0] == token.OP and newtoks[0][-1][1] == "@":
                    newtoks[1].append(newtoks[0][-1][:])
                    newtoks[0].pop()
                sstatus = 1
                status = 1
                flag = False
            codex, value, p1, p2, string = t
            if codex == token.OP and value == "@":
                flag = True
            if codex == token.N_TOKENS:
                comment = value[1:].strip()
                if comment[0] == '"' and comment[-1] == '"':
                    codex = token.OP
                    value = "&"
                    l1, c1 = p1
                    t = codex, value, p1, (l1, c1+1), string
                    lc = len(comment)
                    tokens1.extend([(token.OP, ")", (l1, c1+6+lc), (l1, c1+7+lc),
                                     string),
                                    (token.STRING, comment, (l1, c1+6),
                                     (l1, c1+6+lc), string),
                                    (token.OP, "(", (l1, c1+5), (l1, c1+6), string),
                                    (token.NAME, "Doc", (l1, c1+2), (l1, c1+5),
                                     string),])
            if status <= 0:                 # ...
                if codex == token.NUMBER and sstatus == 0:
                    status = 1
                    queue.append(t)
                else:
                    newtoks[sstatus].append(t)
            elif status == 1:               # ...12 or ... @
                if codex == token.OP and value == "[":
                    status = 2
                    queue.append(t)
                elif auto_brackets and codex == token.NAME and \
                    (units.isunit(ascii2utf(value)) or \
                     (sstatus == 1 and value in units.systems)):
                    status = 3
                    queue.append(t)
                else:
                    newtoks[sstatus].extend(queue)
                    queue = []
                    if sstatus == 0: tokens1.append(t)
                    else: newtoks[sstatus].append(t)
                    status = sstatus
            elif status == 2:               # ...12[ or ... @[
                if codex == token.OP and value == "]":
                    status = sstatus
                    queue.append(t)
                    queue, delta = unit_create(sstatus, queue, True)
                    newtoks[sstatus].extend(queue)
                    offset += delta
                    queue = []
                else:
                    queue.append(t)
            elif status == 3:               # ...12 m or ... @ m
                if codex == token.NAME and units.isunit(ascii2utf(value)):
                    queue.append(t)
                elif codex == token.OP and value == "/":
                    status = 4
                    queue.append(t)
                elif codex == token.OP and value == "^":
                    status = 5
                    queue.append(t)
                else:
                    status = sstatus
                    queue, delta = unit_create(sstatus, queue)
                    newtoks[sstatus].extend(queue)
                    offset += delta
                    tokens1.append(offset_token(t, delta))
                    status = sstatus
                    queue = []
            elif status == 4:               # ...12 m /
                if codex == token.NAME:
                    # Mmh, found a name after a / in a possible unit specification.
                    # Is it really a possible unit or not?  Check...
                    if units.isunit(ascii2utf(value)):
                        # It is a unit, use it
                        status = 3
                        queue.append(t)
                        continue
                # We did not find a name after a / or the name was not a valid
                # unit.  Put everything back!
                status = sstatus
                t0 = queue[-1]
                queue = queue[0:-1]
                queue, delta = unit_create(sstatus, queue)
                newtoks[sstatus].extend(queue)
                offset += delta
                tokens1.append(offset_token(t, delta))
                tokens1.append(offset_token(t0, delta))
                queue = []
            elif status == 5:               # 12 m^
                if codex == token.NUMBER:
                    status = 6
                    queue.append(t)
                elif codex == token.OP and (value == "-" or value == "+"):
                    status = 7
                    queue.append(t)
                else:
                    status = sstatus
                    t0 = queue[-1]
                    queue = queue[0:-1]
                    queue, delta = unit_create(sstatus, queue)
                    newtoks[sstatus].extend(queue)
                    offset += delta
                    tokens1.append(offset_token(t, delta))
                    tokens1.append(offset_token(t0, delta))
                    queue = []
            elif status == 6:               # 12 m^2 or 12 m^-2
                if codex == token.OP and value == "/":
                    status = 4
                    queue.append(t)
                else:
                    status = sstatus
                    queue, delta = unit_create(sstatus, queue)
                    newtoks[sstatus].extend(queue)
                    offset += delta
                    tokens1.append(offset_token(t, delta))
                    queue = []
                continue
            elif status == 7:               # 12 m^-
                if codex == token.NUMBER:
                    status = 6
                    queue.append(t)
                    continue
                else:
                    status = sstatus
                    t0 = queue[-1]
                    t0 = queue[-1]
                    queue = queue[0:-1]
                    queue, delta = unit_create(sstatus, queue)
                    newtoks[sstatus].extend(queue)
                    offset += delta
                    tokens1.append(offset_token(t, delta))
                    tokens1.append(offset_token(t0, delta))
                    queue = []
            else:
                newtoks[sstatus].append(t)
    if sstatus == 0:
        result = newtoks[0]
        # Fix for problem w/ token.ENDMARKER
        if result[-1][0] == token.ENDMARKER and len(result) >= 2:
            l1, c1 = result[-2][3]
            result = result[0:-1]
            result.append((token.ENDMARKER, "",  (l1, c1), (l1, c1+1), result[-1][-1]))
    else:
        l1, c1 = newtoks[0][0][2]
        result = newtoks[0]
        l1, c1 = result[-1][3]
        result.extend([(token.OP, u"|", (l1, c1+1), (l1, c1+2), string),
                       (token.NAME, u"System", (l1, c1+3), (l1, c1+9), string),
                       (token.OP, u"(", (l1, c1+9), (l1, c1+10), string)])
        offset = c1+10 - newtoks[1][1][2][1]
        last = newtoks[1][-1]
        result.extend([offset_token(t, offset) for t in newtoks[1][1:-1]])
        l1, c1 = result[-1][3]
        result.extend([(token.OP, u")", (l1, c1), (l1, c1+1), string),
                           (last[0], last[1], (l1, c1+1), (l1, c1+2), string)])
    if standard_exponent:
        result = [(codex, u"**", p1, p2, string) if codex == token.OP and value == "^"
                  else (codex, value, p1, p2, string) \
                  for codex, value, p1, p2, string in result]
    if use_unicode:
        uresult = []
        offset = 0
        for t in result:
            t = offset_token(t, offset)
            if t[0] == token.STRING:
                old = t[1]
                new = ascii2utf(old)
                if new[0] != "u": new = "u" + new
                delta = len(new) - len(old)
                offset += delta
                t = (t[0], new, t[2], (t[3][0], t[3][1] + delta), t[4])
            uresult.append(t)
        result = uresult
    if engine:
        uresult = []
        offset = 0
        for t in result:
            t = offset_token(t, offset)
            if t[0] == token.NUMBER and (t[1].find(".") >= 0 or t[1].find("e") >= 0 or \
                                         t[1].find("E") >= 0):
                l1, c1 = t[2]
                l2, c2 = t[3]
                le = len(engine)
                uresult.extend([(token.NAME, engine, t[2], (l1, c1+le), t[4]),
                                (token.OP, u"(", (l1, c1+l2), (l1, c1+le+1), t[4]),
                                (token.STRING, '"' + t[1] + '"', (l1, c1+le+1),
                                 (l2, c2+le+3), t[4]),
                                (token.OP, u")", (l2, c2+le+3), (l2, c2+le+4), t[4])])
                offset += le + 4
            else:
                uresult.append(t)
        result = uresult
    return result
input_unit_transformer = TokenInputTransformer.wrap(unit_transformer)

######################################################################
# Engines and related initialization functions

def math_engine(ip):
    import units_math
    global engine, engine_unloader
    if engine_unloader: engine_unloader(ip)
    units_math.load(ip)
    engine = None
    engine_unloader = units_math.unload

def mpmath_engine(ip):
    import units_mpmath
    global engine, engine_unloader
    if engine_unloader: engine_unloader(ip)
    units_mpmath.load(ip)
    ip.user_ns["mp"].pretty = True
    engine = "mpmathify"
    engine_unloader = units_mpmath.unload

def fpmath_engine(ip):
    import units_fpmath
    global engine, engine_unloader
    if engine_unloader: engine_unloader(ip)
    units_fpmath.load(ip)
    ip.user_ns["fp"].pretty = True
    engine = None
    engine_unloader = units_fpmath.unload

def imks_import(name, globals=None, locals=None, fromlist=None):
    import imp
    import sys
    import cStringIO

    print "Loading module " + name
    # Fast path: see if the module has already been imported.
    try:
        return sys.modules[name]
    except KeyError:
        pass
    # If any of the following calls raises an exception,
    # there's a problem we can't handle -- let the caller handle it.
    fp, pathname, description = imp.find_module(name)
    try:
        fq = open("/tmp/" + name + ".py", "wt")
        fq.write("from units import Value\n")
        ts = []
        for t in tokenize.generate_tokens(fp.readline):
            ts.append(t)
        fq.write(tokenize.untokenize(unit_transformer(ts)))
        fp.close()
        fq.close()
        fq = open("/tmp/" + name + ".py", "rt")
        return imp.load_module(name, fq, "/tmp/" + name + ".py", description)
    finally:
        # Since we may exit via an exception, close fp explicitly.
        if fp: fp.close()
        if fq: fq.close()

######################################################################
# Completer

import readline

from IPython.core.error import TryNext
@lazy_import
def unidecode():
    import unidecode
    return unidecode

def _retrieve_obj(name, context):
    # we don't want to call any functions, but I couldn't find a robust regex
    # that filtered them without unintended side effects. So keys containing
    # "(" will not complete.
    try:
        assert "(" not in name
    except AssertionError:
        raise ValueError()

    try:
        # older versions of IPython:
        obj = eval(name, context.shell.user_ns)
    except AttributeError:
        # as of IPython-1.0:
        obj = eval(name, context.user_ns)
    return obj

class Imks_completer(object):
    def get_prefixes(self, text):
        return filter(lambda x: x.startswith(text), units.prefixes.keys())

    def get_units(self, text):
        return filter(lambda x: x.startswith(text), units.units.keys())

    def get_systems(self, text):
        return filter(lambda x: x.startswith(text), units.systems.keys())

    def get_prefunits(self, text):
        us = self.get_units("")
        ps = filter(lambda x: x.startswith(text) or text.startswith(x),
                    self.get_prefixes(""))
        l = len(text)
        r = filter(lambda x: x.startswith(text),
                   us + [p for p in ps if len(p) >= l] +
                   [p + u for u in us for p in ps if len(p) <= l])
        return r

    def get_quotes(self, text, cs):
        ds = [unidecode.unideocde(unicode(c)) for c in cs]
        if text == "" or text[0] == '"':
            r = ['"' + d + '"' for d in ds]
        else:
            r = ["'" + d + "'" for d in ds]
        rx = "[- \t\n@()\[\]+-/*^|&=<>,]"
        m = len(re.findall(rx, text))
        if m == 0: r = [c for c in r if c.startswith(text)]
        else:
            r = [re.split(rx, c, maxsplit=m)[-1] for c in r
                 if c.startswith(text)]
        # Check if we are in a notebook
        import sys
        if not isinstance(sys.stderr, file):
            return [x if x[0] != '"' and x[0] != "'" else x[1:] for x in r]
        else:
            return r

imks_completer = Imks_completer()

re_space_match = re.compile(r"[][ \t\n@()[+-/*^|&=<>,]+")

re_value_match = re.compile(r"(?:.*\=)?(\d+(?:\.\d*)?(?:[eE][-+]?\d*)?)(?:\[)")
def imks_value_completer(self, event):
    # event has command, line, symbol, text_until_cursor
    # self._ofind(base) has obj, parent, isalias, namespace, found, ismagic
    m = re_value_match.split(event.text_until_cursor)
    n = m[-2]                           # number
    u = m[-1]                           # full unit
    if u.find("]") >= 0: return []      # unit specification closed already
    v = re_space_match.split(u)[-1]     # last unit (or generally last word of u)
    readline.set_completer_delims(" \t\n@()[]+-/*^|&=<>,")
    return imks_completer.get_prefunits(v)

re_unit_match = re.compile(r"\[([^]]*)\]\s*,?\s*")
def imks_at_completer(self, event):
    # event has command, line, symbol, text_until_cursor
    # self._ofind(base) has obj, parent, isalias, namespace, found, ismagic
    parts = event.text_until_cursor.split("@")
    if len(parts) != 2: raise TryNext
    us = parts[1]                       # unit or system part
    vs = re_unit_match.split(us)[-1]    # last unit or system
    v = re_space_match.split(vs)[-1]
    readline.set_completer_delims(" \t\n@()[]+-/*^|&=<>,")
    if vs.find("[") >= 0:
        return imks_completer.get_prefunits(v)
    else:
        return imgs_completer.get_systems(v)

re_item_match = re.compile(r"(?:.*\=)?(.*)\[((?P<s>['\"])(?!.*(?P=s)).*)$")
def imks_dict_completer(self, event):
    m = re_item_match.split(event.text_until_cursor)
    if len(m) < 3:
        if event.text_until_cursor[-1] == "[": return ['"']
        else: return []
    base, item = m[-4], m[-3]
    try:
        obj = _retrieve_obj(base, self)
    except:
        return []
    items = obj.keys()
    readline.set_completer_delims(" \t\n@()[]+-/*^|&=<>,")
    return imks_completer.get_quotes(item, items)

def imks_date_completer(self, event):
    text = event.text_until_cursor
    n = len(text) - 1
    quote = None
    while n >= 0:
        c = text[n]
        if (c == '"' or c == "'") and quote is None:
            quote = n
            break
        n -= 1
    n -= 1
    nargs = 1
    npar1 = 0
    npar2 = 0
    npar3 = 0
    quot1 = 0
    quot2 = 0
    name  = ""
    while n >= 0:
        c = text[n]
        if c == ")": npar1 += 1
        elif c == "(":
            npar1 -= 1
            if npar1 == -1 and npar2 == 0 and npar3 == 0 and \
                   quot1 == 0 and quot2 == 0:
                m = re.match(ur".*(\b(?!\d)\w\w*\b)$", text[0:n])
                if m: name = m.group(1)
                else: name = None
                break
        elif c == "," and npar1 == 0 and npar2 == 0 and npar3 == 0 and \
                 quot1 == 0 and quot2 == 0: nargs += 1
        elif c == "]": npar2 += 1
        elif c == "[": npar2 -= 1
        elif c == "}": npar3 += 1
        elif c == "{": npar3 -= 1
        elif c == '"': quot1 = 1 - quot1
        elif c == "'": quot2 = 1 - quot2
        n -= 1
    obj = _retrieve_obj(name, self)
    if not issubclass(obj, calendars.CalDate): return TryNext
    item = text[quote:]
    if nargs == 1:
        readline.set_completer_delims(" \t\n@()[]+-/*^|&=<>,")
        return imks_completer.get_quotes(item, ["today", "now"])
    else:
        names = list(getattr(obj, obj.dateparts_order[nargs-1] + "names", []))
        if nargs == obj.holidayarg+1 and obj.holidays:
            names.extend(obj.holidays.keys())
        names = [name for name in names if name != ""]
        names.sort()
        readline.set_completer_delims(" \t\n@()[]+-/*^|&=<>,")
        return imks_completer.get_quotes(item, names)
    return []
    

def load_ipython_extension(ip):
    # set up simplified quantity input
    for s in (ip.input_splitter, ip.input_transformer_manager): 
        s.logical_line_transforms.insert(0, input_command_transformer()) 
        s.python_line_transforms.extend([input_unit_transformer()])

    # load symbols
    units.load_variables(ip)

    # set the display mode
    # ip = get_ipython()

    # magic
    ip.register_magics(imks_magic)

    # active true float division
    exec ip.compile("from __future__ import division", "<input>", "single") \
        in ip.user_ns

    # load Startup
    mpmath_engine(ip)
    ip.run_line_magic("load_imks", "Startup")
    
    # setup completer
    r"(?:.*\=)?(\d+(?:\.\d*)?(?:[eE][-+]?\d*))(?:\[)"
    ip.set_hook("complete_command", imks_value_completer,
                re_key=r"(?:.*\=)?(\d+(?:\.\d*)?(?:[eE][-+]?\d*)?)\[")
    ip.set_hook("complete_command", imks_at_completer,
                re_key=r"([^@]+)@")
    ip.set_hook("complete_command", imks_dict_completer,
                re_key=r"(\b(?!\d)\w\w*)\[")
    ip.set_hook("complete_command", imks_date_completer,
                re_key=r"(.+)\([^'\"]*['\"]")

    print "Welcome to iMKS 1.0 - (C) Marco Lombardi 2014"
    print "Type %imks -h for help."
