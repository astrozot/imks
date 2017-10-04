import urllib2, json

endpointURL = "http://dbpedia.org/sparql"
name = "Earth"
query = """
SELECT DISTINCT ?label ?value
WHERE {
  ?property rdfs:label ?label .
  <http://dbpedia.org/resource/%s> ?property ?value .
  FILTER (lang(?label) = "en" or !(langMatches(lang(?label), "*")))
  FILTER (lang(?value) = "en" or !(langMatches(lang(?value), "*")))
}
""" % "Carbon_Monoxide"

escapedQuery = urllib2.quote(query)
requestURL = endpointURL + "?format=JSON&query=" + escapedQuery
request = urllib2.Request(requestURL)

data = urllib2.urlopen(request)
res0 = json.load(data)
head = res0["head"]["vars"]
res1 = res0["results"]["bindings"]
res2 = [(v["label"]["value"], v["value"]["value"], v["value"].get("datatype", ""))
        for v in res1]

res3 = {}
for k, v, u in res2:
    if k in res3: res3[k].append((v, u))
    else: res3[k] = [(v, u)]
print res3
