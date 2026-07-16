"""
app.py — Cropbility Home Page
Welcome, app explanation, and parameter weight customisation.
"""

import json
import streamlit as st
from translations import T
from crop_config import CROPS

st.set_page_config(
    page_title='Cropbility',
    page_icon='🌾',
    layout='wide',
    initial_sidebar_state='expanded',
)

# ── Font + CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
  html, body, [class*="css"], .stMarkdown, p, h1, h2, h3, h4, label, div, button, input, select {
    font-family: 'Inter', sans-serif !important;
    letter-spacing: -0.01em;
  }
  .hero        { padding: 2.5rem 0 1.5rem 0; }
  .hero-title  { font-size: 3rem; font-weight: 700; color: #1A5C30;
                 letter-spacing: -0.03em; margin-bottom: 0.5rem; }
  .hero-sub    { font-size: 1.15rem; color: #555; max-width: 680px; line-height: 1.7; }
  .page-card   { background: #F9FBF9; border: 1px solid #D4E8D4; border-radius: 12px;
                 padding: 1.5rem; height: 100%; }
  .page-card h4{ color: #1A5C30; font-size: 1rem; font-weight: 600; margin-bottom: 0.5rem; }
  .page-card p { color: #555; font-size: 0.88rem; line-height: 1.6; margin: 0; }
  .page-num    { font-size: 1.8rem; margin-bottom: 0.5rem; }
  .param-box   { background: #EAF5EE; border-radius: 10px; padding: 1.2rem 1.5rem;
                 border-left: 4px solid #2E7D46; margin-bottom: 0.75rem; }
  .param-box p { font-size: 0.82rem; color: #555; margin: 0.2rem 0 0 0; }
  .weight-total{ font-size: 0.9rem; font-weight: 600; padding: 8px 14px;
                 border-radius: 6px; display: inline-block; margin-top: 8px; }
  .divider     { border: none; border-top: 1px solid #E0EDE0; margin: 2rem 0; }
</style>
""", unsafe_allow_html=True)

# ── Language ──────────────────────────────────────────────────────────────────
if 'lang' not in st.session_state:
    st.session_state['lang'] = 'en'

lang_choice = st.sidebar.radio(
    'Language / Langue',
    options=['🇬🇧 English', '🇫🇷 Français'],
    horizontal=True,
    label_visibility='collapsed',
    key='lang_radio_home'
)
lang = 'fr' if 'Français' in lang_choice else 'en'
st.session_state['lang'] = lang

st.sidebar.markdown('---')
st.sidebar.markdown(
    '<div style="font-size:0.75rem;color:#888;">'
    'Cropbility v1.0<br>'
    'Data: SRTM · HydroSHEDS · Hansen · ESA · VIIRS · CHIRPS · NEX-GDDP<br>'
    'Platform: Google Earth Engine</div>',
    unsafe_allow_html=True
)

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown('<div class="hero">', unsafe_allow_html=True)

if lang == 'fr':
    st.markdown('<div class="hero-title">🌾 Bienvenue sur Cropbility</div>', unsafe_allow_html=True)
    st.markdown('''<div class="hero-sub">
        Cropbility est un outil d\'analyse géospatiale alimenté par Google Earth Engine.
        Téléversez ou dessinez une parcelle agricole et obtenez en quelques minutes :
        une carte d\'aptitude des cultures, une évaluation de l\'impact environnemental
        et des projections climatiques sur 5 à 20 ans.
    </div>''', unsafe_allow_html=True)
else:
    st.markdown('<div class="hero-title">🌾 Welcome to Cropbility</div>', unsafe_allow_html=True)
    st.markdown('''<div class="hero-sub">
        Cropbility is a geospatial analysis tool powered by Google Earth Engine.
        Upload or draw an agricultural parcel and get — in minutes — a crop suitability map,
        an environmental impact assessment, and climate projections for the next 5 to 20 years.
    </div>''', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# ── Page cards ────────────────────────────────────────────────────────────────
st.markdown('<hr class="divider">', unsafe_allow_html=True)

if lang == 'fr':
    st.markdown('### Ce que vous pouvez faire')
else:
    st.markdown('### What you can do')

c1, c2, c3 = st.columns(3)

pages_en = [
    ('🌾', 'Crop Suitability',
     '• Check if your parcel is suitable for the crop you want to plant\n'
     '• Adjust the scoring weights to match your knowledge\n'
     '• Identify the ideal sub-area to plant\n'
     '• Download a suitability report'),
    ('🌿', 'Environmental Impact',
     '• Assess the environmental impact of your crop and parcel\n'
     '• Estimate the carbon stock and forest cover\n'
     '• Calculate potential REDD+ carbon credit value\n'
     '• Download an environmental impact report'),
    ('🌡️', 'Climate Impact',
     '• Check how climate change will affect your parcel\n'
     '• Rainfall and temperature projections: 5 / 10 / 15 / 20 years\n'
     '• Drought risk and flood frequency trends\n'
     '• Download a climate impact report'),
]

pages_fr = [
    ('🌾', 'Aptitude des cultures',
     '• Vérifier si votre parcelle convient à la culture souhaitée\n'
     '• Ajuster les pondérations selon votre expertise\n'
     '• Identifier la meilleure sous-zone à cultiver\n'
     '• Télécharger un rapport d\'aptitude'),
    ('🌿', 'Impact environnemental',
     '• Évaluer l\'impact environnemental de votre culture et parcelle\n'
     '• Estimer le stock de carbone et la couverture forestière\n'
     '• Calculer la valeur potentielle des crédits carbone REDD+\n'
     '• Télécharger un rapport d\'impact environnemental'),
    ('🌡️', 'Impact climatique',
     '• Analyser l\'impact du changement climatique sur votre parcelle\n'
     '• Projections de pluie et température : 5 / 10 / 15 / 20 ans\n'
     '• Risques de sécheresse et tendances d\'inondation\n'
     '• Télécharger un rapport d\'impact climatique'),
]

pages = pages_fr if lang == 'fr' else pages_en

for col, (icon, title, desc) in zip([c1, c2, c3], pages):
    with col:
        items = ''.join(
            f'<li style="margin-bottom:6px;font-size:0.87rem;color:#444;">{line[2:]}</li>'
            for line in desc.strip().split('\n')
        )
        st.markdown(
            f'<div class="page-card">'
            f'<div class="page-num">{icon}</div>'
            f'<h4>{title}</h4>'
            f'<ul style="padding-left:16px;margin:0;">{items}</ul>'
            f'</div>',
            unsafe_allow_html=True
        )

# ── Parameter weights ─────────────────────────────────────────────────────────
st.markdown('<hr class="divider">', unsafe_allow_html=True)

if lang == 'fr':
    st.markdown('### ⚙️ Paramètres de pondération — Utilisateurs avancés')
    st.markdown(
        'Ajustez les pondérations utilisées dans l\'analyse d\'aptitude des cultures. '
        'La somme doit être égale à 100%. Ces paramètres s\'appliquent à toutes les analyses.'
    )
else:
    st.markdown('### ⚙️ Scoring weights — Advanced users')
    st.markdown(
        'Adjust the weights used in the crop suitability scoring. '
        'They must sum to 100%. These apply across all analyses.'
    )

# Load defaults from session state or use standard
default_weights = st.session_state.get('custom_weights', {
    'slope': 30, 'water': 25, 'elec': 15,
    'wetness': 13, 'clearing': 12, 'flood': 5
})

criteria_info = {
    'en': [
        ('slope',    'Slope',               'Flat land scores highest. Rice needs <2% slope for efficient paddy construction.'),
        ('water',    'Water proximity',      'Distance to nearest permanent stream. Closer = cheaper irrigation canal.'),
        ('elec',     'Electricity proximity','Distance to electrified settlements. Needed for pumping and processing.'),
        ('wetness',  'Terrain wetness',      'Low-lying valley bottoms retain water naturally, reducing irrigation cost.'),
        ('clearing', 'Clearing cost',        'Open grassland is cheapest to prepare. Dense forest adds 800–1,200 USD/ha.'),
        ('flood',    'Flood risk',           'Pixels near main stream channels receive a penalty for uncontrolled flooding risk.'),
    ],
    'fr': [
        ('slope',    'Pente',                'Les terrains plats ont le score le plus élevé. Le riz nécessite <2% de pente.'),
        ('water',    'Proximité de l\'eau',  'Distance au cours d\'eau permanent le plus proche. Plus proche = canal moins cher.'),
        ('elec',     'Proximité électrique', 'Distance aux habitations électrifiées. Nécessaire pour le pompage et la transformation.'),
        ('wetness',  'Humidité du terrain',  'Les bas-fonds retiennent l\'eau naturellement, réduisant le coût d\'irrigation.'),
        ('clearing', 'Coût de défrichage',   'La prairie est la moins chère à préparer. La forêt dense ajoute 800–1 200 USD/ha.'),
        ('flood',    'Risque d\'inondation', 'Les pixels proches des chenaux principaux reçoivent une pénalité.'),
    ]
}

cols_a, cols_b = st.columns(2)
new_weights = {}
info = criteria_info[lang]

for i, (key, label, desc) in enumerate(info):
    col = cols_a if i < 3 else cols_b
    with col:
        val = st.slider(
            f'**{label}**',
            min_value=0, max_value=50,
            value=default_weights.get(key, 10),
            step=1, key=f'w_{key}'
        )
        st.markdown(f'<p style="font-size:0.8rem;color:#666;margin-top:-8px;margin-bottom:12px;">{desc}</p>',
                    unsafe_allow_html=True)
        new_weights[key] = val

total = sum(new_weights.values())
color = '#1A9641' if total == 100 else '#E65100'
label_total = 'Total' if lang == 'en' else 'Total'
warn = '' if total == 100 else (' — must equal 100%' if lang == 'en' else ' — doit égaler 100%')

st.markdown(
    f'<div class="weight-total" style="background:{"#EAF5EE" if total==100 else "#FFF3CD"};'
    f'color:{color};border:1px solid {color};">'
    f'{label_total}: {total}%{warn}</div>',
    unsafe_allow_html=True
)

if total == 100:
    st.session_state['custom_weights'] = new_weights
    if lang == 'fr':
        st.success('✅ Pondérations sauvegardées — elles seront utilisées dans l\'analyse d\'aptitude.')
    else:
        st.success('✅ Weights saved — they will be used in the crop suitability analysis.')

# ── How to use ────────────────────────────────────────────────────────────────
st.markdown('<hr class="divider">', unsafe_allow_html=True)

if lang == 'fr':
    st.markdown('### Comment utiliser Cropbility')
    steps = [
        ('1', 'Définir votre parcelle', 'Sur la page **Aptitude des cultures**, dessinez votre parcelle sur la carte ou téléversez un fichier KML/KMZ/GeoJSON.'),
        ('2', 'Choisir votre culture', 'Sélectionnez la culture dans la liste déroulante. Chaque culture a ses propres paramètres agronomiques.'),
        ('3', 'Lancer l\'analyse', 'Cliquez sur **Lancer l\'analyse**. L\'analyse s\'exécute sur Google Earth Engine (~2–4 minutes).'),
        ('4', 'Explorer les résultats', 'Consultez la carte des zones, les statistiques et les rapports téléchargeables sur chaque page.'),
    ]
else:
    steps = [
        ('1', 'Define your parcel', 'On the **Crop Suitability** page, draw your parcel on the map or upload a KML/KMZ/GeoJSON file.'),
        ('2', 'Choose your crop', 'Select the crop from the dropdown. Each crop has its own agronomic scoring parameters.'),
        ('3', 'Run the analysis', 'Click **Run Analysis**. The analysis runs on Google Earth Engine (~2–4 minutes).'),
        ('4', 'Explore results', 'View the zone map, statistics, and downloadable reports on each page.'),
    ]

cols = st.columns(4)
for col, (num, title, desc) in zip(cols, steps):
    with col:
        st.markdown(
            f'<div style="text-align:center;padding:1rem;">'
            f'<div style="font-size:2rem;font-weight:700;color:#1A5C30;">{num}</div>'
            f'<div style="font-weight:600;margin:6px 0 8px 0;font-size:0.9rem;">{title}</div>'
            f'<div style="font-size:0.82rem;color:#555;line-height:1.5;">{desc}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

st.markdown('<hr class="divider">', unsafe_allow_html=True)
st.markdown(
    '<div style="text-align:center;font-size:0.78rem;color:#999;">'
    'Cropbility v1.0 — Powered by Google Earth Engine · '
    'Data: SRTM, HydroSHEDS, Hansen GFC 2025, ESA WorldCover, VIIRS, CHIRPS, NEX-GDDP-CMIP6'
    '</div>',
    unsafe_allow_html=True
)
