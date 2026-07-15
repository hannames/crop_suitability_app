"""
translations.py
All UI strings in English and French.
Usage: from translations import T
       T(lang, 'key')
"""

_T = {
    # ── App title & subtitle ──────────────────────────────────────────────────
    'app_title': {
        'en': '🌾 Crop Suitability Analyser',
        'fr': '🌾 Analyseur d\'Aptitude Agricole',
    },
    'app_subtitle': {
        'en': 'Define a parcel → select a crop → get suitability zones and a report.',
        'fr': 'Définissez une parcelle → choisissez une culture → obtenez les zones d\'aptitude et un rapport.',
    },

    # ── Sidebar ───────────────────────────────────────────────────────────────
    'gee_ok':     {'en': '✅ Google Earth Engine connected', 'fr': '✅ Google Earth Engine connecté'},
    'gee_err':    {'en': '❌ GEE error', 'fr': '❌ Erreur GEE'},
    'gee_hint':   {'en': 'Run `earthengine authenticate` in terminal, then restart.',
                   'fr': 'Lancez `earthengine authenticate` dans le terminal, puis redémarrez.'},

    'step1':      {'en': 'Step 1 — Define your parcel', 'fr': 'Étape 1 — Définir votre parcelle'},
    'how_label':  {'en': 'How?', 'fr': 'Comment ?'},
    'draw_opt':   {'en': '✏️ Draw on map', 'fr': '✏️ Dessiner sur la carte'},
    'upload_opt': {'en': '📂 Upload file', 'fr': '📂 Téléverser un fichier'},

    'step2':      {'en': 'Step 2 — Crop', 'fr': 'Étape 2 — Culture'},
    'crop_label': {'en': 'Crop type', 'fr': 'Type de culture'},

    'step3':      {'en': 'Step 3 — Settings', 'fr': 'Étape 3 — Paramètres'},
    'buffer_lbl': {'en': 'Buffer around parcel (km)', 'fr': 'Tampon autour de la parcelle (km)'},
    'target_chk': {'en': 'Set a target area (ha)?', 'fr': 'Définir une superficie cible (ha) ?'},
    'target_lbl': {'en': 'Target area (ha)', 'fr': 'Superficie cible (ha)'},
    'no_target':  {'en': 'Full suitability map only — no best-area polygon.',
                   'fr': 'Carte d\'aptitude complète uniquement — sans polygone de meilleure zone.'},

    'run_btn':    {'en': '🚀 Run Analysis', 'fr': '🚀 Lancer l\'analyse'},
    'print_btn':  {'en': '🖨️ Print / Save PDF', 'fr': '🖨️ Imprimer / Enregistrer PDF'},

    'data_note':  {'en': 'Data: SRTM · HydroSHEDS · Hansen GFC 2025 · ESA WorldCover · VIIRS\nGEE | 30–250 m/pixel',
                   'fr': 'Données: SRTM · HydroSHEDS · Hansen GFC 2025 · ESA WorldCover · VIIRS\nGEE | 30–250 m/pixel'},

    # ── Draw map ──────────────────────────────────────────────────────────────
    'draw_tip':   {
        'en': '<b>Draw your parcel:</b> use the <b>polygon tool</b> (pentagon icon, top-left of map) → click corners → double-click to close. Use the <b>search box</b> (top-right) to navigate to any location.',
        'fr': '<b>Dessinez votre parcelle :</b> utilisez l\'<b>outil polygone</b> (icône pentagone, en haut à gauche de la carte) → cliquez sur les coins → double-cliquez pour fermer. Utilisez la <b>barre de recherche</b> (en haut à droite) pour naviguer.',
    },
    'jump_label': {'en': '📍 Jump to coordinates', 'fr': '📍 Aller aux coordonnées'},
    'go_btn':     {'en': 'Go', 'fr': 'Aller'},
    'parcel_ok':  {'en': '✅ Parcel captured', 'fr': '✅ Parcelle capturée'},
    'saved_parcel': {'en': 'Using saved parcel', 'fr': 'Utilisation de la parcelle sauvegardée'},
    'draw_info':  {'en': '👆 Draw a polygon on the map, then click **🚀 Run Analysis**.',
                   'fr': '👆 Dessinez un polygone sur la carte, puis cliquez sur **🚀 Lancer l\'analyse**.'},

    # ── Upload ────────────────────────────────────────────────────────────────
    'upload_label': {'en': 'Upload KML, KMZ, or GeoJSON', 'fr': 'Téléverser KML, KMZ ou GeoJSON'},
    'upload_info':  {'en': '👈 Upload a KML, KMZ or GeoJSON file.', 'fr': '👈 Téléversez un fichier KML, KMZ ou GeoJSON.'},

    # ── Parcel metrics ────────────────────────────────────────────────────────
    'lbl_name':   {'en': 'Parcel name', 'fr': 'Nom de la parcelle'},
    'lbl_area':   {'en': 'Total area',  'fr': 'Superficie totale'},
    'lbl_crop':   {'en': 'Selected crop', 'fr': 'Culture sélectionnée'},

    # ── Results ───────────────────────────────────────────────────────────────
    'results_title':   {'en': '## 📊 Results', 'fr': '## 📊 Résultats'},
    'zone_map_title':  {'en': '#### 🗺️ Suitability Zone Map', 'fr': '#### 🗺️ Carte des zones d\'aptitude'},
    'score_title':     {'en': '#### 📈 Score by Criterion', 'fr': '#### 📈 Score par critère'},
    'score_area_title':{'en': '#### 🎯 Score → Area', 'fr': '#### 🎯 Score → Superficie'},
    'target_marker':   {'en': ' ◀ ~target', 'fr': ' ◀ ~cible'},
    'downloads':       {'en': '#### ⬇️ Downloads', 'fr': '#### ⬇️ Téléchargements'},
    'dl_best':         {'en': '📥 Best area — GeoJSON', 'fr': '📥 Meilleure zone — GeoJSON'},
    'dl_best_n':       {'en': '📥 Best {n:,} ha — GeoJSON', 'fr': '📥 Meilleures {n:,} ha — GeoJSON'},
    'dl_zones':        {'en': '🗺️ All zones — GeoJSON', 'fr': '🗺️ Toutes les zones — GeoJSON'},
    'dl_pdf':          {'en': '📄 Generate PDF Report', 'fr': '📄 Générer le rapport PDF'},
    'dl_pdf_btn':      {'en': '⬇️ Download PDF', 'fr': '⬇️ Télécharger le PDF'},

    # ── Zone labels ───────────────────────────────────────────────────────────
    'zone4_lbl': {'en': 'Zone 4 — PRIME',    'fr': 'Zone 4 — PRIME'},
    'zone4_desc':{'en': 'Best — develop first','fr': 'Meilleure — développer en priorité'},
    'zone3_lbl': {'en': 'Zone 3 — GOOD',     'fr': 'Zone 3 — BONNE'},
    'zone3_desc':{'en': 'Good — Phase 2',     'fr': 'Bonne — Phase 2'},
    'zone2_lbl': {'en': 'Zone 2 — MARGINAL', 'fr': 'Zone 2 — MARGINALE'},
    'zone2_desc':{'en': 'Manageable constraints','fr': 'Contraintes gérables'},
    'zone1_lbl': {'en': 'Zone 1 — AVOID',    'fr': 'Zone 1 — ÉVITER'},
    'zone1_desc':{'en': 'Steep/far/dense',   'fr': 'Pente/distance/forêt'},
    'zone0_lbl': {'en': 'Zone 0 — STREAMS',  'fr': 'Zone 0 — COURS D\'EAU'},
    'zone0_desc':{'en': 'Irrigation source', 'fr': 'Source d\'irrigation'},

    # ── Criterion labels ──────────────────────────────────────────────────────
    'crit_slope':    {'en': 'Slope',            'fr': 'Pente'},
    'crit_water':    {'en': 'Water distance',   'fr': 'Distance à l\'eau'},
    'crit_elec':     {'en': 'Electricity',      'fr': 'Électricité'},
    'crit_wetness':  {'en': 'Terrain wetness',  'fr': 'Humidité terrain'},
    'crit_clearing': {'en': 'Clearing cost',    'fr': 'Coût défrichage'},
    'crit_flood':    {'en': 'Flood risk',       'fr': 'Risque inondation'},

    # ── Report ────────────────────────────────────────────────────────────────
    'report_title':    {'en': '## 📝 Suitability Report', 'fr': '## 📝 Rapport d\'aptitude'},
    'caveats_title':   {'en': '⚠️ Caveats — field verification required',
                        'fr': '⚠️ Limites — vérification terrain requise'},
    'caveats_body': {
        'en': """This is a **remote sensing pre-screening** — not a soil survey or engineering study.\n\n**Always verify in the field:**\n• **Slope** — SRTM has ±6–10m vertical error. Re-survey with GNSS before canal design.\n• **Water** — HydroSHEDS shows channels but not dry-season flow.\n• **Soil** — No soil data used. Clay content and drainage must be measured in situ.\n• **Land tenure** — Check for existing users before clearing.\n• **Electricity** — VIIRS brightness ≠ grid voltage or capacity.""",
        'fr': """Ceci est un **présélection par télédétection** — pas une étude pédologique ou d'ingénierie.\n\n**Toujours vérifier sur le terrain :**\n• **Pente** — Erreur verticale SRTM ±6–10m. Re-lever par GNSS avant conception.\n• **Eau** — HydroSHEDS montre les chenaux mais pas le débit en saison sèche.\n• **Sol** — Aucune donnée pédologique utilisée. Texture et drainage à mesurer in situ.\n• **Foncier** — Vérifier les utilisateurs existants avant défrichage.\n• **Électricité** — La luminosité VIIRS ≠ tension ou capacité du réseau.""",
    },
    'run_warning':  {'en': 'Define a parcel first.', 'fr': 'Définissez d\'abord une parcelle.'},
    'start_info':   {'en': 'Define a parcel above and click **🚀 Run Analysis** to get started.',
                     'fr': 'Définissez une parcelle ci-dessus et cliquez sur **🚀 Lancer l\'analyse** pour commencer.'},

    # ── Progress messages ─────────────────────────────────────────────────────
    'prog_connect':  {'en': '🛰️  Connecting to Google Earth Engine...', 'fr': '🛰️  Connexion à Google Earth Engine...'},
    'prog_complete': {'en': '✅  Analysis complete!', 'fr': '✅  Analyse terminée !'},
    'prog_success':  {'en': 'Analysis finished successfully.', 'fr': 'Analyse terminée avec succès.'},
    'prog_step':     {'en': 'Step {s} of {t} — {p}% complete', 'fr': 'Étape {s} sur {t} — {p}% terminé'},
    'prog_failed':   {'en': 'Analysis failed', 'fr': 'Analyse échouée'},

    # ── Legend ────────────────────────────────────────────────────────────────
    'legend_title':  {'en': 'Suitability Zones', 'fr': 'Zones d\'aptitude'},
    'legend_target': {'en': '── Best area target', 'fr': '── Zone cible'},

    # ── Map layer names ───────────────────────────────────────────────────────
    'layer_satellite': {'en': 'Satellite', 'fr': 'Satellite'},
    'layer_streets':   {'en': 'Streets + Admin', 'fr': 'Rues + Limites admin.'},
    'layer_light':     {'en': 'Light map', 'fr': 'Carte claire'},
    'search_placeholder': {'en': 'Search for a place...', 'fr': 'Rechercher un lieu...'},
}


def T(lang: str, key: str, **kwargs) -> str:
    """Get translated string. lang = 'en' or 'fr'."""
    lang = lang if lang in ('en', 'fr') else 'en'
    val  = _T.get(key, {}).get(lang, _T.get(key, {}).get('en', key))
    if kwargs:
        val = val.format(**kwargs)
    return val
