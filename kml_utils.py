"""
kml_utils.py
Parse KML, KMZ, and GeoJSON files into a list of coordinate rings
suitable for ee.Geometry.Polygon()
"""

import io
import json
import zipfile
import xml.etree.ElementTree as ET
from typing import List, Tuple

# KML namespace
KML_NS = '{http://www.opengis.net/kml/2.2}'


def parse_uploaded_file(file_bytes: bytes, filename: str) -> dict:
    """
    Parse any supported vector format.
    Returns GeoJSON-like dict: {type, coordinates, name, area_ha}
    """
    ext = filename.lower().split('.')[-1]

    if ext == 'kmz':
        kml_bytes = _extract_kml_from_kmz(file_bytes)
        return _parse_kml(kml_bytes, filename)
    elif ext == 'kml':
        return _parse_kml(file_bytes, filename)
    elif ext in ('geojson', 'json'):
        return _parse_geojson(file_bytes, filename)
    else:
        raise ValueError(f"Unsupported format: .{ext}. Please use KML, KMZ, or GeoJSON.")


def _extract_kml_from_kmz(kmz_bytes: bytes) -> bytes:
    """Unzip KMZ and return the doc.kml content."""
    with zipfile.ZipFile(io.BytesIO(kmz_bytes)) as z:
        # Find the first .kml file (usually doc.kml)
        kml_files = [n for n in z.namelist() if n.endswith('.kml')]
        if not kml_files:
            raise ValueError("No KML file found inside KMZ archive.")
        return z.read(kml_files[0])


def _parse_kml(kml_bytes: bytes, filename: str) -> dict:
    """Extract the first Polygon from a KML file."""
    try:
        root = ET.fromstring(kml_bytes)
    except ET.ParseError as e:
        raise ValueError(f"Could not parse KML: {e}")

    # Find the name of the first Placemark
    name = filename
    name_el = root.find(f'.//{KML_NS}Placemark/{KML_NS}name')
    if name_el is not None and name_el.text:
        name = name_el.text.strip()

    # Find coordinates element (inside Polygon > outerBoundaryIs > LinearRing)
    coord_paths = [
        f'.//{KML_NS}Polygon/{KML_NS}outerBoundaryIs/{KML_NS}LinearRing/{KML_NS}coordinates',
        f'.//{KML_NS}coordinates',
    ]

    coords_text = None
    for path in coord_paths:
        el = root.find(path)
        if el is not None and el.text:
            coords_text = el.text.strip()
            break

    if not coords_text:
        raise ValueError("No polygon coordinates found in KML file.")

    # Parse "lon,lat,alt lon,lat,alt ..." format
    coords = []
    for triplet in coords_text.split():
        parts = triplet.split(',')
        if len(parts) >= 2:
            try:
                lon, lat = float(parts[0]), float(parts[1])
                coords.append([lon, lat])
            except ValueError:
                continue

    if len(coords) < 3:
        raise ValueError(f"Not enough valid coordinates found (got {len(coords)}).")

    # Remove closing duplicate point if present
    if coords[0] == coords[-1] and len(coords) > 3:
        coords = coords[:-1]

    area_ha = _approx_area_ha(coords)

    return {
        'type': 'Polygon',
        'coordinates': [coords],
        'name': name,
        'area_ha': round(area_ha, 1),
        'centroid': _centroid(coords),
        'bounds': _bounds(coords),
    }


def _parse_geojson(geojson_bytes: bytes, filename: str) -> dict:
    """Extract the first polygon from a GeoJSON file."""
    try:
        data = json.loads(geojson_bytes)
    except json.JSONDecodeError as e:
        raise ValueError(f"Could not parse GeoJSON: {e}")

    name = filename
    coords = None

    # Handle FeatureCollection, Feature, or bare Geometry
    if data.get('type') == 'FeatureCollection':
        features = data.get('features', [])
        if not features:
            raise ValueError("GeoJSON FeatureCollection is empty.")
        feat = features[0]
        name = feat.get('properties', {}).get('name', filename)
        geom = feat.get('geometry', {})
    elif data.get('type') == 'Feature':
        name = data.get('properties', {}).get('name', filename)
        geom = data.get('geometry', {})
    else:
        geom = data

    gtype = geom.get('type', '')
    if gtype == 'Polygon':
        coords = geom['coordinates'][0]
    elif gtype == 'MultiPolygon':
        coords = geom['coordinates'][0][0]
    else:
        raise ValueError(f"GeoJSON geometry type '{gtype}' is not supported. Use Polygon or MultiPolygon.")

    # Ensure [lon, lat] format (no altitude)
    coords = [[c[0], c[1]] for c in coords]
    if coords[0] == coords[-1] and len(coords) > 3:
        coords = coords[:-1]

    area_ha = _approx_area_ha(coords)

    return {
        'type': 'Polygon',
        'coordinates': [coords],
        'name': name,
        'area_ha': round(area_ha, 1),
        'centroid': _centroid(coords),
        'bounds': _bounds(coords),
    }


def _approx_area_ha(coords: List[List[float]]) -> float:
    """Approximate polygon area in hectares using Shoelace formula in metres."""
    import math
    cx = sum(c[0] for c in coords) / len(coords)
    cy = sum(c[1] for c in coords) / len(coords)
    cos_lat = math.cos(math.radians(cy))
    pts_m = [((c[0] - cx) * 111320 * cos_lat,
              (c[1] - cy) * 110574) for c in coords]
    n = len(pts_m)
    area = 0
    for i in range(n):
        area += pts_m[i][0] * pts_m[(i+1) % n][1]
        area -= pts_m[(i+1) % n][0] * pts_m[i][1]
    return abs(area) / 2 / 10000


def _centroid(coords: List[List[float]]) -> Tuple[float, float]:
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return (sum(lons) / len(lons), sum(lats) / len(lats))


def _bounds(coords: List[List[float]]) -> dict:
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return {'minx': min(lons), 'maxx': max(lons),
            'miny': min(lats), 'maxy': max(lats)}
