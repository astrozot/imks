# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
from IPython.core.inputtransformer import (StatelessInputTransformer,
                                           TokenInputTransformer)
from ._version import __version__, __date__
from . import units
from .transformers import command_transformer, unit_transformer
from .completers import *


def load_ipython_extension(ip):
    from .magics import ImksMagic, change_engine
    from .config import config

    # make sure we have a ~/.imks directory
    import os.path
    dotpath = os.path.join(os.environ["HOME"], ".imks")
    if os.path.exists(dotpath):
        if not os.path.isdir(dotpath):
            raise IOError("~/.imks must be a directory")
    else:
        print("Making the directory ~/.imks")
        os.mkdir(dotpath)
    
    # set up simplified quantity input
    input_command_transformer = StatelessInputTransformer.wrap(command_transformer)
    input_unit_transformer = TokenInputTransformer.wrap(unit_transformer)
    for s in (ip.input_splitter, ip.input_transformer_manager): 
        s.logical_line_transforms.insert(0, input_command_transformer()) 
        s.python_line_transforms.extend([input_unit_transformer()])

    # load symbols
    units.load_variables(ip.user_ns)

    # math engine
    config["engine"] = "math"
    change_engine(ip.user_ns, config["engine"])

    # input transformers
    config["intrans"] = {}

    # nice LaTeX formatter
    latex_formatter = ip.display_formatter.formatters['text/latex']
    latex_formatter.for_type(float, lambda x:
                             ("${%s}$" % str(x)).replace("e", r"} \times 10^{"))
    try:
        # noinspection PyUnresolvedReferences
        import mpmath
        latex_formatter.for_type(mpmath.mpf, lambda x:
                                 ("${%s}$" % str(x)).replace("e", r"} \times 10^{"))
    except ImportError:
        pass
    
    # magic
    ImksMagic.imks_doc()
    ip.register_magics(ImksMagic)

    # activate true float division
    exec(ip.compile("from __future__ import division", "<input>", "single"),
         ip.user_ns)

    # save current ipython global variables
    config['initial_status'] = ip.user_ns.keys()
    
    # run command-line options
    if "InteractiveShellApp" in ip.config and \
            "exec_lines" in ip.config.InteractiveShellApp:
        for line in ip.config.InteractiveShellApp.exec_lines:
            ip.run_cell(line, store_history=False)
        # Remove already executed lines
        ip.config.InteractiveShellApp.exec_lines = []
        del ip.config.InteractiveShellApp["exec_lines"]
        if ip.parent:
            ip.parent.exec_lines = []

    # load Startup
    ip.run_line_magic("load_imks", "Startup")

    # avoid jedi in case of a recent IPython version
    try:
        ip.magic('config IPCompleter.use_jedi=False')
    except (NameError, AttributeError):
        pass
    
    # setup completer
    r"(?:.*\=)?(\d+(?:\.\d*)?(?:[eE][-+]?\d*))(?:\[)"
    ip.set_hook("complete_command", imks_value_completer,
                re_key=r"(?:.*[-+=*/%^~()<>:;, ])?(\d+(?:\.\d*)?(?:[eE][-+]?\d*)?\s*)\[")
    ip.set_hook("complete_command", imks_svalue_completer,
                re_key=r"(?:.*[-+=*/%^~()<>:;, ])?(\d+(?:\.\d*)?(?:[eE][-+]?\d*)?\s*)\ ")
    ip.set_hook("complete_command", imks_at_completer,
                re_key=r"([^@]+)@")
    ip.set_hook("complete_command", imks_dict_completer,
                re_key=r".*(\b(?!\d)\w\w*)\[")
    ip.set_hook("complete_command", imks_date_completer,
                re_key=r"(.+)\([^'\"]*['n\"]")
    ip.set_hook("complete_command", imks_load_imks_ext,
                re_key=r"(%load_imks_ext\s+).*")
    ip.set_hook("complete_command", imks_imks_completer,
                re_key=r"^\s*(%imks\s+).*")

    if config["banner"]:
        print("Welcome to iMKS %s - © Marco Lombardi %s" % (__version__, __date__))
        print("Type %imks -h or ! for help.")

# from IPython.core.debugger import Pdb
# Pdb().set_trace()
