import lxml.etree
import urllib
import mwparserfromhell
import re

title = "Aquamole Pot"
title = "Earth"
title = "Venus"
title = "Copper"
title = "Italy"
title = "Rieti"
title = "Napoleon"
# title = "Sandro Pertini"
# title = "Lake Garda"
# title = "Rieti"

ip = None
unit_transformer = None
command_transformer = None


try:
    unicode
except NameError:
    unicode = str


def unit_convert(u):
    uchars = u'\u2070\u00B9\u00B2\u00B3\u2074\u2075\u2076\u2077\u2078\u2079\u207B'
    e = False
    r = []
    for c in unicode(u):
        i = uchars.find(c)
        if i >= 0:
            if not e:
                r.append("^")
                e = True
            if i != 10:
                r.append(str(i))
            else:
                r.append("-")
        else:
            if e:
                r.append(" ")
                e = False
            if c == u"\xb7":
                c = " "
            r.append(c)
    return "".join(r)


# Perform templates interpretation for numeric values (val and convert)
def template_strip(self, normalize, collapse):
    name = self.name.strip()
    if name == "val":
        value = self.get(1)
        if self.has("e"):
            value = unicode(value) + u"e" + unicode(self.get("e").value)
        unit = u"rad"
        if self.has("u"):
            unit = self.get("u").value
        if self.has("ul"):
            unit = self.get("ul").value
        elif self.has("up"):
            unit = unit + u" / " + self.get("up").value
        elif self.has("ul"):
            unit = unit + u" / " + self.get("ul").value
        return unicode(value) + "[" + unit_convert(unit) + "]"
    elif name == "convert":
        return unicode(self.get(1)) + "[" + unit_convert(self.get(2)) + "]"
    elif name == "frac" or name == "sfrac":
        nargs = len(self.params)
        if nargs == 1:
            return "1/" + unicode(self.get(1))
        elif nargs == 2:
            return unicode(self.get(1)) + "/" + unicode(self.get(2))
        elif nargs == 3:
            return unicode(self.get(1)) + "+" + unicode(self.get(2)) + \
                "/" + unicode(self.get(3))
        else:
            return None
    elif name == "M":                   # Italian template for measurements
        value = unicode(self.get(1)).replace(",", ".").replace(" ", "")
        if self.has("e"):
            value = value + "e" + unicode(self.get("e").value)
        unit = unicode(self.get(2)) + unicode(self.get(3))
        return value + "[" + unit_convert(unit) + "]"
    elif name in ["nowrap", "j", "nobr", "nobreak"]:
        return unicode(self.get(1))
    elif name == "plainlist":
        values = []
        cvalue = []
        for node in self.get(1).value.nodes:
            if node == u"*":
                value = ("".join(cvalue)).strip()
                if value:
                    values.append(value)
                cvalue = []
            else:
                tmp = node.__strip__(normalize, collapse)
                if tmp:
                    cvalue.append(unicode(tmp).strip("\n"))
        if len(values) > 1:
            return "<(>" + "<,>".join(values) + "<)>"
        elif len(values) == 1:
            return values[0]
        else:
            return None
    else:
        return None


mwparserfromhell.nodes.template.Template.__strip__ = template_strip


def tag_strip(self, normalize, collapse):
    from mwparserfromhell.definitions import is_visible
    global old_tag_strip
    if self.tag == "br":
        return "\n"
    else:
        if self.contents and is_visible(self.tag):
            return self.contents.strip_code(normalize, collapse)
        return None
mwparserfromhell.nodes.tag.Tag.__strip__ = tag_strip


def parse_disambiguation(contents, active=0, opts=[]):
    if not contents or not contents.nodes: return active
    for node in contents.nodes:
        if isinstance(node, mwparserfromhell.nodes.tag.Tag) and \
                node.tag == "li":
            active = 5
        elif isinstance(node, mwparserfromhell.nodes.tag.Tag):
            active = parse_disambiguation(node.contents, active, opts)
        elif isinstance(node, mwparserfromhell.nodes.wikilink.Wikilink) \
                and active > 0:
            opts.append(unicode(node.title))
            active = 0
        elif active > 0:
            active -= 1
    return active

def parse_infobox(infobox, d=None):
    import StringIO, tokenize
    global ip, unit_transformer
    if d is None: d = OrderedDict()
    for p in infobox.params:
        n = p.name.strip()
        if n == 'isbn':
            import pdb
            pdb.set_trace()
        try:
            n = str(n)
        except UnicodeEncodeError:
            pass
        try:
            int(n)
            continue
        except ValueError:
            pass
        v = p.value
        if hasattr(v, "filter_templates"):
            for i in v.filter_templates(matches="(Infobox|Starbox|Chembox)"):
                d = parse_infobox(i, d)
            for i in v.filter_templates():   # @@@ DEBUG
                s = str(i.name)
                if not (s in ["val", "plainlist "]):
                    print("{{%s}}" % i.name)
        w = []
        for o in v.strip_code().replace(u'\xa0', u' ').split("\n"):
            os = o.strip()
            if len(os) > 3 and os[:3] == "<(>" and os[-3:] == "<)>":
                w.extend([ow.strip() for ow in os[3:-3].split("<,>")])
            else:
                w.append(o.strip())
        w = filter(lambda word: word, w)
        if len(w) > 1:
            for nn, ww in enumerate(w):
                try:
                    ww = str(ww)
                except UnicodeEncodeError:
                    pass
                try:
                    tokens = tokenize.generate_tokens(
                        StringIO.StringIO(command_transformer(ww).strip()).readline)
                    ww = ip.ev(tokenize.untokenize(
                        unit_transformer([t for t in tokens])))
                except:
                    pass
                w[nn] = ww
            d[n] = w
        elif len(w) == 1:
            w = w[0]
            try:
                w = str(w)
            except UnicodeEncodeError:
                pass
            try:
                tokens = tokenize.generate_tokens(
                    StringIO.StringIO(command_transformer(w).strip()).readline)
                w = ip.ev(tokenize.untokenize(unit_transformer([t for t in tokens])))
            except:
                pass
            d[n] = w
    return d


def find_infoboxes(title, lang="en"):
    print(title)
    params = {"format": "xml", "action": "query", "prop": "revisions",
              "rvprop": "timestamp|user|comment|content" }
    params["titles"] = u"API|%s" % urllib.quote(title.encode("utf8"))
    qs = "&".join("%s=%s" % (k, v)  for k, v in params.items())
    url = u"http://%s.wikipedia.org/w/api.php?%s" % (lang, qs)
    tree = lxml.etree.parse(urllib.urlopen(url))
    revs = tree.xpath('//rev')

    if len(revs) == 1:
        raise ValueError("Page not found")
    p=mwparserfromhell.parse(revs[-1].text)
    if p.nodes[0] == "#" and re.match("(REDIRECT|RINVIA)", unicode(p.nodes[1])):
        title = unicode(p.nodes[2].title).replace(" ", "_")
        return find_infoboxes(title, lang)
    infoboxes = p.filter_templates(matches="(Infobox|Starbox|Chembox)")
    if len(infoboxes) == 0:
        infoboxes = []
        for t in p.filter_templates(matches="(?!(Navbox|Sidebar|Cite))"):
            if len(t.params) > 8 and \
                not re.match(r"(Navbox|Sidebar|Cite)", unicode(t.name), re.IGNORECASE):
                infoboxes = [t]
                break
        if not infoboxes:
            if p.filter_templates(matches="(Disambig|Homonym)"):
                opts = []
                parse_disambiguation(p, opts=opts)
                if len(opts) > 2:
                    print("Disambiguation: %s" % "   ".join(opts))
                    return []
            print("Infobox not found")
            return []
    result = []
    for infobox in infoboxes:
        if not infobox.params:
            result.extend(find_infoboxes(u"Template:%s" % infobox.name, lang))
        else:
            result.append(infobox)
    return infoboxes


def wiki(title, lang="en"):
    from collections import OrderedDict
    infoboxes = find_infoboxes(title, lang)
    if infoboxes:
        d = OrderedDict()
        for infobox in infoboxes:
            d = parse_infobox(infobox, d)
        return d
    else: return None
