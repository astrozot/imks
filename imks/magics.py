# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
import re
from collections import OrderedDict as ODict

try:
    __IPYTHON__
    from IPython.core.magic import Magics, magics_class, line_magic
    from IPython.core.page import page
except NameError:
    from .shell import Magics, magics_class, line_magic
    page = print

from . import units, currencies, calendars
from .config import *
from .transformers import command_transformer, unit_transformer, transform
from ._version import __version__, __date__

try:
    from objproxies import CallbackProxy, LazyProxy
except ImportError:
    from peak.util.proxies import CallbackProxy, LazyProxy


def change_engine(namespace, newengine):
    from importlib import import_module
    global internals
    try:
        my_module = import_module("imks.units_" + newengine)
    except:
        print("Cannot load engine %s" % newengine)
        raise ImportError
    if internals["engine_module"]:
        internals["engine_module"].unload(namespace)
    try:
        my_module.load(namespace)
        internals["engine"] = "ufloat"
    except:
        print("Cannot load engine %s" % newengine)
        internals["engine_module"].load(namespace)
        raise ImportError
    internals["engine_module"] = my_module

    
@magics_class
class ImksMagic(Magics):
    re_doc = re.compile(r'([^#]+)\s*#\s*"(.*)(?<!\\)"\s*')

    def split_command_doc(self, line):
        m = re.match(self.re_doc, line)
        if m:
            doc = m.group(2).strip(' ')
            doc = doc.encode('latin-1').decode('unicode_escape')
            line = m.group(1)
        else:
            doc = ""
        return line, doc

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
          -v <0|1|2>   print units in standard form (0), using verbose strings but
                       short exponents (1), or using verbose strings and spelled
                       exponents [%s]
          -$ <0|1|2>   do not complete currencies (0), complete them only if capital
                       letters are present (1), or complete them anyway (2) [%s]
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
        ImksMagic.__dict__["imks"].__doc__ = ImksMagic.imks_doc.__doc__ % \
            ("on" if config["auto_brackets"] else "off",
             "on" if config["standard_exponent"] else "off",
             "on" if config["unit_tolerant"] else "off",
             "on" if config["sort_units"] else "off",
             "on" if config["prefix_only"] else "off",
             "2" if config["unit_verbose"] is True else
             "0" if config["unit_verbose"] is False else "1",
             "2" if config["complete_currencies"] is True else
             "0" if config["complete_currencies"] is False else "1",
             config["engine"], config["show_errors"],
             config.get("default_calendar", "none"),
             config["digits"], config["min_fixed"], config["max_fixed"],
             "on" if config["enabled"] else "off")

    @line_magic
    def imks(self, args):
        def imks_print(*p_args, **p_kwargs):
            if units.units or len(units.prefixes) > 1:
                print(*p_args, **p_kwargs)
                
        global config
        opts, name = self.parse_options(args, 'ha:e:u:s:k:t:$:c:m:M:p:o:d:v:')
        if name in ["on", "1", "yes"]:
            config["enabled"] = True
            imks_print("iMKS enabled")
        elif name in ["off", "0", "no"]:
            config["enabled"] = False
            imks_print("iMKS disabled")
        elif len(args) == 0:
            config["enabled"] = not config["enabled"]
            imks_print("iMKS %s" % ("enabled" if config["enabled"]
                                    else "disabled"))
        if "h" in opts:
            from . import doc
            page(doc.__doc__)
            ImksMagic.imks_doc()
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
                print("Incorrect argument.  Use yes/on/1 or no/off/0")
        if "e" in opts:
            if opts["e"] in ["on", "1", "yes"]:
                config["standard_exponent"] = True
                imks_print("Standard exponent (^) enabled")
            elif opts["e"] in ["off", "0", "no"]:
                config["standard_exponent"] = False
                imks_print("Standard exponent (^) disabled")
            else:
                imks_print("Incorrect argument.  Use yes/on/1 or no/off/0")
        if "s" in opts:
            if opts["s"] in ["on", "1", "yes"]:
                config["sort_units"] = units.sortunits = True
                imks_print("Compound units are sorted")
            elif opts["s"] in ["off", "0", "no"]:
                config["sort_units"] = units.sortunits = False
                imks_print("Compound units are not sorted")
            else:
                print("Incorrect argument.  Use yes/on/1 or no/off/0")
        if "k" in opts:
            if opts["k"] in ["on", "1", "yes"]:
                config["prefix_only"] = units.prefixonly = True
                imks_print("Prefix without unit accepted")
            elif opts["k"] in ["off", "0", "no"]:
                config["prefix_only"] = units.prefixonly = False
                imks_print("Prefix without unit not accepted")
            else:
                print("Incorrect argument.  Use yes/on/1 or no/off/0")
        if "t" in opts:
            if opts["t"] in ["on", "1", "yes"]:
                config["unit_tolerant"] = units.tolerant = True
                imks_print("Zero-value tolerance enabled")
            elif opts["t"] in ["off", "0", "no"]:
                config["unit_tolerant"] = units.tolerant = False
                imks_print("Zero-value tolerance disabled")
            else:
                print("Incorrect argument.  Use yes/on/1 or no/off/0")
        if "v" in opts:
            if opts["v"] in ["on", "2", "yes"]:
                config["unit_verbose"] = units.verbose = True
                imks_print("Verbose output of units fully enabled")
            elif opts["v"] in ["off", "0", "no"]:
                config["unit_verbose"] = units.verbose = False
                imks_print("Verbose output of units disabled")
            elif opts["v"] in ["partial", "1"]:
                config["unit_verbose"] = units.verbose = "partial"
                imks_print("Verbose output of units partially enabled")
            else:
                print("Incorrect argument.  Use yes/on/2, partial/1, or no/off/0")
        if "$" in opts:
            if opts["$"] in ["on", "2", "yes"]:
                config["complete_currencies"] = True
                imks_print("Currency completion enabled")
            elif opts["$"] in ["off", "0", "no"]:
                config["complete_currencies"] = False
                imks_print("Currency completion disabled")
            elif opts["$"] in ["maybe", "1", "perhaps"]:
                config["complete_currencies"] = "maybe"
                imks_print("Currency completion partially enabled")
            else:
                print("Incorrect argument.  Use yes/on/2, maybe/perhaps/1, or no/off/0")
        if "c" in opts:
            if opts["c"] in ["math", "mpmath", "fpmath", "numpy",
                             "umath", "soerp", "mcerp"]:
                try:
                    change_engine(self.shell.user_ns, opts["c"])
                    imks_print("iMKS math engine: %s.  Consider doing a %%reset." %
                               opts["c"])
                except ImportError:
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
            imks_print("Fixed range:", units_mpmath.min_fixed, ":",
                       units_mpmath.max_fixed)
        if "d" in opts:
            calnames = [c.calendar for c in calendars.calendars]
            if opts["d"] in calnames:
                config["default_calendar"] = opts["d"]
            else:
                print("Unkown calendar %s" % opts["d"])
            imks_print("Default calendar set to %s" % opts["d"])
        self.imks_doc()

    @line_magic
    def load_imks(self, arg):
        """Load one ore more imks modules.

        The modules are searched first in the current directory, then in the ~/.imks
        directory, and finally in the /script directory under the package location. The
        latter location contains the standard modules distributed with imks.
        """
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
          wiki          search through Wikipedia infoboxes
          wolfram       use Wolfram Alpha to query quantities
        """
        import os, os.path
        global internals
        ip = self.shell
        oldkeys = set(ip.user_ns.keys())
        oldunits = set(units.units.keys())
        exts = arg.split()
        silent = False
        if len(exts) == 0:
            from textwrap import wrap
            print("\n  ".join(wrap("Extensions loaded: %s." %
                  (u", ".join(sorted(internals["extensions"]))))))
            return
        for ext in exts:
            if ext == "-s":
                silent = True
            else:
                internals["extensions"].add(ext)
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
                    constants.loadconstants(engine=eval(internals["engine"],
                                                        self.shell.user_ns))
                    self.shell.user_ns["const"] = constants.constants
                elif ext == "jpl":
                    from . import jpl
                    planets, moons = jpl.loadJPLconstants()
                    self.shell.user_ns["planets"] = planets
                    self.shell.user_ns["moons"] = moons
                    self.shell.user_ns["minorplanet"] = lambda name: jpl.load_minor(name)
                elif ext == "currencies":
                    if "openexchangerates_id" in ip.user_ns:
                        app_id = self.shell.user_ns["openexchangerates_id"]
                    else:
                        app_id = ""
                    currencies.currencies(app_id)
                elif ext == "wiki" or ext == "wikipedia":
                    from . import wiki
                    wiki.ip = self.shell
                    wiki.unit_transformer = unit_transformer
                    wiki.command_transformer = command_transformer
                    self.shell.user_ns["wiki"] = wiki.wiki
                elif ext == "wolfram":
                    from . import wolfram
                    wolfram.namespace = ip.user_ns
                    if "wolframalpha_id" in ip.user_ns:
                        wolfram.app_id = ip.user_ns["wolframalpha_id"]
                    self.shell.user_ns["wolfram"] = wolfram.wolfram
                else:
                    internals["extensions"].discard(ext)
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

    @staticmethod
    def checkvalidname(arg):
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
          %newbasecurrency, %newunit, %newprefix
        """
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
          %newbaseunit, %newunit, %newprefix
        """
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
          %delprefix, %newunit, %delunit.
        """
        command, doc = self.split_command_doc(arg)
        tmp = command.split("=")
        names, value = tmp[:-1], tmp[-1]
        walue = self.shell.ev(transform(value))
        for name in names:
            self.checkvalidname(name)
            units.newprefix(name.strip(), walue, doc=doc, source=value.strip())
        return

    @line_magic
    def delprefix(self, arg):
        """Delete a prefix previously defined using the %newprefix magic.

        Usage:
          %delprefix name
        """
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

        A unit can be deleted using the %delunit magic.
        """
        command, doc = self.split_command_doc(arg)
        tmp = command.split("=")
        names, value = tmp[:-1], tmp[-1]
        evalue = self.shell.ev(transform(value))
        for name in names:
            self.checkvalidname(name)
            units.newunit(name.strip(), evalue, doc=doc, source=value.strip())
        return

    @line_magic
    def delunit(self, arg):
        """Delete a unit previously defined using the %newunit magic.

        Usage:
          %delunit name
        """
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
        
        A unit system can be deleted using the %delsystem magic.
        """
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
             %delsystem name
        """
        units.delsystem(arg.strip())
        return

    @line_magic
    def defaultsystem(self, arg):
        """Set the default unit system for value representations.
        
        Usage:
          %defaultsystem system

        where system is a previously define unit system or a list of units
        separated by | as in %newsystem.  Do not use any argument to unset the
        default unit system.
        """
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
        variable.
        """
        command, doc = self.split_command_doc(arg)
        tmp = command.split("=")
        names, value = tmp[:-1], tmp[-1]
        evalue = self.shell.ev(transform(value))
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
          %lazy [options] var=[aliases=]=expr  [# "Documentation string"]

        This magic defines the variable var to be the result of expression.  In
        contrast to standard variables, however, expr is not computed immediately:
        rather, it is evaluated only when var is used or displayed.

        Options:
          -1   Evaluate the entire expression only once, the first time the prefix is
               used
        """
        command, doc = self.split_command_doc(arg)
        command = command.replace('"', '\\"').replace("'", "\\'")
        opts, command = self.parse_options(command, "1")
        if "1" in opts:
            proxy = LazyProxy
        else:
            proxy = CallbackProxy
        tmp = command.split("=")
        names, source = tmp[:-1], tmp[-1]
        value = self.shell.ev(transform("lambda : " + source)) & \
            units.Doc(doc, source)
        for name in names:
            self.shell.user_ns[name.strip()] = proxy(value)

    @line_magic
    def lazyprefix(self, arg):
        """Define a prefix lazily in terms of an expression.

        Usage:
          %lazyprefix [options] var=[aliases=]=expr  [# "Documentation string"]

        Similar to %lazy, but used to define a lazy prefix (see also %lazyunit).

        Options:
          -1   Evaluate the entire expression only once, the first time the prefix is
               used
        """
        command, doc = self.split_command_doc(arg)
        opts, command = self.parse_options(command, "1")
        if "1" in opts:
            proxy = LazyProxy
        else:
            proxy = CallbackProxy
        tmp = command.split("=")
        names, source = tmp[:-1], tmp[-1]
        value = self.shell.ev(transform("lambda : " + source))
        for name in names:
            self.checkvalidname(name)
            units.newprefix(name.strip(), proxy(value), doc=doc,
                            source=source.strip())

    @line_magic
    def lazyunit(self, arg):
        """Define a unit lazily in terms of an expression.

        Usage:
          %lazyunit [options] var=[aliases=]=expr  [# "Documentation string"]

        Similar to %lazy, but used to define a lazy unit (see also %lazyprefix).

        Options:
          -1   Evaluate the entire expression only once, the first time the unit is
               used
        """
        command, doc = self.split_command_doc(arg)
        opts, command = self.parse_options(command, "1")
        if "1" in opts:
            proxy = LazyProxy
        else:
            proxy = CallbackProxy
        tmp = command.split("=")
        names, source = tmp[:-1], tmp[-1]
        value = self.shell.ev(transform("lambda : " + source))
        for name in names:
            self.checkvalidname(name)
            units.newunit(name.strip(), proxy(value), doc=doc, source=source.strip())

    @line_magic
    def newtransformer(self, arg):
        """Define a new input transformer.

           Usage:
             %newtransformer name="regex":transformer

           where name is the name of the new input transformer (only used as a key for
           %deltransformer), regexp is a regular expression using the named groups, and
           transformer is a function used to perform the input transformation.
        """
        command, doc = self.split_command_doc(arg)
        i = command.find("=")
        if i < 0:
            raise SyntaxError("equal sign not found")
        name, value = command[0:i], command[i+1:]
        quotes = re.split(r'(?<!\\)\"', value)
        regex = quotes[1]
        trans = quotes[2]
        if trans[0] != ':':
            raise SyntaxError("column sign not found")
        cregex = re.compile(regex)
        self.checkvalidname(name)
        config["intrans"][name] = (cregex, trans[1:].strip()) & \
            units.Doc(doc, regex + " : " + trans[1:])
        return

    @line_magic
    def deltransformer(self, arg=""):
        """Delete an input transformer previously defined using %newtransformer.

           Usage:
             %deltransformer name
        """
        del config["intrans"][arg.strip()]
        return

    @line_magic
    def newformat(self, arg):
        """Define a new output format.

           Usage:
             %newformat name=transformer

           where name is the name of the new output transformer (only used as a key for
           %deltformat) and transformer is a function used to generate the output.
        """
        command, doc = self.split_command_doc(arg)
        i = command.find("=")
        if i < 0:
            raise SyntaxError("equal sign not found")
        name, value = command[0:i], command[i+1:]
        self.checkvalidname(name)
        units.formats[name] = eval(value, self.shell.user_ns) & units.Doc(doc, value)
        return

    @line_magic
    def delformat(self, arg=""):
        """Delete a format previously defined using %newformat.

           Usage:
             %delformat name
        """
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
          -U   Search among verbose units
          -c   Search among currencies
          -p   Search among prefixes
          -P   Search among verbose prefixes
          -s   Search among unit systems
          -t   Search among input transformers
          -f   Search among output formats
          -x   Extended search: include variables
          -i   For wildcard searches, ignore the case
        """
        global config
        opts, name = self.parse_options(args, "ayuUpPstfxci")
        if name == "":
            self.shell.run_line_magic("imks", "-h")
            return
        u0 = dict([(k, w) for k, w in units.units.items()
                   if k in units.baseunits])
        u1 = dict([(k, w) for k, w in units.units.items()
                   if k not in units.baseunits and k not in currencies.basecurrency
                   and k not in currencies.currencydict])
        u2 = dict([(k, units.units[w]) for k, w in units.verbose_units.items()])
        c0 = dict([(k, w) for k, w in units.units.items()
                   if k in currencies.basecurrency])
        c1 = dict([(k, w) for k, w in units.units.items()
                   if k not in currencies.basecurrency
                   and k in currencies.currencydict])
        p2 = dict([(k, units.prefixes[w]) for k, w in units.verbose_prefixes.items()])
        namespaces = []
        if 's' in opts:
            namespaces.append(("Unit systems", units.systems))
        if 'u' in opts:
            namespaces.extend([("Base units", u0),
                               ("Units", u1)])
        if 'U' in opts:
            namespaces.extend([("Verbose units", u2)])
        if 'c' in opts:
            namespaces.extend([("Base currencies", c0),
                               ("Currencies", c1)])
        if 'p' in opts:
            namespaces.append(("Prefixes", units.prefixes))
        if 'P' in opts:
            namespaces.extend([("Verbose prefixes", p2)])
        if 't' in opts:
            namespaces.append(("Input Transformers", config["intrans"]))
        if 'f' in opts:
            namespaces.append(("Output Formats", units.formats))
        if not namespaces:
            namespaces = [("Unit systems", units.systems),
                          ("Base units", u0),
                          ("Base currencies", c0),
                          ("Units", u1),
                          ("Verbose units", u2),
                          ("Currencies", c1),
                          ("Prefixes", units.prefixes),
                          ("Verbose prefixes", p2),
                          ("Input Transformers", config["intrans"]),
                          ("Output Formats", units.formats)]
        if 'x' in opts:
            namespaces.append(("Variables", self.shell.user_ns))
        if 'a' in opts:
            name = name.upper()
            shown = False
            for n, d in namespaces:
                f = [k for k, v in d.items()
                     if str(getattr(v, "__doc__", "")).upper().find(name) >= 0]
                if f:
                    if not shown:
                        print(name)
                    print("%s: %s" % (n, ", ".join(f)))
                    shown = True
            if not shown:
                print("Nothing found")
            return
        if 'y' in opts:
            res = units.isunit(name)
            if res:
                print("%s parsed as prefix(%s) + unit(%s)" % (name, res[0], res[1]))
            else:
                res = units.isunit(name, verbose=True)
                if res:
                    print("%s parsed as prefix(%s) + unit(%s)" % (name, res[0], res[1]))
                else:
                    print("%s is not a valid unit with prefix")
            return
        if '*' in name:
            psearch = self.shell.inspector.psearch
            d = dict(namespaces)
            try:
                psearch(name, d, d.keys(), ignore_case='i' in opts)
            except:
                self.shell.showtraceback()

        else:
            goodones = [n for n, ns in enumerate(namespaces)
                        if name in ns[1]]
            if goodones:
                if len(goodones) > 1:
                    spaces = "  "
                else:
                    spaces = ""
                res = []
                for goodone in goodones:
                    namespace = namespaces[goodone]
                    obj = namespace[1][name]
                    if len(goodones) > 1:
                        fields = [(namespace[0].upper(), "")]
                    else:
                        fields = []
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
                page("\n\n".join(res))
            else:
                res = units.isunit(name)
                if res:
                    print("%s parsed as prefix(%s) + unit(%s)" % (name, res[0], res[1]))
                else:
                    res = units.isunit(name, verbose=True)
                    if res:
                        print("%s parsed as prefix(%s) + unit(%s)" % (name, res[0], res[1]))
                    else:
                        print("Object `%s` not found" % name)
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
        opts, us = self.parse_options(args, "uU:vV:l:")
        level = int(opts.get("l", 1))
        if us[0] == '[' and us[-1] == ']':
            r = units.Value(1, us.strip("[] "))
        else:
            r = self.shell.ev(transform(us))
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
            for u in r.find_compatible(where, level=level):
                found.append(str(u))
            if not found:
                print("No compatible unit")
            else:
                print("Compatible units: %s" % ", ".join(found))
        if "u" not in opts:
            found = []
            if "V" in opts:
                where = ODict([(k.strip(), self.shell.user_ns[k.strip()])
                               for k in opts["V"].split(",")])
            else:
                where = self.shell.user_ns
            where = ODict([(k, v) for k, v in where.items()
                           if isinstance(v, units.Value)])
            for u in r.find_compatible(where, level=level):
                uu = str(u).strip("[] ")
                found.append(uu)
            if not found:
                print("No compatible value")
            else:
                print("Compatible values: %s" % ", ".join(found))

    @line_magic
    def pickle(self, args):
        """Pickle all current variables into a file.

        Usage:
          %pickle [-p protocol] filename
        """
        global config, internals
        import pickle 

        opts, us = self.parse_options(args, ":p")
        protocol = int(opts.get("p", 2))
        us = us.split()
        if len(us) != 1:
            print("Usage: %pickle [-p protocol] filename")
            return
        f = open(us[0], "wb")
        # Unload the engine, to remove engine-related variables
        if internals["engine_module"]:
            internals["engine_module"].unload(self.shell.user_ns)
            internals["engine_module"] = None
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
        change_engine(self.shell.user_ns, config["engine"])
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
        for k, v in d.items():
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

        This does a full reset: the engine, however, is left unchanged.
        """
        global config
        import gc
        # this code is from IPython
        ip = self.shell
        ip.reset(new_session=False)
        gc.collect()
        # load new symbols
        units.reset()
        units.load_variables(ip.user_ns)
        # math engine: this is not reset!
        change_engine(ip.user_ns, config["engine"])
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
