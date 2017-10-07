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
  evaluated only when <name> is used or displayed.

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

* Value, System, and Doc are defined in units.py, and for these objects the
  standard operators are redefined to include tracking of physical units.

* If necessary, one can directly use the Value, System, and Doc objects to
  make more complicated expressions.

* The know prefixes, units, and unit systems are stored in the dictionaries
  prefixes, units, and systems, freely accessible from the user space.
"""

from __future__ import absolute_import, division, print_function
from traitlets import List, Int, Any, Unicode, CBool, Bool, Instance
from collections import OrderedDict as ODict
import re
from unidecode import unidecode
from imks._version import __version__, __date__
from imks import units
from imks import currencies
from imks import calendars
from imks.transformers import command_transformer, unit_transformer, transform

try:
    from objproxies import CallbackProxy, LazyProxy
except:
    from peak.util.proxies import CallbackProxy, LazyProxy

from imks.config import *

######################################################################
# Code

magic = None

def load_imks(shell=None):
    from imks.magics import imks_magic, change_engine
    global config, magic

    # make sure we have a ~/.imks directory
    import os, os.path
    dotpath = os.path.join(os.environ["HOME"], ".imks")
    if os.path.exists(dotpath):
        if not os.path.isdir(dotpath):
            raise IOError("~/.imks must be a directory")
    else:
        print("Making the directory ~/.imks")
        os.mkdir(dotpath)

    # magic
    imks_magic.imks_doc()
    magic = imks_magic(shell=shell)
        
    # load symbols
    units.load_variables(magic.shell.locals)

    # math engine
    config["engine"] = "math"
    change_engine(magic.shell.locals, config["engine"])

    # input transformers
    config["intrans"] = {}

    # activate true float division
    magic.shell.ex("from __future__ import division")

    # save current ipython global variables
    config['initial_status'] = magic.shell.locals.keys()

    # copy the local namespace to the global one
    # magic.shell.user_global_ns.update(magic.shell.user_ns)
    
    # run command-line options
    #if "InteractiveShellApp" in ip.config and \
    #  "exec_lines" in ip.config.InteractiveShellApp:
    #    for line in ip.config.InteractiveShellApp.exec_lines:
    #        ip.run_cell(line, store_history=False)
    #    # Remove already executed lines
    #    ip.config.InteractiveShellApp.exec_lines = []
    #    del ip.config.InteractiveShellApp["exec_lines"]
    #    if ip.parent:
    #        ip.parent.exec_lines = []

    # load Startup
    magic.load_imks("Startup")
    
    if config["banner"]:
        print("Welcome to iMKS %s - © Marco Lombardi %s" % (__version__, __date__))
        print("Type %imks -h or ! for help.")

    return magic


if __name__ == "__main__":
    imks = load_imks()
    try:
        imks.shell.interact(banner="", exitmsg="")
    except TypeError:
        # This line is for Python 2.7
        imks.shell.interact(banner="")
        
    
