import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import requests
import json

st.set_page_config(page_title="SignalArk", page_icon="📡", layout="wide")

@st.cache_data
def load_data():
    return pd.read_csv("dashboard_data.csv")

df = load_data()

# ---------- Sidebar ----------
st.sidebar.title("📡 SignalArk")
st.sidebar.caption("Pre-emptive connectivity blackout prediction — Temerloh, Pahang")

use_live = st.sidebar.toggle("Use live rainfall forecast", value=False)

@st.cache_data(ttl=1800)   # refresh at most every 30 min
def get_live_rain():
    r = requests.get("https://api.open-meteo.com/v1/forecast",
        params={"latitude": 3.45, "longitude": 102.42,
                "daily": "precipitation_sum", "forecast_days": 3,
                "timezone": "Asia/Singapore"}, timeout=10)
    d = r.json()["daily"]
    return float(sum(d["precipitation_sum"])), d["time"][0], d["time"][-1]

if use_live:
    try:
        rain, d1, d2 = get_live_rain()
        st.sidebar.success(f"Live forecast {d1} → {d2}: {rain:.0f} mm")
    except Exception:
        rain = 11.0
        st.sidebar.warning("API unavailable — fallback 11 mm")
else:
    rain = st.sidebar.slider("Scenario: 3-day rainfall (mm)", 0, 300, 11,
        help="Dec 2021 event ≈ 250 mm")

# ---------- Risk engine ----------
rain_factor = min(rain / 150, 1.0)
df["base_risk"] = pd.to_numeric(df["base_risk"], errors="coerce").fillna(0)
df["live_risk"] = (df["base_risk"] * (0.3 + 0.7 * rain_factor)).clip(0, 1)
df["risk_level"] = pd.cut(df["live_risk"], bins=[0, .3, .6, 1],
                          labels=["GREEN", "YELLOW", "RED"],
                          include_lowest=True)
df["risk_level"] = df["risk_level"].astype(str).replace("nan", "GREEN")
df["priority"] = df["live_risk"] * df["pop_served"]

n_red = int((df.risk_level == "RED").sum())
n_yel = int((df.risk_level == "YELLOW").sum())
pop_at_risk = df.loc[df.risk_level.isin(["RED","YELLOW"]), "pop_served"].sum()

# ---------- Header metrics ----------
UNIQUE_POP = json.load(open("unique_pop.json"))

def lookup_unique(rain):
    keys = sorted(int(k) for k in UNIQUE_POP)
    nearest = min(keys, key=lambda k: abs(k - rain))
    return UNIQUE_POP[str(nearest)]

unique_people = lookup_unique(rain)

st.title("SignalArk — Communities About to Go Dark")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("3-day rainfall", f"{rain:.0f} mm")
c2.metric("🔴 RED towers", n_red)
c3.metric("🟡 YELLOW towers", n_yel)
c4.metric("Connections at risk", f"{pop_at_risk:,.0f}",
          help="Tower-coverage relationships; towers overlap so this exceeds unique residents")
c5.metric("👥 Residents affected", f"{unique_people:,.0f}",
          help="Deduplicated population inside at-risk coverage areas")

# ---------- Map ----------
COLORS = {"RED": [220,40,40,200], "YELLOW": [240,190,30,200],
          "GREEN": [40,160,70,160]}
df["fill"] = df["risk_level"].map(lambda r: COLORS.get(r, COLORS["GREEN"]))
df["radius"] = 80 + df["pop_served"] / 80

layer = pdk.Layer("ScatterplotLayer", df,
    get_position=["lon", "lat"], get_fill_color="fill",
    get_radius="radius", pickable=True)
view = pdk.ViewState(latitude=3.45, longitude=102.40, zoom=9.3)

show_plan = st.sidebar.toggle("Show deployment plan (250 mm scenario)", value=False)
if show_plan:
    plan = pd.read_csv("deployment_plan.csv")
    gj = json.load(open("routes.geojson"))
    route_layer = pdk.Layer("GeoJsonLayer", gj, get_line_color=[30,80,220,220],
                            line_width_min_pixels=3)
    site_layer = pdk.Layer("ScatterplotLayer", plan.dropna(subset=['lat']),
        get_position=["lon","lat"], get_fill_color=[30,80,220,255],
        get_radius=400, pickable=True)
    st.pydeck_chart(pdk.Deck(layers=[layer, route_layer, site_layer],
        initial_view_state=view, map_style="road",
        tooltip={"text":"Rank {rank}\n{status}\nConnections: {connections}"}))
    st.subheader("🚚 Deployment order (by need)")
    st.dataframe(plan, use_container_width=True)
else:
    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view,
        map_style="road",
        tooltip={"text": "Site {site_id}\nRisk: {risk_level}\n"
                         "People: {pop_served}\nElev: {elev_m} m"}))

# ---------- Priority action list ----------
st.subheader("⚠️ Priority pre-positioning list")
top = df.sort_values("priority", ascending=False).head(10)
st.dataframe(
    top[["site_id","risk_level","live_risk","pop_served","elev_m","dist_river_m"]]
      .rename(columns={"live_risk":"risk_prob","pop_served":"people_served"})
      .style.format({"risk_prob":"{:.0%}","people_served":"{:,.0f}",
                     "elev_m":"{:.0f}","dist_river_m":"{:.0f}"}),
    use_container_width=True)

st.caption("Model: logistic regression on terrain (AUC 0.84 vs Dec 2021 floods). "
           "100% open data: OpenCelliD, Copernicus DEM, Sentinel-1, WorldPop, Open-Meteo.")
