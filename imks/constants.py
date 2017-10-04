from . import units

class Constants(dict):
    "A constant dictionary taken from http://physics.nist.gov/cuu/Constants"
    def __getattr__(self, attr):
        try:
            return self[attr]
        except KeyError:
            raise AttributeError("Constant not found")

    def __getitem__(self, key):
        x = dict.__getitem__(self, key)
        if type(x) is units.Value: return x
        engine = get_ipython().user_ns["ufloat"]
        try:
            if x[1] != "(exact)": v = "%s +/- %s" % x[0:2]
            else: v = str(x[0])
            v = units.Value(engine(v), x[2])
            doc = "%s\n\nDefined in the NIST database as: " % key
            if x[1] != "(exact)": doc += "(%s +/- %s) [%s]" % (x[0], x[1], x[2])
            else: doc += "%s [%s] (exact)" % (x[0], x[2])
            v.__doc__ = doc
        except ValueError as s:
            v = units.Value(float("NaN"))
            v.__doc__ = "Error parsing NIST data: " + str(s)
        dict.__setitem__(self, key, v)
        return v

constants = Constants({})

def getconstants(offline=False, grace=30, timeout=3, engine=False):
    import os, os.path, time, pickle
    from urllib import request, error
    global constants
    force = False
    url = 'http://physics.nist.gov/cuu/Constants/Table/allascii.txt'
    try:
        path = os.path.join(os.getenv('HOME'), '.imks3', 'constants.dat')
        update = os.path.getmtime(path)
        delta = (time.time() - update) / 86400.0
    except OSError:
        force = True
        delta = 0
    if offline: force = False
    elif delta > grace: force = True
    if force:
        nistconst = {}
        if not engine: engine = float
        try:
            with request.urlopen(url, timeout=timeout) as response:
                header = True
                for line in response:
                    line = line.decode('utf-8')
                    if header:
                        if line[0:40] == '-'*40:
                            header = False
                    else:
                        try:
                            descr = line[0:60].strip()
                            value = ''.join(line[60:85].replace('...', '').split(' '))
                            uncer = ''.join(line[85:110].split(' '))
                            unit  = line[110:].strip()
                            nistconst[descr] = (value, uncer, unit)
                        except ValueError:
                            pass
            if not nistconst: return None
            constants.update([(k, (engine(v1), v2, v3))
                              for k, (v1, v2, v3) in nistconst.items()])
            f = open(path, "wb")
            pickle.dump(nistconst, f)
            f.close()
            return nistconst
        except error.URLError:
            pass
    try:
        f = open(path, "rb")
        nistconst = pickle.load(f)
        f.close()
        constants.update([(k, (engine(v1), v2, v3))
                          for k, (v1, v2, v3) in nistconst.items()])
        return nistconst
    except IOError:
        return None


def loadconstants(grace=30, engine=None):
    # Use cache, if available, to update all units online
    nistconst = getconstants(offline=False, grace=grace, engine=engine)
    # Finally, update all units online using a new thread: REMOVED
    # import threading
    # thread = threading.Thread(target=updateconstants, 
    #                           kwargs={"grace": grace, "engine": engine})
    # thread.setDaemon(True)              # so we can always quit w/o waiting
    # thread.start()

