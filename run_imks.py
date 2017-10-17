import sys
from imks import imks_standalone

if __name__ == "__main__" or sys.platform == 'ios':
    imks = imks_standalone.load_imks()
    try:
        imks.shell.interact(banner="", exitmsg="")
    except TypeError:
        # This line is for Python 2.7
        imks.shell.interact(banner="")
