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
  one tries to add a length with a time).

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

* Allow the use of "lazy" quantities (variables, units, prefixes) whose value is
  evaluated each time the quantity is required.

* Add an easy way to write documentation strings for any quantity, including
  variables.

* Several mathematical engines can be used: the standard Python math module,
  mpmath, fpmath (mpmath with fixed point arithmetic), numpy, and umath (based
  on the uncertanties package), soerp (higher order error analysis), and mcerp
  (Monte Carlo error analysis).  The engines are used to perform calculations
  involving mathematical functions.

* Engines with error analysis (umath, soerp, and mcerp) will keep track of the
  error propagation within all define variables or physical constants.

* Advanced input transformations and output formats for special quantities such
  as angles in sexagesimal format, times, dates...
  
Use of iMKS
-----------

iMKS extends the standard Python syntax in several ways:

* Physical quantities can be entered using the format 9.8[m s^-2] or
  9.8[m/s^2], i.e. with a number followed by a unit specification in brackets.
  In simple cases, quantities can also be entered without the brackets:
  9.8 m/s^2 or 9.8 m s^-2.  This shorter notation however can generate
  ambiguities when the quantity is exponentiated (2m^2 is 2[m^2], while 2[m]^2
  is 4[m^2]) or when a unit has the same name of a variable (12 km/h is a
  speed, 12[km/h] or 12[km] over the Planck constant?).  Moreover, in the
  shorter notation parentheses in units, such as 3[m/(s K)], are not accepted.

* A unit specification follows a standard notation: it is a space-separated
  list of prefixed units followed by an optional exponent.  A prefixed unit is
  a unit with a prefix, such as [km] = prefix k + simple unit m.  The exponent
  in the unit must be a simple number or a fraction: it cannot involve any
  other term (for example, [km^a] is not a valid unit, while [km^2/3] is).  In
  a unit specification one can use an arbitrary number of parentheses; within
  a parenthesis, a single division can be used, as in 9.8[m/s^2]. Additionally,
  a unit specification can contain (at most) one divide (/) sign: in this case
  all units following the sign will have their exponents reversed.

* Physical quantities can be used in expressions with the standard operators.
  
* The result of an expression can be converted into a different unit by using
  the @ operator:

  > 12 m + 3 cm @ km --> 0.01203[km]

  Multiple units can be used after the @ operator: in that case, they are
  combined as necessary to obtain the requested quantity

  > 20[m/s] @ [km|hour] --> 72.0[km hour^-1]

  When the quantity can be represented using multiple combinations, the
  shorter one is used (i.e., the one that involves the smallest number of
  elements in the list at the right of the @ operator):

  > 20[m/s] @ [km|hour|mph] --> 44.738725841088[mph]

* In some cases, it might be useful to use a variable as a unit.  To do this,
  one can use single quotes around a variable name in the unit specification:

  > 5[s 'c'] @ [km] --> 1498962.29[km]
  > 3['g'] --> 29.41995[m s^-2]

* The same operation can be performed in the argument of the at (@) operator:

  > 300000[km] @ [s 'c'] --> 1.00069228559446[s 'c']
  > 1e30[kg] @ ['c'|'G'] --> 742.564845009288['c'^2 m 'G'^-1]
  > 1K @ ['k'|eV] --> 8.61733238496096e-5[eV 'k'^-1]

* The output unit, set by the @ operator, can also contain double quoted
  variables.  In this case the value is completely transformed using the
  appropriate combination of the variables, thus removing any appearance of
  the variable in the final result.  This technique generally changes the
  unit of the quantity (and not only the displayed unit):

  > 300000[km] @ [s|"c"] --> 1.00069228559446[s]
  > 1e30[kg] @ ["c"|"G"] --> 742.564845009288[m]
  
* iMKS understands special units, such as the temperature related ones, that
  are defined together with a zero point, i.e. in terms of an affine
  transformation.  Quantities involving these units alone are called absolute:

  > 300[K] @ [Celsius] --> 26.85[Celsius]
  > 122°F @ °C --> 50.0[°C]

  Absolute quantities can be made relative (and vice-versa) by using the tilde
  (~) operator.  For example, 300[K] is understood as an absolute temperature,
  but ~300[K] as a relative one (i.e. a temperature difference): therefore

  > ~300[K] @ [Celsius] --> ~300.0[Celsius]

  Another example of absolute quantities are calendar dates or datetimes:

  > %load_imks_ext calendars
  > Egyptian("today") + 2[day] --> 1 First of Akhet (Thoth) 2764

* The @ operator can be used to force the display of a result using a specific
  prefix or a set of prefixes.  For this, one can just specify the desired
  prefix(es) after the @ inside the brackets:

  > 1200[s] @ [k] --> 1.2[ks]

  If multiple prefixes are used, the most convenient one is selected:
  
  > 1200[s] @ [k|M] --> 1.2[ks]

  A dot (.) can be used to specify that no prefix is also accepted; a star (*)
  to select all known prefixes:

  > 8[m] @ [.|k|M] --> 8.0[m]
  > 0.12[cm] @ [m|*] --> 1.2[mm]

  Note that if a prefix has the same name as a valid unit, one needs to use a
  star after the prefix name, to indicate that the name must be understood as a
  prefix rather than a unit:

  > 12[cm] @ [m] --> 0.12[m]
  > 12[cm] @ [m*] --> 120.0[mm]

  The star can also be used within a single unit to indicate that an arbitrary
  prefix is allowed:

  > 1200[m] @ [*m] --> 1.2[km]

* Unit systems work just like list of units that can be used after the @
  operator:

  > 72[km/hour] @ [SI] --> 20.0[m s^-1]

  A star prepended or appended to a unit system indicates that a prefix among
  all known ones can be used to make the expression simpler; the same effect is
  obtained if the star is specified within the brackets with the unit system:

  > 5600[K] @ [*SI] --> 5.6[kK]
  > 5600[K] @ [SI|*] --> 5.6[kK]

* Unit systems containing multiple units are especially convenient to reduce
  expressions to the simplest form

  > %newsystem easy=[m|s|kg|K|A|lx|mol|EUR|N|J|W|Pa|C|V|ohm|F|H|T|lx]
  > 6.63e-34[kg m^2 s^-1] @ [easy] --> 6.63e-34[s J]

* Unit systems can also contain variable units: this is especially useful to
  define natural unit systems:

  > %newsystem planck=["c"|"hbar"|"G"|"ke"|"k"] # "Planck's natural system"
  > 1[m] @ [planck] --> 6.18735589978243e+34

  The reverse conversion can be performed by indicating the output unit at the
  beginning of the unit specification, and by adding the unit system:

  > 6.2e34 @ [m|planck] --> 1.00204353853607[m]
  > 1 @ [kg|planck] --> 2.17650925244531e-8[kg]

  Note that this notation is an exception to the general rule that pure numbers
  are not influenced by unit specifications.  Note also that the order is
  relevant here: first the final unit, than all the natural system:

  > 1 @ [planck|kg] --> 1
  > 1 @ [kg/m|"c"|"G"] --> 1.34668373640485e+27[kg m^-1]
  > 1 @ [kg|m|"c"|"G"] --> 1

* When a natural unit system is used enclosed within single or double quotes,
  all the quotes of the unit system are replaced by the one used: hence,
  ['planck'] is identical to ['c'|'hbar'|'G'|'ke'|'k'].  This is useful to
  explicitly show all the converting factors in the result:

  > 1 @ [kg|'planck'] --> 2.17650925244531e-8['G'^1/2 'c'^-1/2 'hbar'^-1/2 kg]
  > 2.17650925244531e-8['G'^1/2 'c'^-1/2 'hbar'^-1/2 kg] --> 0.999999999999999
  
* The @ operator can also be used in variable definitions to set the default
  display unit to be used for a variable:

  > v = 20[m/s] @ [km|hour]
  > v --> 72.0[km hour^-1]

* When an engine with error analysis is used (umath, soerp, or mcerp), the
  special syntax value +/- error can be used to input quantities with errors:

  > %imks -c umath
  > %reset
  > v = (3+/-0.1)[m/s]
  > v^2 @ [mph] --> (45.0+/-3.0)[mph^2]

  Uncertainties are silently ignored with engines not supporting them.  The
  same quantity, (3+/-0.1)[m/s] can also be entered without parentheses,
  3+/-0.1m/s, using the ± sign instead of the +/-, or using a shorter notation
  3.0(1)[m/s] (see uncertainties for a list of formats accepted). 

* Correlation among variables is automatically taken into account:

  > w = (3+/-0.1)[m/s]
  > v + w --> (6.00+/-0.14)[m s^-1]
  > v + v --> (6.00+/-0.20)[m s^-1]

* Input transformer make it easy to enter special quantities such as
  sexagesimal angles or times:

  > 18d 24' 32" --> 0.321295722745
  > 12h 34m 56s --> 45296.0[s]

  The reverse is also possible using output formats

  > 1[rad] @ [dms] --> 57d 17' 44.806s"
  > 10[ks] @ [hms] --> 2h 46m 40s
  
* Documentation strings can be entered even for variables:

  > v = 50[km/hour] # "Standard maximum speed within towns"


Configuration file
------------------

When launched, iMKS load definitions from the configuration file Startup.imks.
This file is searched in the current directory, and if not found in the
~/.imks directory.  The file should contain the standard definitions that one
is likely to need for any computation.  Typically the file uses the following
magic commands:

%newbaseunit <name>
  Define a new base unit.  Base units are the building blocks for all
  subsequent units definitions.  A base unit does not have a value: for
  example, one cannot express a meter in any other unit if no unit of length
  is known.

%newbasecurrency <name>
  Define a new base currency, used for all currency conversions.  A base
  currency is also a base unit.

%newprefix <name>=<expression>
  Define a new prefix.  The <expression> value evaluate to a simple number.

%newunit <name>=<expression>
  Define a new unit.  <expression> should evaluate to a Value'd number.  To
  define a new absolute unit, expression should evaluate to a 2-tuple with
  identical units (indicating the zero-point, and the scale).

%newsystem <name>=[u1], [u2], ...
  Define a new unit system.  A unit system is simply a list of units.

%defaultsystem <name>
  Set the unit system to use in case no @ is used.

%newtransformer <name>="regex":<transformer>
  Define a new input transformer: the regular expression regex is applied to
  each input line, and if a match is found the <transformer> function is
  called together with all named matching groups which must return the
  transformed input.

%newformat <name>=<transformer>
  Define a new output format.  When <name> is entered (alone) in a unit
  specification, <transformer> is called with the result of the expression: it
  must return a string that will be displayed on the screen.
  

Other magic commands
--------------------

%imks [<options>]
  Show this help page or set configuration options for iMKS.

%delprefix, %delunit, %delsystem, %deltransformer, or %delformat <name>
  Delete a previously define prefix, unit, unit system, transformer, or format.

%lazy <name>=<expression>
  Define the variable <name> as <expression> lazily: that is, <expression> is
  evaluated only when <name> is used or displayed.  This is implemented by
  making <name> a function with no arguments, and by automatically adding a
  function call name() when name is used in the input.

%dellazy <name>
  Delete a previously defined %lazy variable.

%lazyvalue <name>=<expression>
  Define the variable <name> as <expression> lazily: that is, <expression> is
  evaluated only when <name> is used or displayed.  This only works for simple
  values, and not for more general objects such as %lazy.

%lazyprefix <name>=<expression>
  Define a lazy prefix (whose <expression> is evaluate only when the prefix is
  used).

%lazyunit <name>=<expression>
  Define a lazy unit (whose <expression> is evaluated only when the unit is
  used).

%compatible <stuff>
  Find out the known variables or units that are compatible to <stuff>.
  <stuff> can be either a unit (in brackets) or an expression.

%load_imks <filename>
  Load an external <filename> with definitions in iMKS format.

%load_imks_ext <filename>
  Load an imks extension.

%uinfo <name>
  Display an help page for a prefix, unit, or unit system.  This is the
  equivalent of %pinfo (which works for objects in the user namespace).  A
  short notation for %uinfo <name> is <name>! (i.e., the name of an imks
  object followed by the exclamation mark).  When used with the -a flag,
  as in %uinfo -a <text>, shows all quantities with <text> in their docstring.
  The same effect is achieved using <text>!!

%pickle <filename>
  Save all current variables into a filename, in the Python pickle format.

%unpickle <filename>
  Load all previously %pickle'd variables from a filename.

%reset
  Perform a full reset of the iMKS interpreter.


Extensions
----------

iMKS comes with a number of extensions that define new commands, new
variables, or new units.  Extensions are loaded with the command
%load_imks_ext.  The currently defined extensions are

* calendars: defines several new functions, one for each calendar (for example
  Gregorian, Julian, Roman, Egyptian...).  Each calendar accepts a date in
  several formats: as an integer (number of days from 1 January 1 C.E.), one of
  the strings "today", "tomorrow", "yesterday", or "now", as a year followed by
  a holiday name such as Gregorian(2017, "Easter"), or as a full year (with a
  number of arguments depending on the calendar).  Optionally, one can also
  add a time, counted from midnight, noon, sunset, or sunrise depending on the
  specification of the calendar.  When calendars are loaded, one can input a
  date using dot-separated integers.  For example, 1973.5.7 is interpreted as
  May 7th, 1973.  The default calendar used to interpret dates is the Gregorian
  one, but it can be changed using %imks -d <calendar>.  A date can be also
  followed by a time, in the format hh:mm[:ss.d].

* constants: loads a large list of constants from the NIST database.  Constants
  are then inserted into the variable const, a dictionary.

* currencies: loads a large list of currencies from the online database
  openexachangerages.org.  Currencies are then used as usual units.  Note that
  in order this to work, you first need to set a variable called
  openexchangerates_id as a string holding your id.

* geolocation: defines two functions to set the current geographic location and
  to retrieve it.

* jpl: loads the JPL database and creates two dictionaries, planets and moons,
  where it stores the physical and orbital data.  Additionally, it defines a
  function called minorplanet, which allows one to search a minor body database.

* wiki: experimental interface to Wikipedia.

  
Internals
---------

Internally, iMKS works by converting an input string into Python expressions.
The following rules are used:

* Physical quantities are converted into Value's:

  > 72[km hour^-1] --> Value(72,"km hour^-1")

* The @ operator is converted into the | operator, and what follows is put in
  a unit System:

  > 72[km hour^-1] @ [m], [s] --> Value(72,"km hour^-1") | System("m", "s")

* Quoted comments, used to enter documentation strings, are transformed into
  the & operator followed by a Doc object:

  > a=2 # "Simple string" --> a=2 & Doc("Simple string")

* Normal Python operator precedence applies to @=| and to #=&: that is, @ has
  a quite low precedence, which makes it possible to write expressions like

  > v = 15[m/s] + 10[m]/2[s] @ [km/hour]

  with the unit specification after @ applying to the result of the other
  operations.  Note also that since & binds stronger than |, in theory a
  # documentation string after the @ operator would apply to the unit
  specification, and not the the expression: however, this is handled
  internally by System (that is, the documentation string that System gets
  from the #=& operator is actually transferred to the result of the unit
  conversion).

* The ! operator, if used at the end of a string, is converted into a %uinfo
  magic (this is similar to the ? operator, that is converted by ipython into
  a %pinfo magic):

  > hour! --> %uinfo hour

  If used alone, instead, it is equivalent to %imks -h.  Note that the same !
  symbol can still be used to perform shell operations if used at the beginning
  of a line:

  > !ls

  Two exclamation marks are converted into the %uinfo -a magic:

  > mile!! --> mile, mph, nmi, mi

* Unicode characters appearing outside strings are converted into strings of 
  the form _uTf_xx_xx_xx..., where each xx is the hexadecimal representation
  of a byte of the character in UTF8 encoding.

* Value, System, and Doc are defined in units.py, and for these objects the
  standard operators are redefined to include tracking of physical units.

* If necessary, one can directly use the Value, System, and Doc objects to
  make more complicated expressions.

* The know prefixes, units, and unit systems are stored in the dictionaries
  prefixes, units, and systems, freely accessible from the user space.
"""

from __future__ import absolute_import, division, print_function
from traitlets import List, Int, Any, Unicode, CBool, Bool, Instance
from IPython.core.inputtransformer import (CoroutineInputTransformer, 
                                           StatelessInputTransformer,
                                           TokenInputTransformer,
                                           _strip_prompts)
from IPython.core import inputsplitter as isp
from IPython.core import inputtransformer as ipt
from collections import OrderedDict as ODict
from collections import deque
from io import StringIO
import token, tokenize, re
from unidecode import unidecode
from ._version import __version__, __date__
from . import units
from . import currencies
from . import calendars

config = {"banner": True,
          "enabled": True,
          "auto_brackets": True,
          "standard_exponent": True,
          "engine": "",
          "sort_units": units.sortunits,
          "unit_tolerant": units.tolerant,
          "prefix_only": units.prefixonly,
          "show_errors": units.showerrors,
          "digits": 15,
          "min_fixed": None,
          "max_fixed": None}
engine = "ufloat"
engine_module = None
lazyvalues = set()
extensions = set()

######################################################################
# Magic functions

from IPython.core.magic import Magics, magics_class, line_magic
from IPython.core import page
from IPython.core.magic_arguments import (argument, magic_arguments,
    parse_argstring)

@magics_class
class imks_magic(Magics):
    re_doc = re.compile(r'([^#]+)\s*#\s*"(.*)(?<!\\)"\s*')

    def split_command_doc(self, line):
        m = re.match(self.re_doc, line)
        if m:
            doc = m.group(2).strip(' ')
            doc = doc.encode('latin-1').decode('unicode_escape')
            line = m.group(1)
        else: doc = ""
        return (line, doc)

    @classmethod
    def imks_doc(cls):
        """Activate and deactivate iMKS, and set iMKS options.

        Options:
          -h           show an help page on iMKS
          -a <on|off>  auto brackets for units [%s]
          -e <on|off>  allow the use of the caret (^) as an exponent (**) [%s]
          -t <on|off>  toggle the zero-value tolerance.  When enabled, zero values
                       are sum-compatible with any unit [%s]
          -s <on|off>  toggle the sorting of compound units.  When enabled, compound
                       units are sorted to show first positive units [%s]
          -k <on|off>  toggle the use of prefixes without units.  When enabled, one
                       can enter quantities such as 1[k] to indicate 1000 [%s]
          -c <name>    specify the engine for mathematical calculations: must be one
                       of math, mpmath, fpmath, numpy, umath, soerp, mcerp [%s]
          -o <0|1|2>   ignore errors on outputs (0), use them only to set the number
                       of significant digits (1), or show them (2) [%d]
          -d <cal>     default calendar to interpret dates (XXXX.YY.ZZ [HH[:MM[:SS]]])
                       [%s]
                       
        Options for the mpmath engine: 
          -p <digits>  set the number of digits to use for calculations [%d]
          -m <min>     specify the minimum digits for fixed notation [%s]
          -M <max>     specify the maximum digits for fixed notation: outside the
                       range indicated by -m min and -M max the exponential notation
                       is used.  To force a fixed format always, use min=-inf and
                       max=+inf; to force an exponential format always, use min=max
                       [%s]

        An additional <on|off> argument enable or disable imks altogether [%s].
        """
        global config
        imks_magic.__dict__["imks"].__doc__ = imks_magic.imks_doc.__doc__ % \
            ("on" if config["auto_brackets"] else "off",
             "on" if config["standard_exponent"] else "off",
             "on" if config["unit_tolerant"] else "off",
             "on" if config["sort_units"] else "off",
             "on" if config["prefix_only"] else "off",
             config["engine"], config["show_errors"],
             config.get("default_calendar", "none"),
             config["digits"], config["min_fixed"], config["max_fixed"],
             "on" if config["enabled"] else "off")


    @line_magic
    def imks(self, args):
        def imks_print(s):
            if units.units or len(units.prefixes) > 1:
                print(s)
                
        global config
        opts, name = self.parse_options(args, 'ha:e:u:s:k:t:c:m:M:p:o:d:')
        if name in ["on", "1", "yes"]:
            config["enabled"] = True
            imks_print("iMKS enabled")
        elif name in ["off", "0", "no"]:
            config["enabled"] = False
            imks_print("iMKS disabled")
        elif len(args) == 0:
            config["enabled"] = not config["enabled"]
            imks_print("iMKS %s" % ("enabled" if config["enabled"] \
                                    else "disabled"))
        if "h" in opts:
            page.page(__doc__)
            imks_magic.imks_doc()
            if not units.units and len(units.prefixes) <= 1:
                config["banner"] = False
                self.shell.confirm_exit = False
                self.shell.exit()
            return 
        if "a" in opts:
            if opts["a"] in ["on", "1", "yes"]:
                config["auto_brackets"] = True
                imks_print("Auto brackets enabled")
            elif opts["a"] in ["off", "0", "no"]:
                config["auto_brackets"] = False
                imks_print("Auto brackets disabled")
            else:
                print("Incorrect argument.  Use on/1 or off/0")
        if "e" in opts:
            if opts["e"] in ["on", "1", "yes"]:
                config["standard_exponent"] = True
                imks_print("Standard exponent (^) enabled")
            elif opts["e"] in ["off", "0", "no"]:
                config["standard_exponent"] = False
                imks_print("Standard exponent (^) disabled")
            else:
                imks_print("Incorrect argument.  Use on/1 or off/0")
        if "s" in opts:
            if opts["s"] in ["on", "1", "yes"]:
                config["sort_units"] = units.sortunits = True
                imks_print("Compound units are sorted")
            elif opts["s"] in ["off", "0", "no"]:
                config["sort_units"] = units.sortunits = False
                imks_print("Compound units are not sorted")
            else:
                print("Incorrect argument.  Use on/1 or off/0")
        if "k" in opts:
            if opts["k"] in ["on", "1", "yes"]:
                config["prefix_only"] = units.prefixonly = True
                imks_print("Prefix without unit accepted")
            elif opts["k"] in ["off", "0", "no"]:
                config["prefix_only"] = units.prefixonly = False
                imks_print("Prefix without unit not accepted")
            else:
                print("Incorrect argument.  Use on/1 or off/0")
        if "t" in opts:
            if opts["t"] in ["on", "1", "yes"]:
                config["unit_tolerant"] = units.tolerant = True
                imks_print("Zero-value tolerance enabled")
            elif opts["t"] in ["off", "0", "no"]:
                config["unit_tolerant"] = units.tolerant = False
                imks_print("Zero-value tolerance disabled")
            else:
                print("Incorrect argument.  Use on/1 or off/0")
        if "c" in opts:
            if opts["c"] in ["math", "mpmath", "fpmath", "numpy",
                             "umath", "soerp", "mcerp"]:
                try:
                    change_engine(self.shell, opts["c"])
                    imks_print("iMKS math engine: %s.  Consider doing a %%reset." %
                               opts["c"])
                except ModuleNotFoundError:
                    pass
            else:
                print("Incorrect argument: must be math, mpmath, fpmath, numpy, umath, soerp, or mcerp.")
                return
            config["engine"] = opts["c"]
        if "o" in opts:
            if opts["o"] == "0":
                config["show_errors"] = units.showerrors = 0
                imks_print("Errors ignored")
            elif opts["o"] == "1":
                config["show_errors"] = units.showerrors = 1
                imks_print("Errors not shown")
            elif opts["o"] == "2":
                config["show_errors"] = units.showerrors = 2
                imks_print("Errors shown")
            else:
                print("Incorrect argument: must be 0, 1, or 2")
                return
        if "p" in opts:
            self.shell.user_ns["mp"].dps = config["digits"] = int(opts["p"])
            imks_print("Precision set to %d digits" % config["digits"])
        if "m" in opts or "M" in opts:
            from . import units_mpmath
            if "m" in opts:
                config["min_fixed"] = units_mpmath.min_fixed = \
                    eval(opts["m"], self.shell.user_ns)
            elif "M" in opts:
                config["max_fixed"] = units_mpmath.max_fixed = \
                    eval(opts["M"], self.shell.user_ns)
            imks_print("Fixed range:", units_mpmath.min_fixed, ":", \
                        units_mpmath.max_fixed)
        if "d" in opts:
            calnames = [c.calendar for c in calendars.calendars]
            if opts["d"] in calnames:
                config["default_calendar"] = opts["d"]
            else: print("Unkown calendar %s" % opts["d"])
            imks_print("Default calendar set to %s" % opts["d"])
        self.imks_doc()

    @line_magic
    def load_imks(self, arg):
        """Load one ore more imks modules.

        The modules are searched first in the current directory, then in the ~/.imks
        directory, and finally in the /script directory under the package location. The
        latter location contains the standard modules distributed with imks."""
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
                        path = os.path.join(os.environ["HOME"], ".imks",
                                            filename)
                        code = ip.find_user_code(path, py_only=True)
                    except:
                        try:
                            path = os.path.dirname(units.__file__)
                            path = os.path.join(path, "scripts", filename)
                            code = ip.find_user_code(path, py_only=True)
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

        Usage:
          %load_imks_ext [-s] extension1 [, extension2...]

        If the -s flag is used the entire operation is silent; otherwise, a list of 
        newly defined symbols is displayed. If no extension is provide, the list of
        all extensions loaded so far is printed.

        Currently, the following extensions are recognized:
          calendars     allow the use of multiple calendars
          constants     load a large list of constants from the NIST database
                        and set the const dictionary accordingly
          currencies    load a large list of currencies from the database
                        openexchangerates.org and define them as units
          geolocation   define two functions, set/get_geolocation to handle
                        geographical locations
          jpl           load planetary data from the SSD JPL database
          wiki          search through Wikipedia infoboxes"""
        import os, os.path
        global extensions
        ip = self.shell
        oldkeys = set(ip.user_ns.keys())
        oldunits = set(units.units.keys())
        exts = arg.split()
        silent = False
        if len(exts) == 0:
            from textwrap import wrap
            print("\n  ".join(wrap("Extensions loaded: %s." %
                                       (u", ".join(sorted(extensions))))))
            return
        for ext in exts:
            if ext == "-s": silent = True
            else:
                extensions.add(ext)
                if ext == "calendars":
                    global config
                    calendars.loadcalendars(ip)
                    config["default_calendar"] = "Gregorian"
                elif ext == "geolocation":
                    from . import geolocation
                    ip.user_ns["get_geolocation"] = geolocation.get_geolocation
                    ip.user_ns["set_geolocation"] = geolocation.set_geolocation
                elif ext == "constants":
                    from . import constants
                    constants.loadconstants(engine=eval(engine, self.shell.user_ns))
                    self.shell.user_ns["const"] = constants.constants
                elif ext == "jpl":
                    from . import jpl
                    planets, moons = jpl.loadJPLconstants()
                    self.shell.user_ns["planets"] = planets
                    self.shell.user_ns["moons"] = moons
                    self.shell.user_ns["minorplanet"] = \
                      lambda name: jpl.load_minor(name)
                elif ext == "currencies":
                    if "openexchangerates_id" in ip.user_ns:
                        app_id = self.shell.user_ns["openexchangerates_id"]
                    else: app_id = ""
                    currencies.currencies(app_id)
                elif ext == "wiki" or ext == "wikipedia":
                    from . import wiki
                    wiki.ip = self.shell
                    wiki.unit_transformer = unit_transformer
                    wiki.command_transformer = command_transformer
                    self.shell.user_ns["wiki"] = wiki.wiki
                else:
                    extensions.discard(ext)
                    print("Unknown extension `%s'." % ext)
        newkeys = set(ip.user_ns.keys())
        newunits = set(units.units.keys())
        if not silent:
            from textwrap import wrap
            if newkeys != oldkeys:
                diff = list(newkeys - oldkeys)
                diff.sort()
                print("\n  ".join(wrap("New definitions: %s." % (u", ".join(diff)))))
            if newunits != oldunits:
                diff = list(newunits - oldunits)
                diff.sort()
                print("\n  ".join(wrap("New units: %s." % (u", ".join(diff)))))

    def checkvalidname(self, arg):
        if re.search(r"[0-9]", arg):
            raise NameError("Invalid name \"%s\"" % arg)
                
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
        self.checkvalidname(command)
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
        self.checkvalidname(command)
        units.newbasecurrency(command.strip(), doc=doc)
        return

    @line_magic
    def newprefix(self, arg):
        """Define a new prefix.

        Usage:
          %newprefix name=[aliases=]value [# "Documentation string"]

        A prefix is used before a unit to build a prefixed unit: for example, the
        unit km is understood as k+m, i.e. the prefix k=1000 times the unit m=meter.
        The value of a prefix must always be a pure number; moreover, fractional
        prefixes (such as m=1/1000) should be entered in the mpmath engine using
        the fraction function (this ensures that the prefix is always computed at
        the required accuracy).

        See also:
          %delprefix, %newunit, %delunit."""
        from io import StringIO
        command, doc = self.split_command_doc(arg)
        tmp = command.split("=")
        names, value = tmp[:-1], tmp[-1]
        tokens = tokenize.generate_tokens(StringIO(value.strip()).readline)
        walue = self.shell.ev(tokenize.untokenize(
            unit_transformer([t for t in tokens])))
        for name in names:
            self.checkvalidname(name)
            units.newprefix(name.strip(), walue, doc=doc, source=value.strip())
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
          %newunit name=[aliases=]value [# "Documentation string"]

        After its definition, a unit can be used for any physical quantity.  If
        value evaluates to a 2-tuple, the unit is understood as an absolute
        unit: in this case the two elements of the tuple must have the same
        unit, and must represent the zero-point and the offset.  This technique
        can also be used with base units, to make them absolute:

        > %newunit Celsius=(273.15[K], 1[K])
        > %newunit K=(0[K], 1[K])

        A unit can be deleted using the %delunit magic."""
        from io import StringIO
        command, doc = self.split_command_doc(arg)
        tmp = command.split("=")
        names, value = tmp[:-1], tmp[-1]
        tokens = tokenize.generate_tokens(StringIO(value.strip()).readline)
        evalue = self.shell.ev(tokenize.untokenize(
            unit_transformer([t for t in tokens])))
        for name in names:
            self.checkvalidname(name)
            units.newunit(name.strip(), evalue, doc=doc, source=value.strip())
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
          %newsystem name=[aliases=]u1 | u2 | ... [# "Documentation string"]

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

        > %newsystem one=[m | s]
        > %newsystem two=[m | s | km/hour]

        If we then type
        > c @ one
        we will obtain c in units of [m s^-1], a combination of the two provided
        units.  Instead
        > c @ two
        will use as a unit [km hour^-1], since this is a unit entered in the system
        and as such it is privileged over the combination [m s^-1] (which instead
        requires the use of two different units entered).
        
        A unit system can be deleted using the %delsystem magic."""
        command, doc = self.split_command_doc(arg)
        tmp = command.split("=")
        names, value = tmp[:-1], tmp[-1]
        values = [value.strip("[] ") for value in value.split("|")] 
        for name in names:
            self.checkvalidname(name)
            units.newsystem(name.strip(), values, doc=doc)
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
          %defaultsystem system

        where system is a previously define unit system or a list of units
        separated by | as in %newsystem.  Do not use any argument to unset the
        default unit system."""
        if len(arg) == 0:
            units.defaultsystem = None
        else:
            units.defaultsystem = units.System(*[v.strip("[] ")
                                                 for v in arg.split("|")])
            units.cachedat = {}

    @line_magic
    def let(self, arg):
        """Define a variable.

        Usage:
          %let name=[aliases=]value [# "Documentation string"]

        The advantage of using let over a simple assignment is that the entire
        variable definition is retained and can be queried when inspecting the
        variable."""
        from io import StringIO
        command, doc = self.split_command_doc(arg)
        tmp = command.split("=")
        names, value = tmp[:-1], tmp[-1]
        tokens = tokenize.generate_tokens(StringIO(value.strip()).readline)
        evalue = self.shell.ev(tokenize.untokenize(
            unit_transformer([t for t in tokens])))
        evalue = evalue & units.Doc(doc, value)
        try:
            evalue.__source__ = value.strip()
        except AttributeError:
            pass
        for name in names:
            self.shell.user_ns[name.strip()] = evalue
        return
            
    @line_magic
    def lazy(self, arg):
        """Define a general lazy value in terms of an expression.

        Usage:
          %lazy var=[aliases=]=expr  [# "Documentation string"]

        This magic defines the variable var to be the result of expression.  In
        contrast to standard variables, however, expr is not computed immediately:
        rather, it is evaluated only when var is used or displayed.

        This magic can be used similarly to %lazyvalue: the difference is that %lazy
        support any kind of variable, while %lazyvalue is limited to simple values.
        The mechanism used is also different: %lazy defines var to be a function with
        no argument, and include it to an internal list used to automatically add ()
        when parsing the input line; %lazyvalue uses the LazyValue python object (a
        child of Value)."""
        from io import StringIO
        global lazyvalues
        command, doc = self.split_command_doc(arg)
        command = command.replace('"', '\\"').replace("'", "\\'")
        opts, command = self.parse_options(command, "1u")
        tmp = command.split("=")
        names, source = tmp[:-1], tmp[-1]
        lazyvalues.difference_update([name.strip() for name in names])
        value = "lambda : " + source
        tokens = tokenize.generate_tokens(StringIO(value.strip()).readline)
        s = tokenize.untokenize(unit_transformer(list(tokens)))
        value = self.shell.ev(s)
        for name in names:
            self.shell.user_ns[name.strip()] = value & units.Doc(doc, source)
            lazyvalues.add(name.strip())

    @line_magic
    def dellazy(self, arg):
        """Delete a previously defined lazy variable.

        Usage:
          %dellazy var

        This magic needs to be used only for variables defined through %lazy, and
        not for the ones defined through %lazyvalue (which can be deleted with the
        usual python del command, or by just overwriting them)."""
        global lazyvalues
        lazyvalues.difference_update([arg.strip()])
        del self.shell.user_ns[arg.strip()]
            
    @line_magic
    def lazyvalue(self, arg):
        """Define a variable lazily in terms of an expression.

        Usage:
          %lazyvalue [options] var=[aliases=]=expr  [# "Documentation string"]

        This magic defines the variable var to be the value of expression.  In contrast
        to standard variables, however, expr is not computed immediately: rather, it is
        evaluated only when var is used or displayed.  Among other uses, this allows
        one to define variables with a arbitrary precision (in the sense that the
        precision used when calculating the variable is the one set at real time), or
        variables that depend dynamically on other external variables.  Note that this
        magic only works for simple values: for more complicated combination, please
        use the %lazy magic.

        Options:
          -u   Evaluate the expression unit each time (by default, the value of the
               expression is recomputed each time it is needed, but the unit is
               computed only once, the first time variable is calculated)
          -1   Evaluate the entire expression (unit and value) only once, the first
               time the variable is calculated

        See also %lazy, %lazyunit, and %lazyprefix."""
        from io import StringIO
        command, doc = self.split_command_doc(arg)
        command = command.replace('"', '\\"').replace("'", "\\'")
        opts, command = self.parse_options(command, "1u")
        tmp = command.split("=")
        names, value = tmp[:-1], tmp[-1]
        value = "lambda : " + value
        tokens = tokenize.generate_tokens(StringIO(value.strip()).readline)
        value = self.shell.ev(tokenize.untokenize(
            unit_transformer([t for t in tokens])))
        lvalue = units.LazyValue(value, once="1" in opts, unit_once="u" not in opts)
        for name in names:
            self.shell.user_ns[name.strip()] = lvalue

    @line_magic
    def lazyprefix(self, arg):
        """Define a prefix lazily in terms of an expression.

        Usage:
          %lazyprefix [options] var=[aliases=]=expr  [# "Documentation string"]

        Similar to %lazy, but used to define a lazy prefix (see also %lazyunit).

        Options:
          -1   Evaluate the entire expression only once, the first time the prefix is
               used"""
        from io import StringIO
        command, doc = self.split_command_doc(arg)
        opts, command = self.parse_options(command, "1")
        tmp = command.split("=")
        names, value = tmp[:-1], tmp[-1]
        walue = "lambda : " + value
        tokens = tokenize.generate_tokens(StringIO(walue.strip()).readline)
        walue = self.shell.ev(tokenize.untokenize(
            unit_transformer([t for t in tokens])))
        lvalue = units.LazyValue(walue, once="1" in opts, unit_once=True)
        for name in names:
            self.checkvalidname(name)
            units.newprefix(name.strip(), lvalue, doc=doc, source=value.strip())

    @line_magic
    def lazyunit(self, arg):
        """Define a unit lazily in terms of an expression.

        Usage:
          %lazyunit [options] var=[aliases=]=expr  [# "Documentation string"]

        Similar to %lazy, but used to define a lazy unit (see also %lazyprefix).

        Options:
          -1   Evaluate the entire expression only once, the first time the unit is
               used"""
        from io import StringIO
        command, doc = self.split_command_doc(arg)
        opts, command = self.parse_options(command, "1")
        tmp = command.split("=")
        names, value = tmp[:-1], tmp[-1]
        walue = "lambda : " + value
        tokens = tokenize.generate_tokens(StringIO(walue.strip()).readline)
        walue = self.shell.ev(tokenize.untokenize(
            unit_transformer([t for t in tokens])))
        lvalue = units.LazyValue(walue, once="1" in opts, unit_once=True)
        for name in names:
            self.checkvalidname(name)
            units.newunit(name.strip(), lvalue, doc=doc, source=value.strip())

    @line_magic
    def newtransformer(self, arg):
        """Define a new input transformer.

           Usage:
             %newtransformer name="regex":transformer

           where name is the name of the new input transformer (only used as a key for
           %deltransformer), regexp is a regular expression using the named groups, and
           transformer is a function used to perform the input transformation."""
        command, doc = self.split_command_doc(arg)
        i = command.find("=")
        if i < 0: raise SyntaxError("equal sign not found")
        name, value = command[0:i], command[i+1:]
        quotes = re.split(r'(?<!\\)\"', value)
        regex = quotes[1]
        trans = quotes[2]
        if trans[0] != ':': raise SyntaxError("column sign not found")
        cregex = re.compile(regex)
        self.checkvalidname(name)
        config["intrans"][name] = (cregex, trans[1:].strip()) & \
            units.Doc(doc, regex + " : " + trans[1:])
        return

    @line_magic
    def deltransformer(self, arg=""):
        """Delete an input transformer previously defined using %newtransformer.

           Usage:
             %deltransformer name"""
        del config["intrans"][arg.strip()]
        return

    @line_magic
    def newformat(self, arg):
        """Define a new output format.

           Usage:
             %newformat name=transformer

           where name is the name of the new output transformer (only used as a key for
           %deltformat) and transformer is a function used to generate the output."""
        command, doc = self.split_command_doc(arg)
        i = command.find("=")
        if i < 0: raise SyntaxError("equal sign not found")
        name, value = command[0:i], command[i+1:]
        self.checkvalidname(name)
        units.formats[name] = eval(value, self.shell.user_ns) & units.Doc(doc, value)
        return

    @line_magic
    def delformat(self, arg=""):
        """Delete a format previously defined using %newformat.

           Usage:
             %delformat name"""
        del units.formats[arg.strip()]
        return

    @line_magic
    def uinfo(self, args):
        """Provide detailed information about an imks-related object.

        Usage:
          %uinfo [options] name

        Options:
          -a   Apropos mode: does search within documentation strings
          -y   Parsing mode: show how a prefix + unit is parsed
          -u   Search among units
          -c   Search among currencies
          -p   Search among prefixes
          -s   Search among unit systems
          -t   Search among input transformers
          -f   Search among output formats
          -x   Extended search: include variables
          -i   For wildcard searches, ignore the case"""
        global config
        opts, name = self.parse_options(args, "ayupstfxci")
        if name == "":
            self.shell.run_line_magic("imks", "-h")
            return
        u0 = dict([(k, w) for k, w in units.units.items()
                   if k in units.baseunits])
        u1 = dict([(k, w) for k, w in units.units.items()
                   if k not in units.baseunits and k not in currencies.basecurrency \
                   and k not in currencies.currencydict])
        c0 = dict([(k, w) for k, w in units.units.items()
                   if k in currencies.basecurrency])
        c1 = dict([(k, w) for k, w in units.units.items()
                    if k not in currencies.basecurrency and \
                       k in currencies.currencydict])
        namespaces = []
        if 's' in opts:
            namespaces.append(("Unit systems", units.systems))
        if 'u' in opts:
            namespaces.extend([("Base units", u0),
                               ("Units", u1)])
        if 'c' in opts:
            namespaces.extend([("Base currencies", c0),
                               ("Currencies", c1)])
        if 'p' in opts:
            namespaces.append(("Prefixes", units.prefixes))
        if 't' in opts:
            namespaces.append(("Input Transformers", config["intrans"]))
        if 'f' in opts:
            namespaces.append(("Output Formats", units.formats))
        if not namespaces:
            namespaces = [("Unit systems", units.systems),
                          ("Base units", u0),
                          ("Base currencies", c0),
                          ("Units", u1),
                          ("Currencies", c1),
                          ("Prefixes", units.prefixes),
                          ("Input Transformers", config["intrans"]),
                          ("Output Formats", units.formats)]
        if 'x' in opts:
            namespaces.append(("Variables", self.shell.user_ns))
        if 'a' in opts:
            name = name.upper()
            shown = False
            for n, d in namespaces:
                f = [k for k,v in d.items() \
                     if str(getattr(v, "__doc__", "")).upper().find(name) >= 0]
                if f:
                    if not shown: print(name)
                    print("%s: %s" % (n, ", ".join(f)))
                    shown = True
            if not shown:
                print("Nothing found")
            return
        if 'y' in opts:
            res = units.isunit(name)
            if res:
                print("%s parsed as prefix(%s) + unit(%s)" % (name, res[0], res[1]))
            else: print("%s is not a valid unit with prefix")
            return
        if '*' in name:
            psearch = self.shell.inspector.psearch
            d = dict(namespaces)
            try:
                psearch(name, d, d.keys(), ignore_case='i' in opts)
            except:
                self.shell.showtraceback()

        else:
            goodones = [n for n,ns in enumerate(namespaces)
                        if name in ns[1]]
            if goodones:
                if len(goodones) > 1: spaces = "  "
                else: spaces = ""
                res = []
                for goodone in goodones:
                    namespace = namespaces[goodone]
                    obj = namespace[1][name]
                    if len(goodones) > 1:
                        fields = [(namespace[0].upper(), "")]
                    else: fields = []
                    fields.extend([(spaces + "Type", obj.__class__.__name__),
                                   (spaces + "String Form", str(obj)),
                                   (spaces + "Namespace", namespace[0])])
                    if hasattr(obj, "__source__"):
                        fields.append((spaces + "Definition", obj.__source__))
                    fields.append((spaces + "Docstring", obj.__doc__ or
                                   "<no docstring>"))
                    if hasattr(obj, "__timestamp__"):
                        fields.append((spaces + "Timestamp",
                                       obj.__timestamp__ or "<no timestamp>"))
                    res.append(self.shell.inspector._format_fields(fields,13+len(spaces)))
                page.page("\n\n".join(res))
            else:
                res = units.isunit(name)
                if res:
                    print("%s parsed as prefix(%s) + unit(%s)" % (name, res[0], res[1]))
                else: print("Object `%s` not found" % name)
        return

    @line_magic
    def compatible(self, args):
        """Check units or variables compatible with a given value or unit.

        By default, the function checks both units and variables, but this can be
        changed using the appropriate flag.

        Usage:
          %compatible [options] <value|unit>
        
        Options:
        -u         Check only units
        -U list    When checking units consider only units in the quoted list
        -v         Check only variables
        -V list    When checking variables consider only the ones in the quoted list
        -l level   Search combined units containing level number of simple units
                   (default: level=1).  Use a negative level to search only for
                   direct compatibilities (without exponent).  Use level=0 to search
                   for aliases (identical units or variables).

        Examples:
        %compatible g
        %compatible -l 3 -v -V "c, G, hbar" [s]
        """
        import sys
        from io import StringIO
        opts, us = self.parse_options(args, "uU:vV:l:")
        level = int(opts.get("l", 1))
        if us[0] == '[' and us[-1] == ']':
            r = units.Value(1, us.strip("[] "))
        else:
            tokens = tokenize.generate_tokens(StringIO(us.strip()).readline)
            r = self.shell.ev(tokenize.untokenize(
                unit_transformer([t for t in tokens])))
        if "v" not in opts:
            print("Compatible units: ", end="")
            found = []
            if "U" in opts:
                where = ODict()
                for k in opts["U"].split(","):
                    k1 = k.strip(" []")
                    if k1 in units.systems:
                        for k2 in units.systems[k1].repr:
                            k3 = k2.strip(" []")
                            tmp = units.unityacc.parse(k3, lexer=units.unitlex)
                            where[str(tmp[1]).strip(" []")] = tmp[0]
                    else:
                        tmp = units.unityacc.parse(k1, lexer=units.unitlex)
                        where[str(tmp[1]).strip(" []")] = tmp[0]
            else:
                where = units.units
            for u in r.findCompatible(where, level=level):
                found.append(str(u))
            if not found: print("No compatible unit")
            else: print("Compatible units: %s" % ", ".join(found))
        if "u" not in opts:
            found = []
            if "V" in opts:
                where = ODict([(k.strip(), self.shell.user_ns[k.strip()])
                                for k in opts["V"].split(",")])
            else:
                where = self.shell.user_ns
            where = ODict([(k,v) for k,v in where.items()
                           if isinstance(v, units.Value)])
            for u in r.findCompatible(where, level=level):
                uu = str(u).strip("[] ")
                found.append(uu)
            if not found: print("No compatible value")
            else: print("Compatible values: %s" % ", ".join(found))

    @line_magic
    def pickle(self, args):
        """Pickle all current variables into a file.

        Usage:
          %pickle [-p protocol] filename
        """
        global config, engine_module
        import pickle 

        opts, us = self.parse_options(args, ":p")
        protocol = int(opts.get("p", 2))
        us = us.split()
        if len(us) != 1:
            print("Usage: %pickle [-p protocol] filename")
            return
        f = open(us[0], "wb")
        # Unload the engine, to remove engine-related variables
        if engine_module:
            engine_module.unload(self.shell)
            engine_module = None
        # Pickle all variables we can
        fails = []
        d = {}
        for k,v in self.shell.user_ns.items():
            try:
                d[k] = pickle.dumps(v)
            except:
                fails.append(k)
        if fails:
            print('Fails: %s' % (", ".join(fails)))

        pickle.dump(d, f, protocol=protocol)
        f.close()
        # Reload the engine
        globals()[config["engine"] + "_engine"](self.shell)
        print("Done.")

        
    @line_magic
    def unpickle(self, args):
        """Unpickle variables from a file.

        Usage:
          %unpickle filename
        """
        global config
        import pickle
        opts, us = self.parse_options(args, "")
        us = us.split()
        if len(us) != 1:
            print("Usage: %unpickle filename")
            return
        f = open(us[0], "rb")
        d = pickle.load(f)
        f.close()
        # Makes a reset
        units.reset()
        # Pickle all variables we can
        fails = []
        ns = self.shell.user_ns
        for k,v in d.items():
            try:
                w = pickle.loads(v)
                ns[k] = w
            except:
                fails.append(k)
        if fails:
            print('Fails: %s' % (", ".join(fails)))
        # Saves back all relevant variables
        units.save_variables(self.shell)
        print("Done.")

        
        
    @line_magic
    def reset(self, args):
        """Reset the iMKS session.

        This does a full reset: the engine, however, is left unchanged."""
        global lazyvalues, config
        import gc
        # this code is from IPython
        ip = self.shell
        ip.reset(new_session=False)
        gc.collect()
        # load new symbols
        units.reset()
        lazyvalues = set()
        units.load_variables(ip)
        # math engine: this is not reset!
        globals()[config["engine"] + "_engine"](ip)
        # input transformers
        config["intrans"] = {}
        # active true float division
        exec(ip.compile("from __future__ import division", "<input>", "single"),
             ip.user_ns)
        # check if currencies are loaded
        currencies.reset()
        # load Startup
        ip.run_line_magic("load_imks", "Startup")
        # reprint the welcome message
        if config["banner"]:
            print("Welcome to iMKS %s - © Marco Lombardi %s" %
                      (__version__, __date__))
            print("Type %imks -h or ! for help.")

        

######################################################################
# Input transformers
import string

re_date = re.compile(r"(\d+(\.\d+){2,})([ ]+\d\d?:\d\d?:\d\d?(\.\d*)?|[ ]+\d\d?:\d\d?(\.\d*)?|[ ]+\d\d?(\.\d*)?)?")
            
def command_transformer(line):
    global config
    if not config["enabled"]: return line
    if line.lstrip()[0:6] == "%lazy ":
        # Preset lazy variables for the token transformer
        names = line.lstrip()[6:].split("=")[0:-1]
        for name in names:
            lazyvalues.add(name.strip())
    if line and line[-1] == '!':
        if len(line) > 1 and line[-2] == '!': line = "%uinfo -a " + line[:-2]
        else: line = "%uinfo " + line[:-1]
    if config.get("default_calendar", None):
        replaces = []
        for m in re_date.finditer(line):
            datetime = [e.strip() for e in m.group(1).split(".")]
            if m.group(3):
                datetime.extend([e.strip() for e in m.group(3).split(":")])
            replaces.insert(0, ("%s(%s)" % (config["default_calendar"],
                                            ",".join(datetime)),
                                m.start(), m.end()))
        for what, start, end in replaces:
            line = line[:start] + what + line[end:]
    for r,t in config["intrans"].values():
        replaces = []
        for m in r.finditer(line):
            args = m.groupdict()
            reps = ['"%s": %s' % arg for arg in args.items()
                    if arg[1] is not None]
            replaces.insert(0, ("%s(**{%s})" % (t, ", ".join(reps)),
                                m.start(), m.end()))
        for what, start, end in replaces:
            line = line[:start] + what + line[end:]
    return line
input_command_transformer = StatelessInputTransformer.wrap(command_transformer)

def offset_token(t, delta):
    return (t[0], t[1], (t[2][0], t[2][1] + delta), (t[3][0], t[3][1]+delta), t[4])

def offset_tokens(ts, delta):
    return ts.__class__(offset_token(t, delta) for t in ts)

def change_token(t, value):
    return (t[0], value, (t[2][0], t[2][1]), (t[3][0], t[3][1]), t[4])

def unit_quote(queue):
    u = tokenize.untokenize(queue).strip()
    if u.find('"') < 0: return u'"' + u + u'"'
    elif u.find("'") < 0: return u"'" + u + u"'"
    else: return u'"""' + u + u'"""'
    

def unit_create(substatus, queue, brackets=False):
    string = queue[0][-1]
    if substatus == 0:
        if brackets:
            u = unit_quote(queue[2:-1])
            l1, c1 = queue[0][2]
            l2, c2 = queue[0][3]
            value = queue[0][1]
            if value.find(".") < 0 and value.find("e") < 0:
                value = value + ".0"
                c2 = c2 + 2
            offset = c2 + 7 + len(u) - queue[-2][3][1]
            return [(token.NAME, u"Value", (l1, c1), (l1, c1+5), string),
                    (token.OP, u'(', (l1, c1+5), (l1, c1+6), string),
                    (token.NUMBER, value, (l1, c1+6), (l2, c2+6), string),
                    (token.OP, u',', (l2, c2+6), (l2, c2+7), string),
                    (token.STRING, u, (l2, c2+7), (l2, c2+7+len(u)), string),
                    (token.OP, u')', (l2, c2+7+len(u)), (l2, c2+8+len(u)), string)], \
                    offset
        else:
            u = unit_quote(queue[1:])
            l1, c1 = queue[0][2]
            l2, c2 = queue[0][3]
            value = queue[0][1]
            if value.find(".") < 0 and value.find("e") < 0:
                value = value + ".0"
                c2 = c2 + 2
            offset = c2 + 7 + len(u) - queue[-1][3][1]
            return [(token.NAME, u"Value", (l1, c1), (l1, c1+5), string),
                    (token.OP, u'(', (l1, c1+5), (l1, c1+6), string),
                    (token.NUMBER, value, (l1, c1+6), (l2, c2+6), string),
                    (token.OP, u',', (l2, c2+6), (l2, c2+7), string),
                    (token.STRING, u, (l2, c2+7), (l2, c2+7+len(u)), string),
                    (token.OP, u')', (l2, c2+7+len(u)), (l2, c2+8+len(u)), string)], \
                    offset
    else:
        if brackets:
            u = unit_quote(queue[1:-1])
            l1, c1 = queue[0][2]
            offset = c1 + len(u) - queue[-1][3][1]
            return [(token.STRING, u, (l1, c1), (l1, c1+len(u)), string)], \
                   offset
        else:
            u = unit_quote(queue)
            l1, c1 = queue[0][2]
            offset = c1 + len(u) - queue[-1][3][1]
            return [(token.STRING, u, (l1, c1), (l1, c1+len(u)), string)], \
                   offset

def unit_transformer(tokens):
    global config
    if not config["enabled"]: return tokens

    # fix multiline issue
    tokens = list(filter(lambda t: t[0] != tokenize.NL, tokens))

    # @@@DEBUG
    # for t in tokens:
    #     tokenize.printtoken(*t)
    
    # First, check if there are uncertainties combinations
    if engine == "ufloat":
        newtoks = []
        ntokens = len(tokens)
        n = 0
        while n < ntokens:
            c0 = tokens[n][0]
            if c0 == token.NUMBER:
                if n < ntokens - 4 and \
                  tokens[n+1][0] == token.OP and tokens[n+1][1] == "+" and \
                  tokens[n+2][0] == token.OP and tokens[n+2][1] == "/" and \
                  tokens[n+3][0] == token.OP and tokens[n+3][1] == "-" and \
                  tokens[n+4][0] == token.NUMBER:
                    # check if we are using the (a +/- b)[exp] syntax
                    if n > 0 and n < ntokens - 5 and \
                      tokens[n-1][0] == token.OP and tokens[n-1][1] == "(" and \
                      tokens[n+5][0] == token.OP and tokens[n+5][1] == ")":
                      # OK, we might be using it, check if this is a function
                      # call
                        if n <= 1 or tokens[n-2][0] != token.NAME:
                            # not a function call: we need to remove the
                            # parentheses; check if the exponent is following
                            newtoks.pop()
                            if n < ntokens - 6 and \
                              tokens[n+6][0] == token.NAME and \
                              len(tokens[n+6][1]) >= 2 and \
                              tokens[n+6][1][0].lower() == "e" and \
                              tokens[n+6][1][1].isdigit():
                                # Get all digits after "e": the rest might be a
                                # unit specification
                                i = 2
                                t1 = tokens[n+6]
                                s = t1[1]
                                while i < len(s) and s[i].isdigit(): i = i+1
                                tokens[n+6] = (t1[0], s[0:i], t1[2],
                                               (t1[3][0], t1[2][1] + i), t1[4])
                                t = (token.NUMBER,
                                     tokenize.untokenize(tokens[n-1:n+7]),
                                     tokens[n-1][2], tokens[n+6][3],
                                     tokens[n][4])
                                newtoks.append(t)
                                if len(s.rstrip()) > i:
                                    t1 = (t1[0], s[i:], (t1[2][0], t1[2][1]+i),
                                          t1[3], t1[4])
                                    tokens[n+6] = t1
                                    n = n -1
                                n = n + 7
                                continue
                            elif (n < ntokens - 8 and \
                              tokens[n+6][0] == token.NAME and \
                              tokens[n+6][1].lower() == "e" and \
                              tokens[n+7][0] == token.OP and \
                              tokens[n+7][1] in ["+", "-"] and \
                              tokens[n+8][0] == token.NUMBER):
                                t = (token.NUMBER,
                                     tokenize.untokenize(tokens[n-1:n+9]),
                                     tokens[n-1][2], tokens[n+8][3],
                                     tokens[n][4])
                                newtoks.append(t)
                                n = n + 9
                                continue
                            else:
                                # The parentheses are not needed: remove them!
                                t = (token.NUMBER,
                                     tokenize.untokenize(tokens[n:n+5]),
                                     tokens[n-1][2], tokens[n+4][3],
                                     tokens[n][4])
                                newtoks.append(t)
                                n = n + 6
                                continue
                    t = (token.NUMBER, tokenize.untokenize(tokens[n:n+5]),
                         tokens[n][2], tokens[n+4][3], tokens[n][4])
                    newtoks.append(t)
                    n = n + 5
                    continue
                if n < ntokens - 3 and \
                  tokens[n+1][0] == token.OP and tokens[n+1][1] == "(" and \
                  tokens[n+2][0] == token.NUMBER and \
                  tokens[n+3][0] == token.OP and tokens[n+3][1] == ")":
                  # using the 1.234(5) notation: verify the possible presence
                  # of an exponent

                    if n < ntokens - 4 and \
                      tokens[n+4][0] == token.NAME and \
                      len(tokens[n+4][1]) >= 2 and \
                      tokens[n+4][1][0].lower() == "e" and \
                      tokens[n+4][1][1].isdigit():
                        # Get all digits after "e": the rest might be a
                        # unit specification
                        i = 2
                        t1 = tokens[n+4]
                        s = t1[1]
                        while i < len(s) and s[i].isdigit(): i = i+1
                        tokens[n+4] = (t1[0], s[0:i], t1[2],
                                       (t1[3][0], t1[2][1] + i), t1[4])
                        t = (token.NUMBER,
                             tokenize.untokenize(tokens[n:n+5]),
                             tokens[n][2], tokens[n+4][3],
                             tokens[n][4])
                        newtoks.append(t)
                        if len(s.rstrip()) > i:
                            t1 = (t1[0], s[i:], (t1[2][0], t1[2][1]+i),
                                  t1[3], t1[4])
                            tokens[n+4] = t1
                            n = n - 1
                        n = n + 5
                        continue
                    elif n < ntokens - 6 and \
                      tokens[n+4][0] == token.NAME and \
                      tokens[n+4][1].lower() == "e" and \
                      tokens[n+5][0] == token.OP and \
                      tokens[n+5][1] in ["+", "-"] and \
                      tokens[n+6][0] == token.NUMBER:
                        t = (token.NUMBER,
                             tokenize.untokenize(tokens[n:n+7]),
                             tokens[n][2], tokens[n+6][3],
                             tokens[n][4])
                        newtoks.append(t)
                        n = n + 7
                        continue
                    else:
                        t = (token.NUMBER, tokenize.untokenize(tokens[n:n+4]),
                             tokens[n][2], tokens[n+3][3], tokens[n][4])
                        newtoks.append(t)
                        n = n + 4
                        continue
            newtoks.append(tokens[n])
            n = n + 1
        tokens = newtoks
    # Now scan for lazy values
    global lazyvalues
    newtoks = []
    ntokens = len(tokens)
    n = 0
    offset = 0
    while n < ntokens:
        t = offset_token(tokens[n], offset)
        if t[0] == token.NAME and t[1] in lazyvalues:
            newtoks.append(t)
            newtoks.append((token.OP, "(", t[3], (t[3][0], t[3][1]+1), t[4]))
            newtoks.append((token.OP, ")", (t[3][0], t[3][1]+1),
                            (t[3][0], t[3][1]+2), t[4]))
            offset += 2
        else:
            newtoks.append(t)
        n = n + 1
    tokens = newtoks
    # Now proceed
    newtoks = []                        # Transformed tokens
    queue = []                          # Queue used to store partial units
    status = 0                          # General status
    substatus = 0                       # Substatus: before (0) or after (1) @
    offset = 0                          # Current offset of the tokens
    for tt in tokens:                   # Feed loop
        if False and tt[1] == "~":      # Debug me! @@@
            import pdb
            pdb.set_trace()
            continue
        tokens1 = deque([offset_token(tt, offset)])
        while tokens1:                  # Internal loop
            t = tokens1.popleft()
            codex, value, p1, p2, string = t
            if codex == token.OP and value == "@" and not queue:
                substatus = 1
                status = 1
            if codex == token.N_TOKENS:
                comment = value[1:].strip()
                if comment[0] in "'\"" and comment[-1] == comment[0]:
                    comment = comment.encode('latin-1').decode('unicode_escape')
                    codex = token.OP
                    value = "&"
                    l1, c1 = p1
                    t = codex, value, p1, (l1, c1+1), string
                    lc = len(comment)
                    tokens1.extend([t,
                                    (token.NAME, "Doc", (l1, c1+2), (l1, c1+5),
                                     string),
                                     (token.OP, "(", (l1, c1+5), (l1, c1+6), string),
                                     (token.STRING, comment, (l1, c1+6),
                                     (l1, c1+6+lc), string),
                                     (token.OP, ")", (l1, c1+6+lc), (l1, c1+7+lc),
                                      string)])
                    continue
            if status <= 0:                 # ...
                if codex == token.NUMBER and substatus == 0:
                    status = 1
                    queue.append(t)
                else:
                    newtoks.append(t)
            elif status == 1:               # ...12 or ... @
                if codex == token.OP and value == "[":
                    status = 2
                    queue.append(t)
                elif config["auto_brackets"] and codex == token.NAME and \
                    (units.isunit(value) or substatus == 1):
                    status = 3
                    queue.append(t)
                elif config["auto_brackets"] and value == "*" and \
                    substatus == 1:
                    status = 1
                    queue.append(t)
                elif substatus == 1 and value == "@":
                    value == "|"
                    l1, c1 = t[3]
                    s = t[-1]
                    offset += 8             # This is OK, tokens1 should be empty now!
                    newtoks.extend([change_token(t, "|"), 
                                    (token.NAME, u"System", (l1,c1+1), (l1,c1+7), s),
                                    (token.OP, u"(", (l1,c1+7), (l1,c1+8), s)])
                else:
                    newtoks.extend(queue)
                    queue = []
                    tokens1.appendleft(t)
                    if substatus == 1:
                        l1, c1 = t[3]
                        s = t[-1]
                        newtoks.append((token.OP, u")", (l1,c1+1), (l1,c1+2), s))
                        substatus = 0
                        offset += 1
                        tokens1 = offset_tokens(tokens1, 2)
                    status = 0
            elif status == 2:               # ...12[ or ... @[
                if codex == token.OP and value == "]":
                    status = 0
                    queue.append(t)
                    queue, delta = unit_create(substatus, queue, True)
                    newtoks.extend(queue)
                    if substatus == 1:
                        delta += 1
                        newtoks.append(offset_token(change_token(t, ")"), delta))
                        substatus = 0
                    offset += delta
                    tokens1 = offset_tokens(tokens1, delta)
                    queue = []
                elif substatus == 1 and codex == token.OP and \
                    (value == "," or value == "|"):
                    queue.append(change_token(t, "]"))
                    queue, delta = unit_create(substatus, queue, True)
                    newtoks.extend(queue)
                    newtoks.append(offset_token(change_token(t, ","), delta + 1))
                    queue = [offset_token(change_token(t, "["), delta + 2)]
                    offset += delta + 3
                    tokens1 = offset_tokens(tokens1, delta + 4)
                else:
                    queue.append(t)
            elif status == 3:               # ...12 m or ... @ m
                if codex == token.NAME and units.isunit(value):
                    queue.append(t)
                elif codex == token.OP and value == "/":
                    status = 4
                    queue.append(t)
                elif codex == token.OP and value == "^":
                    status = 5
                    queue.append(t)
                elif codex == token.OP and value == ".":
                    status = 8
                    queue.append(t)
                else:
                    queue, delta = unit_create(substatus, queue)
                    newtoks.extend(queue)
                    tokens1.appendleft(t)
                    offset += delta
                    tokens1 = offset_tokens(tokens1, delta+1)
                    if substatus == 1:
                        col = queue[-1][3][1]
                        tokens1.appendleft((token.OP, ")",
                                           (t[2][0], col),
                                           (t[2][0], col+1), t[4]))
                        substatus = 0
                        offset += 1
                    status = 0
                    queue = []
            elif status == 4 or status == 8: # ...12 m / or ...12 m.
                if codex == token.NAME:
                    # Mmh, found a name after a / in a possible unit specification.
                    # Is it really a possible unit or not?  Check...
                    if units.isunit(value):
                        # It is a unit, use it
                        status = 3
                        queue.append(t)
                        continue
                # We did not find a name after a / or the name was not a valid
                # unit.  Put everything back!
                status = 0
                t0 = queue[-1]
                queue = queue[0:-1]
                queue, delta = unit_create(substatus, queue)
                newtoks.extend(queue)
                if substatus == 1:
                    tokens1.appendleft(offset_token(t, 1))
                    tokens1.appendleft((token.OP, ")", (t[2][0], t[2][1]),
                                       (t[2][0], t[2][1]+1), t[4]))
                    substatus = 0
                else:
                    tokens1.appendleft(t)
                tokens1.appendleft(t0)
                offset += delta
                tokens1 = offset_tokens(tokens1, delta)
                queue = []
            elif status == 5:               # 12 m^
                if codex == token.NUMBER:
                    status = 6
                    queue.append(t)
                elif codex == token.OP and (value == "-" or value == "+"):
                    status = 7
                    queue.append(t)
                else:
                    status = 0
                    t0 = queue[-1]
                    queue = queue[0:-1]
                    queue, delta = unit_create(substatus, queue)
                    newtoks.extend(queue)
                    if substatus == 1:
                        tokens1.appendleft(offset_token(t, 1))
                        tokens1.appendleft((token.OP, ")", (t[2][0], t[2][1]),
                                            (t[2][0], t[2][1]+1), t[4]))
                        substatus = 0
                    else:
                        tokens1.appendleft(t)
                    tokens1.appendleft(t0)
                    offset += delta
                    tokens1 = offset_tokens(tokens1, delta)
                    queue = []
            elif status == 6:               # 12 m^2 or 12 m^-2
                if codex == token.NAME and units.isunit(value):
                    queue.append(t)
                    status = 3
                elif codex == token.OP and value == "/":
                    status = 4
                    queue.append(t)
                elif codex == token.OP and value == ".":
                    status = 8
                    queue.append(t)
                else:
                    status = 0
                    queue, delta = unit_create(substatus, queue)
                    newtoks.extend(queue)
                    if substatus == 1:
                        tokens1.appendleft(offset_token(t, 1))
                        tokens1.appendleft((token.OP, ")", (t[2][0], t[2][1]),
                                            (t[2][0], t[2][1]+1), t[4]))
                        substatus = 0
                    else:
                        tokens1.appendleft(t)
                    offset += delta
                    tokens1 = offset_tokens(tokens1, delta)
                    queue = []
                continue
            elif status == 7:               # 12 m^-
                if codex == token.NUMBER:
                    status = 6
                    queue.append(t)
                    continue
                else:
                    status = 0
                    t0 = queue[-1]
                    queue = queue[0:-1]
                    queue, delta = unit_create(substatus, queue)
                    newtoks.extend(queue)
                    if substatus == 1:
                        tokens1.appendleft(offset_token(t, 1))
                        tokens1.appendleft((token.OP, ")", (t[2][0], t[2][1]),
                                            (t[2][0], t[2][1]+1), t[4]))
                        substatus = 0
                    else:
                        tokens1.appendleft(t)
                    tokens1.appendleft(t0)
                    tokens1.appendleft(t)
                    tokens1.appendleft(t)
                    offset += delta
                    tokens1 = offset_tokens(tokens1, delta)
                    queue = []
            else:
                newtoks.append(t)
    if substatus == 0:
        result = newtoks
        # Fix for problem w/ token.ENDMARKER
        if result[-1][0] == token.ENDMARKER and len(result) >= 2:
            l1, c1 = result[-2][3]
            result = result[0:-1]
            result.append((token.ENDMARKER, "",  (l1, c1), (l1, c1+1), result[-1][-1]))
    else:
        result = newtoks
    if config["standard_exponent"]:
        result = [(codex, u"**", p1, p2, string) if codex == token.OP and value == "^"
                  else (codex, value, p1, p2, string) \
                  for codex, value, p1, p2, string in result]
    if engine:
        uresult = []
        offset = 0
        for t in result:
            t = offset_token(t, offset)
            if t[0] == token.NUMBER and \
              (t[1].find(".") >= 0 or t[1].find("e") >= 0 or \
               t[1].find("E") >= 0 or \
               t[1].find("/") >= 0 or t[1].find("(") >= 0):
                l1, c1 = t[2]
                l2, c2 = t[3]
                le = len(engine)
                uresult.extend([(token.NAME, engine, t[2], (l1, c1+le), t[4]),
                                (token.OP, u"(", (l1, c1+le), (l1, c1+le+1), t[4]),
                                (token.STRING, '"' + t[1] + '"', (l1, c1+le+1),
                                 (l2, c2+le+3), t[4]),
                                (token.OP, u")", (l2, c2+le+3), (l2, c2+le+4), t[4])])
                offset += le + 4
            else:
                uresult.append(t)
        result = uresult
    # @@@DEBUG
    # for t in result:
    #    tokenize.printtoken(*t)
    return result

input_unit_transformer = TokenInputTransformer.wrap(unit_transformer)

######################################################################
# Engines and related initialization functions

from importlib import import_module

def change_engine(ip, newengine):
    global engine, engine_module
    try:
        module = import_module("imks.units_" + newengine)
    except:
        print("Cannot load engine %s" % newengine)
        raise ModuleNotFoundError
    if engine_module: engine_module.unload(ip)
    try:
        module.load(ip)
        engine = "ufloat"
    except:
        print("Cannot load engine %s" % newengine)
        engine_module.load(ip)
        raise ModuleNotFoundError
    engine_module = module    

def imks_import(name, globals=None, locals=None, fromlist=None):
    import imp
    import sys

    print("Loading module " + name)
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
    def is_ascii(self, text):
        try:
            s = str(text)
        except UnicodeEncodeError:
            return False
        return True
    
    def get_prefixes(self, text):
        return filter(lambda x: x.startswith(text) and self.is_ascii(x),
                      units.prefixes.keys())

    def get_units(self, text):
        return filter(lambda x: x.startswith(text) and self.is_ascii(x),
                      units.units.keys())

    def get_systems(self, text):
        return filter(lambda x: x.startswith(text) and self.is_ascii(x),
                      units.systems.keys())

    def get_prefunits(self, text):
        us = units.units.keys()
        ps = filter(lambda x: (x.startswith(text) or text.startswith(x)) and
                    self.is_ascii(x), units.prefixes.keys())
        l = len(text)
        # Note that below we do not explicitely add us, since the null prefix
        # is a valid prefix and is already in the list ps.  We do instead add
        # the list of prefixes, as the null unit is not included in us.
        r = filter(lambda x: x.startswith(text) and self.is_ascii(x),
                   [p for p in ps if len(p) >= l] +
                   [p + u for u in us for p in ps if len(p) <= l])
        return r

    def get_quotes(self, text, cs):
        ds = [unidecode(c) for c in cs]
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
        from io import IOBase
        if not isinstance(sys.stderr, IOBase):
            return [x if x[0] != '"' and x[0] != "'" else x[1:] for x in r]
        else:
            return r

imks_completer = Imks_completer()

re_space_match = re.compile(r"[][ \t\n@()[+-/*^|&=<>,]+")

re_value_match = re.compile(r"(?:.*\=)?(\d+(?:\.\d*)?(?:[eE][-+]?\d*)?\s*)(?:\[)")
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

re_svalue_match = re.compile(r"(?:.*\=)?(\d+(?:\.\d*)?(?:[eE][-+]?\d*)?\s*)(?:\ )")
def imks_svalue_completer(self, event):
    m = re_svalue_match.split(event.text_until_cursor)
    n = m[-2]                           # number
    u = m[-1]                           # full unit
    if u.find("[") >= 0: raise TryNext  # unit specification with [...]
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
    return imks_completer.get_systems(v) + imks_completer.get_prefunits(v)

re_item_match = re.compile(r".*(\b(?!\d)\w\w*(\[[^\]]+\])*)\[((?P<s>['\"])(?!.*(?P=s)).*)$")
def imks_dict_completer(self, event):
    m = re_item_match.split(event.text_until_cursor)
    if len(m) < 3:
        if event.text_until_cursor[-1] == "[": return ['"']
        else: return []
    base, item = m[1], m[3]
    try:
        obj = _retrieve_obj(base, self)
    except:
        return []
    items = obj.keys()
    readline.set_completer_delims(" \t\n@()[]+-/*^|&=<>,")
    return imks_completer.get_quotes(item, items)

def imks_load_imks_ext(self, event):
    return ["constants", "currencies", "calendars", "geolocation", "jpl",
            "wiki"]

def imks_imks_completer(self, event):
    words = re.split(r"\s+", event.text_until_cursor)
    lword = words[-1]
    nwords = len(words)
    opts = "ha:e:u:s:k:t:c:m:M:p:o:d:"
    argopt = None
    for word in words[:-1]:
        if argopt:
            argopt = None
        if word[0] == "-" and len(word) == 2:
            i = opts.find(word[1])
            if i >= 0:
                if len(opts) > i+1 and opts[i+1] == ":":
                    argopt = word[1]
                    opts = opts[:i] + opts[i+2:]
                else:
                    argopt = None
                    opts = opts[:i] + opts[i+1:]
    if argopt == "c":
        return ["math", "mpmath", "fpmath", "numpy", "umath", "soerp", "mcerp"]
    elif argopt == "o":
        return ["0", "1", "2"]
    elif argopt == "d":
        return [c.calendar for c in calendars.calendars]
    elif argopt in ["p", "m", "M"]:
        return []
    elif argopt:
        return ["on", "off"]
    else:
        return ["on", "off"] + ["-" + o for o in opts if o != ":"]

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
                m = re.match(r".*(\b(?!\d)\w\w*\b)$", text[0:n])
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
    try:
        obj = _retrieve_obj(name, self)
    except:
        return []
    if not issubclass(obj, calendars.CalDate): return TryNext
    item = text[quote:]
    if nargs == 1:
        readline.set_completer_delims(" \t\n@()[]+-/*^|&=<>,")
        return imks_completer.get_quotes(item, ["today", "tomorrow",
                                                "yesterday", "now"])
    else:
        names = list(getattr(obj, list(obj.dateparts.keys())[nargs-1] + "names", []))
        if nargs == obj.holidayarg+1 and obj.holidays:
            names.extend(obj.holidays.keys())
        names = [name for name in names if name != ""]
        names.sort()
        readline.set_completer_delims(" \t\n@()[]+-/*^|&=<>,")
        return imks_completer.get_quotes(item, names)
    return []
    

def load_ipython_extension(ip):
    global config

    # make sure we have a ~/.imks directory
    import os, os.path
    dotpath = os.path.join(os.environ["HOME"], ".imks")
    if os.path.exists(dotpath):
        if not os.path.isdir(dotpath):
            raise IOError("~/.imks must be a directory")
    else:
        print("Making the directory ~/.imks")
        os.mkdir(dotpath)
    
    # set up simplified quantity input
    for s in (ip.input_splitter, ip.input_transformer_manager): 
        s.logical_line_transforms.insert(0, input_command_transformer()) 
        s.python_line_transforms.extend([input_unit_transformer()])

    # load symbols
    units.load_variables(ip)

    # math engine
    config["engine"] = "math"
    change_engine(ip, config["engine"])

    # input transformers
    config["intrans"] = {}

    # nice LaTeX formatter
    import mpmath
    latex_formatter = ip.display_formatter.formatters['text/latex']
    latex_formatter.for_type(float, lambda x: \
                             ("${%s}$" % str(x)).replace("e", r"} \times 10^{"))
    latex_formatter.for_type(mpmath.mpf, lambda x: \
                             ("${%s}$" % str(x)).replace("e", r"} \times 10^{"))
    
    # magic
    imks_magic.imks_doc()
    ip.register_magics(imks_magic)

    # activate true float division
    exec(ip.compile("from __future__ import division", "<input>", "single"),
         ip.user_ns)

    # save current ipython global variables
    config['initial_status'] = ip.user_ns.keys()
    
    # run command-line options
    if "InteractiveShellApp" in ip.config and \
      "exec_lines" in ip.config.InteractiveShellApp:
        for line in ip.config.InteractiveShellApp.exec_lines:
            ip.run_cell(line, store_history=False)
        # Remove already executed lines
        ip.config.InteractiveShellApp.exec_lines = []
        del ip.config.InteractiveShellApp["exec_lines"]
        if ip.parent:
            ip.parent.exec_lines = []

    # load Startup
    ip.run_line_magic("load_imks", "Startup")
    
    # setup completer
    r"(?:.*\=)?(\d+(?:\.\d*)?(?:[eE][-+]?\d*))(?:\[)"
    ip.set_hook("complete_command", imks_value_completer,
                re_key=r"(?:.*[-+=*/%^~()<>:;, ])?(\d+(?:\.\d*)?(?:[eE][-+]?\d*)?\s*)\[")
    ip.set_hook("complete_command", imks_svalue_completer,
                re_key=r"(?:.*[-+=*/%^~()<>:;, ])?(\d+(?:\.\d*)?(?:[eE][-+]?\d*)?\s*)\ ")
    ip.set_hook("complete_command", imks_at_completer,
                re_key=r"([^@]+)@")
    ip.set_hook("complete_command", imks_dict_completer,
                re_key=r".*(\b(?!\d)\w\w*)\[")
    ip.set_hook("complete_command", imks_date_completer,
                re_key=r"(.+)\([^'\"]*['n\"]")
    ip.set_hook("complete_command", imks_load_imks_ext,
                re_key=r"(%load_imks_ext\s+).*")
    ip.set_hook("complete_command", imks_imks_completer,
                re_key=r"^\s*(%imks\s+).*")

    if config["banner"]:
        print("Welcome to iMKS %s - © Marco Lombardi %s" % (__version__, __date__))
        print("Type %imks -h or ! for help.")

# from IPython.core.debugger import Pdb
# Pdb().set_trace()

