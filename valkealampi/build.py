#!/usr/bin/env python3
"""Hakee Valkealammen reittidatan (LIPAS, OSM) ja rakentaa index.html + README-tilastot.

Ajo: python3 build.py   (vain Python-standardikirjasto)
"""
import json, math, os, subprocess, time, urllib.parse
from collections import defaultdict
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
UA = "valkealampi-reittikartta/1.0 (open data demo)"
ADDRESS = "Valkealammentie 200, 63510 Alajärvi"
HALF_KM = 3.0


def get(url, data=None):
    # curl eikä urllib: osa macOS:n Python-asennuksista ei saa TLS-kättelyä overpass-api.de:hen
    cmd = ["curl", "-sS", "--fail", "--max-time", "180", "-A", UA, url]
    if data is not None:
        cmd[1:1] = ["--data-binary", data]
    return json.loads(subprocess.run(cmd, check=True, capture_output=True).stdout)


# ---------- geometria ----------
def hav(a, b):
    R = 6371008.8
    la1, la2 = math.radians(a[1]), math.radians(b[1])
    dla, dlo = la2 - la1, math.radians(b[0] - a[0])
    h = math.sin(dla / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin(dlo / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def line_len(coords):
    return sum(hav(coords[i], coords[i + 1]) for i in range(len(coords) - 1))


def geom_len(g):
    if g["type"] == "LineString":
        return line_len(g["coordinates"])
    return sum(line_len(c) for c in g["coordinates"])


def clip_seg(p, q, b):
    """Liang–Barsky. b = (W,S,E,N). Palauttaa leikatun janan tai None."""
    x0, y0 = p; dx, dy = q[0] - x0, q[1] - y0
    t0, t1 = 0.0, 1.0
    for pp, qq in ((-dx, x0 - b[0]), (dx, b[2] - x0), (-dy, y0 - b[1]), (dy, b[3] - y0)):
        if pp == 0:
            if qq < 0:
                return None
        else:
            r = qq / pp
            if pp < 0:
                if r > t1: return None
                t0 = max(t0, r)
            else:
                if r < t0: return None
                t1 = min(t1, r)
    return ([x0 + t0 * dx, y0 + t0 * dy], [x0 + t1 * dx, y0 + t1 * dy], t0 > 0, t1 < 1)


def clip_line(coords, b):
    parts, cur = [], []
    for i in range(len(coords) - 1):
        c = clip_seg(coords[i][:2], coords[i + 1][:2], b)
        if c is None:
            if cur: parts.append(cur); cur = []
            continue
        a, z, cut_start, cut_end = c
        if not cur or cut_start:
            if cur: parts.append(cur)
            cur = [a]
        cur.append(z)
        if cut_end:
            parts.append(cur); cur = []
    if cur: parts.append(cur)
    parts = [[[round(x, 7), round(y, 7)] for x, y in p] for p in parts if len(p) > 1]
    if not parts: return None
    if len(parts) == 1: return {"type": "LineString", "coordinates": parts[0]}
    return {"type": "MultiLineString", "coordinates": parts}


def lines_of(g):
    return [g["coordinates"]] if g["type"] == "LineString" else g["coordinates"]


# ---------- 1. alue ----------
def area():
    q = urllib.parse.quote(ADDRESS)
    res = get(f"https://nominatim.openstreetmap.org/search?format=json&q={q}")
    lat, lon = float(res[0]["lat"]), float(res[0]["lon"])
    print(f"Geokoodattu: {res[0]['display_name']} -> {lat:.6f}, {lon:.6f}")
    dlat = HALF_KM / 111.32
    dlon = HALF_KM / (111.32 * math.cos(math.radians(lat)))
    bbox = (lon - dlon, lat - dlat, lon + dlon, lat + dlat)  # W,S,E,N
    print("BBOX (W,S,E,N, EPSG:4326): %.6f,%.6f,%.6f,%.6f" % bbox)
    time.sleep(1.1)
    lake = get("https://nominatim.openstreetmap.org/search?format=json&q=" + urllib.parse.quote("Valkealampi, Alajärvi"))
    lake = [l for l in lake if l.get("class") == "natural" and l.get("type") == "water"]
    if lake:
        llat, llon = float(lake[0]["lat"]), float(lake[0]["lon"])
        inside = bbox[1] < llat < bbox[3] and bbox[0] < llon < bbox[2]
        print(f"Valkealampi {llat:.5f},{llon:.5f} rajauksessa: {inside}")
        if not inside:
            lat, lon = llat, llon
            dlon = HALF_KM / (111.32 * math.cos(math.radians(lat)))
            bbox = (lon - dlon, lat - dlat, lon + dlon, lat + dlat)
            print("Keskipiste siirretty järvelle. Uusi BBOX: %.6f,%.6f,%.6f,%.6f" % bbox)
    return (lat, lon), bbox, res[0]["display_name"]


# ---------- 2. LIPAS ----------
DUPES = []  # (lipas_id, osa) – lähdedatassa toistuvat identtiset reittiosat

def lipas(bbox):
    W, S, E, N = bbox
    url = ("https://lipas.fi/geoserver/lipas/ows?service=WFS&version=1.0.0&request=GetFeature"
           "&typeName=lipas:lipas_kaikki_reitit&outputFormat=application/json&srsName=EPSG:4326"
           f"&bbox={W},{S},{E},{N},EPSG:4326")
    wfs = get(url)
    ids = {}
    for f in wfs["features"]:
        p = f["properties"]
        ids.setdefault(p["id"], p)
    print(f"LIPAS WFS: {len(wfs['features'])} reittiosaa, {len(ids)} liikuntapaikkaa")
    feats = []
    for lid, wp in ids.items():
        site = get(f"https://api.lipas.fi/v2/sports-sites/{lid}")
        props = site.get("properties", {})
        base = {
            "source": "LIPAS",
            "lipas_id": lid,
            "name": site.get("name"),
            "type_code": site["type"]["type-code"],
            "type_name": wp.get("tyyppi_nimi_fi"),
            "route_length_km": props.get("route-length-km"),
            "lit_route_length_km": props.get("lit-route-length-km"),
            "lit": ("kyllä" if props.get("lit-route-length-km") else "ei tietoa"),
            "maintainer": wp.get("yllapitaja"),
            "owner": wp.get("omistaja"),
            "municipality": wp.get("kunta_nimi_fi"),
        }
        seen = set()
        for i, gf in enumerate(site["location"]["geometries"]["features"]):
            g = clip_line(gf["geometry"]["coordinates"], bbox) if gf["geometry"]["type"] == "LineString" else None
            if not g: continue
            key = json.dumps(sorted(json.dumps([[round(x, 5), round(y, 5)] for x, y in l]) for l in lines_of(g)))
            rkey = json.dumps(sorted(json.dumps([[round(x, 5), round(y, 5)] for x, y in l[::-1]]) for l in lines_of(g)))
            if key in seen or rkey in seen:
                DUPES.append((lid, i + 1)); continue
            seen.add(key)
            p = dict(base, part=i + 1, length_m_in_bbox=round(geom_len(g)))
            feats.append({"type": "Feature", "properties": p, "geometry": g})
    return {"type": "FeatureCollection", "features": feats}, len(wfs["features"]), len(ids)


# ---------- 3. OSM ----------
OVERPASS_Q = ('[out:json][timeout:60];('
              'way["highway"~"^(path|footway|track|bridleway|cycleway)$"]({s},{w},{n},{e});'
              'way["piste:type"]({s},{w},{n},{e});'
              'relation["route"~"^(hiking|foot|mtb|ski|piste)$"]({s},{w},{n},{e});'
              ');out geom;')


def osm_category(t):
    if t.get("piste:type") == "nordic": return "latu"
    if t.get("piste:type"): return "rinne"
    hw = t.get("highway")
    if hw in ("path", "footway", "bridleway", "cycleway"): return "polku"
    if hw == "track": return "ajoura"
    return "muu"


def osm(bbox):
    W, S, E, N = bbox
    q = OVERPASS_Q.format(s=S, w=W, n=N, e=E)
    data = urllib.parse.urlencode({"data": q})
    res = get("https://overpass-api.de/api/interpreter", data=data)
    feats, nrel = [], 0
    for el in res["elements"]:
        t = el.get("tags", {})
        if el["type"] == "way":
            coords = [[n["lon"], n["lat"]] for n in el["geometry"]]
            g = clip_line(coords, bbox)
            if not g: continue
            cat = osm_category(t)
        elif el["type"] == "relation":
            nrel += 1
            lines = [[[n["lon"], n["lat"]] for n in m["geometry"]] for m in el.get("members", [])
                     if m["type"] == "way" and m.get("geometry")]
            parts = []
            for l in lines:
                c = clip_line(l, bbox)
                if c: parts += lines_of(c)
            if not parts: continue
            g = {"type": "MultiLineString", "coordinates": parts}
            cat = "reittirelaatio"
        else:
            continue
        p = {"source": "OSM", "osm_id": f"{el['type']}/{el['id']}", "category": cat,
             "name": t.get("name"), "highway": t.get("highway"), "piste_type": t.get("piste:type"),
             "route": t.get("route"), "lit": t.get("lit"), "length_m_in_bbox": round(geom_len(g)), "tags": t}
        feats.append({"type": "Feature", "properties": p, "geometry": g})
    print(f"OSM: {len(res['elements'])} elementtiä, {nrel} relaatiota, {len(feats)} kohdetta rajauksessa")
    return {"type": "FeatureCollection", "features": feats}, len(res["elements"]), nrel


# ---------- vertailu ----------
def densify(lines, step=10):
    pts = []
    for l in lines:
        for i in range(len(l) - 1):
            a, b = l[i], l[i + 1]
            d = hav(a, b); n = max(1, int(d // step))
            for k in range(n):
                pts.append(([a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n], d / n))
    return pts


def coverage(src_lines, ref_lines, lat0, tol=30):
    """Paljonko src-viivoista (m) on tol metrin päässä ref-viivoista."""
    kx, ky = 111320 * math.cos(math.radians(lat0)), 110574
    segs = []
    for l in ref_lines:
        for i in range(len(l) - 1):
            segs.append(((l[i][0] * kx, l[i][1] * ky), (l[i + 1][0] * kx, l[i + 1][1] * ky)))
    near = far = 0.0
    for p, w in densify(src_lines):
        px, py = p[0] * kx, p[1] * ky
        best = 1e18
        for (ax, ay), (bx, by) in segs:
            if abs(px - ax) > 300 and abs(px - bx) > 300: continue
            dx, dy = bx - ax, by - ay
            L = dx * dx + dy * dy
            t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
            d = (px - ax - t * dx) ** 2 + (py - ay - t * dy) ** 2
            if d < best: best = d
        if best <= tol * tol: near += w
        else: far += w
    return near, far


# ---------- 4. laavut ja kodat ----------
def shelter_kind(name, t):
    n = (name or "").lower()
    if "kota" in n: return "kota"
    if "laavu" in n or t.get("shelter_type") == "lean_to": return "laavu"
    if t.get("tourism") == "wilderness_hut": return "autiotupa"
    return "katos (tyyppi puuttuu)"


def shelters(bbox):
    W, S, E, N = bbox
    feats = []
    url = ("https://lipas.fi/geoserver/lipas/ows?service=WFS&version=1.0.0&request=GetFeature"
           "&typeName=lipas:lipas_301_laavu_kota_kammi&outputFormat=application/json&srsName=EPSG:4326"
           f"&bbox={W},{S},{E},{N},EPSG:4326")
    for f in get(url)["features"]:
        lid = f["properties"]["id"]
        site = get(f"https://api.lipas.fi/v2/sports-sites/{lid}")
        g = site["location"]["geometries"]["features"][0]["geometry"]
        pr = site.get("properties", {})
        feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(c, 7) for c in g["coordinates"][:2]]},
                      "properties": {"source": "LIPAS", "lipas_id": lid, "name": site.get("name"),
                                     "kind": shelter_kind(site.get("name"), {}),
                                     "type_code": site["type"]["type-code"], "type_name": f["properties"].get("tyyppi_nimi_fi"),
                                     "maintainer": f["properties"].get("yllapitaja"), "comment": site.get("comment"),
                                     "toilet": pr.get("toilet?"), "free_use": pr.get("free-use?")}})
    q = (f'[out:json][timeout:60];(nwr["amenity"="shelter"]({S},{W},{N},{E});'
         f'nwr["tourism"="wilderness_hut"]({S},{W},{N},{E}););out center tags;')
    for e in get("https://overpass-api.de/api/interpreter", data=urllib.parse.urlencode({"data": q}))["elements"]:
        c = e.get("center") or {"lat": e["lat"], "lon": e["lon"]}
        t = e.get("tags", {})
        feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [c["lon"], c["lat"]]},
                      "properties": {"source": "OSM", "osm_id": f"{e['type']}/{e['id']}", "name": t.get("name"),
                                     "kind": shelter_kind(t.get("name"), t), "shelter_type": t.get("shelter_type"),
                                     "fireplace": t.get("fireplace"), "tags": t}})
    n = {s: sum(f["properties"]["source"] == s for f in feats) for s in ("LIPAS", "OSM")}
    print(f"Laavut/kodat: LIPAS {n['LIPAS']}, OSM {n['OSM']}")
    return {"type": "FeatureCollection", "features": feats}


def main():
    os.makedirs(DATA, exist_ok=True)
    fetched = datetime.now(timezone.utc).astimezone().isoformat(timespec="minutes")
    center, bbox, disp = area()
    status = {}
    try:
        lip, lip_wfs_n, lip_sites = lipas(bbox); status["LIPAS"] = "ok"
    except Exception as e:
        print("LIPAS epäonnistui:", e); lip, lip_wfs_n, lip_sites = {"type": "FeatureCollection", "features": []}, 0, 0
        status["LIPAS"] = f"virhe: {e}"
    try:
        om, osm_n, osm_rel = osm(bbox); status["OSM"] = "ok"
    except Exception as e:
        print("OSM epäonnistui:", e); om, osm_n, osm_rel = {"type": "FeatureCollection", "features": []}, 0, 0
        status["OSM"] = f"virhe: {e}"

    meta = {"fetched": fetched, "address": ADDRESS, "geocoded": disp, "center": center,
            "bbox": bbox, "status": status}
    lip["metadata"] = dict(meta, dropped_duplicate_parts=DUPES, source="LIPAS WFS lipas:lipas_kaikki_reitit + api.lipas.fi/v2", license="CC BY 4.0, LIPAS / Jyväskylän yliopisto")
    om["metadata"] = dict(meta, source="Overpass API", query=OVERPASS_Q, license="ODbL, © OpenStreetMap -tekijät")
    json.dump(lip, open(os.path.join(DATA, "lipas.geojson"), "w"), ensure_ascii=False)
    json.dump(om, open(os.path.join(DATA, "osm.geojson"), "w"), ensure_ascii=False)
    try:
        sh = shelters(bbox); status["laavut"] = "ok"
    except Exception as e:
        print("Laavuhaku epäonnistui:", e); sh = {"type": "FeatureCollection", "features": []}
        status["laavut"] = f"virhe: {e}"
    sh["metadata"] = dict(meta, source="LIPAS WFS lipas:lipas_301_laavu_kota_kammi + api.lipas.fi/v2; Overpass amenity=shelter, tourism=wilderness_hut")
    json.dump(sh, open(os.path.join(DATA, "laavut.geojson"), "w"), ensure_ascii=False, indent=1)

    # tilastot
    st = {"meta": meta, "lipas_dupes": DUPES, "lipas_wfs_segments": lip_wfs_n, "lipas_sites": lip_sites, "osm_elements": osm_n,
          "osm_relations": osm_rel, "lipas": defaultdict(lambda: [0, 0.0, set()]), "osm": defaultdict(lambda: [0, 0.0])}
    for f in lip["features"]:
        p = f["properties"]; k = f"{p['type_code']} {p['type_name']}"
        st["lipas"][k][0] += 1; st["lipas"][k][1] += p["length_m_in_bbox"]; st["lipas"][k][2].add(p["name"])
    for f in om["features"]:
        p = f["properties"]; k = p["category"] + (f" ({p['highway']})" if p["highway"] and p["category"] != "latu" else "")
        st["osm"][k][0] += 1; st["osm"][k][1] += p["length_m_in_bbox"]

    lat0 = center[0]
    L_latu = [l for f in lip["features"] if f["properties"]["type_code"] == 4402 for l in lines_of(f["geometry"])]
    O_latu = [l for f in om["features"] if f["properties"]["category"] == "latu" for l in lines_of(f["geometry"])]
    O_all = [l for f in om["features"] for l in lines_of(f["geometry"])]
    cmp = {
        "lipas_latu_near_osm_latu": coverage(L_latu, O_latu, lat0),
        "lipas_latu_near_any_osm": coverage(L_latu, O_all, lat0),
        "osm_latu_near_lipas_latu": coverage(O_latu, L_latu, lat0),
    }
    L_unlit = [l for f in lip["features"] if f["properties"]["lipas_id"] == 509835 for l in lines_of(f["geometry"])]
    L_lit = [l for f in lip["features"] if f["properties"]["lipas_id"] == 509834 for l in lines_of(f["geometry"])]
    cmp["lipas_unlit_near_osm_latu"] = coverage(L_unlit, O_latu, lat0)
    cmp["lipas_lit_near_osm_latu"] = coverage(L_lit, O_latu, lat0)
    st["compare"] = cmp
    st["lipas"] = {k: [v[0], v[1], sorted(v[2])] for k, v in st["lipas"].items()}
    st["osm"] = dict(st["osm"])
    json.dump(st, open(os.path.join(DATA, "_stats.json"), "w"),
              ensure_ascii=False, indent=1, default=list)

    tpl = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
    html = (tpl.replace("/*LIPAS*/null", json.dumps(lip, ensure_ascii=False, separators=(",", ":")))
               .replace("/*OSM*/null", json.dumps(om, ensure_ascii=False, separators=(",", ":")))
               .replace("/*SHELTERS*/null", json.dumps(sh, ensure_ascii=False, separators=(",", ":")))
               .replace("/*META*/null", json.dumps(meta, ensure_ascii=False)))
    open(os.path.join(HERE, "index.html"), "w", encoding="utf-8").write(html)
    print(json.dumps(st, ensure_ascii=False, indent=1, default=list))


if __name__ == "__main__":
    main()
