# 📡 SignalArk

**Pre-Emptive Connectivity Blackout Prediction for Flood-Prone Communities**

*"Know which communities will go dark — before the flood arrives."*

Built for the **ASEAN GeoAI Fusion Bootcamp & Hackathon 2026** (organised by MCMC — Malaysian Communications and Multimedia Commission).

---

## What it does

When monsoon floods hit Malaysia, cell towers fail and communities lose connectivity exactly when they need flood warnings and rescue calls most. Today, outages are only detected **after** they happen.

SignalArk fuses open cell-tower data, satellite flood mapping, terrain elevation, and rainfall forecasts to **predict and rank which towers — and the communities they serve — will lose connectivity before a flood event**, so regulators (MCMC), disaster agencies (NADMA), and telcos can pre-position backup generators and portable base stations at the right sites, before the blackout happens.

The prototype is trained and demonstrated on **Temerloh–Mentakab, Pahang** (Sungai Pahang basin), validated against the December 2021 Malaysian floods, and achieves an **AUC of 0.84** using a terrain-only, leakage-free logistic regression model.

## Live dashboard

The app is a Streamlit dashboard with three main views:

- **Blackout Risk Map** — every tower site colour-coded 🔴 RED / 🟡 YELLOW / 🟢 GREEN by live blackout risk, sized by population served.
- **Scenario Mode** — a rainfall slider (or a live 3-day Open-Meteo forecast toggle) recomputes risk in real time. Dragging the slider to the Dec 2021 flood level (245 mm) reproduces the historical event.
- **Deployment Plan** — toggle to overlay the pre-positioning plan: ranked staging sites, safe road routes from a flood-safe depot, and which zones are reachable vs. cut off and must be pre-positioned *before* the flood hits.
- **Priority Action List** — a ranked table of the top 10 sites to act on first, by risk × population served.

## How the risk engine works

1. Each tower site has a **base risk** (0–1), pre-computed offline from terrain (elevation, distance to river) and historical flood exposure (Sentinel-1 radar, Dec 2021 ground truth).
2. The dashboard scales base risk live against the selected **3-day rainfall total**, blending a fixed baseline (30%) with a rainfall-driven component (70%) — `live_risk = base_risk × (0.3 + 0.7 × min(rain / 300, 1))`.
3. Sites are bucketed into GREEN / YELLOW / RED bands, and a **priority score** (`live_risk × population served`) ranks which sites need attention first.
4. At preset rainfall bands, a precomputed deployment plan (`plans_by_rain.json`) and safe road routes (`routes_by_rain.json`) show where to stage equipment and how to reach each site from the depot without crossing flooded roads.

## Data & model pipeline

Everything runs on **100% free, open data** — no telco internal data, no personal data:

| Layer | Source | Use |
|---|---|---|
| Cell tower locations | OpenCelliD (MCC 502, Malaysia) | 953 cell records clustered into ~660 physical tower sites |
| Elevation / terrain | Copernicus DEM GLO-30 | Primary flood-risk predictor |
| Surface water / flood extent | JRC Global Surface Water, Sentinel-1 SAR (Google Earth Engine) | Distance-to-river feature; Dec 2021 flood ground truth (28 confirmed flooded sites) |
| Roads | OpenStreetMap | Road network for routing (77,439 nodes, 156,867 edges) |
| Population | WorldPop | Population served per tower, deduplicated residents at risk |
| Rainfall forecast | Open-Meteo API (free, no key) | Live 3-day rainfall scenario |

The offline pipeline (Google Earth Engine → Google Colab, using pandas, numpy, scikit-learn, osmnx, networkx) produces the static files this app reads at runtime — the app itself does no heavy geospatial processing, so it runs comfortably on Streamlit Community Cloud's free tier.

## Project structure

```
signalark-main/
├── app.py                 # Streamlit dashboard (entry point)
├── dashboard_data.csv     # Per-tower site data: location, elevation, risk, population served
├── plans_by_rain.json     # Precomputed deployment plans, keyed by rainfall band (mm)
├── routes_by_rain.json    # Safe road routes to each deployment site, as GeoJSON, by rainfall band
├── unique_pop.json        # Deduplicated residents-at-risk lookup, by rainfall band
└── requirements           # Python dependencies
```

## Running locally

```bash
# from this folder
pip install -r requirements
streamlit run app.py
```

The app will open at `http://localhost:8501`. Use the sidebar to switch between a manual rainfall scenario slider and a live Open-Meteo forecast, and toggle the deployment plan overlay.

## Known limitations

- **Tower data completeness**: OpenCelliD is crowdsourced and road-biased; some records may be for decommissioned towers. Site clustering mitigates this; operator data would replace it at pilot stage.
- **Overlapping coverage**: per-tower population figures are valid for ranking but not summable — aggregate "connections at risk" figures can exceed the deduplicated resident count because towers overlap.
- **Single validation event**: the model is calibrated on one flood (Dec 2021). Transfer testing on Selangor (urban) and Kelantan (rural) is planned to confirm generalisation.
- **Depth estimation is approximate**: terrain-derived, not hydraulic — treat passability as indicative triage, not engineering certainty.
- **Deployment plan is precomputed** at fixed rainfall bands rather than recomputed live for every slider position.

## Roadmap

1. Hackathon prototype (this build) — one district, 5-day build.
2. Pilot with MCMC/NADMA over one monsoon season.
3. Incorporate national and telco data.
4. Scale to ASEAN (typhoons in the Philippines/Vietnam, Mekong floods).
5. Continuous improvement.

## Stakeholders

- **MCMC** — telecom regulator; targets network resilience and rural-connectivity funding using the risk map.
- **NADMA** — national disaster agency; uses the "communities about to go dark" list for early warning and evacuation priority.
- **Telcos** (Maxis, CelcomDigi, TM, U Mobile) — pre-position generators and portable base stations at high-risk sites.
- **Communities, schools & clinics** — stay connected during floods.

## Ethics

No personal data or call-detail records are used anywhere. The model is fully explainable (logistic regression on terrain features, no black box) and is designed to prioritise vulnerable rural communities. Aligned with UN SDGs 9, 11, 13, and 17.

