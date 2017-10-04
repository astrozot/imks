from IPython.utils.traitlets import List, Int, Any, Unicode, CBool, Bool, Instance
from IPython.core.inputtransformer import (CoroutineInputTransformer, 
                                           StatelessInputTransformer,
                                           TokenInputTransformer,
                                           _strip_prompts)
from IPython.core import inputsplitter as isp
from IPython.core import inputtransformer as ipt
import re

@StatelessInputTransformer.wrap
def test_transformer_0(line):
    print "@", line
    return line

@CoroutineInputTransformer.wrap
def test_transformer_1():
    line = ''
    while True:
        line = (yield line)
        print "*", line

test_transformer_1.look_in_string = True

@TokenInputTransformer.wrap
def test_transformer_2(tokens):
    print "$", tokens
    return tokens


def load_ipython_extension(ip):
    # set up simplified quantity input
    ip.user_ns['mks'] = True

    shell = ip
    for s in (shell.input_splitter, shell.input_transformer_manager): 
        #s.physical_line_transforms.extend([test_transformer_1()]) 
        #s.logical_line_transforms.insert(0, magic_transformer()) 
        s.logical_line_transforms.insert(0, test_transformer_0()) 
        s.python_line_transforms.extend([test_transformer_1()]) 
        s.python_line_transforms.extend([test_transformer_2()]) 

    # active true float division
    exec ip.compile('from __future__ import division', '<input>', 'single') \
        in ip.user_ns
    print 'Test extension activated.'

def unload_ipython_extension(ip):
    ip.prefilter_manager.unregister_transformer(testTransformer)
