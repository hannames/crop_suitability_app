"""
pages/2_🌿_Environment.py
Environmental impact assessment — carbon stock, forest cover, REDD+ credits.
"""

import json
import streamlit as st
import folium
from streamlit_folium import st_folium
from translations import T

st.set_page_config(page_title='Cropbility — Environment', page_icon='🌿', layout='wide')

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
  .green-box  { background:#EAF5EE; border-left:4px solid #2E7D46;
                border-radius:6px; padding:10px 14px; font-size:0.85rem; }
</style>
""", unsafe_allow_html=True)

lang = st.session_state.get('lang', 'en')

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    lang_choice = st.radio('Language / Langue',
        options=['🇬🇧 English', '🇫🇷 Français'],
        horizontal=True, label_visibility='collapsed', key='lang_env')
    lang = 'fr' if 'Français' in lang_choice else 'en'
    st.session_state['lang'] = lang
    st.markdown('---')
    st.markdown('**Parcel from Suitability page**')
    if st.session_state.get('parcel_info'):
        pi = st.session_state['parcel_info']
        st.success(f"✅ {pi['name']} — {pi['area_ha']:,.0f} ha")
    else:
        st.warning('No parcel loaded yet.\nGo to 🌾 Crop Suitability first.')

    run_env = st.button('🌿 Run Environmental Analysis',
        disabled=not bool(st.session_state.get('parcel_info')),
        use_container_width=True, type='primary')

# ── Header ────────────────────────────────────────────────────────────────────
if lang == 'fr':
    st.markdown('## 🌿 Impact environnemental')
    st.markdown('Évaluez l\'impact environnemental de votre parcelle : couverture forestière, stock de carbone et potentiel de crédits REDD+.')
else:
    st.markdown('## 🌿 Environmental Impact')
    st.markdown('Assess the environmental impact of your parcel: forest cover, carbon stock, and REDD+ carbon credit potential.')

if not st.session_state.get('parcel_info'):
    st.info('👈 Go to **🌾 Crop Suitability** first to define your parcel, then come back here.' if lang == 'en'
            else '👈 Allez d\'abord sur **🌾 Aptitude des cultures** pour définir votre parcelle.')
    st.stop()

if run_env:
    import ee
    from gee_analysis import initialise_gee

    with st.spinner('Running environmental analysis on Google Earth Engine...' if lang == 'en'
                    else 'Analyse environnementale en cours sur Google Earth Engine...'):
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
            area_ha = pi['area_ha']

            progress = st.progress(0, text='Loading forest data...')

            # Hansen forest cover 2025
            hansen     = ee.Image('UMD/hansen/global_forest_change_2025_v1_13')
            tc2000     = hansen.select('treecover2000')
            loss       = hansen.select('loss')
            lossYr     = hansen.select('lossyear')
            gain       = hansen.select('gain')
            currentTC  = tc2000.where(loss.eq(1), 0)
            pixelArea  = ee.Image.pixelArea().divide(10000)

            progress.progress(20, text='Calculating tree cover...')

            # Tree cover stats
            tc_stats = tc2000.reduceRegion(
                reducer=ee.Reducer.mean().combine(ee.Reducer.max(),'',True),
                geometry=aoi, scale=250, maxPixels=1e9, bestEffort=True
            ).getInfo()

            progress.progress(35, text='Calculating current forest cover...')

            curr_tc = currentTC.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=aoi, scale=250, maxPixels=1e9, bestEffort=True
            ).getInfo()

            progress.progress(50, text='Calculating forest loss...')

            # Total forest loss area
            loss_area = pixelArea.updateMask(loss).reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=aoi, scale=250, maxPixels=1e9, bestEffort=True
            ).getInfo()

            # Forest gain area
            gain_area = pixelArea.updateMask(gain).reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=aoi, scale=250, maxPixels=1e9, bestEffort=True
            ).getInfo()

            progress.progress(65, text='Computing carbon stock...')

            # Forest loss by year
            loss_by_year = pixelArea.addBands(lossYr).updateMask(loss).reduceRegion(
                reducer=ee.Reducer.sum().group(groupField=1, groupName='year'),
                geometry=aoi, scale=250, maxPixels=1e9, bestEffort=True
            ).getInfo()

            progress.progress(80, text='Estimating carbon credits...')

            # ESA WorldCover for land classification
            wc = ee.ImageCollection('ESA/WorldCover/v200').first().clip(aoi)
            lc_area = pixelArea.addBands(wc.rename('lc')).reduceRegion(
                reducer=ee.Reducer.sum().group(groupField=1, groupName='class'),
                geometry=aoi, scale=250, maxPixels=1e9, bestEffort=True
            ).getInfo()

            progress.progress(100, text='Complete!')

            # Carbon calculations
            mean_tc    = tc_stats.get('treecover2000_mean', 0) or 0
            curr_tc_val = curr_tc.get('treecover2000', 0) or 0
            loss_ha    = loss_area.get('area', 0) or 0
            gain_ha    = gain_area.get('area', 0) or 0

            # Biomass estimate: 49 tC/ha × mean tree cover fraction
            # Based on Saatchi et al. 2011 for Sudano-Guinean savanna
            BIOMASS_FACTOR = 49  # tC/ha at 100% cover
            carbon_stock   = (curr_tc_val / 100) * BIOMASS_FACTOR * area_ha
            co2_stock      = carbon_stock * 3.67
            carbon_lost    = (mean_tc / 100) * BIOMASS_FACTOR * loss_ha
            co2_lost       = carbon_lost * 3.67

            # REDD+ credit value
            redd_low  = co2_stock * 5   / 1e6  # USD million at $5/tCO2
            redd_high = co2_stock * 15  / 1e6  # USD million at $15/tCO2

            st.session_state['env_results'] = {
                'mean_tc': mean_tc, 'curr_tc': curr_tc_val,
                'loss_ha': loss_ha, 'gain_ha': gain_ha,
                'carbon_stock': carbon_stock, 'co2_stock': co2_stock,
                'carbon_lost': carbon_lost, 'co2_lost': co2_lost,
                'redd_low': redd_low, 'redd_high': redd_high,
                'loss_by_year': loss_by_year, 'lc_area': lc_area,
                'area_ha': area_ha
            }
            progress.empty()
            st.rerun()

        except Exception as e:
            st.error(f'Analysis failed: {e}')

# ── Show results ──────────────────────────────────────────────────────────────
if st.session_state.get('env_results'):
    r  = st.session_state['env_results']
    pi = st.session_state['parcel_info']

    st.markdown('---')
    st.markdown('### 🌳 Forest Cover' if lang == 'en' else '### 🌳 Couverture forestière')

    c1, c2, c3, c4 = st.columns(4)
    metrics = [
        (f"{r['mean_tc']:.1f}%",  'Tree cover 2000 (baseline)' if lang=='en' else 'Couvert 2000 (référence)'),
        (f"{r['curr_tc']:.1f}%",  'Current tree cover (est.)' if lang=='en' else 'Couvert actuel (est.)'),
        (f"{r['loss_ha']:,.0f} ha",'Forest loss 2001–2025' if lang=='en' else 'Perte forêt 2001–2025'),
        (f"{r['gain_ha']:,.0f} ha",'Forest gain 2001–2025' if lang=='en' else 'Gain forêt 2001–2025'),
    ]
    for col, (val, lbl) in zip([c1,c2,c3,c4], metrics):
        with col:
            st.markdown(f'<div class="metric-box"><div class="metric-val">{val}</div>'
                        f'<div class="metric-lbl">{lbl}</div></div>', unsafe_allow_html=True)

    st.markdown('---')
    st.markdown('### 💨 Carbon Stock' if lang == 'en' else '### 💨 Stock de carbone')

    c1, c2, c3 = st.columns(3)
    carbon_metrics = [
        (f"{r['carbon_stock']/1000:,.0f} kt C", 'Standing carbon stock' if lang=='en' else 'Stock de carbone'),
        (f"{r['co2_stock']/1000:,.0f} kt CO₂e", 'CO₂ equivalent (if cleared)' if lang=='en' else 'Équivalent CO₂ (si défriché)'),
        (f"{r['carbon_lost']:,.0f} t C", 'Carbon lost (2001–2025)' if lang=='en' else 'Carbone perdu (2001–2025)'),
    ]
    for col, (val, lbl) in zip([c1,c2,c3], carbon_metrics):
        with col:
            st.markdown(f'<div class="metric-box"><div class="metric-val">{val}</div>'
                        f'<div class="metric-lbl">{lbl}</div></div>', unsafe_allow_html=True)

    st.markdown('---')
    st.markdown('### 💰 REDD+ Carbon Credit Potential' if lang == 'en'
                else '### 💰 Potentiel de crédits carbone REDD+')

    st.markdown(
        f'<div class="green-box">'
        f'{"Indicative REDD+ value of standing carbon stock:" if lang=="en" else "Valeur indicative REDD+ du stock de carbone debout :"}<br>'
        f'<b>USD {r["redd_low"]:.1f}M – {r["redd_high"]:.1f}M</b> '
        f'{"(at USD 5–15/tCO₂e on voluntary carbon markets)" if lang=="en" else "(à 5–15 USD/tCO₂e sur les marchés volontaires)"}'
        f'</div>', unsafe_allow_html=True
    )

    st.markdown('')

    if lang == 'en':
        st.markdown('''**What this means:** If the woodland is not fully cleared and a portion is
        protected under a REDD+ scheme, the standing carbon qualifies for voluntary carbon credits.
        This value is an estimate based on average biomass factors for the Sudano-Guinean savanna
        ecoregion (~49 tC/ha at full cover). A formal carbon inventory would refine this figure.''')
    else:
        st.markdown('''**Ce que cela signifie :** Si la forêt n\'est pas entièrement défrichée et qu\'une partie
        est protégée dans le cadre d\'un projet REDD+, le carbone debout est éligible aux crédits carbone volontaires.
        Cette valeur est une estimation basée sur des facteurs de biomasse moyens pour l\'écozone soudano-guinéenne
        (~49 tC/ha à couvert complet). Un inventaire carbone formel affinerait ce chiffre.''')

    st.markdown('<div class="warn-box">'
                + ('⚠️ <b>Disclaimer:</b> Carbon estimates use regional biomass factors '
                   '(Saatchi et al. 2011, IPCC Tier 1). An on-site carbon inventory '
                   'is required for any formal REDD+ project registration.'
                   if lang == 'en' else
                   '⚠️ <b>Avertissement :</b> Les estimations de carbone utilisent des facteurs de biomasse régionaux '
                   '(Saatchi et al. 2011, GIEC Niveau 1). Un inventaire carbone sur site est requis pour '
                   'toute inscription formelle à un projet REDD+.')
                + '</div>', unsafe_allow_html=True)

    # Download report
    st.markdown('---')
    report_lines = [
        f"ENVIRONMENTAL IMPACT REPORT — {pi['name']}",
        f"Area: {pi['area_ha']:,.0f} ha | Date: {__import__('datetime').datetime.now().strftime('%d/%m/%Y')}",
        "",
        "FOREST COVER",
        f"  Baseline tree cover (2000): {r['mean_tc']:.1f}%",
        f"  Current tree cover (est.):  {r['curr_tc']:.1f}%",
        f"  Forest loss 2001-2025:      {r['loss_ha']:,.0f} ha",
        f"  Forest gain 2001-2025:      {r['gain_ha']:,.0f} ha",
        "",
        "CARBON STOCK",
        f"  Standing carbon:  {r['carbon_stock']/1000:,.1f} kt C",
        f"  CO2 equivalent:   {r['co2_stock']/1000:,.1f} kt CO2e",
        f"  Carbon lost:      {r['carbon_lost']:,.0f} t C",
        "",
        "REDD+ CREDIT POTENTIAL",
        f"  Low estimate (USD 5/tCO2e):  USD {r['redd_low']:.2f}M",
        f"  High estimate (USD 15/tCO2e): USD {r['redd_high']:.2f}M",
        "",
        "DATA SOURCES",
        "  Hansen Global Forest Change 2025 v1.13 (UMD/GEE)",
        "  ESA WorldCover 2021 v200",
        "  Biomass factor: Saatchi et al. 2011 / IPCC Tier 1",
        "",
        "DISCLAIMER: Pre-screening estimate only. On-site carbon inventory required for formal REDD+ registration.",
    ]
    st.download_button(
        label='📄 Download Environmental Report (TXT)' if lang == 'en' else '📄 Télécharger le rapport environnemental (TXT)',
        data='\n'.join(report_lines),
        file_name=f'{pi["name"]}_environmental_report.txt',
        mime='text/plain',
        use_container_width=True
    )
