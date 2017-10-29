from __future__ import print_function

import re
import sys
import six

dict_key_re = re.compile(r'''(?x)
(   # preceding string of '.'-delimited identifiers
    (?!\d)\w+
    (?:\.(?!\d)\w+)*
)
\[   # open bracket
\s*  # and optional whitespace
([uUbB]?  # string prefix (r not handled)
    (?:   # unclosed string
        '(?:[^']|(?<!\\)\\')*
    |
        "(?:[^"]|(?<!\\)\\")*
    )
)?
$
''')

assert dict_key_re.search('d[').groups() == ('d', None)
assert dict_key_re.search('d["').groups() == ('d', '"')
assert dict_key_re.search('d["a').groups() == ('d', '"a')
assert dict_key_re.search('d["\\"').groups() == ('d', '"\\"')
assert dict_key_re.search('c.d["a').groups() == ('c.d', '"a')
assert dict_key_re.search('+ c.d["a').groups() == ('c.d', '"a')
assert dict_key_re.search('["a') is None
assert dict_key_re.search('d["a"') is None
assert dict_key_re.search('d["a" +') is None
assert dict_key_re.search('d["\\\\"') is None


def match_keys(keys, prefix):
    if not prefix:
        return [repr(k) for k in keys if isinstance(k, six.string_types)]
    quote_match = re.search('["\']', prefix)
    quote = quote_match.group()
    try:
        prefix_str = eval(prefix + quote, {})
    except Exception:
        return None

    token_prefix = re.search('\w*$', prefix).group()

    matched = []
    for key in keys:
        try:
            if not key.startswith(prefix_str):
                continue
        except (AttributeError, TypeError):
            # Python 3+ TypeError on b'a'.startswith('a')
            continue

        # reformat remainder of key to begin with prefix
        rem = key[len(prefix_str):]
        # force repr with '
        rem_repr = repr(rem + '"')
        if rem_repr.startswith('u') and prefix[0] not in 'uU':
            try:
                rem_repr = repr(rem.encode('ascii') + '"')
            except UnicodeDecodeError:
                continue

        rem_repr = rem_repr[1 + rem_repr.index("'"):-2]
        if quote == '"':
            rem_repr = rem_repr.replace('"', '\\"')

        # then reinsert prefix from start of token
        matched.append('%s%s%s' % (token_prefix, rem_repr, quote))
    return matched


TEST_KEYS = [5, object(), 'abc', u'abd', "a'b", 'a"b', 'a"\'b', 'a\nb', u'a\u05d0', b'abc', 'a b']
TEST_PREFIXES = [None, "'", '"', "u'", 'u"', "'a", "'b"] # "'a '
# Doing all pairs is too hard to document, especially with py2-3 variations on u'' and b''
# test logically rather than exhaustively.
# use if sys.version_info >= (3, 0)

def get_keys(obj):
    if not callable(getattr(obj, '__getitem__', None)):
        return []
    if hasattr(obj, 'keys'):
        try:
            return list(obj.keys())
        except Exception:
            return []
    return getattr(getattr(obj, 'dtype', None), 'names', [])


def dict_key_completer(self):
    match = dict_key_re.search(self.text_until_cursor)
    if match is None:
        return []
    expr, prefix = match.groups()
    try:
        obj = eval(expr, self.namespace)
    except Exception:
        try:
            obj = eval(expr, self.global_namespace)
        except Exception:
            return []
    keys = get_keys(obj)
    if not keys:
        return keys
    return ['%s]' % k for k in match_keys(keys, prefix)]
