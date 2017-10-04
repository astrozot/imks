from .units import Value, System
from lxml import html
import requests

planet_table = """
Mercury   0.38709927      0.20563593      7.00497902      252.25032350     77.45779628     48.33076593
          0.00000037      0.00001906     -0.00594749   149472.67411175      0.16047689     -0.12534081
Venus     0.72333566      0.00677672      3.39467605      181.97909950    131.60246718     76.67984255
          0.00000390     -0.00004107     -0.00078890    58517.81538729      0.00268329     -0.27769418
EM Bary   1.00000261      0.01671123     -0.00001531      100.46457166    102.93768193      0.0
          0.00000562     -0.00004392     -0.01294668    35999.37244981      0.32327364      0.0
Mars      1.52371034      0.09339410      1.84969142       -4.55343205    -23.94362959     49.55953891
          0.00001847      0.00007882     -0.00813131    19140.30268499      0.44441088     -0.29257343
Jupiter   5.20288700      0.04838624      1.30439695       34.39644051     14.72847983    100.47390909
         -0.00011607     -0.00013253     -0.00183714     3034.74612775      0.21252668      0.20469106
Saturn    9.53667594      0.05386179      2.48599187       49.95424423     92.59887831    113.66242448
         -0.00125060     -0.00050991      0.00193609     1222.49362201     -0.41897216     -0.28867794
Uranus   19.18916464      0.04725744      0.77263783      313.23810451    170.95427630     74.01692503
         -0.00196176     -0.00004397     -0.00242939      428.48202785      0.40805281      0.04240589
Neptune  30.06992276      0.00859048      1.77004347      -55.12002969     44.96476227    131.78422574
          0.00026291      0.00005105      0.00035372      218.45945325     -0.32241464     -0.00508664
Pluto    39.48211675      0.24882730     17.14001206      238.92903833    224.06891629    110.30393684
         -0.00031596      0.00005170      0.00004818      145.20780515     -0.04062942     -0.01183482
"""

def genitive(name):
    if name[-1] == "s": return name + "'"
    return name + "'s"

def JPLconst(value, error, unit, name="", absolute=False):
    try:
        dummy = float(value) + float(error if error.strip() != "" else "0")
        engine = get_ipython().user_ns["ufloat"]
        if unit == "days" or unit == "d": unit = "day"
        if error: value = value + " +/- " + error
        if unit: v = Value(engine(value), unit, original=True,
                           absolute=absolute) 
        else: v = Value(engine(value), absolute=absolute)
        doc = "%s\n\nConstant defined in the SSD JPL database as: " % name
        if error: doc += "(%s +/- %s) [%s]" % (value, error, unit)
        else: doc += "%s [%s]" % (value, unit)
        v.__doc__ = doc
    except ValueError as s:
        v = Value(float("NaN"))
        v.__doc__ = "Error parsing JPL data: " + str(s)
    return v

def load_planets():
    url = "http://ssd.jpl.nasa.gov/?planet_phys_par"
    page = requests.get(url)
    tree = html.fromstring(page.text)
    table = tree.xpath('//table[@border="1"]')[0]
    newlabels = {"BulkDensity": "Bulk Density",
                 "EquatorialGravity": "Equatorial Gravity",
                 "EquatorialRadius": "Equatorial Radius",
                 "EscapeVelocity": "Escape Velocity",
                 "GeometricAlbedo": "Geometric Albedo", 
                 "MeanRadius": "Mean Radius",
                 "SiderealOrbit Period": "Sidereal Orbit Period",
                 "SiderealRotation Period": "Sidereal Rotation Period"}
    texts = [td.text_content() for td in table.xpath('*/td')]
    labels = texts[0:11]
    for l, label in enumerate(labels):
        if label in newlabels: labels[l] = newlabels[label]
    units = texts[11:22]
    data = []
    for n in range(22,len(texts),11):
        data.append(texts[n:n+11])
    planets = {}
    for line in data:
        for n, value in enumerate(line):
            if n == 0:
                name = value.strip(u" \n\t\xA0")
                planets[name] = {}
                continue
            v, e = [s.strip(u" \n\t\xA0")
                    for s in value.partition("[")[0].partition(u"\xB1")[::2]]
            u = units[n].strip(u" \n\t\xA0()")
            if labels[n] == "Mass" and u == "x 1024 kg":
                v = v + "e24"
                e = e + "e24"
                u = "kg"
            elif u == "mag": u = ""            
            planets[name][labels[n]] = (v, e, u)
    # Now add the planetary data
    T = 0.0
    labels = ["Semi-major axis", "Eccentricity", "Inclination", "Mean Longitude",
              "Longitude of Perihelius", "Longitude of Ascending Node"]
    units = ["AU", "", "deg", "deg", "deg", "deg"]
    for line in planet_table.split("\n")[1:-1]:
        if line[0:7] == "EM Bary": line = "Earth  " + line[7:]
        if line[0] != " ":
            values = line.split()
            name = values[0]
            for l, value in enumerate(values[1:]):
                planets[name][labels[l]] = (value, "", units[l])
        else:
            values = line.split()
            for l, value in enumerate(values):
                w = dict.__getitem__(planets[name], labels[l])
                planets[name][labels[l]] = (str(float(w[0]) + float(value)*T),
                                            "", units[l])
    return planets
    
    
def load_moons():
    # First we do the physical data
    url = "http://ssd.jpl.nasa.gov/?sat_phys_par"
    page = requests.get(url)
    tree = html.fromstring(page.text)
    tables = tree.xpath('//table[@border="1"]')
    planets = ["Earth", "Mars", "Jupiter", "Saturn", "Uranus", "Neptunus", "Pluto"]
    newlabels = {"GeometricAlbedo": "Geometric Albedo", "a": "Semi-major axis",
                 "e": "Eccentricity", "w": "Argument of periapsis",
                 "M": "Mean anomaly", "i": "Inclination",
                 "node": "Longitude of the ascending node", "n": "Longitude rate",
                 "P": "Sidereal period",
                 "Pw": "Argument of periapsis precession period",
                 "Pnode": "Longitude of the ascending node precession period"}
    moons = {}
    for p, table in enumerate(tables):
        planet = planets[p]
        lines = table.xpath('tr')
        labels = [s.text_content().partition("\n")[0].partition("(")[0].strip(" \t\n")
                  for s in lines[0].xpath("td|th")]
        units = [s.text_content().partition("(")[2].strip(" \t\n)")
                 for s in lines[0].xpath("td|th")]
        for l, label in enumerate(labels):
            if label in newlabels: labels[l] = newlabels[label]
            if labels[l] == "GM": units[l] = "km3/s2"
        moons[planet] = {}
        for line in lines[1:]:
            for n, value in enumerate(line.xpath(".//td|th")):
                if n == 0:
                    name = value.text_content().strip(u" \n\t\xA0").replace(" ", "")
                    moons[planet][name] = {}
                    continue
                elif n not in (1,3,5,6,8): continue
                v, e = [s.strip(u" \n\t\xA0")
                        for s in value.text_content().partition("[")[0].partition(u"\xB1")[::2]]
                l = n//2+1
                if labels[l] == "Magnitude": v = v.strip("RVr")
                if v == "?": v = "nan"
                moons[planet][name][labels[l]] = (v, e, units[l])
    # Now go for the satellite elements
    url = "http://ssd.jpl.nasa.gov/?sat_elem"
    page = requests.get(url)
    tree = html.fromstring(page.text)
    titles = tree.xpath('//tr[@bgcolor="#CCCCCC"]')
    for p, title in enumerate(titles):
        planet = planets[p]
        tables = title.xpath('..//table')
        for table in tables:
            lines = table.xpath('tr')
            labels = [td.text_content() for td in lines[0].xpath('td|th')]
            for l, label in enumerate(labels):
                if label in newlabels: labels[l] = newlabels[label]
            units = [td.text_content() for td in lines[1].xpath('td|th')]
            for line in lines[2:]:
                for n, value in enumerate(line.xpath(".//td|th")):
                    if n == 0:
                        name = value.text_content().strip(u" \n\t\xA0").replace(" ", "")
                        continue
                    elif labels[n] == "Ref.": continue
                    moons[planet][name][labels[n]] = \
                        (value.text_content(), "", units[n].strip(" ()"))
    return moons


def load_minor(minor):
    import urllib
    url = "http://ssd.jpl.nasa.gov/sbdb.cgi?sstr=%s;orb=0;cov=0;log=0;cad=0" \
        % urllib.quote(minor.encode("utf8"))
    page = requests.get(url)
    tree = html.fromstring(page.text)
    try:
        name = tree.xpath('//table[@bgcolor="#EEEEEE"]//b')[0].text
    except IndexError:
        raise NameError("Unknown minor planet")
    classification = tree.xpath('//table[@bgcolor="#EEEEEE"]//font[@size="-1"]')[1].text_content()
    spk_id = tree.xpath('//table[@bgcolor="#EEEEEE"]//font[@size="-1"]')[3].text_content()
    table = tree.xpath('//table[@border="1"]')[0]
    result = {}
    result["name"] = name
    result["classification"] = classification
    result["SPK-ID"] = spk_id
    for line in table.xpath('tr|th'):
        cols = line.xpath('td')
        name = cols[0].text_content().strip(u" \n\t\xA0")
        value = cols[2].text_content().strip(u" \n\t\xA0")
        unit = cols[3].text_content().strip(u" \n\t\xA0")
        sigma = cols[4].text_content().strip(u" \n\t\xA0")
        if value == "Value": continue
        if unit == "mag": unit = ""
        if sigma == "n/a": sigma = 0
        try:
            subname = genitive(minor) + " " + name
            result[name] = JPLconst(value, sigma, unit, name=subname)
            if result[name] != result[name]: result[name] = value
        except (ValueError, TypeError):
            result[name] = value
    title = tree.xpath('//tr[@bgcolor="#999999"]')[0]
    table = title.xpath('../..//table')[0]
    names = {"e": "ellipticity", "a": "semi-major axis",
             "q": "perihelion distance",
             "i": "inclination", "node": "longitude of ascending node",
             "peri": "argument of perihelion", "M": "mean anomaly",
             "tp": "time of perihelion passage", "period": "period",
             "n": "mean motion", "Q": "aphelion distance"}
    for line in table.xpath('tr|th'):
        absolute = False
        cols = line.xpath('td')
        name = cols[0].text_content().strip(u" \n\t\xA0")
        name = names.get(name, name)
        if cols[1].xpath(".//br"):
            value = cols[1].xpath(".//*[(preceding::br)]")[0].text
        else:
            value = cols[1].text_content()
        value = value.strip(u" \n\t\xA0")
        if cols[3].xpath(".//br"):
            unit = cols[3].xpath(".//*[(preceding::br)]")[0].text
        else:
            unit = cols[3].text_content()
        unit = unit.strip(u" \n\t\xA0")
        if unit == "deg/d": unit = "deg/day"
        elif unit == "d": unit = "day"
        elif unit == "mag": unit = ""
        elif unit == "JED":
            unit = "day"
            absolute = True
        if cols[2].xpath(".//br"):
            sigma = cols[2].xpath(".//*[(preceding::br)]")[0].text
        else:
            sigma = cols[2].text_content()
        sigma = sigma.strip(u" \n\t\xA0")
        if value == "Value": continue
        try:
            subname = genitive(minor) + " " + name
            result[name] = JPLconst(value, sigma, unit, name=subname,
                                    absolute=absolute)
        except (ValueError, TypeError):
            result[name] = value
    
    return result


def loadJPLconstants(force=False):
    import pickle, os, os.path
    path = os.path.join(os.getenv('HOME'), '.imks', 'JPLconstants.idat')
    planets = {}
    moons = {}
    f = None
    try:
        f = open(path, "rb")
        planets = pickle.load(f)
        moons = pickle.load(f)
    except:
        pass
    finally:
        if f: f.close()
    if force or len(planets) < 8 or len(moons) < 6:
        planets = load_planets()
        moons = load_moons()
        f = open(path, "wb")
        pickle.dump(planets, f)
        pickle.dump(moons, f)
        f.close()
    for k1,v1 in planets.items():
        for k2,v2 in v1.items():
            name = genitive(k1) + " " + k2
            v1[k2] = JPLconst(v2[0], v2[1], v2[2], name=name)
    for k1,v1 in moons.items():
        for k2,v2 in v1.items():
            for k3,v3 in v2.items():
                name = k3 + " of " + k2 + ", moon of " + k1
                v2[k3] = JPLconst(v3[0], v3[1], v3[2], name=name)
    return planets, moons
