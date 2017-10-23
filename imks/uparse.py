# -*- coding: utf-8 -*-

"""Parses a number with error in various formats.

   The formats and the algorithm are taken from the uncertainties package.
"""

import re

POSITIVE_DECIMAL = r"((\d+)(\.\d*)?|nan|inf)"
NUMBER_WITH_UNCERT_RE_STR = r"""
    ([+-])?              # Sign
    %s                   # Main number
    (?:\(%s\))?          # Optional uncertainty
    ([eE][-+]?\d+)?      # Optional exponent
    """ % (POSITIVE_DECIMAL, POSITIVE_DECIMAL)
NUMBER_WITH_UNCERT_RE_MATCH = re.compile(
    u"%s$" % NUMBER_WITH_UNCERT_RE_STR, re.VERBOSE).match
NUMBER_WITH_UNCERT_GLOBAL_EXP_RE_MATCH = re.compile(r"""
    \(
    (?P<simple_num_with_uncert>.*)
    \)
    (?P<exp_value>[eE][-+]?\d+)
    $""", re.VERBOSE).match


def uparse(representation):
    if representation.find("+/-") >= 0 or representation.find(u"±") or \
      representation.find("("):
        match = NUMBER_WITH_UNCERT_GLOBAL_EXP_RE_MATCH(representation)
        if match:
            exp_value_str = match.group("exp_value")
            representation = match.group("simple_num_with_uncert")
        else:
            exp_value_str = ""
        match = re.match(r"(.*)(?:\+/-|±)(.*)", representation)
        if match:
            nom_value, uncert = match.groups()
            nom_value = nom_value + exp_value_str
            uncert = uncert + exp_value_str
        else:
            match = NUMBER_WITH_UNCERT_RE_MATCH(representation)
            sign = main = uncert = uncert_dec = main_dec = None
            if match:
                sign, main, main_int, main_dec, \
                    uncert, uncert_int, uncert_dec, exp_value_str = \
                    match.groups()
            nom_value = (sign or "") + main + (exp_value_str or "")
            if uncert is None:
                uncert = ""
            elif uncert_dec is None and main_dec is not None:
                lm = len(main_dec) - 1
                lu = len(uncert)
                if lm >= lu:
                    uncert = "0." + "0" * (lm - lu) + uncert
                else:
                    uncert = uncert[0:lu-lm] + "." + uncert[lu-lm:]
                uncert = uncert + (exp_value_str or "")
    else:
        uncert = ""
        nom_value = representation
    return nom_value, uncert
