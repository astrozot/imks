from ._version import __version__
try:
    __IPYTHON__
    from .imks import *
except NameError:
    pass

