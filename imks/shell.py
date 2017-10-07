import tokenize
from io import StringIO, open

from .config import *
from .transformers import command_transformer, unit_transformer, transform, magic_transformer

class Shell(object):
    def __init__(self):
        self.user_ns = {}
        self.user_global_ns = {"run_magic": lambda s: self.run_magic(s)}

    def ev(self, expr):
        """Evaluate python expression expr in user namespace.

        Returns the result of evaluation
        """
        return eval(expr, self.user_global_ns, self.user_ns)

    def ex(self, cmd):
        """Execute a normal python statement in user namespace."""
        exec(cmd, self.user_global_ns, self.user_ns)
    
    def run_magic(self, line):
        s = line.split(" ")
        return self.run_line_magic(s[0], " ".join(s[1:]))

    def run_line_magic(self, magic_name, line):
        """Execute the given line magic.

        Parameters
        ----------
        magic_name : str
          Name of the desired magic function, without '%' prefix.

        line : str
          The rest of the input line as a single string.
        """
        fn = self.magics[magic_name]
        if fn is None:
            raise ValueError('Magic `%s` not found' % magic_name)
        else:
            # Note: no variable expansion here!
            result = fn(line)
            return result

    def find_user_code(self, target, *args, **kwargs):
        with open(target, "rt", encoding="utf-8") as f:
            return f.read()

    def run_cell(self, cell):
        # N.B.: formally almost identical to transformers.transform, but w/
        # the addition of magic_transformer
        cell = command_transformer(cell.rstrip())
        tokens = tokenize.generate_tokens(StringIO(cell).readline)
        newtokens = unit_transformer(magic_transformer(list(tokens)))
        newcell = tokenize.untokenize(newtokens)
        try:
            code = compile(newcell, '<stdin>', 'eval')
        except SyntaxError:
            code = compile(newcell, '<stdin>', 'exec')
        return self.ev(code)
    
import sys, os, shlex, getopt

magics = {}

def magics_class(cls):
    """Class decorator for all subclasses of the main Magics class.

    Any class that subclasses Magics *must* also apply this decorator, to
    ensure that all the methods that have been decorated as line/cell magics
    get correctly registered in the class instance.  This is necessary because
    when method decorators run, the class does not exist yet, so they
    temporarily store their information into a module global.  Application of
    this class decorator copies that global data to the class instance and
    clears the global.

    Obviously, this mechanism is not thread-safe, which means that the
    *creation* of subclasses of Magic should only be done in a single-thread
    context.  Instantiation of the classes has no restrictions.  Given that
    these classes are typically created at IPython startup time and before user
    application code becomes active, in practice this should not pose any
    problems.
    """
    global magics
    cls.registered = True
    cls.magics = magics
    magics = {}
    return cls


def line_magic(func):
    magics[func.__name__] = func.__name__
    return func


class Magics(object):
    # Dict holding all command-line options for each magic.
    options_table = None
    # Dict for the mapping of magic names to methods, set by class decorator
    magics = None
    # Flag to check that the class decorator was properly applied
    registered = False
    # Instance of IPython shell
    shell = None


    def __init__(self, shell=None, **kwargs):
        if not(self.__class__.registered):
            raise ValueError('Magics subclass without registration - '
                             'did you forget to apply @magics_class?')
        self.options_table = {}
        # The method decorators are run when the instance doesn't exist yet, so
        # they can only record the names of the methods they are supposed to
        # grab.  Only now, that the instance exists, can we create the proper
        # mapping to bound methods.  So we read the info off the original names
        # table and replace each method name by the actual bound method.
        # But we mustn't clobber the *class* mapping, in case of multiple instances.
        if shell is None:
            self.shell = Shell()
        else:
            self.shell = shell
        class_magics = self.magics
        self.magics = {}
        for magic_name, meth_name in class_magics.items():
            if isinstance(meth_name, str):
                # it's a method name, grab it
                self.magics[magic_name] = getattr(self, meth_name)
            else:
                # it's the real thing
                self.magics[magic_name] = meth_name
        self.shell.magics = self.magics

    def arg_err(self,func):
        """Print docstring if incorrect arguments were passed"""
        print('Error in arguments:')
        print(oinspect.getdoc(func))

    def parse_options(self, arg_str, opt_str, *long_opts, **kw):
        """Parse options passed to an argument string.

        The interface is similar to that of :func:`getopt.getopt`, but it
        returns a :class:`~IPython.utils.struct.Struct` with the options as keys
        and the stripped argument string still as a string.

        arg_str is quoted as a true sys.argv vector by using shlex.split.
        This allows us to easily expand variables, glob files, quote
        arguments, etc.

        Parameters
        ----------

        arg_str : str
          The arguments to parse.

        opt_str : str
          The options specification.

        mode : str, default 'string'
          If given as 'list', the argument string is returned as a list (split
          on whitespace) instead of a string.

        list_all : bool, default False
          Put all option values in lists. Normally only options
          appearing more than once are put in a list.

        posix : bool, default True
          Whether to split the input line in POSIX mode or not, as per the
          conventions outlined in the :mod:`shlex` module from the standard
          library.
        """

        # inject default options at the beginning of the input line
        caller = sys._getframe(1).f_code.co_name
        arg_str = '%s %s' % (self.options_table.get(caller,''),arg_str)

        mode = kw.get('mode','string')
        if mode not in ['string','list']:
            raise ValueError('incorrect mode given: %s' % mode)
        # Get options
        list_all = kw.get('list_all',0)
        posix = kw.get('posix', os.name == 'posix')
        strict = kw.get('strict', True)

        # Check if we have more than one argument to warrant extra processing:
        odict = {}  # Dictionary with options
        args = arg_str.split()
        if len(args) >= 1:
            # If the list of inputs only has 0 or 1 thing in it, there's no
            # need to look for options
            argv = shlex.split(arg_str, posix, strict)
            # Do regular option processing
            try:
                opts,args = getopt.getopt(argv, opt_str, long_opts)
            except getopt.GetoptError as e:
                raise UsageError('%s ( allowed: "%s" %s)' % (e.msg,opt_str,
                                        " ".join(long_opts)))
            for o,a in opts:
                if o.startswith('--'):
                    o = o[2:]
                else:
                    o = o[1:]
                try:
                    odict[o].append(a)
                except AttributeError:
                    odict[o] = [odict[o],a]
                except KeyError:
                    if list_all:
                        odict[o] = [a]
                    else:
                        odict[o] = a

        # Prepare opts,args for return
        if mode == 'string':
            args = ' '.join(args)

        return odict,args


