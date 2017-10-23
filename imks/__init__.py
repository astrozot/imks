from ._version import __version__
try:
    # noinspection PyStatementEffect
    __IPYTHON__
    from .imks import *
except NameError:
    pass

