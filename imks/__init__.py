from ._version import __version__
try:
    # noinspection PyUnresolvedReferences
    # noinspection PyStatementEffect
    __IPYTHON__
    from .imks import *
except NameError:
    pass

