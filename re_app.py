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
    final = final.rename(columns={"PRICE_x": "ASKING PRICE", "PRICE_y": "SALE PRICE"})
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
map_data = data[["LATITUDE", "LONGITUDE", "DIFF", "ASKING PRICE", "SALE PRICE"]]

# APP

# display summary stats
st.metric("Average amount over asking price", '${:.0f}'.format(m_over(data)))
st.metric("Percent of properties over asking price", "{:.2f}%".format(p_over(data)))
st.metric("Percent of properties under asking price", "{:.2f}%".format(p_under(data)))

# view = pdk.data_utils.compute_view(final[["LONGITUDE", "LATITUDE"]])

col_layer = pdk.Layer(
        "ColumnLayer",
        map_data,
        get_position=["LONGITUDE", "LATITUDE"],
        get_elevation=["DIFF"],
        elevation_scale=.01,
        radius=100,
        elevation_range=[0, 1000],
        pickable=True,
        auto_highlight=True,
        extruded=True,
)

st.pydeck_chart(pdk.Deck(
    col_layer,
    tooltip=True,
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