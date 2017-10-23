import inspect

def getargspec(obj):
    """Get the names and default values of a function's arguments.

    A tuple of four things is returned: (args, varargs, varkw, defaults).
    'args' is a list of the argument names (it may contain nested lists).
    'varargs' and 'varkw' are the names of the * and ** arguments or None.
    'defaults' is an n-tuple of the default values of the last n arguments.

    Modified version of inspect.getargspec from the Python Standard
    Library."""

    if inspect.isfunction(obj):
        func_obj = obj
    elif inspect.ismethod(obj):
        func_obj = obj.im_func
    elif hasattr(obj, '__call__'):
        func_obj = obj.__call__
    else:
        raise TypeError('arg is not a Python function')
    args, varargs, varkw = inspect.getargs(func_obj.func_code)
    return args, varargs, varkw, func_obj.func_defaults


def unit_wrapper(name, func, powers):
    argspect = getargspec(func)
    args, varargs, varkw, defaults = argspec
    s = ["def %s%s:" % (name, inspect.formatargspect(*argspec))]
    newargs = []
    for n,p in enumerate(powers):
        arg = args[n]
        if p is None:
            newargs.append(arg)
            s.append("  if isinstance(%s, units.Value): %s.check_pure()" % (arg, arg))
        elif isinstance(p, (int, long, float)):
            newargs.append("_" + arg)
            s.append("  if isinstance(%s, units.Value):")
        
    


def getdef(self,obj,oname=''):
    """Return the call signature for any callable object.
    
    If any exception is generated, None is returned instead and the
    exception is suppressed."""
    
    try:
        hdef = oname + inspect.formatargspec(*getargspec(obj))
        return hdef
    except:
        return None

