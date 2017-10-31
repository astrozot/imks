# -*- coding: utf-8 -*-

import re

# TODO: try to remove inflect dependency
try:
    import inflect
    inflect_engine = inflect.engine()
except ImportError:
    inflect_engine = None


__all__ = ["cardinal_to_number", "ordinal_to_number", "number_to_cardinal", "number_to_ordinal", "plural"]

small_numerals = {
    'zero': 0,
    'one': 1,
    'two': 2,
    'three': 3,
    'four': 4,
    'five': 5,
    'six': 6,
    'seven': 7,
    'eight': 8,
    'nine': 9,
    'ten': 10,
    'eleven': 11,
    'twelve': 12,
    'thirteen': 13,
    'fourteen': 14,
    'fifteen': 15,
    'sixteen': 16,
    'seventeen': 17,
    'eighteen': 18,
    'nineteen': 19,
    'twenty': 20,
    'thirty': 30,
    'forty': 40,
    'fifty': 50,
    'sixty': 60,
    'seventy': 70,
    'eighty': 80,
    'ninety': 90
}

magnitudes = {
    'thousand': 1000,
    'million': 1000000,
    'billion': 1000000000,
    'trillion': 1000000000000,
    'quadrillion': 1000000000000000,
    'quintillion': 1000000000000000000,
    'sextillion': 1000000000000000000000,
    'septillion': 1000000000000000000000000,
    'octillion': 1000000000000000000000000000,
    'nonillion': 1000000000000000000000000000000,
    'decillion': 1000000000000000000000000000000000,
}

small_ordinals = {
    'zeroth': 0,
    'first': 1,
    'second': 2,
    'third': 3,
    'fourth': 4,
    'fifth': 5,
    'sixth': 6,
    'seventh': 7,
    'eighth': 8,
    'ninth': 9,
    'tenth': 10,
    'eleventh': 11,
    'twelfth': 12,
    'thirteenth': 13,
    'fourteenth': 14,
    'fifteenth': 15,
    'sixteenth': 16,
    'seventeenth': 17,
    'eighteenth': 18,
    'nineteenth': 19,
    'twentieth': 20,
    'thirtieth': 30,
    'fortieth': 40,
    'fiftieth': 50,
    'sixtieth': 60,
    'seventieth': 70,
    'eightieth': 80,
    'ninetieth': 90
}


def cardinal_to_number(s):
    """Convert a cardinal string into an integer.

    For example:
        cardinal_to_number("twenty") -> 20
    """
    a = re.split(r"[-\s,]+", s)
    n = 0
    g = 0
    for w in a:
        if w == "and":
            continue
        x = small_numerals.get(w, None)
        if x is not None:
            g += x
        elif w == "hundred" and g != 0:
            g *= 100
        else:
            x = magnitudes.get(w, None)
            if x is not None:
                n += g * x
                g = 0
            else:
                raise ValueError("Unknown numeral: " + w)
    return n + g


def ordinal_to_number(s, fraction=False):
    """Parse an ordinal string as a number.

    If fraction is set, fraction denominators are also recongnized.

    For example:
        ordinal_to_number("second") -> 2
        ordinal_to_number("quarters", fraction=True) -> 4
        ordinal_to_number("10th") -> 10
        ordinal_to_number("tenths", fraction=True) -> 10
    """
    # Try first to match a short ordinal
    m = re.match(r"\s*(\d+)-?(st|nd|rd|th)\s*", s)
    if m:
        return int(m.group(1))
    # Failed: assume it is a long ordinal
    a = re.split(r"[-\s,]+", s)
    if fraction and len(a) == 1:
        if a[0] in ('half', 'halves'):
            return 2
        if a[0] in ('quarter', 'quarters'):
            return 4
        if a[0] in ('second', 'seconds'):
            raise ValueError("Unknown ordinal: " + a[0])
    n = 0
    g = 0
    for w in a:
        if w == "and":
            continue
        if fraction and w[-1] == "s":
            w = w[:-1]
        x = small_ordinals.get(w, None)
        if x is None:
            x = small_numerals.get(w, None)
        if x is not None:
            g += x
        elif (w == "hundred" or w == "hundredth") and g != 0:
            g *= 100
        else:
            x = magnitudes.get(w[:-2] if w[-2:] == "th" else w, None)
            if x is not None:
                n += g * x
                g = 0
            else:
                raise ValueError("Unknown ordinal: " + w)
    return n + g


def number_to_cardinal(n):
    """Return the cardinal string corresponding to a natural number.

    For example:
        number_to_cardinal(2) -> "two"
        number_to_cardinal(4) -> "four"
    """
    return inflect_engine.number_to_words(n)


def number_to_ordinal(n, short=False, numerator=False):
    """Return the ordinal string corresponding to a natural number.

    If short is set, the ordinal string is in compact form:
        number_to_ordinal(2) -> "second"
        number_to_ordinal(4, short=True) -> "4th"

    If numerator is set, the ordinal string is suitable to be used as the
    denominator of a fraction. In this case, the parameter should be set to
    the numerator of the fraction.
    """
    if short:
        return str(n) + 'tsnrhtdd'[n % 5 * (n % 100 ^ 15 > 4 > n % 10)::4]
    elif numerator:
        if n == 2:
            s = "half"
        else:
            s = inflect_engine.ordinal(inflect_engine.number_to_words(n))
        return inflect_engine.plural(s, count=numerator)
    else:
        return inflect_engine.ordinal(inflect_engine.number_to_words(n))


def plural(s):
    """Return the plural of a name."""
    return inflect_engine.plural(s)
