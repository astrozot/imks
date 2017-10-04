# -*- coding: utf-8 -*-

from collections import OrderedDict as ODict

class link:
    def __init__(self, what=None):
        self.link = what

    def __repr__(self):
        return '-> ' + self.link


class xdict(ODict):
    def __init__(self, v=None, **kw):
        if v:
            if isinstance(v, (dict, ODict, xdict)):
                super(xdict, self).__init__(v)
            elif isinstance(v, (list, tuple)):
                super(xdict, self).__init__()
                for a,b in v:
                    self[a] = b
            else: super(xdict, self).__init__(**kw)
        else: super(xdict, self).__init__(**kw)
    
    def __getitem__(self, y):
        item = super(xdict, self).__getitem__(y)
        if isinstance(item, link):
            item = super(xdict, self).__getitem__(item.link)
        return item

    def __setitem__(self, i, y):
        if isinstance(i, (list, tuple)):
            for n,ii in enumerate(i):
                if ii in self: del self[ii]
                if n == 0: super(xdict, self).__setitem__(ii, y)
                else: super(xdict, self).__setitem__(ii, link(i[0]))
        else:
            if i in self:
                super(xdict, self).__setitem__(self.getorig(i), y)
            else:
                super(xdict, self).__setitem__(i, y)

    def __delitem__(self, y):
        item = super(xdict, self).__getitem__(y)
        if isinstance(item, link): y = item.link
        black = []
        for k, v in super(xdict, self).iteritems():
            if (isinstance(v, link) and v.link == y) or k == y:
                black.append(k)
        for k in black:
            super(xdict, self).__delitem__(k)

    def __len__(self):
        l = 0
        for k, v in super(xdict, self).iteritems():
            if not isinstance(v, link): l = l + 1
        return l

    def get(self, k, d=None):
        if k in self: return self[k]
        else: return d

    def iteritems(self, aliases=True):
        if aliases is True:
            for k, v in super(xdict, self).iteritems():
                yield (k, self[k])
        elif aliases is False:
            for k, v in super(xdict, self).iteritems():
                if not isinstance(v, link): yield (k, v)
        else:
            d1 = {}
            d2 = {}
            for k, v in super(xdict, self).iteritems():
                if not isinstance(v, link):
                    d1[k] = v
                    d2[k] = [k]
            for k, v in super(xdict, self).iteritems():
                if isinstance(v, link): d2[v.link].append(k)
            for k, v in d1.iteritems():
                yield (d2[k], d1[k])

    def iterkeys(self, aliases=True):
        for k, v in self.iteritems(aliases):
            yield k

    def itervalues(self, aliases=True):
        for k, v in super(xdict, self).iteritems(aliases):
            yield v

    def items(self):
        r = []
        for k, v in self.iteritems():
            r.append((k, v))
        return r

    def keys(self, aliases=True):
        if aliases is True: return super(xdict, self).keys()
        elif aliases is False:
            return [k for k,v in super(xdict, self).iteritems()
                    if not isinstance(v, link)]
        else:
            r = []
            for k, v in self.iteritems():
                r.append(k)
            return r
    
    def values(self, aliases=True):
        if aliases is True: return super(xdict, self).values()
        else:
            return [v for k, v in super(xdict, self).iteritems()
                    if not isinstance(v, link)]
     
    def pop(self, k, d=None):
        if k in self:
            r = self[k]
            del self[k]
            return r
        else:
            if d is None: raise KeyError(k)
            else: return d

    def popitem(self):
        if len(self) == 0: raise KeyError('popitem(): dictionary is empty')
        for k, v in self.iteritems():
            break
        del self[k[0]]
        return (k, v)
    
    def  __repr__(self):
        return '{' + ', '.join([str(k) + ': ' + str(v)
                                for k, v in self.iteritems(None)]) + '}'

    def getorig(self, k):
        item = super(xdict, self).__getitem__(k)
        if isinstance(item, link): return item.link
        else: return k

    def getaliases(self, k):
        item = self.getorig(k)
        return [i for i,v in super(xdict, self).iteritems()
                if isinstance(v, link) and v.link == item]

    def addalias(self, k, l):
        alias = self.getorig(l)
        if alias != k:
            super(xdict, self).__setitem__(k, link(alias))
        else: raise KeyError("circular link in addalias")

    def delalias(self, k, force=False):
        alias = self.getorig(k)
        if alias != k: super(xdict, self).__delitem__(k)
        elif force:
            found = False
            for i, v in super(xdict, self).iteritems():
                if isinstance(v, link) and v.link == k:
                    found = True
                    where = i
                    break
            if found:
                super(xdict, self).__setitem__(where, self[k])
                super(xdict, self).__delitem__(k)
                for i, v in super(xdict, self).iteritems():
                    if isinstance(v, link) and v.link == k:
                        super(xdict, self).__setitem__(i, link(where))
            else: del self[k]
        else: raise KeyError('key is not an alias')


