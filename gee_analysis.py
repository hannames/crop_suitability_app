"""
gee_analysis.py - Google Earth Engine analysis engine.
Supports progress callback for live progress bar in Streamlit.
"""

import ee
import json
from typing import Optional, Callable
from crop_config import CROPS


def initialise_gee(service_account=None, key_json=None):
    try:
        if service_account and key_json:
            credentials = ee.ServiceAccountCredentials(
                service_account, key_data=json.dumps(key_json))
            ee.Initialize(credentials, project='ee-meslet')
        else:
            ee.Initialize(project='ee-meslet')
    except Exception as e:
        raise RuntimeError(
            f"GEE authentication failed: {e}\n"
            "For local dev: run `earthengine authenticate` in terminal.\n"
            "For Streamlit Cloud: add GEE_SERVICE_ACCOUNT and GEE_KEY_JSON to secrets.")


def run_analysis(parcel_geojson: dict,
                 crop_name: str,
                 buffer_m: int = 0,
                 target_ha: Optional[int] = None,
                 progress_callback: Optional[Callable] = None) -> dict:
    """
    Run full suitability analysis.
    progress_callback(step, total, message) is called before each server call.
    """

    if crop_name not in CROPS:
        raise ValueError(f"Unknown crop: {crop_name}.")

    cfg    = CROPS[crop_name]
    target = target_ha or cfg['target_ha']

    # Total number of server-side .getInfo() calls
    TOTAL_STEPS = 21
    step = [0]  # mutable counter

    def tick(message):
        step[0] += 1
        if progress_callback:
            progress_callback(step[0], TOTAL_STEPS, message)

    # ── Build geometry ────────────────────────────────────────────────────────
    coords = parcel_geojson['coordinates'][0]
    parcel = ee.Geometry.Polygon([coords])
    aoi    = parcel.buffer(buffer_m) if buffer_m > 0 else parcel

    # ── Prepare all images (no server calls yet) ──────────────────────────────
    dem      = ee.Image('USGS/SRTMGL1_003').clip(aoi)
    slope    = ee.Terrain.slope(dem).rename('slope')
    min_elev = ee.Number(dem.unmask(0).reduceRegion(
        reducer=ee.Reducer.min(), geometry=aoi, scale=250,
        maxPixels=1e9, bestEffort=True
    ).get('elevation', 0))
    elev_rel = dem.unmask(0).subtract(min_elev).rename('elev_rel')

    flow_acc      = ee.Image('WWF/HydroSHEDS/15ACC').select('b1').clip(aoi.buffer(5000))
    streams       = flow_acc.gt(cfg['stream_threshold']).rename('streams')
    dist_to_water = ee.Image(1).cumulativeCost(
        source=streams, maxDistance=15000).rename('dist_water').clip(aoi)

    tree_cover = ee.Image(
        'UMD/hansen/global_forest_change_2025_v1_13'
    ).select('treecover2000').clip(aoi)

    worldcover = ee.ImageCollection('ESA/WorldCover/v200').first().clip(aoi).rename('lc')

    viirs = (ee.ImageCollection('NOAA/VIIRS/DNB/MONTHLY_V1/VCMCFG')
             .filterDate('2022-01-01', '2024-01-01')
             .select('avg_rad').median().rename('nightlight'))
    dist_to_grid = ee.Image(1).cumulativeCost(
        source=viirs.gt(0.3).selfMask(), maxDistance=100000
    ).rename('dist_grid').clip(aoi)

    # ── Scores ────────────────────────────────────────────────────────────────
    slope_score    = _threshold_score(slope,          cfg['slope_thresholds'],   'score_slope')
    water_score    = _threshold_score(dist_to_water,  cfg['water_thresholds'],   'score_water')
    elec_score     = _threshold_score(dist_to_grid,   cfg['elec_thresholds'],    'score_elec')
    wetness_score  = _threshold_score(elev_rel,       cfg['wetness_thresholds'], 'score_wet')
    clearing_score = _clearing_score(tree_cover, worldcover, crop_name)
    flood_score    = _flood_score(flow_acc, cfg['stream_threshold'])

    w = cfg['weights']
    suitability = (
        slope_score.multiply(w['slope'])
        .add(water_score.multiply(w['water']))
        .add(elec_score.multiply(w['elec']))
        .add(wetness_score.multiply(w['wetness']))
        .add(clearing_score.multiply(w['clearing']))
        .add(flood_score.multiply(w['flood']))
        .rename('suitability').clip(aoi)
    )

    # ── Zones ─────────────────────────────────────────────────────────────────
    on_stream = flow_acc.gt(cfg['stream_threshold'] * 5)
    zones = (ee.Image(1)
        .where(suitability.gte(3.5).And(suitability.lt(5.5)), 2)
        .where(suitability.gte(5.5).And(suitability.lt(7.5)), 3)
        .where(suitability.gte(7.5), 4)
        .where(on_stream, 0)
        .rename('zone').clip(aoi))

    pixel_area = ee.Image.pixelArea().divide(10000)

    # ══════════════════════════════════════════════════════════════════════════
    # SERVER CALLS START HERE — each tick() updates the progress bar
    # ══════════════════════════════════════════════════════════════════════════

    # 1. Zone areas
    tick('Calculating zone areas...')
    zone_areas_raw = pixel_area.addBands(zones).reduceRegion(
        reducer=ee.Reducer.sum().group(groupField=1, groupName='zone'),
        geometry=aoi, scale=250, maxPixels=1e9, bestEffort=True).getInfo()

    zone_areas = {str(int(g['zone'])): round(g['sum'], 1)
                  for g in zone_areas_raw.get('groups', [])}
    for z in ['0','1','2','3','4']:
        zone_areas.setdefault(z, 0.0)

    # 2-9. Score threshold areas (8 calls)
    score_thresholds = []
    thresholds = [8.0, 7.5, 7.0, 6.5, 6.0, 5.5, 5.0, 4.5]
    for i, thresh in enumerate(thresholds):
        tick(f'Computing score distribution ({i+1}/8)...')
        area = pixel_area.updateMask(suitability.gte(thresh)).reduceRegion(
            reducer=ee.Reducer.sum(), geometry=aoi, scale=250, maxPixels=1e9, bestEffort=True
        ).getInfo().get('area', 0)
        score_thresholds.append({'threshold': thresh, 'area_ha': round(area, 1)})

    # 10. Suitability stats
    tick('Computing suitability statistics...')
    suit_stats = suitability.reduceRegion(
        reducer=ee.Reducer.mean().combine(ee.Reducer.min(),'',True)
                  .combine(ee.Reducer.max(),'',True).combine(ee.Reducer.stdDev(),'',True),
        geometry=aoi, scale=250, maxPixels=1e9, bestEffort=True).getInfo()

    # 11. Slope stats
    tick('Computing slope statistics...')
    slope_stats = slope.reduceRegion(
        reducer=ee.Reducer.mean().combine(ee.Reducer.max(),'',True)
                  .combine(ee.Reducer.percentile([25,50,75]),'',True),
        geometry=aoi, scale=250, maxPixels=1e9, bestEffort=True).getInfo()

    # 12. Water stats
    tick('Computing water distance statistics...')
    water_stats = dist_to_water.reduceRegion(
        reducer=ee.Reducer.min().combine(ee.Reducer.mean(),'',True),
        geometry=aoi, scale=250, maxPixels=1e9, bestEffort=True).getInfo()

    # 13. Electricity stats
    tick('Computing electricity distance...')
    elec_stats = dist_to_grid.reduceRegion(
        reducer=ee.Reducer.min().combine(ee.Reducer.mean(),'',True),
        geometry=aoi, scale=500, maxPixels=1e9).getInfo()

    # 14. Best area polygon (skip if no target set)
    if target_ha is not None:
        tick('Extracting best area polygon...')
        best_area_geojson = _extract_best_area(suitability, aoi, target, score_thresholds)
    else:
        tick('Skipping best area extraction (no target set)...')
        best_area_geojson = {'type': 'FeatureCollection', 'features': []}

    # 15. Zone polygons
    tick('Vectorising zone boundaries...')
    zones_geojson = _zones_to_geojson(zones, aoi)

    # 16-21. Component score means (6 calls)
    component_means = {}
    score_names = [
        ('slope_score',    slope_score,    'Slope scores'),
        ('water_score',    water_score,    'Water scores'),
        ('elec_score',     elec_score,     'Electricity scores'),
        ('wetness_score',  wetness_score,  'Terrain wetness'),
        ('clearing_score', clearing_score, 'Clearing cost scores'),
        ('flood_score',    flood_score,    'Flood risk scores'),
    ]
    for name, img, label in score_names:
        tick(f'Finalising {label}...')
        val = img.reduceRegion(
            reducer=ee.Reducer.mean(), geometry=aoi, scale=250, maxPixels=1e9, bestEffort=True
        ).getInfo()
        component_means[name] = round(list(val.values())[0] or 0, 2)

    return {
        'zones_geojson':     zones_geojson,
        'best_area_geojson': best_area_geojson,
        'zone_areas':        zone_areas,
        'score_thresholds':  score_thresholds,
        'suit_stats':        suit_stats,
        'slope_stats':       slope_stats,
        'water_stats':       water_stats,
        'elec_stats':        elec_stats,
        'component_means':   component_means,
        'crop_config':       cfg,
        'target_ha':         target,
        'buffer_m':          buffer_m,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _threshold_score(image, thresholds, name):
    score = ee.Image(0)
    prev  = 0
    for limit, val in thresholds:
        if prev == 0:
            score = score.where(image.lt(limit), val)
        else:
            score = score.where(image.gte(prev).And(image.lt(limit)), val)
        prev = limit
    return score.rename(name)


def _clearing_score(tree_cover, worldcover, crop_name):
    score = (ee.Image(5)
        .where(tree_cover.lte(10), 10)
        .where(tree_cover.gt(10).And(tree_cover.lte(25)), 8)
        .where(tree_cover.gt(25).And(tree_cover.lte(50)), 5)
        .where(tree_cover.gt(50).And(tree_cover.lte(75)), 2)
        .where(tree_cover.gt(75), 0)
        .where(worldcover.eq(30), 10)
        .where(worldcover.eq(40), 9)
        .where(worldcover.eq(80), 0))
    if crop_name == 'Maïs pluvial':
        score = score.where(worldcover.eq(90), 2)
    return score.rename('score_clearing')


def _flood_score(flow_acc, stream_threshold):
    on_channel = flow_acc.gt(stream_threshold * 5)
    flood_zone  = on_channel.focal_max(radius=3, units='pixels')
    return (flood_zone.multiply(-1).add(1).multiply(10)
            .clamp(0, 10).where(on_channel, 0).rename('score_flood'))


def _extract_best_area(suitability, aoi, target_ha, score_thresholds):
    best_thresh = 5.0
    for item in sorted(score_thresholds, key=lambda x: x['threshold'], reverse=True):
        if item['area_ha'] <= target_ha * 1.2:
            best_thresh = item['threshold']
            break
    best_mask = suitability.gte(best_thresh).selfMask()
    vectors   = best_mask.reduceToVectors(
        geometry=aoi, scale=90, geometryType='polygon',
        eightConnected=True, maxPixels=1e10, labelProperty='zone')
    try:
        return vectors.getInfo()
    except Exception:
        return {'type': 'FeatureCollection', 'features': []}


def _zones_to_geojson(zones, aoi):
    try:
        vectors = zones.reduceToVectors(
            geometry=aoi, scale=60, geometryType='polygon',
            eightConnected=False, maxPixels=1e10, labelProperty='zone')
        return vectors.getInfo()
    except Exception:
        return {'type': 'FeatureCollection', 'features': []}
