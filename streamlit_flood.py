import streamlit as st
# To make things easier later, we're also importing numpy and pandas for
# working with sample data.
import numpy as np
import pandas as pd
from streamlit_folium import folium_static
import folium
import requests
import json
from folium.plugins import MarkerCluster
from datetime import datetime
import os
import seaborn as sns
import matplotlib.pyplot as plt

"# Environment Agency: Live Flood Data"

# get data
url = 'http://environment.data.gov.uk/flood-monitoring/id/floods'
r = requests.get(url).json()

flood_area_id_list = []
county_list = []
severity_list = []
time_changed_list = []
flood_id_list = []
lat_list = []
long_list = []
polygon_url_list = []
riverorsea_list = []
severity_level_list = []

for i in range(len(r['items'])):
    flood_area_id = r['items'][i]['floodAreaID']
    county = r['items'][i]['floodArea']['county']
    severity = r['items'][i]['severity']
    severity_level = r['items'][i]['severityLevel']
    time_changed = r['items'][i]['timeSeverityChanged']
    flood_id = r['items'][i]['floodArea']['@id']
    polygon_url = r['items'][i]['floodArea']['polygon']
    riverorsea = r['items'][i]['floodArea']['riverOrSea']

    flood_area_id_list.append(flood_area_id)
    county_list.append(county)
    severity_list.append(severity)
    severity_level_list.append(severity_level)
    time_changed_list.append(time_changed)
    flood_id_list.append(flood_id)
    polygon_url_list.append(polygon_url)
    riverorsea_list.append(riverorsea)

df = pd.DataFrame(list(zip(flood_area_id_list, county_list, 
                severity_list, severity_level_list, time_changed_list, flood_id_list, polygon_url_list, riverorsea_list)),
columns = ["id", "county", "status", 'severity_level', "date changed", "latlon_url", "polygon_url", "riverorsea"])    

df = df[df['status']!= 'Flood alert']
df.reset_index(inplace=True, drop=True)

df = df.copy()
df['lat'] = ""
df['long'] = ""
df['coords'] =""
df['description']=""
df['CTY19NM'] = ""

for i in range(len(df['latlon_url'])): 
    if i % 10 == 0:
        print('{} of {} urls processed.\r'.format(i, len(df)))
    r2 = requests.get(df['latlon_url'].iloc[i]).json()
    df['long'].iloc[i] = r2['items']['long']
    df['lat'].iloc[i] = r2['items']['lat']
    
    r3 = requests.get(df['polygon_url'].iloc[i]).json()
    df['description'].iloc[i] =r3['features'][0]['properties']['DESCRIP']
    df['CTY19NM'].iloc[i] = r3['features'][0]['properties']['LA_NAME']
    
def get_coord(x):
    r3 = requests.get(x).json()
    coords = r3['features'][0]['geometry']
    return coords

coords_list = map(get_coord, df['polygon_url'])
df['coords'] = list(coords_list) 

df_360 = pd.read_csv('https://raw.githubusercontent.com/jenniferbufton/flood_app/main/data/360Giving_flood_20210204.csv')

date = datetime.now()

df_360['Award Date'] = pd.to_datetime(df_360['Award Date'])
df['date changed'] = pd.to_datetime(df['date changed'])

# add sidebar logo and input
st.sidebar.image('logo.png')

st.sidebar.write('Enter a postcode in the "Postcode finder" widget to change the focus of the map and to see investments that have been made in that area.')

latlon = st.sidebar.text_input('Postcode finder:', value='RH20 4EE', max_chars=8, key=None, type='default')

# API for OS - remove until it is possible to reference secrets in streamlit
#key = os.environ.get("api_key")

#layer = 'Outdoor_3857'
#zxy_path = 'https://api.os.uk/maps/raster/v1/zxy/{}/{{z}}/{{x}}/{{y}}.png?key={}'.format(layer, key)
#print('=> Constructed OS Maps ZXY API path: {}'.format(zxy_path))

try:
    r = requests.get('https://api.postcodes.io/postcodes/{}'.format(latlon))
    lat = r.json()['result']['latitude']
    lon = r.json()['result']['longitude']
    lsoa = r.json()['result']['lsoa']
except:
    st.sidebar.write('**This is not a valid postcode. Please try again** :sunglasses:')
    r = requests.get('https://api.postcodes.io/postcodes/{}'.format('WC1B3HF'))
    lat = r.json()['result']['latitude']
    lon = r.json()['result']['longitude']
    lsoa = r.json()['result']['lsoa']



flood_df = df[df['status']=='Flood warning']
flood_df = flood_df.sort_values('severity_level', ascending=False)
flood_df.reset_index(inplace=True)


m = folium.Map(location=[lat, lon],
            min_zoom=7, 
            max_zoom=16,
            zoom_start=15 )

#tile = folium.TileLayer(
 #       tiles = zxy_path,
 #       attr = 'Contains OS data © Crown copyright and database right {}'.format(date.year),
 #       name = 'OS Outdoor 3857',
 #       overlay = False,
 #       control = True
 #      ).add_to(m)

# map 
tile2 = folium.TileLayer(
    tiles = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attr = 'Esri',
    name = 'Esri Satellite',
    overlay = False,
    control = True
    ).add_to(m)

folium.TileLayer('Stamen Terrain').add_to(m)

style_0 = {'fillColor': '#2ca25f',  'color': '#2ca25f', "fillOpacity": 0.1, "weight": 1.7}
style_1 = {'fillColor': '#dd1c77',  'color': '#dd1c77', "fillOpacity": 0.5}
style_2 = {'fillColor': '#bdbdbd',  'color': '#756bb1', "fillOpacity": 0.5}

fg = folium.FeatureGroup(name='Active Partnership', show=True)
m.add_child(fg)

point = folium.FeatureGroup(name='Previous Flood Relief investment', show=True)
m.add_child(point)

flood = folium.FeatureGroup(name='Flooded area', show=True)
m.add_child(flood)

flood_no = folium.FeatureGroup(name='Warning no longer active', show=True)
m.add_child(flood_no)

marker_cluster = MarkerCluster().add_to(point)

ap = requests.get('https://raw.githubusercontent.com/jenniferbufton/flood_app/main/data/AP.json').json()

for row in range(len(ap['features'])):
    ap_json = folium.GeoJson(data=(ap['features'][row]['geometry']), style_function = lambda x:style_0).add_to(fg)
    ap_json.add_child(folium.Popup(ap['features'][row]['properties']['Label']))

for i in range(len(df_360)):
    folium.Circle(
        location=[df_360['Beneficiary Location:0:Latitude'][i],
                df_360['Beneficiary Location:0:Longitude'][i]],
        popup=('Organisation: {} \n Amount: £{:,} \n Award date: {} \n URN: {}' .format(df_360['Recipient Org:Name'].iloc[i], 
                                                        df_360['Amount Awarded'].iloc[i], df_360['Award Date'][i].strftime("%d/%m/%Y"),
                                                        df_360['URN'][i])),
        radius= 100, #df_360['Amount Awarded'].astype('float')[i]/10,
        color='#00441b',
        fill=True,
        fill_color='#2ca25f',
    opacity=0.8,
    fill_opacity=0.7,
    ).add_to(marker_cluster)

warning_df = df[df['status']=='Flood warning']
warning_df.reset_index(inplace=True, drop=True)

no_df = df[df['status']!='Flood warning']
no_df.reset_index(inplace=True, drop=True)


for i in range(len(warning_df)):
    geo_json = folium.GeoJson(warning_df['coords'][i], style_function = lambda x:style_1)
    geo_json.add_child( folium.Popup('Status: {} \n Description: {} \n Severity: {}' .format(warning_df['status'][i],
    warning_df['description'][i], warning_df['severity_level'][i])))
    geo_json.add_to(flood)

for i in range(len(no_df)):
    geo_json2 = folium.GeoJson(no_df['coords'][i], style_function = lambda x:style_2)
    geo_json2.add_child( folium.Popup('Status: {} \n Description: {} \n Severity: {} \n Date changed: {}' .format(no_df['status'][i],
    no_df['description'][i], no_df['severity_level'][i], no_df['date changed'][i].strftime("%d/%m/%Y"))))
    geo_json2.add_to(flood_no)
    
folium.LayerControl(collapsed = False).add_to(m)

# sidebar options for flood relief

st.sidebar.write('If there are no flood warnings or warnings that have been removed, this input will not be selectable.')
option = st.sidebar.selectbox(
    'Status:',
     df['status'].unique())

#st.title('Flood Relief') - not required 

if option == "Warning no longer in force":
    'Warnings that are no longer in force are shown for 24 hours after they have been issued'

## plot 
plot_df = df[df['status']== option]

plot_df['count'] = int(1)

font = {'family' : 'Poppins', # define font
        'weight' : 'normal',
        'size'   : 10}
plt.rc('font', **font)

try:
    f = sns.barplot(y='county',x='count', data=plot_df, estimator=sum, palette='Set2', orient='h')
    locs, labels = plt.xticks()
    plt.title('{} by county area'.format(option))
    f.set(ylabel="Counties", xlabel="Number of '{}' statuses".format(option))
    st.set_option('deprecation.showPyplotGlobalUse', False)
    st.pyplot()
except ValueError:
    st.write("### There are currently no active warnings")

# call to render Folium map in Streamlit
st.write("### Use the 'Postcode finder' widget in the sidebar to focus on a place, or zoom out to see a country-wide view:")

# add map
folium_static(m)

# add dataframe
st.write("### Organisations funded in that area (LSOA):")

df = df_360[df_360['Beneficiary Location:3:Name']== lsoa]
st.write(df[['URN','Recipient Org:Name', 'Amount Awarded',  'Award Date']].sort_values('Award Date'))
