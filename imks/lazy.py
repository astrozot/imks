#  Copyright (c) 2009-2010, Cloud Matrix Pty. Ltd.
#  All rights reserved; available under the terms of the BSD License.
"""

  esky.util:  misc utility functions for esky

"""

from __future__ import with_statement
from __future__ import absolute_import

import sys
import errno

#  Since esky apps are required to call the esky.run_startup_hooks() method on
#  every invocation, we want as little overhead as possible when importing
#  the main module.  We therefore use a simple lazy-loading scheme for many
#  of our imports, built from the functions below.

def lazy_import(func):
    """Decorator for declaring a lazy import.

    This decorator turns a function into an object that will act as a lazy
    importer.  Whenever the object's attributes are accessed, the function
    is called and its return value used in place of the object.  So you
    can declare lazy imports like this:

        @lazy_import
        def socket():
            import socket
            return socket

    The name "socket" will then be bound to a transparent object proxy which
    will import the socket module upon first use.
 
    The syntax here is slightly more verbose than other lazy import recipes,
    but it's designed not to hide the actual "import" statements from tools
    like py2exe or grep.
    """
    try:
        f = sys._getframe(1)
    except Exception:
        namespace = None
    else:
        namespace = f.f_locals
    return _LazyImport(func.__name__,func,namespace)


class _LazyImport(object):
    """Class representing a lazy import."""

    def __init__(self,name,loader,namespace=None):
        self._esky_lazy_target = _LazyImport
        self._esky_lazy_name = name
        self._esky_lazy_loader = loader
        self._esky_lazy_namespace = namespace

    def _esky_lazy_load(self):
        if self._esky_lazy_target is _LazyImport:
            self._esky_lazy_target = self._esky_lazy_loader()
            ns = self._esky_lazy_namespace
            if ns is not None:
                try: 
                    if ns[self._esky_lazy_name] is self:
                        ns[self._esky_lazy_name] = self._esky_lazy_target
                except KeyError:
                    pass

    def __getattribute__(self,attr):
        try:
            return object.__getattribute__(self,attr)
        except AttributeError:
            if self._esky_lazy_target is _LazyImport:
                self._esky_lazy_load()
            return object.__getattribute__(self._esky_lazy_target,attr)

    def __nonzero__(self):
        if self._esky_lazy_target is _LazyImport:
            self._esky_lazy_load()
        return bool(self._esky_lazy_target)


@lazy_import
def os():
    import os
    return os

@lazy_import
def shutil():
    import shutil
    return shutil

@lazy_import
def time():
    import time
    return time

@lazy_import
def re():
    import re
    return re

@lazy_import
def zipfile():
    import zipfile
    return zipfile

@lazy_import
def itertools():
    import itertools
    return itertools

@lazy_import
def StringIO():
    from io import StringIO
    return StringIO

@lazy_import
def distutils():
    import distutils
    import distutils.log   # need to prompt cxfreeze about this dep
    import distutils.util
    return distutils

# lazy - Decorators and utilities for lazy evaluation in Python
# Alberto Bertogli (albertito@blitiri.com.ar)

class _LazyWrapper:
	"""Lazy wrapper class for the decorator defined below.
	It's closely related so don't use it.

	We don't use a new-style class, otherwise we would have to implement
	stub methods for __getattribute__, __hash__ and lots of others that
	are inherited from object by default. This works too and is simple.
	I'll deal with them when they become mandatory.
	"""
	def __init__(self, f, args, kwargs):
		self._override = True
		self._isset = False
		self._value = None
		self._func = f
		self._args = args
		self._kwargs = kwargs
		self._override = False

	def _checkset(self):
		if not self._isset:
			self._override = True
			self._value = self._func(*self._args, **self._kwargs)
			self._isset = True
			self._checkset = lambda: True
			self._override = False

	def __getattr__(self, name):
		if self.__dict__['_override']:
			return self.__dict__[name]
		self._checkset()
		return self._value.__getattribute__(name)

	def __setattr__(self, name, val):
		if name == '_override' or self._override:
			self.__dict__[name] = val
			return
		self._checkset()
		setattr(self._value, name, val)
		return

def lazy(f):
	"Lazy evaluation decorator"
	def newf(*args, **kwargs):
		return _LazyWrapper(f, args, kwargs)

	return newf
