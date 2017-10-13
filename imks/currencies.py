# -*- coding: utf-8 -*-

try:
    from urllib import request, error
except:
    import urllib2 as request
    error = request

from . import units

basecurrency = None
currencydict = {}
currencytime = None

class Currency(units.Value):
    def __init__(self, value, unit={}, absolute=False, timestamp=None):
        units.Value.__init__(self, value, unit, absolute)
        self.timestamp = timestamp

# Extracted from: http://en.wikipedia.org/wiki/List_of_circulating_currencies
currency_symbols = {
    'AED': u'د.إ',
    'AFN': u'؋',
    'BDT': u'৳',
    'BGN': u'лв',
    'BHD': u'.د.ب',
    'CNY': u'元',
    'CRC': u'₡',
    'CZK': u'Kč',
    'DZD': u'د.ج',
    'EGP': u'ج.م',
    'ERN': u'Nfk',
    'EUR': u'€',
    'GBP': u'£',
    'GEL': u'ლ',
    'GHS': u'₵',
    'ILS': u'₪',
    'IQD': u'ع.د',
    'IRR': u'﷼',
    'JOD': u'د.ا',
    'JPY': u'¥',
    'KES': u'Sh',
    'KHR': u'៛',
    'KRW': u'₩',
    'KWD': u'د.ك',
    'LAK': u'₭',
    'LBP': u'ل.ل',
    'LKR': u'රු',
    'LYD': u'ل.د',
    'MAD': u'د.م.',
    'MKD': u'ден',
    'MNT': u'₮',
    'NGN': u'₦',
    'OMR': u'ر.ع.',
    'PHP': u'₱',
    'PLN': u'zł',
    'PYG': u'₲',
    'QAR': u'ر.ق',
    'RSD': u'дин',
    'RUB': u'руб.',
    'SAR': u'ر.س',
    'SYP': u'ل.س',
    'THB': u'฿',
    'TND': u'د.ت',
    'UAH': u'₴',
    'VND': u'₫',
    'YER': u'﷼'}

def getrates(app_id="", base='EUR', offline=False, grace=3, historical=None,
             strict=False, timeout=3):
    import os, os.path, time, pickle, json
    global currencydict, currencytime
    url1 = 'http://openexchangerates.org/api/currencies.json'
    url2 = 'https://openexchangerates.org/api/latest.json?app_id=%s' % app_id
    url3 = 'http://openexchangerates.org/api/historical/%%s.json?app_id=%s' % app_id
    if historical: force = True
    else:
        force = False
        try:
            path = os.path.join(os.getenv('HOME'), '.imks', 'currencies.dat')
            currencytime = os.path.getmtime(path)
            delta = (time.time() - currencytime) / 86400.0
        except OSError:
            force = True
            delta = 0
        if offline: force = False
        elif delta > grace: force = True
    if force:
        try:
            response = request.urlopen(url1, timeout=timeout).read()
            currencydict = json.loads(response.decode('utf-8'))
            if historical: url = url3 % historical
            else: url = url2
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

def saverates(app_id="", base_id=0, base='EUR', *args, **kw):
    import time
    global basecurrency, currencydict, currencytime
    rates = getrates(app_id=app_id, base=base, *args, **kw)
    timestamp = time.strftime("%Y-%m-%d %H:%M", time.localtime(currencytime))
    if rates:
        for k, v in rates.items():
            if v:
                c = Currency(rates[basecurrency], {base_id: 1}) \
                    / units.Value(v)
                c.__doc__ = currencydict[k]
                c.__timestamp__ = timestamp
                c.__source__ = "openexchangerates.org"
                units.units[k] = c
                if k in currency_symbols:
                    units.units[currency_symbols[k]] = c
                    currencydict[currency_symbols[k]] = currencydict[k]
        
def currencies(app_id="", grace=3, historical=None, background=False):
    import threading
    global basecurrency, currencydict
    # Check that the ID has been set
    if len(app_id) < 5:
        raise ValueError("Currencies are not available without a valid openexchangerates_id")
    # Check if a currency is a base currency
    if basecurrency is None:
        basecurrency = 'EUR'
    if not basecurrency in units.baseunits:
        base_id = len(units.baseunits)
        v = units.Value(1, {len(units.baseunits): 1})
        v.__doc__ = basecurrency
        units.units[basecurrency] = v
        units.baseunits.append(basecurrency)
    else:
        for base_id, base in enumerate(units.baseunits):
            if base == basecurrency: break
    if historical:
        rates = saverates(app_id=app_id, base_id=base_id, base=basecurrency,
                          offline=False, historical=historical, strict=True)
    else:
        # Use cache, if available, to update all units offline
        rates = saverates(app_id=app_id, base_id=base_id, base=basecurrency,
                          offline=background, grace=grace, strict=(grace == 0))
        # Finally, update all units online using a new thread if requested to do so
        if background:
            thread = threading.Thread(target=saverates,
                                      kwargs={'base_id': base_id, 'base': basecurrency,
                                              'grace': grace})
            thread.setDaemon(True)              # so we can always quit w/o waiting
            thread.start()


def reset():
    global basecurrency, currencydict, currencytime
    basecurrency = None
    currencydict = {}
    currencytime = None
