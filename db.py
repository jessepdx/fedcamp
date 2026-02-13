"""
db.py — Data access layer for RV Camping Finder

All database queries live here. Flask routes call these functions
and receive plain dicts/lists. No Flask dependencies in this module.
"""

import math
import re
import sqlite3

DB_PATH = "ridb.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.create_function("radians", 1, math.radians)
    conn.create_function("cos", 1, math.cos)
    conn.create_function("sin", 1, math.sin)
    conn.create_function("acos", 1, math.acos)
    return conn


# ------------------------------------------------------------------
# State list (for search dropdown)
# ------------------------------------------------------------------

def get_states(conn):
    rows = conn.execute(
        "SELECT state_code, facility_count FROM n_state_cache ORDER BY state_code"
    ).fetchall()
    return [dict(r) for r in rows]


# ------------------------------------------------------------------
# Search by state
# ------------------------------------------------------------------

def search_by_state(conn, state_code, camping_types=None,
                    tag_filters=None, agencies=None,
                    road_access=None, seasonal_status=None, fire_status=None,
                    min_rv_length=None,
                    limit=25, offset=0):
    if not camping_types:
        camping_types = ["DEVELOPED"]

    sql = """
        SELECT
            r.facility_id, r.facility_name, r.org_abbrev, r.camping_type,
            r.latitude, r.longitude, r.total_campsites,
            r.rv_type_sites, r.sites_accepting_rv,
            r.has_full_hookup, r.has_electric_hookup,
            r.has_water_hookup, r.has_sewer_hookup, r.max_amps,
            r.max_rv_length, r.pullthrough_sites, r.backin_sites,
            r.surface_predominant, r.reservable, r.full_hookup_sites,
            r.electric_hookup_sites, r.camping_type_confidence,
            c.road_access, c.driveway_surface, c.seasonal_status,
            c.fire_status, c.elevation_ft, c.boondock_accessibility,
            fa.city, fa.state_code,
            p.photo_url
        FROM n_facility_rollup r
        JOIN n_facility_conditions c ON r.facility_id = c.facility_id
        LEFT JOIN facility_addresses fa
            ON r.facility_id = fa.facility_id AND fa.address_type = 'Physical'
        LEFT JOIN n_facility_photo p ON r.facility_id = p.facility_id
        WHERE fa.state_code = ?
          AND r.camping_type IN ({})
    """.format(','.join('?' * len(camping_types)))
    params = [state_code] + camping_types

    # Agency filter
    if agencies:
        sql += "  AND r.org_abbrev IN ({})\n".format(','.join('?' * len(agencies)))
        params.extend(agencies)

    # Condition filters
    if road_access:
        sql += "  AND c.road_access IN ({})\n".format(','.join('?' * len(road_access)))
        params.extend(road_access)

    if seasonal_status:
        sql += "  AND c.seasonal_status IN ({})\n".format(','.join('?' * len(seasonal_status)))
        params.extend(seasonal_status)

    if fire_status:
        sql += "  AND c.fire_status IN ({})\n".format(','.join('?' * len(fire_status)))
        params.extend(fire_status)

    if min_rv_length:
        sql += "  AND (r.max_rv_length >= ? OR r.max_rv_length IS NULL)\n"
        params.append(min_rv_length)

    # Tag filters
    if tag_filters:
        for tag in tag_filters:
            sql += """
          AND EXISTS (SELECT 1 FROM n_facility_tags t
                      WHERE t.facility_id = r.facility_id AND t.tag = ?)
            """
            params.append(tag)

    sql += """
        ORDER BY r.total_campsites DESC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])

    rows = conn.execute(sql, params).fetchall()
    results = [dict(r) for r in rows]

    # Attach tags to each result
    _attach_top_tags(conn, results)

    return results


# ------------------------------------------------------------------
# Search by location (lat/lon + radius)
# ------------------------------------------------------------------

def search_by_location(conn, lat, lon, radius_miles=100,
                       camping_types=None, tag_filters=None,
                       agencies=None,
                       road_access=None, seasonal_status=None, fire_status=None,
                       min_rv_length=None,
                       limit=25, offset=0):
    if not camping_types:
        camping_types = ["DEVELOPED"]

    # Bounding box
    lat_delta = radius_miles / 69.0
    lon_delta = radius_miles / (69.0 * max(math.cos(math.radians(lat)), 0.01))
    lat_min, lat_max = lat - lat_delta, lat + lat_delta
    lon_min, lon_max = lon - lon_delta, lon + lon_delta

    # Haversine expression (reused in WHERE and SELECT)
    haversine = """(3959 * acos(
                min(1.0, max(-1.0,
                    cos(radians(?)) * cos(radians(r.latitude))
                    * cos(radians(r.longitude) - radians(?))
                    + sin(radians(?)) * sin(radians(r.latitude))
                ))))"""
    hav_params = [lat, lon, lat]

    sql = """
        SELECT
            r.facility_id, r.facility_name, r.org_abbrev, r.camping_type,
            r.latitude, r.longitude, r.total_campsites,
            r.rv_type_sites, r.sites_accepting_rv,
            r.has_full_hookup, r.has_electric_hookup,
            r.has_water_hookup, r.has_sewer_hookup, r.max_amps,
            r.max_rv_length, r.pullthrough_sites, r.backin_sites,
            r.surface_predominant, r.reservable, r.full_hookup_sites,
            r.electric_hookup_sites, r.camping_type_confidence,
            c.road_access, c.driveway_surface, c.seasonal_status,
            c.fire_status, c.elevation_ft, c.boondock_accessibility,
            fa.city, fa.state_code,
            p.photo_url,
            {} AS distance_miles
        FROM n_facility_rollup r
        JOIN n_facility_conditions c ON r.facility_id = c.facility_id
        LEFT JOIN facility_addresses fa
            ON r.facility_id = fa.facility_id AND fa.address_type = 'Physical'
        LEFT JOIN n_facility_photo p ON r.facility_id = p.facility_id
        WHERE r.coords_valid = 1
          AND r.latitude BETWEEN ? AND ?
          AND r.longitude BETWEEN ? AND ?
          AND r.camping_type IN ({})
          AND {} <= ?
    """.format(haversine, ','.join('?' * len(camping_types)), haversine)
    params = hav_params + [lat_min, lat_max, lon_min, lon_max] + camping_types + hav_params + [radius_miles]

    # Agency filter
    if agencies:
        sql += "  AND r.org_abbrev IN ({})\n".format(','.join('?' * len(agencies)))
        params.extend(agencies)

    # Condition filters
    if road_access:
        sql += "  AND c.road_access IN ({})\n".format(','.join('?' * len(road_access)))
        params.extend(road_access)

    if seasonal_status:
        sql += "  AND c.seasonal_status IN ({})\n".format(','.join('?' * len(seasonal_status)))
        params.extend(seasonal_status)

    if fire_status:
        sql += "  AND c.fire_status IN ({})\n".format(','.join('?' * len(fire_status)))
        params.extend(fire_status)

    if min_rv_length:
        sql += "  AND (r.max_rv_length >= ? OR r.max_rv_length IS NULL)\n"
        params.append(min_rv_length)

    if tag_filters:
        for tag in tag_filters:
            sql += """
          AND EXISTS (SELECT 1 FROM n_facility_tags t
                      WHERE t.facility_id = r.facility_id AND t.tag = ?)
            """
            params.append(tag)

    sql += """
        ORDER BY distance_miles ASC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])

    rows = conn.execute(sql, params).fetchall()
    results = [dict(r) for r in rows]
    _attach_top_tags(conn, results)
    return results


# ------------------------------------------------------------------
# Facility detail
# ------------------------------------------------------------------

def get_facility(conn, facility_id):
    row = conn.execute("""
        SELECT
            r.*,
            c.road_access, c.driveway_surface, c.seasonal_status,
            c.fire_status, c.elevation_ft, c.boondock_accessibility,
            c.max_rv_length AS cond_max_rv_length,
            f.facility_description, f.facility_directions,
            f.facility_reservation_url, f.facility_phone, f.facility_email,
            f.facility_use_fee, f.stay_limit, f.facility_ada_access,
            fa.city, fa.state_code, fa.postal_code,
            fa.street1,
            p.photo_url
        FROM n_facility_rollup r
        JOIN n_facility_conditions c ON r.facility_id = c.facility_id
        LEFT JOIN facilities f ON r.facility_id = f.facility_id
        LEFT JOIN facility_addresses fa
            ON r.facility_id = fa.facility_id AND fa.address_type = 'Physical'
        LEFT JOIN n_facility_photo p ON r.facility_id = p.facility_id
        WHERE r.facility_id = ?
    """, (facility_id,)).fetchone()

    if not row:
        return None

    data = dict(row)

    # Clean fee field: strip HTML tags, collapse whitespace, None if empty
    raw_fee = data.get("facility_use_fee") or ""
    clean_fee = re.sub(r"<[^>]+>", " ", raw_fee).strip()
    clean_fee = re.sub(r"\s+", " ", clean_fee)
    data["facility_use_fee"] = clean_fee or None

    # Tags grouped by category
    tags = conn.execute("""
        SELECT tag, tag_category, display_order
        FROM n_facility_tags
        WHERE facility_id = ?
        ORDER BY display_order, tag
    """, (facility_id,)).fetchall()

    tag_groups = {}
    for t in tags:
        cat = t["tag_category"]
        if cat not in tag_groups:
            tag_groups[cat] = []
        tag_groups[cat].append(t["tag"])

    data["tags"] = tag_groups
    data["tag_list"] = [t["tag"] for t in tags]

    # Activities
    activities = conn.execute("""
        SELECT activity_name FROM facility_activities
        WHERE facility_id = ?
        ORDER BY activity_name
    """, (facility_id,)).fetchall()
    data["activities"] = [a["activity_name"] for a in activities]

    # Photos
    photos = conn.execute("""
        SELECT m.url, m.title, m.description
        FROM media m
        JOIN campsites c ON m.entity_id = c.campsite_id
        WHERE c.facility_id = ?
          AND m.entity_type = 'Campsite'
          AND m.media_type = 'Image'
        ORDER BY m.is_primary DESC
        LIMIT 12
    """, (facility_id,)).fetchall()
    data["photos"] = [dict(ph) for ph in photos]

    return data


# ------------------------------------------------------------------
# Nearby facilities
# ------------------------------------------------------------------

def get_nearby(conn, facility_id, lat, lon, radius_miles=50, limit=8):
    if not lat or not lon:
        return []

    lat_delta = radius_miles / 69.0
    lon_delta = radius_miles / (69.0 * max(math.cos(math.radians(lat)), 0.01))

    haversine = """(3959 * acos(
                min(1.0, max(-1.0,
                    cos(radians(?)) * cos(radians(r.latitude))
                    * cos(radians(r.longitude) - radians(?))
                    + sin(radians(?)) * sin(radians(r.latitude))
                ))))"""

    rows = conn.execute("""
        SELECT
            r.facility_id, r.facility_name, r.org_abbrev, r.camping_type,
            r.latitude, r.longitude, r.max_rv_length, r.total_campsites,
            c.road_access, c.boondock_accessibility,
            fa.city, fa.state_code,
            {} AS distance_miles
        FROM n_facility_rollup r
        JOIN n_facility_conditions c ON r.facility_id = c.facility_id
        LEFT JOIN facility_addresses fa
            ON r.facility_id = fa.facility_id AND fa.address_type = 'Physical'
        WHERE r.facility_id != ?
          AND r.coords_valid = 1
          AND r.camping_type IN ('DEVELOPED', 'PRIMITIVE', 'DISPERSED')
          AND r.latitude BETWEEN ? AND ?
          AND r.longitude BETWEEN ? AND ?
          AND {} <= ?
        ORDER BY distance_miles ASC
        LIMIT ?
    """.format(haversine, haversine),
        (lat, lon, lat,
         facility_id,
         lat - lat_delta, lat + lat_delta,
         lon - lon_delta, lon + lon_delta,
         lat, lon, lat,
         radius_miles, limit)).fetchall()

    return [dict(r) for r in rows]


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _attach_top_tags(conn, results, max_tags=4):
    """Attach top N tags to each result dict (avoids N+1 query)."""
    if not results:
        return

    fac_ids = [r["facility_id"] for r in results]
    placeholders = ",".join("?" * len(fac_ids))

    rows = conn.execute("""
        SELECT facility_id, tag, tag_category
        FROM n_facility_tags
        WHERE facility_id IN ({})
        ORDER BY display_order, tag
    """.format(placeholders), fac_ids).fetchall()

    tag_map = {}
    for r in rows:
        fid = r["facility_id"]
        if fid not in tag_map:
            tag_map[fid] = []
        tag_map[fid].append(r["tag"])

    for r in results:
        all_tags = tag_map.get(r["facility_id"], [])
        r["top_tags"] = all_tags[:max_tags]
        r["tag_count"] = len(all_tags)


def get_search_count(conn, state_code=None, lat=None, lon=None,
                     radius_miles=100, camping_types=None,
                     tag_filters=None, agencies=None,
                     road_access=None, seasonal_status=None, fire_status=None,
                     min_rv_length=None):
    """Get total count for pagination (without LIMIT/OFFSET)."""
    if not camping_types:
        camping_types = ["DEVELOPED"]

    if state_code:
        sql = """
            SELECT COUNT(DISTINCT r.facility_id)
            FROM n_facility_rollup r
            JOIN n_facility_conditions c ON r.facility_id = c.facility_id
            LEFT JOIN facility_addresses fa
                ON r.facility_id = fa.facility_id AND fa.address_type = 'Physical'
            WHERE fa.state_code = ?
              AND r.camping_type IN ({})
        """.format(','.join('?' * len(camping_types)))
        params = [state_code] + camping_types
    elif lat is not None and lon is not None:
        lat_delta = radius_miles / 69.0
        lon_delta = radius_miles / (69.0 * max(math.cos(math.radians(lat)), 0.01))
        sql = """
            SELECT COUNT(*)
            FROM n_facility_rollup r
            JOIN n_facility_conditions c ON r.facility_id = c.facility_id
            WHERE r.coords_valid = 1
              AND r.latitude BETWEEN ? AND ?
              AND r.longitude BETWEEN ? AND ?
              AND r.camping_type IN ({})
        """.format(','.join('?' * len(camping_types)))
        params = [lat - lat_delta, lat + lat_delta,
                  lon - lon_delta, lon + lon_delta] + camping_types
    else:
        return 0

    if agencies:
        sql += "  AND r.org_abbrev IN ({})\n".format(','.join('?' * len(agencies)))
        params.extend(agencies)

    if road_access:
        sql += "  AND c.road_access IN ({})\n".format(','.join('?' * len(road_access)))
        params.extend(road_access)

    if seasonal_status:
        sql += "  AND c.seasonal_status IN ({})\n".format(','.join('?' * len(seasonal_status)))
        params.extend(seasonal_status)

    if fire_status:
        sql += "  AND c.fire_status IN ({})\n".format(','.join('?' * len(fire_status)))
        params.extend(fire_status)

    if min_rv_length:
        sql += "  AND (r.max_rv_length >= ? OR r.max_rv_length IS NULL)\n"
        params.append(min_rv_length)

    if tag_filters:
        for tag in tag_filters:
            sql += """
          AND EXISTS (SELECT 1 FROM n_facility_tags t
                      WHERE t.facility_id = r.facility_id AND t.tag = ?)
            """
            params.append(tag)

    return conn.execute(sql, params).fetchone()[0]
