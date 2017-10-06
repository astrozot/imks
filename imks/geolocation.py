from __future__ import absolute_import, division, print_function
import math, json, time, pickle

try:
    from urllib import request, error
except:
    import urllib2 as request
    error = request
    
import pytz
from . import units
from . import pycalcal as pcc

# http://api.hostip.info/get_json.php?position=true

geolocation = None
location = pcc.location(0, 0, 0, 0)

def set_geolocation(address=None, latitude=None, longitude=None, elevation=None,
                    timezone=None, cache=True):
    """Set the current geografic location.

    The function operats in the following way:
      1. If both latitude and longitude are provided, they are used as geographical
         coordinates.
      2. Otherwise, if address is provided, the latitude and longitude are resolved
         using the address.
      3. Otherwise, the latitude and longitude are inferred from the computer IP.
      4. The elevation and timezone, if provided, are used; otherwise, they are
         inferred from the latitude and longitude.  Note that the timezone is
         obtained for the current date, and that it might change with time (for
         example as a result of daylight saving time).
      5. If cache is True, the data are also saved (pickled) in a file for later
         use.

    The function returns a dictionary with the following terms:
    address:              the address provided, as a string
    latitude & longitude: the location's coordinates in degrees
    elevation:            the location's elevation in meters
    timezone:             the location's timezone in seconds
    """
    global geolocation, location
    if latitude is not None and longitude is not None:
        loc = {"address": "", "latitude": latitude,
               "longitude": longitude}
    else:
        try:
            loc = get_location(address)
        except ValueError:
            raise ValueError("Could not set the location")
    if timezone is not None:
        timezone = units.Value(timezone)
        if not timezone.unit: timezone = units.Value(timezone*3600, "s")
        timezone.checkUnits(units.Value(1, "s").unit)
    else:
        try:
            timezone = get_timezone(**loc)
            timezone = units.Value(timezone["dstOffset"] +
                                   timezone["rawOffset"], "s")
        except ValueError:
            timezone = None
    if elevation is not None:
        elevation = units.Value(elevation)
        if not elevation.unit: elevation = units.Value(elevation, "m")
        elevation.checkUnits(units.Value(1, "m").unit)
    else:
        try:
            elevation = units.Value(get_elevation(**loc), "m")
        except ValueError:
            elevation = units.Value(0, "m")
    # Set the variables
    latitude = units.Value(loc["latitude"], "deg") | units.System("deg")
    latitude.__doc__ = "Latitude of the current geographic position, in degrees"
    longitude = units.Value(loc["longitude"], "deg") | units.System("deg")
    longitude.__doc__ = "Longitude of the current geographic position, in degrees"
    timezone.__doc__ = "Timezone (in seconds) of the current geographic position"
    elevation.__doc__ = "Elevation above see level of the current geographic position"
    geolocation = {"address": loc["address"] or address or "",
                   "latitude": latitude,
                   "longitude": longitude,
                   "elevation": elevation,
                   "timezone": timezone}
    location = pcc.location(latitude.value, longitude.value, elevation.value,
                            timezone.value)
    if cache:
        try:
            import os, os.path
            path = os.path.join(os.getenv("HOME"), ".imks", "geolocation.dat")
            f = open(path, "w")
            picke.dump(f, geolocation)
            f.close()
        except:
            pass
    return geolocation

def get_geolocation(cache=True):
    """Return a previously computed geolocation."""
    global geolocation
    if geolocation: return geolocation
    elif cache:
        try:
            import os, os.path
            path = os.path.join(os.getenv("HOME"), ".imks", "geolocation.dat")
            f = open(path, "w")
            geolocation = picke.load(f)
            f.close()
            location = pcc.location(latitude.value, longitude.value,
                                    elevation.value, timezone.value)
            return geolocation
        except:
            pass
    raise ValueError("Could not get the location")

def get_location(name=None, ip=None):
    if name:
        url = "http://maps.googleapis.com/maps/api/geocode/json?address=%s&sensor=false" % \
              request.quote(name)
        try:
            data = json.loads(request.urlopen(url).read())
            if data["status"] != "OK":
                raise ValueError("Could not geoencode %s (location not found)")
            address = data["results"][0]["formatted_address"]
            location = data["results"][0]["geometry"]["location"]
            result = {"address": address,
                      "latitude": location["lat"],
                      "longitude": location["lng"]}
            return result
        except error.URLError as e:
            raise ValueError("Cound not geoencode %s (server unreachable)" % name)
    else:
        if ip: url = "http://api.hostip.info/get_json.php?ip=%s&position=true" % ip
        else: url = "http://api.hostip.info/get_json.php?position=true"
        try:
            data = json.loads(request.urlopen(url).read())
            result = {"address": "%s, %s" % (data["city"], data["country_name"]),
                      "latitude": float(data["lat"]),
                      "longitude": float(data["lng"])}
            return result
        except error.URLError as e:
            raise ValueError("Cound not perform geolocation discovery (server unreachable)")
    
        
def get_timezone(longitude, latitude, timestamp=None, **kw):
    if timestamp is None:
        timestamp = time.time()
    url = "https://maps.googleapis.com/maps/api/timezone/json?location=%s,%s&timestamp=%s&sensor=false" % \
          (request.quote(str(latitude)), urllib2.quote(str(longitude)),
           request.quote(str(timestamp)))
    try:
        data = json.loads(request.urlopen(url).read())
        if data["status"] != "OK": 
            print("Could not find the timezone, assuming a standard one")
            return {"status": "COMPUTED",
                    "dstOffset": 0,
                    "timeZoneId": "UTC",
                    "rawOffset": math.floor(float(longitude) / 15 + 0.5) * 3600,}
        return data
    except error.URLError as e:
        raise ValueError("Cound not find the timezone (server unreachable)")


def get_elevation(longitude, latitude, **kw):
    url = "http://maps.googleapis.com/maps/api/elevation/json?locations=%s,%s&sensor=false" % \
          (request.quote(str(latitude)), request.quote(str(longitude)))
    try:
        data = json.loads(request.urlopen(url).read())
        if data["status"] != "OK":
            raise ValueError("Could not find the elevation")
        return data["results"][0]["elevation"]
    except error.URLError as e:
        raise ValueError("Cound not find the elevation (server unreachable)")
