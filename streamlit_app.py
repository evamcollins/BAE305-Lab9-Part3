import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import folium
from streamlit_folium import st_folium

# ----------------------------
# TITLE
# ----------------------------

st.title("Water Quality Analysis App")

# ----------------------------
# LOAD DATA
# ----------------------------

@st.cache_data
def load_data():
    stations = pd.read_csv("station.csv")
    results = pd.read_csv("narrowresult.csv")
    return stations, results

stations, df = load_data()

# ----------------------------
# COLUMN NAMES
# ----------------------------

site_col  = "MonitoringLocationIdentifier"
date_col  = "ActivityStartDate"
value_col = "ResultMeasureValue"
param_col = "CharacteristicName"

# ----------------------------
# CLEAN DATA
# ----------------------------

df[date_col] = pd.to_datetime(df[date_col], errors='coerce')

# Keep only numeric values
df = df[pd.to_numeric(df[value_col], errors='coerce').notnull()]
df[value_col] = df[value_col].astype(float)

# Remove invalid values
df = df.dropna(subset=[date_col, value_col])
df = df[df[value_col] > 0]

# Sort
df = df.sort_values(by=[site_col, param_col, date_col])

# ----------------------------
# FIXED INTERPOLATION FUNCTION
# ----------------------------

def interpolate_all(data):
    cleaned = []

    for (param, site), group in data.groupby([param_col, site_col]):
        group = group.copy()
        group = group.sort_values(by=date_col)

        # Set time index
        group = group.set_index(date_col)

        # 🔥 ONLY numeric column
        numeric = group[[value_col]]

        # Resample safely
        numeric = numeric.resample("D").mean()

        # Interpolate
        numeric[value_col] = numeric[value_col].interpolate(method='time')

        # Restore columns
        numeric[param_col] = param
        numeric[site_col] = site

        numeric = numeric.reset_index()

        cleaned.append(numeric)

    return pd.concat(cleaned)

df = interpolate_all(df)

# ----------------------------
# SIDEBAR INPUT
# ----------------------------

st.sidebar.header("Controls")

param_list = sorted(df[param_col].dropna().unique())

param1 = st.sidebar.selectbox("Select First Characteristic", param_list)
param2 = st.sidebar.selectbox("Select Second Characteristic (optional)", ["None"] + param_list)

# ----------------------------
# FILTER DATA
# ----------------------------

df1 = df[df[param_col] == param1].copy()

if param2 != "None":
    df2 = df[df[param_col] == param2].copy()
else:
    df2 = None

# Limit sites
top_sites = df1[site_col].value_counts().head(5).index
df1 = df1[df1[site_col].isin(top_sites)]

if df2 is not None:
    df2 = df2[df2[site_col].isin(top_sites)]

# ----------------------------
# MAP
# ----------------------------

st.subheader("Monitoring Station Map")

name_col = [col for col in stations.columns if "name" in col.lower()][0]
lat_col  = [col for col in stations.columns if "lat" in col.lower()][0]
lon_col  = [col for col in stations.columns if "lon" in col.lower()][0]

stations_clean = stations[[name_col, lat_col, lon_col]].dropna().drop_duplicates()

map_center = [stations_clean[lat_col].mean(), stations_clean[lon_col].mean()]
m = folium.Map(location=map_center, zoom_start=6)

for _, row in stations_clean.iterrows():
    folium.Marker(
        location=[row[lat_col], row[lon_col]],
        popup=row[name_col]
    ).add_to(m)

st_folium(m, width=700, height=500)

# ----------------------------
# PLOT
# ----------------------------

st.subheader("Water Quality Trends")

fig, ax1 = plt.subplots(figsize=(10,5))

# PARAM 1
for site in df1[site_col].unique():
    site_data = df1[df1[site_col] == site].sort_values(by=date_col)

    ax1.plot(
        site_data[date_col],
        site_data[value_col],
        label=f"{param1} - {site}"
    )

ax1.set_xlabel("Time")
ax1.set_ylabel(param1)

# PARAM 2
if df2 is not None:
    ax2 = ax1.twinx()

    for site in df2[site_col].unique():
        site_data = df2[df2[site_col] == site].sort_values(by=date_col)

        ax2.plot(
            site_data[date_col],
            site_data[value_col],
            linestyle='--',
            label=f"{param2} - {site}"
        )

    ax2.set_ylabel(param2)

# Legend
lines1, labels1 = ax1.get_legend_handles_labels()

if df2 is not None:
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=8)
else:
    ax1.legend(lines1, labels1, loc="upper left", fontsize=8)

plt.xticks(rotation=45)
plt.tight_layout()

st.pyplot(fig)

