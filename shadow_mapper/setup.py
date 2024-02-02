import overpass
import osm2geojson
import json

#Env variables
overpass_url = "https://overpass-api.de/api/interpreter"
France_projections = "EPSG:2154"
path_geojson = "shadow_mapper/data/In/Paris.geojson"
path_elevation = "shadow_mapper/data/In/"
path_heightmap = "shadow_mapper/data/output/Paris.heightmap"
path_image = "shadow_mapper/data/output/Paris.png"

#Get GeoJSON
def getgeojson():
    api = overpass.API(timeout=500)
    res = api.get("""
        area["name"="Paris"]->.searchArea;
        (
        way["building"](area.searchArea);
        );
        (._;>;);
        """,responseformat="json")
    obj = json.dumps(res,indent=4)
    with open("shadow_mapper/data/In/Paris.json", "w") as outfile:
        outfile.write(obj)

    data = json.load(open("shadow_mapper/data/In/Paris.json",))
    var = osm2geojson.json2geojson(data)
    obj = json.dumps(var,indent=4)
    with open("shadow_mapper/data/Paris.geojson", "w") as outfile:
        outfile.write(obj)

#Inputs
lat = 48.85661
lon = 2.35222
resolution = 4 #(m/pixel)
size = 1024 #(pixels)

! python3 shadow_mapper/heightmap.py --projection $France_projections \
    --elevation-dir $path_elevation \
    --geojson $path_geojson \
    --output $path_heightmap \
    --save-image $path_image \
    $lat $lon $resolution $size
