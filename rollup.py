"""
Phase 2: Facility-Level Rollup for RV Camping Finder

Aggregates campsite-level data from n_campsite + n_campsite_equipment
into a single n_facility_rollup table — one row per facility.

Includes camping_type inference (DEVELOPED/PRIMITIVE/DISPERSED/DAY_USE/NON_CAMPING)
and description-based signal enrichment.

Dependencies: Phase 1 (normalize.py) must have run first.

Usage:
    python rollup.py
"""

import sqlite3
import sys
import time
from datetime import datetime, timezone

DB_PATH = "ridb.db"

# ============================================================
# SCHEMA
# ============================================================

SCHEMA_SQL = """
DROP TABLE IF EXISTS n_facility_rollup;
CREATE TABLE IF NOT EXISTS n_facility_rollup (
    facility_id             TEXT PRIMARY KEY,

    -- Identity
    facility_name           TEXT,
    facility_type           TEXT,
    org_abbrev              TEXT,
    org_name                TEXT,
    parent_rec_area_id      TEXT,
    reservable              INTEGER,

    -- Coordinates
    latitude                REAL,
    longitude               REAL,
    coords_valid            INTEGER,

    -- Site counts
    total_campsites         INTEGER NOT NULL DEFAULT 0,
    overnight_sites         INTEGER NOT NULL DEFAULT 0,
    day_use_sites           INTEGER NOT NULL DEFAULT 0,

    -- Campsite type breakdown
    rv_type_sites           INTEGER NOT NULL DEFAULT 0,
    tent_only_sites         INTEGER NOT NULL DEFAULT 0,
    standard_sites          INTEGER NOT NULL DEFAULT 0,
    group_sites             INTEGER NOT NULL DEFAULT 0,
    cabin_sites             INTEGER NOT NULL DEFAULT 0,
    equestrian_sites        INTEGER NOT NULL DEFAULT 0,
    walk_hike_boat_sites    INTEGER NOT NULL DEFAULT 0,
    management_sites        INTEGER NOT NULL DEFAULT 0,

    -- Equipment-derived
    sites_accepting_rv      INTEGER NOT NULL DEFAULT 0,
    sites_accepting_tent    INTEGER NOT NULL DEFAULT 0,

    -- Hookups
    has_water_hookup        INTEGER NOT NULL DEFAULT 0,
    has_sewer_hookup        INTEGER NOT NULL DEFAULT 0,
    has_electric_hookup     INTEGER NOT NULL DEFAULT 0,
    has_full_hookup         INTEGER NOT NULL DEFAULT 0,
    water_hookup_sites      INTEGER NOT NULL DEFAULT 0,
    sewer_hookup_sites      INTEGER NOT NULL DEFAULT 0,
    electric_hookup_sites   INTEGER NOT NULL DEFAULT 0,
    full_hookup_sites       INTEGER NOT NULL DEFAULT 0,
    max_amps                INTEGER,

    -- Driveway
    has_pullthrough         INTEGER NOT NULL DEFAULT 0,
    pullthrough_sites       INTEGER NOT NULL DEFAULT 0,
    backin_sites            INTEGER NOT NULL DEFAULT 0,
    parallel_sites          INTEGER NOT NULL DEFAULT 0,
    paved_sites             INTEGER NOT NULL DEFAULT 0,
    gravel_sites            INTEGER NOT NULL DEFAULT 0,
    surface_predominant     TEXT,

    -- Vehicle length (three sources + resolved)
    max_rv_length           INTEGER,
    max_rv_length_equip     INTEGER,
    max_rv_length_attr      INTEGER,
    max_rv_length_desc      INTEGER,

    -- Access
    site_access_predominant TEXT,
    drive_in_sites          INTEGER NOT NULL DEFAULT 0,
    walk_in_sites           INTEGER NOT NULL DEFAULT 0,
    hike_in_sites           INTEGER NOT NULL DEFAULT 0,
    boat_in_sites           INTEGER NOT NULL DEFAULT 0,

    -- Description signals (from n_facility)
    desc_mentions_rv            INTEGER NOT NULL DEFAULT 0,
    desc_mentions_hookups       INTEGER NOT NULL DEFAULT 0,
    desc_mentions_full_hookup   INTEGER NOT NULL DEFAULT 0,
    desc_mentions_electric      INTEGER NOT NULL DEFAULT 0,
    desc_mentions_dump_station  INTEGER NOT NULL DEFAULT 0,
    desc_mentions_pull_through  INTEGER NOT NULL DEFAULT 0,
    desc_mentions_generator     INTEGER NOT NULL DEFAULT 0,
    desc_rv_not_recommended     INTEGER NOT NULL DEFAULT 0,
    desc_road_paved             INTEGER NOT NULL DEFAULT 0,
    desc_road_gravel            INTEGER NOT NULL DEFAULT 0,
    desc_road_dirt              INTEGER NOT NULL DEFAULT 0,
    desc_road_high_clearance    INTEGER NOT NULL DEFAULT 0,
    desc_road_4wd               INTEGER NOT NULL DEFAULT 0,
    desc_mentions_dispersed     INTEGER NOT NULL DEFAULT 0,
    desc_mentions_primitive     INTEGER NOT NULL DEFAULT 0,
    desc_mentions_vault_toilet  INTEGER NOT NULL DEFAULT 0,
    desc_mentions_potable_water INTEGER NOT NULL DEFAULT 0,

    -- Condition signals (from n_facility)
    desc_seasonal_closure       INTEGER NOT NULL DEFAULT 0,
    desc_winter_closure         INTEGER NOT NULL DEFAULT 0,
    desc_mentions_snow          INTEGER NOT NULL DEFAULT 0,
    desc_fire_restrictions      INTEGER NOT NULL DEFAULT 0,
    desc_mentions_elevation     INTEGER NOT NULL DEFAULT 0,
    desc_elevation_ft           INTEGER,
    desc_remote_no_cell         INTEGER NOT NULL DEFAULT 0,
    desc_flood_risk             INTEGER NOT NULL DEFAULT 0,

    -- Campfire aggregation
    campfire_yes_sites          INTEGER NOT NULL DEFAULT 0,
    campfire_no_sites           INTEGER NOT NULL DEFAULT 0,

    -- Activity signals
    has_camping_activity    INTEGER NOT NULL DEFAULT 0,
    has_rv_activity         INTEGER NOT NULL DEFAULT 0,
    has_dispersed_activity  INTEGER NOT NULL DEFAULT 0,

    -- Classification
    camping_type            TEXT,
    camping_type_confidence TEXT,

    -- Metadata
    normalized_at           TEXT
);
"""

INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_nfr_type ON n_facility_rollup(camping_type);
CREATE INDEX IF NOT EXISTS idx_nfr_rv_len ON n_facility_rollup(max_rv_length);
CREATE INDEX IF NOT EXISTS idx_nfr_hookups ON n_facility_rollup(has_full_hookup, has_electric_hookup, max_amps);
CREATE INDEX IF NOT EXISTS idx_nfr_org ON n_facility_rollup(org_abbrev);
CREATE INDEX IF NOT EXISTS idx_nfr_coords ON n_facility_rollup(coords_valid, latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_nfr_pullthrough ON n_facility_rollup(has_pullthrough);
CREATE INDEX IF NOT EXISTS idx_nfr_rv_filter ON n_facility_rollup(camping_type, max_rv_length, has_electric_hookup);
"""


# ============================================================
# CAMPING TYPE INFERENCE
# ============================================================

def infer_camping_type(r):
    """
    Priority-ordered decision tree.
    r is a dict with all rollup fields.
    Returns (camping_type, confidence).
    """
    tc = r['total_campsites']
    overnight = r['overnight_sites']
    day_use = r['day_use_sites']
    ftype = r['facility_type'] or ''
    org = r['org_abbrev'] or ''
    resv = r['reservable']
    has_water = r['has_water_hookup']
    has_sewer = r['has_sewer_hookup']
    has_elec = r['has_electric_hookup']
    has_full = r['has_full_hookup']
    has_pt = r['has_pullthrough']
    paved = r['paved_sites']
    gravel = r['gravel_sites']
    drive_in = r['drive_in_sites']
    rv_accept = r['sites_accepting_rv']
    d_hookups = r['desc_mentions_hookups']
    d_full = r['desc_mentions_full_hookup']
    d_elec = r['desc_mentions_electric']
    d_dump = r['desc_mentions_dump_station']
    d_dispersed = r['desc_mentions_dispersed']
    d_primitive = r['desc_mentions_primitive']
    d_vault = r['desc_mentions_vault_toilet']
    d_dirt = r['desc_road_dirt']
    d_gravel = r['desc_road_gravel']
    has_camp_act = r['has_camping_activity']
    has_disp_act = r['has_dispersed_activity']

    # 1. NON_CAMPING: non-camping facility types with zero campsites
    if tc == 0 and ftype not in ('Campground', 'Facility'):
        return ('NON_CAMPING', 'HIGH')

    # 2. DAY_USE: all sites are day-use
    if tc > 0 and overnight == 0 and day_use > 0:
        return ('DAY_USE', 'HIGH')

    # 3. DEVELOPED: any hookups reported at campsite level
    if tc > 0 and (has_elec or has_water or has_sewer or has_full):
        return ('DEVELOPED', 'HIGH')

    # 4. DEVELOPED: pull-through + paved + meaningful sites
    if tc >= 5 and paved > 0 and has_pt:
        return ('DEVELOPED', 'HIGH')

    # 5. DEVELOPED: drive-in + surfaced + RV equipment
    if tc >= 5 and drive_in > 0 and (paved > 0 or gravel > 0) and rv_accept > 0:
        return ('DEVELOPED', 'MEDIUM')

    # 6. DEVELOPED from description signals
    if tc > 0 and (d_hookups or d_full or d_elec or d_dump):
        return ('DEVELOPED', 'MEDIUM')

    # 7. DISPERSED: BLM/FS, no campsites, description says dispersed
    if tc == 0 and org in ('BLM', 'FS') and d_dispersed:
        return ('DISPERSED', 'HIGH')

    # 8. DISPERSED: BLM/FS, no campsites, has dispersed activity
    if tc == 0 and org in ('BLM', 'FS') and has_disp_act:
        return ('DISPERSED', 'HIGH')

    # 9. DISPERSED: BLM/FS generic facility with camping activity but no sites
    if tc == 0 and org in ('BLM', 'FS') and ftype == 'Facility' and has_camp_act:
        return ('DISPERSED', 'MEDIUM')

    # 10. DISPERSED: BLM generic facility (low confidence)
    if tc == 0 and org == 'BLM' and ftype == 'Facility':
        return ('DISPERSED', 'LOW')

    # 11. PRIMITIVE: description says primitive, no hookups
    if tc > 0 and d_primitive and not has_elec and not has_water:
        return ('PRIMITIVE', 'HIGH')

    # 12. PRIMITIVE: overnight, no hookups, no pavement, vault/dirt signals
    if tc > 0 and overnight > 0 and not has_elec and not has_water and not has_sewer:
        if paved == 0 and (d_vault or d_dirt or d_gravel):
            return ('PRIMITIVE', 'MEDIUM')

    # 13. PRIMITIVE: overnight, no hookups, no RV equipment
    if tc > 0 and overnight > 0 and not has_elec and not has_water and not has_sewer:
        if rv_accept == 0:
            return ('PRIMITIVE', 'LOW')

    # 14. DEVELOPED fallback: any remaining facility with overnight sites
    if tc > 0 and overnight > 0:
        return ('DEVELOPED', 'LOW')

    # 15. DAY_USE fallback: campsites but no overnight
    if tc > 0:
        return ('DAY_USE', 'LOW')

    # 16. NON_CAMPING fallback
    return ('NON_CAMPING', 'LOW')


# ============================================================
# AGGREGATION
# ============================================================

def build_rollup(conn):
    """Build the facility rollup from normalized tables."""
    c = conn.cursor()

    # --- Step 1: Campsite aggregation ---
    print("  Aggregating campsites by facility...")
    c.execute("""
        SELECT
            facility_id,
            COUNT(*) AS total_campsites,
            SUM(CASE WHEN type_of_use = 'Overnight' THEN 1 ELSE 0 END),
            SUM(CASE WHEN type_of_use = 'Day' THEN 1 ELSE 0 END),

            SUM(CASE WHEN campsite_type LIKE '%RV%' THEN 1 ELSE 0 END),
            SUM(CASE WHEN campsite_type LIKE '%TENT ONLY%' THEN 1 ELSE 0 END),
            SUM(CASE WHEN campsite_type LIKE 'STANDARD%' THEN 1 ELSE 0 END),
            SUM(CASE WHEN campsite_type LIKE 'GROUP%' THEN 1 ELSE 0 END),
            SUM(CASE WHEN campsite_type IN (
                'CABIN NONELECTRIC','CABIN ELECTRIC','YURT','LOOKOUT',
                'OVERNIGHT SHELTER ELECTRIC','OVERNIGHT SHELTER NONELECTRIC',
                'SHELTER NONELECTRIC','SHELTER ELECTRIC'
            ) THEN 1 ELSE 0 END),
            SUM(CASE WHEN campsite_type LIKE 'EQUESTRIAN%' THEN 1 ELSE 0 END),
            SUM(CASE WHEN campsite_type IN ('WALK TO','HIKE TO','BOAT IN') THEN 1 ELSE 0 END),
            SUM(CASE WHEN campsite_type = 'MANAGEMENT' THEN 1 ELSE 0 END),

            SUM(CASE WHEN has_water_hookup = 1 THEN 1 ELSE 0 END),
            SUM(CASE WHEN has_sewer_hookup = 1 THEN 1 ELSE 0 END),
            SUM(CASE WHEN has_electric_hookup = 1 THEN 1 ELSE 0 END),
            SUM(CASE WHEN has_full_hookup = 1 THEN 1 ELSE 0 END),
            MAX(max_electric_amps),

            SUM(CASE WHEN driveway_entry = 'PULL_THROUGH' THEN 1 ELSE 0 END),
            SUM(CASE WHEN driveway_entry = 'BACK_IN' THEN 1 ELSE 0 END),
            SUM(CASE WHEN driveway_entry = 'PARALLEL' THEN 1 ELSE 0 END),
            SUM(CASE WHEN driveway_surface = 'PAVED' THEN 1 ELSE 0 END),
            SUM(CASE WHEN driveway_surface = 'GRAVEL' THEN 1 ELSE 0 END),

            MAX(max_vehicle_length),

            SUM(CASE WHEN site_access = 'DRIVE_IN' THEN 1 ELSE 0 END),
            SUM(CASE WHEN site_access = 'WALK_IN' THEN 1 ELSE 0 END),
            SUM(CASE WHEN site_access = 'HIKE_IN' THEN 1 ELSE 0 END),
            SUM(CASE WHEN site_access = 'BOAT_IN' THEN 1 ELSE 0 END),

            SUM(CASE WHEN campfire_allowed = 1 THEN 1 ELSE 0 END),
            SUM(CASE WHEN campfire_allowed = 0 THEN 1 ELSE 0 END)
        FROM n_campsite
        GROUP BY facility_id
    """)
    campsite_agg = {}
    for row in c.fetchall():
        campsite_agg[row[0]] = row[1:]  # keyed by facility_id

    # --- Step 2: Equipment aggregation ---
    print("  Aggregating equipment by facility...")
    c.execute("""
        SELECT
            nc.facility_id,
            COUNT(DISTINCT CASE WHEN ne.equipment_category IN
                ('RV','TRAILER','FIFTH_WHEEL','PICKUP_CAMPER','POP_UP','CAMPER_VAN')
                THEN nc.campsite_id END),
            COUNT(DISTINCT CASE WHEN ne.equipment_category = 'TENT'
                THEN nc.campsite_id END),
            MAX(CASE WHEN ne.equipment_category IN ('RV','TRAILER','FIFTH_WHEEL')
                THEN ne.max_length_ft END)
        FROM n_campsite nc
        JOIN n_campsite_equipment ne ON nc.campsite_id = ne.campsite_id
        GROUP BY nc.facility_id
    """)
    equip_agg = {}
    for row in c.fetchall():
        equip_agg[row[0]] = row[1:]

    # --- Step 3: Activity signals ---
    print("  Aggregating activities...")
    c.execute("""
        SELECT
            facility_id,
            MAX(CASE WHEN activity_name = 'CAMPING' THEN 1 ELSE 0 END),
            MAX(CASE WHEN activity_name = 'RECREATIONAL VEHICLES' THEN 1 ELSE 0 END),
            MAX(CASE WHEN activity_name = 'Dispersed Camping' THEN 1 ELSE 0 END)
        FROM facility_activities
        GROUP BY facility_id
    """)
    activity_agg = {}
    for row in c.fetchall():
        activity_agg[row[0]] = row[1:]

    # --- Step 4: Load all facilities + orgs + n_facility ---
    print("  Loading facilities...")
    c.execute("""
        SELECT
            f.facility_id,
            f.facility_name,
            f.facility_type,
            o.org_abbrev,
            o.org_name,
            f.parent_rec_area_id,
            f.reservable,
            nf.facility_latitude_clean,
            nf.facility_longitude_clean,
            nf.coords_valid,
            nf.desc_mentions_rv,
            nf.desc_mentions_hookups,
            nf.desc_mentions_full_hookup,
            nf.desc_mentions_electric,
            nf.desc_mentions_water_hookup,
            nf.desc_mentions_sewer,
            nf.desc_mentions_dump_station,
            nf.desc_mentions_pull_through,
            nf.desc_mentions_generator,
            nf.desc_rv_not_recommended,
            nf.desc_road_paved,
            nf.desc_road_gravel,
            nf.desc_road_dirt,
            nf.desc_road_high_clearance,
            nf.desc_road_4wd,
            nf.desc_mentions_dispersed,
            nf.desc_mentions_primitive,
            nf.desc_mentions_vault_toilet,
            nf.desc_mentions_potable_water,
            nf.desc_max_rv_length,
            nf.desc_seasonal_closure,
            nf.desc_winter_closure,
            nf.desc_mentions_snow,
            nf.desc_fire_restrictions,
            nf.desc_mentions_elevation,
            nf.desc_elevation_ft,
            nf.desc_remote_no_cell,
            nf.desc_flood_risk
        FROM facilities f
        LEFT JOIN organizations o ON f.parent_org_id = o.org_id
        LEFT JOIN n_facility nf ON f.facility_id = nf.facility_id
    """)
    facilities = c.fetchall()
    print(f"  Processing {len(facilities):,} facilities...")

    now = datetime.now(timezone.utc).isoformat()
    batch = []

    for fac in facilities:
        (fid, fname, ftype, org_abbrev, org_name, rec_area_id, reservable,
         lat, lon, coords_valid,
         d_rv, d_hookups, d_full_hookup, d_electric, d_water_hookup, d_sewer,
         d_dump, d_pullthrough, d_generator, d_rv_not_rec,
         d_road_paved, d_road_gravel, d_road_dirt, d_road_hc, d_road_4wd,
         d_dispersed, d_primitive, d_vault, d_potable_water,
         d_max_rv_len,
         d_seasonal, d_winter, d_snow, d_fire_restrict,
         d_elev_mention, d_elev_ft, d_no_cell, d_flood) = fac

        # Campsite aggregation (defaults if no campsites)
        ca = campsite_agg.get(fid)
        if ca:
            (total, overnight, day_use,
             rv_type, tent_only, standard, group, cabin, equestrian, whb, mgmt,
             water_sites, sewer_sites, elec_sites, full_sites, max_amps_val,
             pt_sites, bi_sites, par_sites, paved, gravel_ct,
             max_vlen_attr,
             drive_in, walk_in, hike_in, boat_in,
             campfire_yes, campfire_no) = ca
        else:
            (total, overnight, day_use,
             rv_type, tent_only, standard, group, cabin, equestrian, whb, mgmt,
             water_sites, sewer_sites, elec_sites, full_sites, max_amps_val,
             pt_sites, bi_sites, par_sites, paved, gravel_ct,
             max_vlen_attr,
             drive_in, walk_in, hike_in, boat_in,
             campfire_yes, campfire_no) = (
                0, 0, 0,
                0, 0, 0, 0, 0, 0, 0, 0,
                0, 0, 0, 0, None,
                0, 0, 0, 0, 0,
                None,
                0, 0, 0, 0,
                0, 0)

        # Equipment aggregation
        ea = equip_agg.get(fid)
        if ea:
            rv_accept, tent_accept, max_vlen_equip = ea
        else:
            rv_accept, tent_accept, max_vlen_equip = 0, 0, None

        # Activity signals
        aa = activity_agg.get(fid)
        if aa:
            has_camp_act, has_rv_act, has_disp_act = aa
        else:
            has_camp_act, has_rv_act, has_disp_act = 0, 0, 0

        # --- Derived fields ---

        # Boolean hookup flags (campsite data + description enrichment)
        has_water = 1 if water_sites > 0 else 0
        has_sewer = 1 if sewer_sites > 0 else 0
        has_elec = 1 if elec_sites > 0 else 0
        has_full = 1 if full_sites > 0 else 0
        has_pt = 1 if pt_sites > 0 else 0

        # Description enrichment: override booleans when description mentions features
        if not has_water and d_water_hookup:
            has_water = 1
        if not has_sewer and d_sewer:
            has_sewer = 1
        if not has_elec and d_electric:
            has_elec = 1
        if not has_full and d_full_hookup:
            has_full = 1
        if not has_pt and d_pullthrough:
            has_pt = 1

        # Surface predominant
        if paved > 0 and gravel_ct > 0:
            surface_pre = 'PAVED' if paved > gravel_ct else ('GRAVEL' if gravel_ct > paved else 'MIXED')
        elif paved > 0:
            surface_pre = 'PAVED'
        elif gravel_ct > 0:
            surface_pre = 'GRAVEL'
        else:
            surface_pre = None

        # Max RV length: best of three sources
        lengths = [v for v in [max_vlen_attr, max_vlen_equip, d_max_rv_len] if v is not None and v > 0]
        max_rv = max(lengths) if lengths else None

        # Clamp equipment length to 150 (same rule as normalize.py)
        if max_vlen_equip is not None and max_vlen_equip > 150:
            max_vlen_equip = None
        if max_rv is not None and max_rv > 150:
            max_rv = 150

        # Access predominant
        access_counts = {
            'DRIVE_IN': drive_in, 'WALK_IN': walk_in,
            'HIKE_IN': hike_in, 'BOAT_IN': boat_in,
        }
        nonzero = {k: v for k, v in access_counts.items() if v > 0}
        if nonzero:
            site_access_pre = max(nonzero, key=nonzero.get)
        else:
            site_access_pre = None

        # --- Camping type inference ---
        r = {
            'total_campsites': total,
            'overnight_sites': overnight,
            'day_use_sites': day_use,
            'facility_type': ftype,
            'org_abbrev': org_abbrev,
            'reservable': reservable,
            'has_water_hookup': has_water,
            'has_sewer_hookup': has_sewer,
            'has_electric_hookup': has_elec,
            'has_full_hookup': has_full,
            'has_pullthrough': has_pt,
            'paved_sites': paved,
            'gravel_sites': gravel_ct,
            'drive_in_sites': drive_in,
            'sites_accepting_rv': rv_accept,
            'desc_mentions_hookups': d_hookups,
            'desc_mentions_full_hookup': d_full_hookup,
            'desc_mentions_electric': d_electric,
            'desc_mentions_dump_station': d_dump,
            'desc_mentions_dispersed': d_dispersed,
            'desc_mentions_primitive': d_primitive,
            'desc_mentions_vault_toilet': d_vault,
            'desc_road_dirt': d_road_dirt,
            'desc_road_gravel': d_road_gravel,
            'has_camping_activity': has_camp_act,
            'has_dispersed_activity': has_disp_act,
        }
        camp_type, camp_conf = infer_camping_type(r)

        batch.append((
            fid, fname, ftype, org_abbrev, org_name, rec_area_id, reservable,
            lat, lon, coords_valid or 0,
            total, overnight, day_use,
            rv_type, tent_only, standard, group, cabin, equestrian, whb, mgmt,
            rv_accept, tent_accept,
            has_water, has_sewer, has_elec, has_full,
            water_sites, sewer_sites, elec_sites, full_sites, max_amps_val,
            has_pt, pt_sites, bi_sites, par_sites, paved, gravel_ct, surface_pre,
            max_rv, max_vlen_equip, max_vlen_attr, d_max_rv_len,
            site_access_pre, drive_in, walk_in, hike_in, boat_in,
            d_rv or 0, d_hookups or 0, d_full_hookup or 0, d_electric or 0,
            d_dump or 0, d_pullthrough or 0, d_generator or 0,
            d_rv_not_rec or 0,
            d_road_paved or 0, d_road_gravel or 0, d_road_dirt or 0,
            d_road_hc or 0, d_road_4wd or 0,
            d_dispersed or 0, d_primitive or 0, d_vault or 0, d_potable_water or 0,
            d_seasonal or 0, d_winter or 0, d_snow or 0, d_fire_restrict or 0,
            d_elev_mention or 0, d_elev_ft, d_no_cell or 0, d_flood or 0,
            campfire_yes, campfire_no,
            has_camp_act, has_rv_act, has_disp_act,
            camp_type, camp_conf,
            now,
        ))

    # --- Step 6: Handle orphaned facilities (in n_campsite but not in facilities table) ---
    known_fids = {row[0] for row in batch}
    orphan_fids = set(campsite_agg.keys()) - known_fids
    if orphan_fids:
        print(f"  Adding {len(orphan_fids):,} orphaned facilities ({sum(campsite_agg[f][0] for f in orphan_fids):,} campsites)...")
        for fid in orphan_fids:
            ca = campsite_agg[fid]
            (total, overnight, day_use,
             rv_type, tent_only, standard, group, cabin, equestrian, whb, mgmt,
             water_sites, sewer_sites, elec_sites, full_sites, max_amps_val,
             pt_sites, bi_sites, par_sites, paved, gravel_ct,
             max_vlen_attr,
             drive_in, walk_in, hike_in, boat_in,
             campfire_yes, campfire_no) = ca

            ea = equip_agg.get(fid)
            rv_accept, tent_accept, max_vlen_equip = ea if ea else (0, 0, None)
            aa = activity_agg.get(fid)
            has_camp_act, has_rv_act, has_disp_act = aa if aa else (0, 0, 0)

            has_water = 1 if water_sites > 0 else 0
            has_sewer = 1 if sewer_sites > 0 else 0
            has_elec = 1 if elec_sites > 0 else 0
            has_full = 1 if full_sites > 0 else 0
            has_pt = 1 if pt_sites > 0 else 0

            surface_pre = None
            if paved > 0 and gravel_ct > 0:
                surface_pre = 'PAVED' if paved > gravel_ct else ('GRAVEL' if gravel_ct > paved else 'MIXED')
            elif paved > 0:
                surface_pre = 'PAVED'
            elif gravel_ct > 0:
                surface_pre = 'GRAVEL'

            lengths = [v for v in [max_vlen_attr, max_vlen_equip] if v is not None and v > 0]
            max_rv = max(lengths) if lengths else None
            if max_vlen_equip is not None and max_vlen_equip > 150:
                max_vlen_equip = None
            if max_rv is not None and max_rv > 150:
                max_rv = 150

            access_counts = {'DRIVE_IN': drive_in, 'WALK_IN': walk_in, 'HIKE_IN': hike_in, 'BOAT_IN': boat_in}
            nonzero = {k: v for k, v in access_counts.items() if v > 0}
            site_access_pre = max(nonzero, key=nonzero.get) if nonzero else None

            # Minimal inference for orphans
            if total > 0 and (has_elec or has_water or has_sewer):
                camp_type, camp_conf = 'DEVELOPED', 'MEDIUM'
            elif total > 0 and overnight > 0:
                camp_type, camp_conf = 'DEVELOPED', 'LOW'
            elif total > 0:
                camp_type, camp_conf = 'DAY_USE', 'LOW'
            else:
                camp_type, camp_conf = 'NON_CAMPING', 'LOW'

            batch.append((
                fid, None, None, None, None, None, None,
                None, None, 0,
                total, overnight, day_use,
                rv_type, tent_only, standard, group, cabin, equestrian, whb, mgmt,
                rv_accept, tent_accept,
                has_water, has_sewer, has_elec, has_full,
                water_sites, sewer_sites, elec_sites, full_sites, max_amps_val,
                has_pt, pt_sites, bi_sites, par_sites, paved, gravel_ct, surface_pre,
                max_rv, max_vlen_equip, max_vlen_attr, None,
                site_access_pre, drive_in, walk_in, hike_in, boat_in,
                0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                0, 0, 0, 0, 0, None, 0, 0,
                campfire_yes, campfire_no,
                has_camp_act, has_rv_act, has_disp_act,
                camp_type, camp_conf,
                now,
            ))

    c.execute("DELETE FROM n_facility_rollup")
    placeholders = ','.join(['?'] * 81)
    c.executemany(f"INSERT INTO n_facility_rollup VALUES ({placeholders})", batch)
    print(f"  Inserted {len(batch):,} n_facility_rollup rows")


# ============================================================
# VALIDATION
# ============================================================

def validate(conn):
    c = conn.cursor()
    print("\n" + "=" * 60)
    print("  VALIDATION")
    print("=" * 60)
    errors = 0

    # 1. Row count (rollup = facilities + orphaned facility_ids from n_campsite)
    c.execute("SELECT COUNT(*) FROM facilities")
    fac_count = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT facility_id) FROM n_campsite WHERE facility_id NOT IN (SELECT facility_id FROM facilities)")
    orphan_count = c.fetchone()[0]
    expected = fac_count + orphan_count
    c.execute("SELECT COUNT(*) FROM n_facility_rollup")
    rollup_count = c.fetchone()[0]
    ok = expected == rollup_count
    print(f"  Row count: facilities={fac_count:,} + orphans={orphan_count:,} = {expected:,}  rollup={rollup_count:,}  {'OK' if ok else 'FAIL'}")
    if not ok:
        errors += 1

    # 2. Total campsites sum
    c.execute("SELECT COUNT(*) FROM n_campsite")
    nc_count = c.fetchone()[0]
    c.execute("SELECT SUM(total_campsites) FROM n_facility_rollup")
    rollup_sum = c.fetchone()[0] or 0
    ok = nc_count == rollup_sum
    print(f"  Campsite sum: n_campsite={nc_count:,}  rollup_sum={rollup_sum:,}  {'OK' if ok else 'FAIL'}")
    if not ok:
        errors += 1

    # 3. rv_sites + tent_only_sites <= total
    c.execute("""
        SELECT COUNT(*) FROM n_facility_rollup
        WHERE (rv_type_sites + tent_only_sites) > total_campsites
    """)
    bad = c.fetchone()[0]
    print(f"  rv+tent <= total: violations={bad}  {'OK' if bad == 0 else 'FAIL'}")
    if bad:
        errors += 1

    # 4. full_hookup_sites <= min(water, sewer, electric)
    c.execute("""
        SELECT COUNT(*) FROM n_facility_rollup
        WHERE full_hookup_sites > water_hookup_sites
           OR full_hookup_sites > sewer_hookup_sites
           OR full_hookup_sites > electric_hookup_sites
    """)
    bad = c.fetchone()[0]
    print(f"  full <= w/s/e: violations={bad}  {'OK' if bad == 0 else 'FAIL'}")
    if bad:
        errors += 1

    # 5. pullthrough + backin <= total
    c.execute("""
        SELECT COUNT(*) FROM n_facility_rollup
        WHERE (pullthrough_sites + backin_sites) > total_campsites
    """)
    bad = c.fetchone()[0]
    print(f"  pt+bi <= total: violations={bad}  {'OK' if bad == 0 else 'FAIL'}")
    if bad:
        errors += 1

    # 6. max_rv_length >= max from campsites
    c.execute("""
        SELECT COUNT(*) FROM (
            SELECT nc.facility_id, MAX(nc.max_vehicle_length) as cs_max
            FROM n_campsite nc
            WHERE nc.max_vehicle_length IS NOT NULL
            GROUP BY nc.facility_id
        ) sub
        JOIN n_facility_rollup fr ON sub.facility_id = fr.facility_id
        WHERE fr.max_rv_length < sub.cs_max
    """)
    bad = c.fetchone()[0]
    print(f"  max_rv_length hierarchy: violations={bad}  {'OK' if bad == 0 else 'FAIL'}")
    if bad:
        errors += 1

    # 7. No hookup count exceeds total campsites
    c.execute("""
        SELECT COUNT(*) FROM n_facility_rollup
        WHERE water_hookup_sites > total_campsites
           OR sewer_hookup_sites > total_campsites
           OR electric_hookup_sites > total_campsites
           OR full_hookup_sites > total_campsites
    """)
    bad = c.fetchone()[0]
    print(f"  hookup counts <= total: violations={bad}  {'OK' if bad == 0 else 'FAIL'}")
    if bad:
        errors += 1

    # --- Distribution Summaries ---
    print("\n  --- Camping Type Distribution ---")
    c.execute("""
        SELECT camping_type, camping_type_confidence, COUNT(*),
               SUM(total_campsites)
        FROM n_facility_rollup
        GROUP BY camping_type, camping_type_confidence
        ORDER BY camping_type, camping_type_confidence
    """)
    for ct, conf, cnt, sites in c.fetchall():
        print(f"    {ct:15s} {conf:8s}  {cnt:>6,} facilities  {sites or 0:>8,} sites")

    print("\n  --- By Organization (top 10) ---")
    c.execute("""
        SELECT org_abbrev, camping_type, COUNT(*), SUM(total_campsites)
        FROM n_facility_rollup
        WHERE total_campsites > 0
        GROUP BY org_abbrev, camping_type
        ORDER BY SUM(total_campsites) DESC
        LIMIT 15
    """)
    for org, ct, cnt, sites in c.fetchall():
        print(f"    {org or 'NULL':8s} {ct:15s}  {cnt:>5,} fac  {sites:>8,} sites")

    print("\n  --- Hookup Coverage (facilities with campsites) ---")
    c.execute("""
        SELECT
            COUNT(*) as total,
            SUM(has_water_hookup) as water,
            SUM(has_sewer_hookup) as sewer,
            SUM(has_electric_hookup) as electric,
            SUM(has_full_hookup) as full,
            SUM(has_pullthrough) as pullthrough
        FROM n_facility_rollup
        WHERE total_campsites > 0
    """)
    r = c.fetchone()
    print(f"    Facilities with campsites: {r[0]:,}")
    print(f"    Water hookup:   {r[1]:,} ({100*r[1]/r[0]:.1f}%)")
    print(f"    Sewer hookup:   {r[2]:,} ({100*r[2]/r[0]:.1f}%)")
    print(f"    Electric:       {r[3]:,} ({100*r[3]/r[0]:.1f}%)")
    print(f"    Full hookup:    {r[4]:,} ({100*r[4]/r[0]:.1f}%)")
    print(f"    Pull-through:   {r[5]:,} ({100*r[5]/r[0]:.1f}%)")

    print("\n  --- RV Length Coverage ---")
    c.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN max_rv_length IS NOT NULL THEN 1 ELSE 0 END) as with_len,
            SUM(CASE WHEN max_rv_length >= 40 THEN 1 ELSE 0 END) as class_a,
            SUM(CASE WHEN max_rv_length >= 30 AND max_rv_length < 40 THEN 1 ELSE 0 END) as class_c,
            SUM(CASE WHEN max_rv_length >= 20 AND max_rv_length < 30 THEN 1 ELSE 0 END) as trailer,
            SUM(CASE WHEN max_rv_length < 20 THEN 1 ELSE 0 END) as small_only
        FROM n_facility_rollup
        WHERE total_campsites > 0
    """)
    r = c.fetchone()
    print(f"    Facilities with campsites: {r[0]:,}")
    print(f"    Have max_rv_length:  {r[1]:,} ({100*r[1]/r[0]:.1f}%)")
    print(f"    Class A (40+ ft):    {r[2]:,}")
    print(f"    Class C (30-39 ft):  {r[3]:,}")
    print(f"    Trailer (20-29 ft):  {r[4]:,}")
    print(f"    Small only (<20 ft): {r[5]:,}")

    # Spot checks
    print("\n  --- Spot Checks (top full-hookup facilities) ---")
    c.execute("""
        SELECT facility_name, org_abbrev, total_campsites, full_hookup_sites,
               max_amps, max_rv_length, pullthrough_sites, camping_type
        FROM n_facility_rollup
        WHERE full_hookup_sites > 0
        ORDER BY full_hookup_sites DESC
        LIMIT 10
    """)
    print(f"    {'Name':40s} {'Org':5s} {'Sites':>6s} {'Full':>5s} {'Amps':>5s} {'MaxRV':>6s} {'PT':>4s} {'Type'}")
    for r in c.fetchall():
        print(f"    {(r[0] or '')[:40]:40s} {r[1] or '':5s} {r[2]:>6,} {r[3]:>5,} {str(r[4] or ''):>5s} {str(r[5] or ''):>6s} {r[6]:>4,} {r[7]}")

    print(f"\n  Validation errors: {errors}")
    return errors


# ============================================================
# MAIN
# ============================================================

def main():
    start = time.time()
    print(f"Phase 2 Facility Rollup — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Database: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    # Pre-flight: verify Phase 1 tables exist
    c = conn.cursor()
    for table in ['n_campsite', 'n_campsite_equipment', 'n_facility']:
        c.execute(f"SELECT COUNT(*) FROM {table}")
        cnt = c.fetchone()[0]
        print(f"  Pre-flight: {table} = {cnt:,} rows")
        if cnt == 0:
            print(f"  ERROR: {table} is empty. Run normalize.py first.")
            return 1

    print("\n1. Creating schema...")
    conn.executescript(SCHEMA_SQL)

    print("\n2. Building rollup...")
    build_rollup(conn)

    print("\n3. Creating indexes...")
    conn.executescript(INDEX_SQL)

    print("\n4. Updating metadata...")
    now = datetime.now(timezone.utc).isoformat()
    c.execute("DELETE FROM n_meta WHERE key LIKE 'rollup_%'")
    c.execute("SELECT COUNT(*) FROM n_facility_rollup")
    cnt = c.fetchone()[0]
    c.executemany("INSERT OR REPLACE INTO n_meta VALUES (?,?,?)", [
        ('rollup_last_run', now, now),
        ('rollup_count', str(cnt), now),
    ])

    conn.commit()
    elapsed = time.time() - start
    print(f"\nRollup complete in {elapsed:.1f}s")

    errors = validate(conn)
    conn.close()
    return 1 if errors > 0 else 0


if __name__ == '__main__':
    sys.exit(main())
