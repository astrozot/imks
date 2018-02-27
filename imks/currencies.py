# -*- coding: utf-8 -*-

try:
    from urllib import request, error
except ImportError:
    import urllib2 as request
    error = request

from . import units

basecurrency = None
currencydict = {}
currencytime = None


class Currency(units.Value):
    def __new__(cls, value, unit=None, timestamp=None, **kw):
        v = super(Currency, cls).__new__(cls, value, unit=unit, **kw)
        v.timestamp = timestamp
        return v


def getrates(app_id="", offline=False, grace=3, historical=None,
             strict=False, timeout=3):
    import os, time, pickle, json
    global currencydict, currencytime
    url1 = 'http://openexchangerates.org/api/currencies.json'
    url2 = 'https://openexchangerates.org/api/latest.json?app_id=%s' % app_id
    url3 = 'http://openexchangerates.org/api/historical/%%s.json?app_id=%s' % app_id
    # FIXME: ~/.imks might not exist
    path = os.path.join(os.getenv('HOME'), '.imks', 'currencies.dat')
    if historical:
        force = True
    else:
        force = False
        try:
            currencytime = os.path.getmtime(path)
            delta = (time.time() - currencytime) / 86400.0
        except OSError:
            force = True
            delta = 0
        if offline:
            force = False
        elif delta > grace:
            force = True
    if force:
        try:
            response = request.urlopen(url1, timeout=timeout).read()
            currencydict = json.loads(response.decode('utf-8'))
            if historical:
                url = url3 % historical
            else:
                url = url2
            response = request.urlopen(url, timeout=timeout).read()
            data = json.loads(response.decode('utf-8'))
            currencytime = data["timestamp"]
            rates = data["rates"]
            if not historical:
                f = open(path, "wb")
                pickle.dump(currencydict, f, protocol=2)
                pickle.dump(rates, f, protocol=2)
                f.close()
            return rates
        except error.URLError as e:
            if strict:
                try:
                    response = e.read()
                    data = json.loads(e.decode('utf-8'))
                    description = data.get("description",
                                           "Unknown error in the currency server")
                    description = description[0:description.find("-")].strip() 
                except:
                    description = "Could not access the currency server"
                raise ValueError(description)
    if not historical:
        try:
            f = open(path, "rb")
            currencydict = pickle.load(f)
            rates = pickle.load(f)
            f.close()
            return rates
        except IOError:
            return None


def saverates(app_id="", *args, **kw):
    import time
    global basecurrency, currencydict, currencytime
    currency_unit = units.units[basecurrency].unit
    rates = getrates(app_id=app_id, *args, **kw)
    timestamp = time.strftime("%Y-%m-%d %H:%M", time.localtime(currencytime))
    if rates:
        for k, v in rates.items():
            if v:
                c = Currency(rates[basecurrency], currency_unit) \
                    / units.Value(v)
                c.__doc__ = currencydict[k]
                c.__timestamp__ = timestamp
                c.__source__ = "openexchangerates.org"
                units.units[k] = c
                if k in units.currency_symbols:
                    units.units[units.currency_symbols[k]] = c
                    currencydict[units.currency_symbols[k]] = currencydict[k]


def currencies(app_id="", grace=3, historical=None, background=False):
    import threading
    global basecurrency, currencydict
    # Check that the ID has been set
    if len(app_id) < 5:
        raise ValueError("Currencies are not available without a valid openexchangerates_id")
    # Check if a currency is a base currency
    if not basecurrency or basecurrency not in units.baseunits:
        raise ValueError("Base currency not defined")
    if historical:
        saverates(app_id=app_id, offline=False,
                  historical=historical, strict=True)
    else:
        # Use cache, if available, to update all units offline
        saverates(app_id=app_id, offline=background,
                  grace=grace, strict=(grace == 0))
        # Finally, update all units online using a new thread if requested to do so
        if background:
            thread = threading.Thread(target=saverates,
                                      kwargs={'grace': grace})
            thread.setDaemon(True)              # so we can always quit w/o waiting
            thread.start()


def reset():
    global basecurrency, currencydict, currencytime
    basecurrency = None
    currencydict = {}
    currencytime = None
