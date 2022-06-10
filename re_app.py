from typing import final
import streamlit as st
import pandas as pd
import glob
import matplotlib.pyplot as plt
import seaborn as sns
import pydeck as pdk
from datetime import datetime

# DATA IMPORT

# utility to drop columns across all data from this source
def drop_columns (df):
    df.drop(['index', 'NEXT OPEN HOUSE START TIME', 'NEXT OPEN HOUSE END TIME', 'SOURCE', 'FAVORITE', 'INTERESTED'], axis=1, inplace=True)
    return df

# utility to take a row and reformat to display , for thousands
def show_thous(series):
    series.apply(lambda d: f"{d:,}")
    return series

# import listings from daily CSVs and concatenate to a single df
def import_listings(files):
    all_files = []
    for f in files:
        df = pd.read_csv(f)
        df['UPDATED'] = str(f)
        all_files.append(df)
    df = pd.concat(all_files)
    # light cleanup
    df.reset_index(inplace=True)
    df = drop_columns(df)
    return df


# load listing data
@st.cache
def load_final():
    for_sale_files = glob.glob("for_sale/*.csv")
    reduced_files = glob.glob("reduced/*.csv")
    sold_files = glob.glob("sold/*.csv")
    for_sale = import_listings(for_sale_files)
    reduced = import_listings(reduced_files)
    sold = import_listings(sold_files)

    # Clean up the updated field on for sale listings
    for_sale['UPDATED'] = for_sale['UPDATED'].str.slice(start=9, stop=19)
    for_sale['UPDATED'] = pd.to_datetime(for_sale['UPDATED'])

    # Clean up the updated field on reduced listings
    reduced['UPDATED'] = reduced['UPDATED'].str.slice(start=8, stop=18)
    reduced['UPDATED'] = pd.to_datetime(reduced['UPDATED'])

    # Update the datatype for sold listings
    sold["SOLD DATE"] = pd.to_datetime(sold["SOLD DATE"])

    # Combine for sale and reduced listings so we can get the latest asking price for comparison
    for_sale = pd.concat([for_sale, reduced])
    for_sale = for_sale.drop(['SOLD DATE'], axis=1)

    # Drop any duplicates from the sales listings
    final = for_sale.sort_values(by=["UPDATED"])
    final = final.drop_duplicates(subset=['MLS#'], keep='last')

    # Join sold and for sale listings
    final = pd.merge(final, sold[['SOLD DATE', 'PRICE', 'MLS#']], how='inner', on='MLS#')
    final = final.rename(columns={"PRICE_x": "ASKING PRICE", "PRICE_y": "SALE PRICE", "URL (SEE https://www.redfin.com/buy-a-home/comparative-market-analysis FOR INFO ON PRICING)": "URL"})
    final['DIFF'] = final["SALE PRICE"] - final['ASKING PRICE']

    return final

# SUMMARY STATS
# calculate mean amount over asking price
def m_over(df):
    m = df["DIFF"].loc[df['DIFF'] > 0].mean()
    return m

# calculate % of properties that went over asking price
def p_over(df):
    p = (df["DIFF"].loc[df['DIFF'] > 0].count() / df["DIFF"].count())*100
    return p

# calculate % of properties that went over asking price
def p_under(df):
    p = (df["DIFF"].loc[df['DIFF'] < 0].count() / df["DIFF"].count())*100
    return p

data = load_final()

# Calculate variables to populate filter inputs
min_asking = int(data["ASKING PRICE"].min())
max_asking = int(data["ASKING PRICE"].max())

min_date = datetime.date(data["SOLD DATE"].min())
max_date = datetime.date(data["SOLD DATE"].max())

cities = data["CITY"].drop_duplicates(keep='first')

hoods = data["LOCATION"].drop_duplicates(keep='first')

min_sf = int(data["SQUARE FEET"].min())
max_sf = int(data["SQUARE FEET"].max())

min_beds = int(data["BEDS"].min())
max_beds = int(data["BEDS"].max())

min_baths = float(data["BATHS"].min())
max_baths = float(data["BATHS"].max())

p_type = data["PROPERTY TYPE"].drop_duplicates(keep='first')

# APP
# filters in sidebar
with st.sidebar:
    # price range
    p_range = st.slider(
        'Select an asking price range', 
        min_value = 0, 
        max_value = max_asking, 
        value=[min_asking, max_asking]
        )
    
    # sold date
    d_range = st.slider(
        'Select a date range', 
        min_value = min_date, 
        max_value = max_date, 
        value=[min_date, max_date], 
        format="MM/DD/YY"
        )
    
    with st.expander("Advanced filters"):
        # city
        c_con = st.container()
        c_all = st.checkbox("Select all", value=True)
        if c_all:
            city = c_con.multiselect(
            'City', 
            cities,
            cities
            )
        else:
            city = c_con.multiselect(
                'City', 
                cities
                )
        
        # neighborhood
        n_con = st.container()
        n_all = st.checkbox("Select all", value=True, key=1)
        if n_all:
            neighborhood = n_con.multiselect(
                'Neighborhood', 
                hoods,
                hoods
                )
        else:
            neighborhood = n_con.multiselect(
                'Neighborhood', 
                hoods)
        
        # sq ft
        sqft = st.slider(
            'Sq. Feet', 
            min_value = min_sf,
            max_value = max_sf,
            value=[min_sf, max_sf]
            )
        
        # bed/bath
        beds = st.slider(
            'Beds', 
            min_value = min_beds,
            max_value = max_beds,
            value=[min_beds, max_beds]
            )
        
        
        baths = st.slider(
            'Baths', 
            min_value = min_baths,
            max_value = max_baths,
            value=[min_baths, max_baths]
            )
        
        # property type
        p_con = st.container()
        p_all = st.checkbox("Select all", value=True, key=2)
        if p_all:
            property_type = p_con.multiselect(
                'Property type',
                p_type,
                p_type 
                )
        else:
            property_type = p_con.multiselect(
                'Property type',
                p_type 
                )

# filter based on inputs - needs refactoring
df = data.loc[(data["ASKING PRICE"] > p_range[0]) & (data["ASKING PRICE"] < p_range[1])]
df = df.loc[(df["SOLD DATE"].dt.date > d_range[0]) & (df["SOLD DATE"].dt.date < d_range[1])]
df = df[df["CITY"].isin(city)]
df = df[df["LOCATION"].isin(neighborhood)]
df = df.loc[(df["SQUARE FEET"] > sqft[0]) & (df["SQUARE FEET"] < sqft[1])]
df = df.loc[(df["BEDS"] > beds[0]) & (df["BEDS"] < beds[1])]
df = df.loc[(df["BATHS"] > baths[0]) & (df["BATHS"] < baths[1])]
df = df[df["PROPERTY TYPE"].isin(property_type)]

# display summary stats
st.metric("Average amount over asking price", '${:,.0f}'.format(m_over(df)))
st.metric("Percent of properties over asking price", "{:.2f}%".format(p_over(df)))
st.metric("Percent of properties under asking price", "{:.2f}%".format(p_under(df)))

# Format data for map vizualization
map_data = df[["LATITUDE", "LONGITUDE", "DIFF", "ASKING PRICE", "SALE PRICE", "SOLD DATE"]]
map_data = map_data.rename(columns={"ASKING PRICE": "ASKING_PRICE", "SALE PRICE": "SALE_PRICE", "SOLD DATE": "SOLD_DATE"})
map_data["F_DIFF"] = map_data["DIFF"].apply(lambda d: f"{d:,}")
map_data["F_ASKING_PRICE"] = map_data["ASKING_PRICE"].apply(lambda d: f"{d:,}")
map_data["F_SALE_PRICE"] = map_data["SALE_PRICE"].apply(lambda d: f"{d:,}")

# Allow users to choose what value to render on the map
option = st.selectbox(
     'Select a field to display on the map',
     ('Asking Price', 'Sale Price', 'Price difference (over/under asking)'),
     index=2
     )

map_display_lookup = {
    "Asking Price": "ASKING_PRICE",
    "Sale Price": "SALE_PRICE",
    "Price difference (over/under asking)": "DIFF"
}

elevation = map_display_lookup[option]

col_layer = pdk.Layer(
        "ColumnLayer",
        map_data,
        get_position=["LONGITUDE", "LATITUDE"],
        get_elevation=[elevation],
        elevation_scale=.01,
        radius=100,
        elevation_range=[0, 1000],
        pickable=True,
        auto_highlight=True,
        extruded=True,
        get_fill_color=[255, 75, 75]
)

tooltip = {
    "html": "<b>Asking Price:</b> ${F_ASKING_PRICE}<br/><b>Sale Price:</b> ${F_SALE_PRICE}<br/><b>Difference:</b> ${F_DIFF}",
    "style": {"background": "black", "color": "white", "font-family": '"Source Sans Pro", sans-serif', "z-index": "10000"},
}

st.pydeck_chart(pdk.Deck(
    col_layer,
    tooltip=tooltip,
    # initial_view_state = view,
    initial_view_state = {
                "latitude": 47.6161,
                "longitude": -122.3964,
                "zoom": 10,
                "pitch": 40,
    },
    map_provider = "mapbox",
    map_style = 'mapbox://styles/mapbox/light-v9',
))