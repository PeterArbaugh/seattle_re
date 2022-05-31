import streamlit as st
import pandas as pd
import glob
import matplotlib.pyplot as plt
import seaborn as sns

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
    reduced['UPDATED'] = reduced['UPDATED'].str.slice(start=7, stop=17)
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

data = load_final()
data
