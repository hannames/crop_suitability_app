<<<<<<< HEAD
# 🌾 Crop Suitability Analyser

Upload a parcel boundary (KML/KMZ/GeoJSON), select a crop, and get
suitability zones, statistics, and a PDF report — powered by Google Earth Engine.

---

## What it does

1. **Upload** a parcel boundary file (KML from Google Earth, KMZ, or GeoJSON)
2. **Select** a crop (Irrigated Rice, Aquaculture, Maize, Sorghum)
3. **Run** — the app scores every 30×30m pixel on six criteria via GEE
4. **Download** the best-N-ha polygon (GeoJSON), all zones (GeoJSON), and a PDF report

### Scoring criteria (example: irrigated rice)

| Criterion | Weight | Data source |
|---|---|---|
| Slope | 30% | SRTM 30m DEM |
| Distance to water | 25% | HydroSHEDS |
| Electricity proximity | 15% | VIIRS night-time lights |
| Terrain wetness | 13% | SRTM relative elevation |
| Clearing cost | 12% | Hansen GFC 2023 + ESA WorldCover |
| Flood risk | 5% | HydroSHEDS stream network |

---

## Setup — Local development

### 1. Clone and install

```bash
git clone https://github.com/your-username/crop-suitability-app.git
cd crop-suitability-app
pip install -r requirements.txt
```

### 2. Authenticate with Google Earth Engine

```bash
earthengine authenticate
```

This opens a browser. Sign in with your GEE-registered Google account.

### 3. Run the app

```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser.

---

## Deployment — Streamlit Cloud (free)

### 1. Push to GitHub

```bash
git init
git add .
git commit -m "Initial crop suitability app"
git remote add origin https://github.com/your-username/crop-suitability-app.git
git push -u origin main
```

### 2. Connect to Streamlit Cloud

1. Go to https://share.streamlit.io/
2. Click **New app** → connect your GitHub repo
3. Set main file: `app.py`
4. Click **Deploy**

### 3. Add GEE credentials (required for cloud)

For Streamlit Cloud, the app uses a GEE Service Account instead of interactive auth.

**Create a Service Account:**
1. Go to https://console.cloud.google.com/
2. Enable **Earth Engine API** for your project
3. Go to **IAM & Admin → Service Accounts** → Create
4. Download the JSON key file
5. Register the service account email at https://signup.earthengine.google.com/

**Add to Streamlit secrets:**
1. In Streamlit Cloud, open your app → **Settings → Secrets**
2. Add:

```toml
GEE_SERVICE_ACCOUNT = "your-sa@your-project.iam.gserviceaccount.com"
GEE_KEY_JSON = '''{ ... paste entire JSON key here ... }'''
```

See `.streamlit/secrets.toml.example` for the full format.

---

## Adding new crops

Edit `crop_config.py` — add a new entry to the `CROPS` dictionary with:
- `weights` — six scoring weights (must sum to 1.0)
- `slope_thresholds`, `water_thresholds`, `elec_thresholds`, `wetness_thresholds`
- `target_ha`, `min_viable_ha`

The app picks it up automatically with no other changes needed.

---

## Adding new file formats

Edit `kml_utils.py` — add a new branch in `parse_uploaded_file()` for the new extension,
and add the extension to the `type` list in `st.file_uploader()` in `app.py`.

Planned: Shapefile (.shp + .zip), DXF/DWG (via ezdxf), CSV of coordinates.

---

## Project structure

```
crop_suitability_app/
├── app.py                  # Main Streamlit UI
├── gee_analysis.py         # GEE analysis engine (scoring + vectorisation)
├── crop_config.py          # Crop scoring criteria and weights
├── kml_utils.py            # KML/KMZ/GeoJSON parser
├── report_generator.py     # PDF report builder (ReportLab)
├── requirements.txt        # Python dependencies
├── .streamlit/
│   └── secrets.toml.example  # GEE credentials template
└── README.md
```

---

## Limitations

- Analysis takes 1–3 minutes (GEE cloud computation)
- SRTM slope has ±6–10m vertical error — field survey required before engineering
- No soil data used — soil survey always required before investment
- Electricity scored via VIIRS brightness proxy — confirm with national utility
- Results are pre-screening only, not engineering design

---

## Roadmap

- [ ] Shapefile upload support
- [ ] DWG/DXF coordinate import
- [ ] Multi-parcel batch analysis
- [ ] CHIRPS rainfall layer in report
- [ ] JRC water seasonality scoring
- [ ] Soil data integration (SoilGrids)
- [ ] Export GEE script for custom editing
- [ ] User login + history of past analyses
=======
# crop_suitability_app
>>>>>>> e2e2f4ebb7552732830888c6de72db6b6de74986
