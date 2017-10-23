try:
    from urllib import request, error
except:
    import urllib2 as request
    error = request

app_id = ""


def wolfram(query):
    timeout = 5
    url = "http://api.wolframalpha.com/v1/result?appid=%s&i=%s&units=metric" % \
        (app_id, query)
    response = request.urlopen(url, timeout=timeout).read()

