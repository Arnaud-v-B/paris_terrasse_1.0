#dependencies
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
from requests.structures import CaseInsensitiveDict
import pickle
from PIL import Image
from math import sin, cos

#local imports
from shadow_mapper.heightmap import HeightMap
import shadow_mapper.query_sm as shadow_map
from shadow_mapper.suncalc import solar_position


#calculating now, if no given time by usr
now = datetime.now().strftime('%Y-%m-%d %H:%M')
now_plus1 = (datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M')

# API_Key
Key_geopapify = "9bc5e5daf799415587200846f5a53481"

# Local var
hm_file = "shadow_mapper/data/output/Paris.heightmap"
terrasses_url = "https://opendata.paris.fr/api/explore/v2.1/catalog/datasets/terrasses-autorisations/exports/csv?lang=fr&timezone=Europe%2FBerlin&use_labels=true&delimiter=%3B"

from math import radians, cos, sin, asin, sqrt
def distance(lat, usr_lat, lon, usr_lon):


    lon1 = radians(lon)
    lon2 = radians(usr_lon)
    lat1 = radians(lat)
    lat2 = radians(usr_lat)

    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2

    c = 2 * asin(sqrt(a))

    # Radius of earth in kilometers. Use 3956 for miles
    r = 6371

    # calculate the result
    return(c * r)

from operator import contains

def cleaner(df:pd.DataFrame):
    clean_df = df.copy()
    l = ["ETALAGE", "CONTRE ETALAGE", "Contre étalage sur trottoir","Contre étalage sur place de stationnement",
     "Contre étalage sur voie piétonne","Étalage sur voie piétonne", "Étalage sur trottoir", "PLANCHER MOBILE"]

    clean_df["Nom de la société"] = clean_df.apply(lambda x: x["Nom de l'enseigne"] if pd.isna(x["Nom de la société"])  else x["Nom de la société"],axis=1)

    clean_df = clean_df[clean_df["Nom de la société"].isna() == False]
    clean_df = clean_df[clean_df["Période d\'installation"].isna() == False]
    clean_df = clean_df[~clean_df["Typologie"].isin(l)]

    return clean_df

def get_latlon(address:str=address):
    url_geopapify = "https://api.geoapify.com/v1/geocode/search?"

    headers_geopapify = {
        "Accept" : "application/json"
        }

    params_geopapify = {
        "text" : address,
        "apiKey" : Key_geopapify
        }

    response_geoapify = requests.get(url_geopapify,params=params_geopapify, headers=headers_geopapify).json()
    data = {k:v for (k,v) in response_geoapify["features"][0]["properties"].items() if k!="datasource" and k!="timezone" and k!="rank"}

    geocode = pd.DataFrame(data, index=[0])
    rank = pd.DataFrame({k:v for (k,v) in response_geoapify["features"][0]["properties"]["rank"].items()},index=[0])
    timezone = pd.DataFrame({k:v for (k,v) in response_geoapify["features"][0]["properties"]["timezone"].items()},index=[0])
    datasource = pd.DataFrame({k:v for (k,v) in response_geoapify["features"][0]["properties"]["datasource"].items()},index=[0])

    usr_lon = geocode["lon"].values[0]
    usr_lat = geocode["lat"].values[0]
    return usr_lat,usr_lon

with open(hm_file, 'rb') as f:
        hm = pickle.load(f)

def query_sm(x:float,y:float,hm=hm,start:str=now,end:str=now_plus1,interval:int=60):

    t1 = datetime.strptime(start, '%Y-%m-%d %H:%M')
    t2 = datetime.strptime(end, '%Y-%m-%d %H:%M')
    delta = timedelta(minutes=interval)
    t = t1

    print("query_sm - Starting solar_position: ")
    sunpos = solar_position(t, hm.lat, hm.lng)
    print("query_sm - End solar_position: ")

    print("query_sm - Starting get_projection_north_deviation: ")
    dev = shadow_map.get_projection_north_deviation(hm.proj, hm.lat, hm.lng)
    print("query_sm - End get_projection_north_deviation: ")

    sun_x = -sin(sunpos['azimuth'] - dev) * cos(sunpos['altitude'])
    sun_y = -cos(sunpos['azimuth'] - dev) * cos(sunpos['altitude'])
    sun_z = sin(sunpos['altitude'])

    sm = shadow_map.ShadowMap(hm.lat, hm.lng, hm.resolution, hm.size, hm.proj, sun_x, sun_y, sun_z, hm, 1.5)

    if 0 <= x <= hm.size and 0 <= y <= hm.size:
        return True if sm.is_lit(x, y) else False
    else:
        return None


def return_xy(lat:float,lon:float):
    x, y = shadow_map.Map(hm.lat, hm.lng, hm.resolution,hm.size,hm.proj)._latLngToIndex(lat=lat,lng=lon)
    return x, y

def get_terrasses_df(address:str=address,start:str=now, end:str=now_plus1,interval:int=60, maxdist:float=1.5):

    print("get_terrasses_df - Starting get_latlon: ")
    usr_lat,usr_lon = get_latlon(address=address)
    print("get_terrasses_df - End get_latlon: ")

    print("get_terrasses_df - Starting cleaner: ")
    terrasses = cleaner(pd.read_csv(terrasses_url,delimiter=';'))
    print("get_terrasses_df - End cleaner: ")

    terrasses["lat"] = terrasses["geo_point_2d"].apply(lambda x: x.split(",")[0])
    terrasses["lon"] = terrasses["geo_point_2d"].apply(lambda x: x.split(",")[1])

    print("get_terrasses_df - Starting haversine_distance: ")
    terrasses["dist_from_usr(km)"] = terrasses[["lat","lon"]].apply(lambda x:
                                                                    distance(
                                                                        lat=float(x.lat),
                                                                        usr_lat=usr_lat,
                                                                        lon=float(x.lon),
                                                                        usr_lon=usr_lon
                                                                        ),axis=1)

    terrasses = terrasses[terrasses["dist_from_usr(km)"]<maxdist].sort_values(by="dist_from_usr(km)")

    terrasses["surface(m²)"] = terrasses[["Longueur","Largeur"]].apply(lambda x: x.Longueur * x.Largeur ,axis=1)
    terrasses["capacity"] = terrasses["surface(m²)"].apply(lambda x: np.round(x/2))

    print("get_terrasses_df - Starting return_xy: ")
    terrasses["xy_pixels"] = terrasses[["lat","lon"]].apply(lambda x: tuple(return_xy(lat=x.lat,lon=x.lon)),axis=1)




    terrasses["open?"] = terrasses.apply(lambda x:True if
                                        x["Période d'installation"].lower() == "toute l'année"
                                         or
                                         datetime.strptime(x["Période d'installation"][3:8]+"/"+str(datetime.now().year),"%d/%m/%Y")
                                         <=
                                         datetime.strptime(start[:10],"%Y-%m-%d")
                                         <=
                                         datetime.strptime(x["Période d'installation"][12:17]+"/"+str(datetime.now().year),"%d/%m/%Y")
                                         else False,axis=1)

    print("get_terrasses_df - Starting query_sm: ")
    terrasses["sun?"] = terrasses["xy_pixels"].apply(lambda x: query_sm(x=x[0],y=x[1],start=start,end=end))
    print("get_terrasses_df - End query_sm: ")

    return terrasses


def tarrasse(address:str="6 rue charles-francois dupuis",start:str=datetime.now().strftime('%Y-%m-%d %H:%M'),end:str=(datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M')):
    print("Main - Address used: ",address)
    print("Main - Time used: ",start)

    print("Main - Starting: get_terrasses_df")
    terrasses = get_terrasses_df(address=address,start=start,end=end)
    print("Main - End: get_terrasses_df")

    best = terrasses[(terrasses["sun?"] == True) & (terrasses["open?"] == True)]
    best = best.groupby(["Numéro et voie", "Nom de la société"]).aggregate({
    'Typologie':"first",
    'Arrondissement':"first",
    'Longueur':"sum",
    'Largeur':"sum",
    "Période d'installation":"first",
    'dist_from_usr(km)':"mean",
    'open?':"first",
    'sun?':"first"}).reset_index().sort_values(by="dist_from_usr(km)",axis=0)


    best["capacity(max)"] = best.apply(lambda x: np.floor((x.Longueur * x.Largeur)/2) ,axis=1)
    if len(best) > 10:
        best = best.head(10)
        return best
    else:
        return best
