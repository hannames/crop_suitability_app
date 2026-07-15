"""
app.py
Main Streamlit application for crop suitability analysis.
Supports: file upload (KML/KMZ/GeoJSON) OR drawing on map.
"""

import json
import streamlit as st
import folium
from folium.plugins import Draw, Geocoder, MiniMap, LocateControl
from streamlit_folium import st_folium

from kml_utils import parse_uploaded_file
from gee_analysis import initialise_gee, run_analysis
from report_generator import generate_report
from crop_config import CROPS
from translations import T

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title='Crop Suitability Analyser',
    page_icon='🌾',
    layout='wide',
    initial_sidebar_state='expanded',
)

# ── Inline CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

  html, body, [class*="css"], .stMarkdown, p, h1, h2, h3, h4, label, div, button, input, select {
    font-family: 'Inter', sans-serif !important;
    letter-spacing: -0.01em;
  }

  .main-title { font-size: 2rem; font-weight: 700; color: #1A5C30; margin-bottom: 0;
                font-family: 'Inter', sans-serif !important; letter-spacing: -0.02em; }
  .sub-title  { font-size: 1rem; color: #555; margin-bottom: 1.5rem;
                font-family: 'Inter', sans-serif !important; font-weight: 400; }
  .metric-box { background: #EAF5EE; border-radius: 8px; padding: 12px 16px;
                border-left: 4px solid #2E7D46; margin-bottom: 8px; }
  .metric-val { font-size: 1.4rem; font-weight: 700; color: #1A5C30; }
  .metric-lbl { font-size: 0.8rem; color: #555; }
  .warn-box   { background: #FFF3CD; border-left: 4px solid #E65100;
                border-radius: 6px; padding: 10px 14px; font-size: 0.85rem; }
  .draw-tip   { background: #E8F1FB; border-left: 4px solid #1F4E79;
                border-radius: 6px; padding: 10px 14px; font-size: 0.85rem; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# ── GEE init ──────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner='Connecting to Google Earth Engine...')
def init_gee():
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
        return True
    except Exception as e:
        return str(e)

gee_status = init_gee()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('### 🌾 Crop Suitability Analyser')

    # Language selector
    lang_choice = st.radio(
        'Language / Langue',
        options=['🇬🇧 English', '🇫🇷 Français'],
        horizontal=True, label_visibility='collapsed')
    lang = 'fr' if 'Français' in lang_choice else 'en'
    st.session_state['lang'] = lang
    st.markdown('---')

    if gee_status is True:
        st.success(T(lang, 'gee_ok'))
    else:
        st.error(f"{T(lang, 'gee_err')}: {gee_status}")
        st.info(T(lang, 'gee_hint'))

    st.markdown('---')

    # ── Input method toggle ───────────────────────────────────────────────────
    st.markdown(f"**{T(lang,'step1')}**")
    input_method = st.radio(
        'How do you want to define the parcel?',
        options=['✏️ Draw on map', '📂 Upload file'],
        horizontal=True
    )

    st.markdown('---')
    st.markdown('**Step 2 — Choose crop**')
    crop_name = st.selectbox(
        'Crop type',
        options=list(CROPS.keys()),
        format_func=lambda k: f"{CROPS[k]['icon']} {CROPS[k]['label_fr']}" if lang=='fr' else f"{CROPS[k]['icon']} {CROPS[k]['label_en']}",
    )

    st.markdown(f"**{T(lang,'step3')}**")
    buffer_km = st.slider(T(lang,'buffer_lbl'), 0, 5, 0)

    crop_cfg   = CROPS[crop_name]
    use_target = st.checkbox(T(lang,'target_chk'), value=True)
    if use_target:
        target_ha = st.number_input(
            T(lang,'target_lbl'),
            min_value=int(crop_cfg['min_viable_ha']),
            max_value=100000,
            value=int(crop_cfg['target_ha']),
            step=500,
        )
    else:
        target_ha = None
        st.caption(T(lang,'no_target'))

    st.markdown('---')
    run_btn = st.button(
        T(lang,'run_btn'),
        disabled=(gee_status is not True),
        use_container_width=True,
        type='primary'
    )

    st.markdown('---')
    st.markdown(
        '<div style="font-size:0.75rem;color:#888;">'
        'Data: SRTM · HydroSHEDS · Hansen GFC · ESA WorldCover · VIIRS<br>'
        'Platform: Google Earth Engine | Resolution: 30 m/pixel'
        '</div>', unsafe_allow_html=True
    )

# ── Main area ─────────────────────────────────────────────────────────────────
lang = st.session_state.get('lang','en')
st.markdown(f'<div class="main-title">{T(lang,"app_title")}</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">Define a parcel boundary → select a crop → '
    'get suitability zones and a downloadable report.</div>',
    unsafe_allow_html=True
)

# ── Initialise session state ──────────────────────────────────────────────────
if 'drawn_parcel' not in st.session_state:
    st.session_state['drawn_parcel'] = None
if 'parcel_info' not in st.session_state:
    st.session_state['parcel_info'] = None

parcel_info = None

# ══════════════════════════════════════════════════════════════════════════════
# OPTION A — DRAW ON MAP
# ══════════════════════════════════════════════════════════════════════════════
if T(lang,'draw_opt') in input_method:

    st.markdown("""
<div class="draw-tip">
<b>How to draw your parcel:</b><br>
1. Use the <b>polygon tool</b> (pentagon icon) in the top-left of the map<br>
2. Click to place each corner of your parcel<br>
3. Double-click to close the polygon<br>
4. The coordinates are captured automatically — then click <b>Run Analysis</b>
</div>
""", unsafe_allow_html=True)

    # Drawing map — centred on Cameroon by default
    draw_map = folium.Map(
        location=[6.5, 13.5],
        zoom_start=8,
        tiles='CartoDB positron'
    )

    # Add satellite layer
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri', name='Satellite', overlay=False
    ).add_to(draw_map)

    # Draw plugin — polygon and rectangle only
    Draw(
        export=False,
        draw_options={
            'polygon':   {'allowIntersection': False},
            'rectangle': True,
            'polyline':  False,
            'circle':    False,
            'marker':    False,
            'circlemarker': False,
        },
        edit_options={'edit': True, 'remove': True}
    ).add_to(draw_map)

    # Search box directly on the map — type a place, map pans there
    Geocoder(
        position='topright',
        add_marker=True,
        placeholder=T(lang,'search_placeholder'),
        collapsed=False
    ).add_to(draw_map)

    # Locate me button
    LocateControl(position='topleft').add_to(draw_map)

    # Mini map for context
    MiniMap(toggle_display=True).add_to(draw_map)

    folium.LayerControl().add_to(draw_map)

    # If there's a previously drawn polygon, show it
    if st.session_state['drawn_parcel']:
        coords = st.session_state['drawn_parcel']['coordinates'][0]
        folium.Polygon(
            locations=[[c[1], c[0]] for c in coords],
            color='#FF6600', weight=3,
            fill=True, fill_color='#FF6600', fill_opacity=0.15,
            tooltip='Your parcel'
        ).add_to(draw_map)

    map_output = st_folium(
        draw_map,
        height=500,
        use_container_width=True,
        returned_objects=['all_drawings']
    )

    # Read drawn geometry
    drawings = map_output.get('all_drawings') or []
    if drawings:
        last = drawings[-1]
        geom = last.get('geometry', {})
        gtype = geom.get('type', '')

        if gtype == 'Polygon':
            raw_coords = geom['coordinates'][0]
            coords = [[c[0], c[1]] for c in raw_coords]
        elif gtype == 'Rectangle':
            raw_coords = geom['coordinates'][0]
            coords = [[c[0], c[1]] for c in raw_coords]
        else:
            coords = None

        if coords:
            # Close the ring if not already closed
            if coords[0] != coords[-1]:
                coords.append(coords[0])

            # Build parcel_info
            import math
            def approx_area(pts):
                cx = sum(c[0] for c in pts) / len(pts)
                cy = sum(c[1] for c in pts) / len(pts)
                cos_lat = math.cos(math.radians(cy))
                pts_m = [((c[0]-cx)*111320*cos_lat, (c[1]-cy)*110574) for c in pts]
                n = len(pts_m)
                area = 0
                for i in range(n):
                    area += pts_m[i][0]*pts_m[(i+1)%n][1] - pts_m[(i+1)%n][0]*pts_m[i][1]
                return abs(area)/2/10000

            lons = [c[0] for c in coords]
            lats = [c[1] for c in coords]
            area = approx_area(coords[:-1])
            cx   = sum(lons)/len(lons)
            cy   = sum(lats)/len(lats)

            parcel_info = {
                'type': 'Polygon',
                'coordinates': [coords],
                'name': 'Drawn parcel',
                'area_ha': round(area, 1),
                'centroid': (cx, cy),
                'bounds': {'minx': min(lons), 'maxx': max(lons),
                           'miny': min(lats), 'maxy': max(lats)},
            }
            st.session_state['drawn_parcel']  = {'coordinates': [coords]}
            st.session_state['parcel_info']   = parcel_info
            st.success(f'✅ Parcel captured — {area:,.1f} ha at {cy:.4f}°N, {cx:.4f}°E')

    elif st.session_state['parcel_info']:
        parcel_info = st.session_state['parcel_info']
        st.info(f'Using previously drawn parcel — {parcel_info["area_ha"]:,.1f} ha')

    if not parcel_info:
        st.info('👆 Draw a polygon on the map above, then click **Run Analysis** in the sidebar.')

# ══════════════════════════════════════════════════════════════════════════════
# OPTION B — UPLOAD FILE
# ══════════════════════════════════════════════════════════════════════════════
else:
    uploaded_file = st.file_uploader(
        T(lang,'upload_label'),
        type=['kml', 'kmz', 'geojson', 'json'],
    )

    if uploaded_file is not None:
        try:
            file_bytes = uploaded_file.read()
            parcel_info = parse_uploaded_file(file_bytes, uploaded_file.name)
            st.session_state['parcel_info'] = parcel_info

            # Preview map
            coords = parcel_info['coordinates'][0]
            lon, lat = parcel_info['centroid']
            m = folium.Map(location=[lat, lon], zoom_start=11, tiles='CartoDB positron')
            folium.TileLayer(
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='Esri', name='Satellite'
            ).add_to(m)
            folium.Polygon(
                locations=[[c[1], c[0]] for c in coords],
                color='#FF6600', weight=3,
                fill=True, fill_color='#FF6600', fill_opacity=0.15,
                tooltip=parcel_info['name']
            ).add_to(m)
            folium.LayerControl().add_to(m)
            st_folium(m, height=400, use_container_width=True)

        except Exception as e:
            st.error(f'Could not read file: {e}')
            parcel_info = None

    elif st.session_state['parcel_info']:
        parcel_info = st.session_state['parcel_info']

    if not parcel_info:
        st.info('👈 Upload a KML, KMZ or GeoJSON file above.')

# ── Parcel summary metrics ────────────────────────────────────────────────────
if parcel_info:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-box"><div class="metric-val">{parcel_info["name"]}</div>'
                    f'<div class="metric-lbl">Parcel name</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-box"><div class="metric-val">{parcel_info["area_ha"]:,.0f} ha</div>'
                    f'<div class="metric-lbl">Total area</div></div>', unsafe_allow_html=True)
    with col3:
        lon, lat = parcel_info['centroid']
        st.markdown(f'<div class="metric-box"><div class="metric-val">{lat:.4f}°N</div>'
                    f'<div class="metric-lbl">{lon:.4f}°E</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="metric-box"><div class="metric-val">'
                    f'{crop_cfg["icon"]} {crop_name}</div>'
                    f'<div class="metric-lbl">Selected crop</div></div>', unsafe_allow_html=True)

# ── Run analysis ──────────────────────────────────────────────────────────────
if run_btn and parcel_info:

    # Progress UI
    progress_bar = st.progress(0, text=T(lang,'prog_connect'))
    status_text  = st.empty()
    step_list    = st.empty()
    completed    = []

    def update_progress(step, total, message):
        pct = int((step / total) * 100)
        progress_bar.progress(pct, text=f'🛰️  {message}')
        status_text.markdown(T(lang,'prog_step',s=step,t=total,p=pct))
        completed.append(f'✅ {message}')
        step_list.markdown('\n'.join(completed[-5:]))

    try:
        results = run_analysis(
            parcel_geojson=parcel_info,
            crop_name=crop_name,
            buffer_m=buffer_km * 1000,
            target_ha=int(target_ha) if target_ha else None,
            progress_callback=update_progress)
        progress_bar.progress(100, text=T(lang,'prog_complete'))
        status_text.success(T(lang,'prog_success'))
        step_list.empty()
        st.session_state['results']     = results
        st.session_state['parcel_info'] = parcel_info
        st.session_state['crop_name']   = crop_name
    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        step_list.empty()
        st.error(f'Analysis failed: {e}')
        st.stop()

elif run_btn and not parcel_info:
    st.warning(T(lang,'run_warning'))

# ── Show results ──────────────────────────────────────────────────────────────
if 'results' in st.session_state:
    results     = st.session_state['results']
    parcel_info = st.session_state['parcel_info']
    crop_name   = st.session_state['crop_name']

    st.markdown('---')
    st.markdown(T(lang,'results_title'))

    zone_areas = results['zone_areas']
    zone_meta  = {
        '4': ('Zone 4 — PRIME',    '#1A9641', 'Best — develop first'),
        '3': ('Zone 3 — GOOD',     '#66BD63', 'Good — Phase 2'),
        '2': ('Zone 2 — MARGINAL', '#FFA500', 'Manageable constraints'),
        '1': ('Zone 1 — AVOID',    '#D73027', 'Steep/far/dense forest'),
        '0': ('Zone 0 — STREAMS',  '#0033CC', 'Irrigation source'),
    }

    cols = st.columns(5)
    for i, (key, (label, color, desc)) in enumerate(zone_meta.items()):
        ha = zone_areas.get(key, 0)
        with cols[i]:
            st.markdown(
                f'<div style="background:{color};color:white;border-radius:8px;'
                f'padding:12px;text-align:center;">'
                f'<div style="font-size:1.3rem;font-weight:700;">{ha:,.0f} ha</div>'
                f'<div style="font-size:0.7rem;margin-top:4px;">{label}</div>'
                f'<div style="font-size:0.65rem;opacity:0.85;">{desc}</div>'
                f'</div>', unsafe_allow_html=True
            )

    st.markdown('<br>', unsafe_allow_html=True)

    map_col, stat_col = st.columns([3, 2])

    with map_col:
        st.markdown(T(lang,'zone_map_title'))
        zone_colors = {'4':'#1A9641','3':'#A6D96A','2':'#FDAE61','1':'#D73027','0':'#0033CC'}
        coords = parcel_info['coordinates'][0]
        lon, lat = parcel_info['centroid']

        m2 = folium.Map(location=[lat, lon], zoom_start=11)
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri', name='Satellite'
        ).add_to(m2)
        folium.TileLayer('CartoDB positron', name='Light map').add_to(m2)

        zones_fc = results.get('zones_geojson', {})
        if zones_fc and zones_fc.get('features'):
            for feat in zones_fc['features']:
                zone_val = str(int(feat['properties'].get('zone', 1)))
                color    = zone_colors.get(zone_val, '#888888')
                lbl, _, desc = zone_meta.get(zone_val, (f'Zone {zone_val}', '#888', ''))
                folium.GeoJson(
                    feat,
                    style_function=lambda f, c=color: {
                        'fillColor': c, 'color': c,
                        'weight': 0.5, 'fillOpacity': 0.6
                    },
                    tooltip=f'{lbl} — {desc}'
                ).add_to(m2)

        best_fc = results.get('best_area_geojson', {})
        if best_fc and best_fc.get('features'):
            folium.GeoJson(
                best_fc,
                name=f'Best {target_ha:,} ha',
                style_function=lambda f: {
                    'color': '#FF00FF', 'weight': 2.5,
                    'fillColor': 'none', 'fillOpacity': 0
                },
                tooltip='Best area' if not target_ha else f'Best {target_ha:,} ha'
            ).add_to(m2)

        folium.Polygon(
            locations=[[c[1], c[0]] for c in coords],
            color='#FF6600', weight=3, fill=False,
            tooltip=parcel_info['name']
        ).add_to(m2)

        legend_html = '''
        <div style="position:fixed;bottom:20px;left:20px;z-index:1000;
                    background:white;padding:10px 14px;border-radius:8px;
                    border:1px solid #ccc;font-size:12px;line-height:1.8;">
            <b>Suitability Zones</b><br>
            <span style="background:#1A9641;color:white;padding:1px 8px;border-radius:3px;">Zone 4</span> Prime<br>
            <span style="background:#A6D96A;padding:1px 8px;border-radius:3px;">Zone 3</span> Good<br>
            <span style="background:#FDAE61;padding:1px 8px;border-radius:3px;">Zone 2</span> Marginal<br>
            <span style="background:#D73027;color:white;padding:1px 8px;border-radius:3px;">Zone 1</span> Avoid<br>
            <span style="background:#0033CC;color:white;padding:1px 8px;border-radius:3px;">Zone 0</span> Streams<br>
            <span style="color:#FF00FF;font-weight:700;">── </span> Best area target
        </div>'''
        m2.get_root().html.add_child(folium.Element(legend_html))
        folium.LayerControl().add_to(m2)
        st_folium(m2, height=500, use_container_width=True)

    with stat_col:
        st.markdown(T(lang,'score_title'))
        comp    = results.get('component_means', {})
        cfg     = results.get('crop_config', {})
        weights = cfg.get('weights', {})
        criteria = [
            ('slope_score',    'Slope',        'slope',    '#1A9641'),
            ('water_score',    'Water dist.',  'water',    '#1A90C8'),
            ('elec_score',     'Electricity',  'elec',     '#F9A825'),
            ('wetness_score',  'Terrain wet.', 'wetness',  '#00897B'),
            ('clearing_score', 'Clearing',     'clearing', '#E65100'),
            ('flood_score',    'Flood risk',   'flood',    '#6A1B9A'),
        ]
        for key, label, wkey, color in criteria:
            score = comp.get(key, 0)
            w     = weights.get(wkey, 0)
            pct   = int(score * 10)
            st.markdown(
                f'<div style="margin-bottom:10px;">'
                f'<div style="display:flex;justify-content:space-between;margin-bottom:2px;">'
                f'<span style="font-size:0.85rem;font-weight:500;">{label} '
                f'<span style="color:#888;font-size:0.75rem;">({w*100:.0f}%)</span></span>'
                f'<span style="font-size:0.85rem;font-weight:700;color:{color};">{score:.1f}/10</span></div>'
                f'<div style="background:#eee;border-radius:4px;height:8px;">'
                f'<div style="background:{color};width:{pct}%;height:8px;border-radius:4px;"></div>'
                f'</div></div>', unsafe_allow_html=True
            )

        st.markdown('---')
        st.markdown('#### 🎯 Score → Area Table')
        for item in results.get('score_thresholds', []):
            t_val  = item['threshold']
            ha     = item['area_ha']
            marker = ' ◀ ~target' if abs(ha - target_ha) < target_ha * 0.15 else ''
            color  = '#1A9641' if marker else '#333'
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;'
                f'font-size:0.82rem;padding:3px 6px;border-radius:4px;'
                f'background:{"#EAF5EE" if marker else "transparent"};">'
                f'<span style="color:{color};">Score ≥ {t_val}</span>'
                f'<span style="font-weight:600;color:{color};">{ha:,.0f} ha{marker}</span>'
                f'</div>', unsafe_allow_html=True
            )

    # ── Downloads ─────────────────────────────────────────────────────────────
    st.markdown('---')
    st.markdown(T(lang,'downloads'))
    dl1, dl2, dl3 = st.columns(3)

    with dl1:
        best_fc = results.get('best_area_geojson', {})
        if best_fc:
            st.download_button(
                label=T(lang,'dl_best') if not target_ha else T(lang,'dl_best_n',n=target_ha),
                data=json.dumps(best_fc, indent=2),
                file_name=f'{parcel_info["name"]}_best_{target_ha}ha.geojson',
                mime='application/geo+json',
                use_container_width=True
            )
    with dl2:
        zones_fc = results.get('zones_geojson', {})
        if zones_fc:
            st.download_button(
                label=T(lang,'dl_zones'),
                data=json.dumps(zones_fc, indent=2),
                file_name=f'{parcel_info["name"]}_zones.geojson',
                mime='application/geo+json',
                use_container_width=True
            )
    with dl3:
        if st.button(T(lang,'dl_pdf'), use_container_width=True):
            with st.spinner('Building report...'):
                try:
                    pdf_bytes = generate_report(
                        parcel_info=parcel_info,
                        results=results,
                        crop_name=crop_name
                    )
                    st.download_button(
                        label='⬇️ Download PDF',
                        data=pdf_bytes,
                        file_name=f'{parcel_info["name"]}_{crop_name}_report.pdf',
                        mime='application/pdf',
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f'Report generation failed: {e}')

    with st.expander('⚠️ Important caveats before field decisions'):
        st.markdown(f'<div class="warn-box">{T(lang,"caveats_body")}</div>', unsafe_allow_html=True)

else:
    if not parcel_info:
        st.markdown('---')
        st.info('Define a parcel above and click **🚀 Run Analysis** in the sidebar to get started.')

def build_report_text(parcel_info, results, crop_name, lang='en'):
    za     = results['zone_areas']
    comp   = results['component_means']
    cfg    = results['crop_config']
    w      = cfg['weights']
    total  = sum(za.values()) or 1
    prime  = za.get('4', 0)
    good   = za.get('3', 0)
    marg   = za.get('2', 0)
    avoid  = za.get('1', 0)
    best   = prime + good
    pct    = best / total * 100

    mean_score = results['suit_stats'].get('suitability_mean', 0) or 0
    min_water  = results['water_stats'].get('dist_water_min', 0) or 0
    min_elec   = results['elec_stats'].get('dist_grid_min', 0) or 0
    mean_slope = results['slope_stats'].get('slope_mean', 0) or 0

    crop_label = cfg.get('label_fr', crop_name) if lang == 'fr' else cfg.get('label_en', crop_name)

    if pct >= 50:
        verdict_en = "The parcel presents **good overall suitability** for the selected crop."
        verdict_fr = "La parcelle présente une **bonne aptitude générale** pour la culture sélectionnée."
    elif pct >= 25:
        verdict_en = "The parcel presents **moderate suitability** with significant constraints in some areas."
        verdict_fr = "La parcelle présente une **aptitude modérée** avec des contraintes significatives."
    else:
        verdict_en = "The parcel presents **limited suitability**. Most of the area has significant constraints."
        verdict_fr = "La parcelle présente une **aptitude limitée**. La majorité de la zone présente des contraintes importantes."

    en = f"""
**Parcel:** {parcel_info['name']} | **Area:** {parcel_info['area_ha']:,.0f} ha | **Crop:** {cfg.get('label_en', crop_name)}

---

#### Summary

{verdict_en}

Out of the total {parcel_info['area_ha']:,.0f} ha, **{best:,.0f} ha ({pct:.0f}%)** fall into Zone 3 (Good) or Zone 4 (Prime). A further **{marg:,.0f} ha** are marginal, while **{avoid:,.0f} ha** should be avoided.

Mean composite suitability score: **{mean_score:.1f} / 10**

---

#### Scoring criteria

| Criterion | Weight | Mean score |
|---|---|---|
| Slope | {w['slope']*100:.0f}% | {comp.get('slope_score',0):.1f}/10 |
| Water proximity | {w['water']*100:.0f}% | {comp.get('water_score',0):.1f}/10 |
| Electricity | {w['elec']*100:.0f}% | {comp.get('elec_score',0):.1f}/10 |
| Terrain wetness | {w['wetness']*100:.0f}% | {comp.get('wetness_score',0):.1f}/10 |
| Clearing cost | {w['clearing']*100:.0f}% | {comp.get('clearing_score',0):.1f}/10 |
| Flood risk | {w['flood']*100:.0f}% | {comp.get('flood_score',0):.1f}/10 |
| **Composite** | 100% | **{mean_score:.1f}/10** |

Key distances: water **{min_water/1000:.1f} km** | electricity **{min_elec/1000:.1f} km** | mean slope **{mean_slope:.1f}°**

---

#### Zone breakdown

| Zone | Area (ha) | % | Recommendation |
|---|---|---|---|
| Zone 4 — Prime | {prime:,.0f} | {prime/total*100:.1f}% | Develop first |
| Zone 3 — Good | {good:,.0f} | {good/total*100:.1f}% | Phase 2 expansion |
| Zone 2 — Marginal | {marg:,.0f} | {marg/total*100:.1f}% | Targeted investment needed |
| Zone 1 — Avoid | {avoid:,.0f} | {avoid/total*100:.1f}% | Not recommended |
"""

    fr = f"""
**Parcelle :** {parcel_info['name']} | **Superficie :** {parcel_info['area_ha']:,.0f} ha | **Culture :** {cfg.get('label_fr', crop_name)}

---

#### Résumé

{verdict_fr}

Sur les {parcel_info['area_ha']:,.0f} ha analysés, **{best:,.0f} ha ({pct:.0f}%)** se situent en Zone 3 (Bonne) ou Zone 4 (Prime). **{marg:,.0f} ha** supplémentaires sont marginaux, et **{avoid:,.0f} ha** sont à éviter.

Score moyen de l'analyse : **{mean_score:.1f} / 10**

---

#### Critères de notation

| Critère | Poids | Score moyen |
|---|---|---|
| Pente | {w['slope']*100:.0f}% | {comp.get('slope_score',0):.1f}/10 |
| Proximité eau | {w['water']*100:.0f}% | {comp.get('water_score',0):.1f}/10 |
| Électricité | {w['elec']*100:.0f}% | {comp.get('elec_score',0):.1f}/10 |
| Humidité terrain | {w['wetness']*100:.0f}% | {comp.get('wetness_score',0):.1f}/10 |
| Coût défrichage | {w['clearing']*100:.0f}% | {comp.get('clearing_score',0):.1f}/10 |
| Risque inondation | {w['flood']*100:.0f}% | {comp.get('flood_score',0):.1f}/10 |
| **Score composite** | 100% | **{mean_score:.1f}/10** |

Distances clés : eau **{min_water/1000:.1f} km** | électricité **{min_elec/1000:.1f} km** | pente moyenne **{mean_slope:.1f}°**

---

#### Répartition par zone

| Zone | Superficie (ha) | % | Recommandation |
|---|---|---|---|
| Zone 4 — Prime | {prime:,.0f} | {prime/total*100:.1f}% | Développer en priorité |
| Zone 3 — Bonne | {good:,.0f} | {good/total*100:.1f}% | Extension Phase 2 |
| Zone 2 — Marginale | {marg:,.0f} | {marg/total*100:.1f}% | Investissement ciblé requis |
| Zone 1 — Éviter | {avoid:,.0f} | {avoid/total*100:.1f}% | Non recommandé |
"""

    # Return both languages with a divider
    if lang == 'fr':
        return fr + "\n\n---\n\n" + en
    else:
        return en + "\n\n---\n\n" + fr


