import sys
from imks import imks_standalone

try:
    import readline
except ImportError:
    readline = False

imks = imks_standalone.load_imks()

if readline:
    readline.set_completer(imks_standalone.imks_standalone_completer)
    readline.parse_and_bind('tab:complete')
    
try:
    imks.shell.interact(banner="", exitmsg="")
except TypeError:
    # This line is for Python 2.7
    imks.shell.interact(banner="")
