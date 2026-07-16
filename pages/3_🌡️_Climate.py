"""
pages/3_🌡️_Climate.py
Climate impact — historical trends + projections 5/10/15/20 years (NEX-GDDP-CMIP6 + CHIRPS).
"""

import json
import streamlit as st
from streamlit_folium import st_folium

st.set_page_config(page_title='Cropbility — Climate', page_icon='🌡️', layout='wide')

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
  html, body, [class*="css"], p, h1, h2, h3, h4, label, div, button {
    font-family: 'Inter', sans-serif !important; letter-spacing: -0.01em;
  }
  .metric-box { background:#EAF5EE; border-radius:8px; padding:12px 16px;
                border-left:4px solid #2E7D46; margin-bottom:8px; }
  .metric-val { font-size:1.4rem; font-weight:700; color:#1A5C30; }
  .metric-lbl { font-size:0.8rem; color:#555; }
  .warn-box   { background:#FFF3CD; border-left:4px solid #E65100;
                border-radius:6px; padding:10px 14px; font-size:0.85rem; }
  .climate-card { background:#F0F7FF; border:1px solid #B8D4F0; border-radius:10px;
                  padding:1rem 1.2rem; text-align:center; }
  .climate-card h3 { color:#1F4E79; font-size:1.4rem; margin:4px 0; }
  .climate-card p  { color:#555; font-size:0.82rem; margin:0; }
</style>
""", unsafe_allow_html=True)

lang = st.session_state.get('lang', 'en')

with st.sidebar:
    lang_choice = st.radio('Language / Langue',
        options=['🇬🇧 English', '🇫🇷 Français'],
        horizontal=True, label_visibility='collapsed', key='lang_climate')
    lang = 'fr' if 'Français' in lang_choice else 'en'
    st.session_state['lang'] = lang
    st.markdown('---')

    horizon = st.selectbox(
        'Projection horizon' if lang == 'en' else 'Horizon de projection',
        options=['5 years / 5 ans', '10 years / 10 ans', '15 years / 15 ans', '20 years / 20 ans'],
        index=1
    )
    years_ahead = int(horizon.split()[0])

    scenario = st.selectbox(
        'Climate scenario' if lang == 'en' else 'Scénario climatique',
        options=['SSP2-4.5 (moderate)', 'SSP5-8.5 (high emissions)'],
        index=0
    )
    ssp = 'ssp245' if '4.5' in scenario else 'ssp585'

    st.markdown('---')
    if st.session_state.get('parcel_info'):
        pi = st.session_state['parcel_info']
        st.success(f"✅ {pi['name']} — {pi['area_ha']:,.0f} ha")
    else:
        st.warning('No parcel loaded.\nGo to 🌾 Crop Suitability first.')

    run_climate = st.button(
        '🌡️ Run Climate Analysis' if lang == 'en' else '🌡️ Lancer l\'analyse climatique',
        disabled=not bool(st.session_state.get('parcel_info')),
        use_container_width=True, type='primary'
    )

# ── Header ────────────────────────────────────────────────────────────────────
if lang == 'fr':
    st.markdown('## 🌡️ Impact climatique')
    st.markdown(f'Projections climatiques pour votre parcelle — horizon **{years_ahead} ans** | Scénario **{scenario}**')
else:
    st.markdown('## 🌡️ Climate Impact')
    st.markdown(f'Climate projections for your parcel — **{years_ahead}-year** horizon | Scenario **{scenario}**')

if not st.session_state.get('parcel_info'):
    st.info('👈 Go to **🌾 Crop Suitability** first to define your parcel.' if lang == 'en'
            else '👈 Allez d\'abord sur **🌾 Aptitude des cultures** pour définir votre parcelle.')
    st.stop()

if run_climate:
    import ee
    from gee_analysis import initialise_gee
    from datetime import datetime

    with st.spinner('Running climate analysis on Google Earth Engine...' if lang == 'en'
                    else 'Analyse climatique en cours...'):
        try:
            try:
                sa  = st.secrets.get('GEE_SERVICE_ACCOUNT', None)
                key = st.secrets.get('GEE_KEY_JSON', None)
            except Exception:
                sa, key = None, None
            if sa and key:
                key_dict = json.loads(key) if isinstance(key, str) else key
                initialise_gee(service_account=sa, key_json=key_dict)
            else:
                initialise_gee()

            pi     = st.session_state['parcel_info']
            coords = pi['coordinates'][0]
            aoi    = ee.Geometry.Polygon([coords])
            now_yr = datetime.now().year
            fut_yr = now_yr + years_ahead

            progress = st.progress(0, text='Loading historical rainfall...')

            # ── CHIRPS historical rainfall (1991-2020 baseline) ────────────────
            chirps_hist = (ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY')
                .filterBounds(aoi)
                .filterDate('1991-01-01', '2020-12-31')
                .select('precipitation'))

            annual_hist = chirps_hist.sum().divide(30).reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=aoi, scale=5500, maxPixels=1e9, bestEffort=True
            ).getInfo()

            progress.progress(20, text='Computing monthly rainfall pattern...')

            # Monthly average (seasonal cycle)
            monthly_rain = {}
            for m in range(1, 13):
                val = (chirps_hist
                    .filter(ee.Filter.calendarRange(m, m, 'month'))
                    .mean().multiply(30.44)
                    .reduceRegion(reducer=ee.Reducer.mean(),
                                  geometry=aoi, scale=5500, maxPixels=1e9, bestEffort=True)
                    .getInfo())
                monthly_rain[m] = round(val.get('precipitation', 0) or 0, 1)

            progress.progress(40, text='Loading climate projections (NEX-GDDP-CMIP6)...')

            # ── NEX-GDDP-CMIP6 future projections ────────────────────────────
            cmip6 = (ee.ImageCollection('NASA/GDDP-CMIP6')
                .filterBounds(aoi)
                .filter(ee.Filter.eq('scenario', ssp))
                .filter(ee.Filter.eq('model', 'ACCESS-CM2'))
                .filterDate(f'{fut_yr-2}-01-01', f'{fut_yr+2}-12-31'))

            # Future annual rainfall
            pr_future = (cmip6.select('pr')
                .mean()
                .multiply(86400 * 365)  # kg/m2/s → mm/year
                .reduceRegion(reducer=ee.Reducer.mean(),
                              geometry=aoi, scale=25000, maxPixels=1e9, bestEffort=True)
                .getInfo())

            progress.progress(60, text='Computing temperature projections...')

            # Future temperature
            tasmax_future = (cmip6.select('tasmax')
                .mean()
                .subtract(273.15)  # K → °C
                .reduceRegion(reducer=ee.Reducer.mean(),
                              geometry=aoi, scale=25000, maxPixels=1e9, bestEffort=True)
                .getInfo())

            tasmin_future = (cmip6.select('tasmin')
                .mean()
                .subtract(273.15)
                .reduceRegion(reducer=ee.Reducer.mean(),
                              geometry=aoi, scale=25000, maxPixels=1e9, bestEffort=True)
                .getInfo())

            progress.progress(80, text='Computing baseline temperature...')

            # Baseline temperature (ERA5)
            era5_temp = (ee.ImageCollection('ECMWF/ERA5_LAND/MONTHLY_AGGR')
                .filterBounds(aoi)
                .filterDate('1991-01-01', '2020-12-31')
                .select('temperature_2m')
                .mean()
                .subtract(273.15)
                .reduceRegion(reducer=ee.Reducer.mean(),
                              geometry=aoi, scale=11132, maxPixels=1e9, bestEffort=True)
                .getInfo())

            progress.progress(100, text='Complete!')

            # Extract values
            hist_rain_yr = annual_hist.get('precipitation', 0) or 0
            fut_rain_yr  = pr_future.get('pr', 0) or 0
            hist_temp    = era5_temp.get('temperature_2m', 25) or 25
            fut_tmax     = tasmax_future.get('tasmax', 35) or 35
            fut_tmin     = tasmin_future.get('tasmin', 20) or 20
            fut_tmean    = (fut_tmax + fut_tmin) / 2

            rain_change  = fut_rain_yr - hist_rain_yr
            rain_pct     = (rain_change / hist_rain_yr * 100) if hist_rain_yr > 0 else 0
            temp_change  = fut_tmean - hist_temp

            st.session_state['climate_results'] = {
                'hist_rain_yr': hist_rain_yr,
                'fut_rain_yr':  fut_rain_yr,
                'rain_change':  rain_change,
                'rain_pct':     rain_pct,
                'hist_temp':    hist_temp,
                'fut_tmean':    fut_tmean,
                'temp_change':  temp_change,
                'monthly_rain': monthly_rain,
                'years_ahead':  years_ahead,
                'scenario':     scenario,
                'fut_yr':       fut_yr,
            }
            progress.empty()
            st.rerun()

        except Exception as e:
            st.error(f'Climate analysis failed: {e}')

# ── Show results ──────────────────────────────────────────────────────────────
if st.session_state.get('climate_results'):
    r  = st.session_state['climate_results']
    pi = st.session_state['parcel_info']

    st.markdown('---')

    # Horizon cards
    horizons = [5, 10, 15, 20]
    cols = st.columns(4)
    for col, h in zip(cols, horizons):
        scale = h / r['years_ahead']
        proj_rain = r['hist_rain_yr'] + r['rain_change'] * scale
        proj_temp = r['hist_temp'] + r['temp_change'] * scale
        rain_d    = proj_rain - r['hist_rain_yr']
        temp_d    = proj_temp - r['hist_temp']
        rain_col  = '#C62828' if rain_d < -50 else ('#F57F17' if rain_d < 0 else '#2E7D46')
        temp_col  = '#C62828' if temp_d > 2 else ('#F57F17' if temp_d > 1 else '#1F4E79')
        with col:
            st.markdown(
                f'<div class="climate-card">'
                f'<p style="font-weight:600;font-size:0.9rem;color:#1F4E79;">+{h} {"years" if lang=="en" else "ans"}</p>'
                f'<h3 style="color:{rain_col};">{proj_rain:,.0f} mm</h3>'
                f'<p>{"Rainfall/year" if lang=="en" else "Pluie/an"} '
                f'<span style="color:{rain_col};">({rain_d:+.0f} mm)</span></p>'
                f'<h3 style="color:{temp_col};">{proj_temp:.1f}°C</h3>'
                f'<p>{"Mean temp." if lang=="en" else "Temp. moy."} '
                f'<span style="color:{temp_col};">({temp_d:+.1f}°C)</span></p>'
                f'</div>',
                unsafe_allow_html=True
            )

    st.markdown('---')
    st.markdown('### 📊 Seasonal Rainfall Pattern (1991–2020 baseline)' if lang == 'en'
                else '### 📊 Répartition mensuelle des pluies (référence 1991–2020)')

    # Bar chart using streamlit's native chart
    import pandas as pd
    month_names_en = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    month_names_fr = ['Jan','Fév','Mar','Avr','Mai','Juin','Jul','Août','Sep','Oct','Nov','Déc']
    month_names = month_names_fr if lang == 'fr' else month_names_en

    df_rain = pd.DataFrame({
        'Month' if lang == 'en' else 'Mois': month_names,
        'Rainfall (mm)' if lang == 'en' else 'Pluies (mm)': [r['monthly_rain'].get(m, 0) for m in range(1,13)]
    }).set_index('Month' if lang == 'en' else 'Mois')

    st.bar_chart(df_rain, color='#1A90C8')

    st.markdown('---')
    st.markdown('### 🌾 Implications for rice cultivation' if lang == 'en'
                else '### 🌾 Implications pour la riziculture')

    temp_ok   = r['fut_tmean'] < 35
    rain_ok   = r['fut_rain_yr'] > 800
    dry_months = sum(1 for m in r['monthly_rain'].values() if m < 50)

    implications = []
    if lang == 'en':
        implications.append(('✅' if temp_ok else '⚠️',
            f"Mean temperature in {r['fut_yr']}: **{r['fut_tmean']:.1f}°C** "
            f"({'within' if temp_ok else 'above'} rice optimal range of 22–33°C)"))
        implications.append(('✅' if rain_ok else '⚠️',
            f"Annual rainfall: **{r['fut_rain_yr']:,.0f} mm** "
            f"({'sufficient' if rain_ok else 'below minimum'} for Season 1 rain-fed rice)"))
        implications.append(('ℹ️',
            f"**{dry_months} months/year** receive <50mm — irrigation required for Season 2"))
        implications.append(('📈' if r['temp_change'] > 0 else '📉',
            f"Temperature change by {r['fut_yr']}: **{r['temp_change']:+.1f}°C** "
            f"({'increases evapotranspiration demand' if r['temp_change'] > 0 else 'reduces heat stress'})"))
    else:
        implications.append(('✅' if temp_ok else '⚠️',
            f"Température moyenne en {r['fut_yr']}: **{r['fut_tmean']:.1f}°C** "
            f"({'dans la' if temp_ok else 'au-dessus de la'} plage optimale du riz 22–33°C)"))
        implications.append(('✅' if rain_ok else '⚠️',
            f"Pluviométrie annuelle: **{r['fut_rain_yr']:,.0f} mm** "
            f"({'suffisant' if rain_ok else 'inférieur au minimum'} pour le riz pluvial Saison 1)"))
        implications.append(('ℹ️',
            f"**{dry_months} mois/an** reçoivent <50mm — irrigation requise pour la Saison 2"))
        implications.append(('📈' if r['temp_change'] > 0 else '📉',
            f"Changement de température d\'ici {r['fut_yr']}: **{r['temp_change']:+.1f}°C** "
            f"({'augmente la demande en évapotranspiration' if r['temp_change'] > 0 else 'réduit le stress thermique'})"))

    for icon, text in implications:
        st.markdown(f'{icon} {text}')

    st.markdown('')
    st.markdown(
        '<div class="warn-box">⚠️ '
        + ('Climate projections use the NASA NEX-GDDP-CMIP6 dataset (ACCESS-CM2 model). '
           'These are ensemble projections with inherent uncertainty. '
           'Use as indicative trends, not precise forecasts.'
           if lang == 'en' else
           'Les projections climatiques utilisent le jeu de données NASA NEX-GDDP-CMIP6 (modèle ACCESS-CM2). '
           'Ce sont des projections d\'ensemble avec une incertitude inhérente. '
           'À utiliser comme tendances indicatives, non comme prévisions précises.')
        + '</div>', unsafe_allow_html=True
    )

    # Download
    st.markdown('---')
    from datetime import datetime
    report_lines = [
        f"CLIMATE IMPACT REPORT — {pi['name']}",
        f"Area: {pi['area_ha']:,.0f} ha | Scenario: {r['scenario']} | Horizon: +{r['years_ahead']} years",
        f"Generated: {datetime.now().strftime('%d/%m/%Y')}",
        "",
        "HISTORICAL BASELINE (1991-2020)",
        f"  Annual rainfall:    {r['hist_rain_yr']:,.0f} mm/year",
        f"  Mean temperature:   {r['hist_temp']:.1f}°C",
        "",
        f"PROJECTIONS FOR {r['fut_yr']} ({r['scenario']})",
        f"  Annual rainfall:    {r['fut_rain_yr']:,.0f} mm/year ({r['rain_change']:+.0f} mm, {r['rain_pct']:+.1f}%)",
        f"  Mean temperature:   {r['fut_tmean']:.1f}°C ({r['temp_change']:+.1f}°C change)",
        "",
        "MONTHLY RAINFALL BASELINE (mm/month)",
    ] + [f"  {m:02d}: {r['monthly_rain'].get(m,0):.1f} mm" for m in range(1,13)] + [
        "",
        "DATA SOURCES",
        "  CHIRPS Daily (1991-2020 baseline)",
        "  NASA NEX-GDDP-CMIP6 — ACCESS-CM2",
        "  ECMWF ERA5-Land (temperature baseline)",
        "",
        "DISCLAIMER: Climate projections are model-based estimates with inherent uncertainty.",
    ]
    st.download_button(
        label='📄 Download Climate Report (TXT)' if lang == 'en' else '📄 Télécharger le rapport climatique (TXT)',
        data='\n'.join(report_lines),
        file_name=f'{pi["name"]}_climate_report.txt',
        mime='text/plain',
        use_container_width=True
    )
