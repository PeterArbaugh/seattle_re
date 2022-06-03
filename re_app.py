from typing import final
import streamlit as st
import pandas as pd
import glob
import matplotlib.pyplot as plt
import seaborn as sns
import pydeck as pdk

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

# Format data for map vizualization
map_data = data[["LATITUDE", "LONGITUDE", "DIFF", "ASKING PRICE", "SALE PRICE"]]
map_data = map_data.rename(columns={"ASKING PRICE": "ASKING_PRICE", "SALE PRICE": "SALE_PRICE"})
# map_data["F_DIFF"] = show_thous(map_data["DIFF"])
map_data["F_DIFF"] = map_data["DIFF"].apply(lambda d: f"{d:,}")
map_data["F_ASKING_PRICE"] = map_data["ASKING_PRICE"].apply(lambda d: f"{d:,}")
map_data["F_SALE_PRICE"] = map_data["SALE_PRICE"].apply(lambda d: f"{d:,}")

# APP
# filters
# price range
p_range = st.slider('Select a price range', value=[300000, 1000000])
# city
city = st.multiselect('City', ['Option 1', 'Option 2'])
# neighborhood
neighborhood = st.multiselect('Neighborhood', ['Option 1', 'Option 2'])
# sq ft
sqft = st.slider('Sq. Feet', value=[500, 4000])
# bed/bath
beds = st.slider('Beds', value=[1, 5])
baths = st.slider('Baths', value=[1, 5])
# property type
property_type = st.multiselect('Property type', ['Option 1', 'Option 2'])
# display summary stats
st.metric("Average amount over asking price", '${:.0f}'.format(m_over(data)))
st.metric("Percent of properties over asking price", "{:.2f}%".format(p_over(data)))
st.metric("Percent of properties under asking price", "{:.2f}%".format(p_under(data)))

# view = pdk.data_utils.compute_view(final[["LONGITUDE", "LATITUDE"]])

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

data