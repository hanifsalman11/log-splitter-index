import os
import json
import re
import time
import math
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone

# ==========================================
# ENVIRONMENT CONFIGURATION
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "https://hanifsalman11.github.io/log-splitter-index").rstrip("/")
INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY", "c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9").strip()
CUSTOM_SPLITTER = os.environ.get("CUSTOM_SPLITTER", "").strip()
PAGES_PER_RUN = int(os.environ.get("PAGES_PER_RUN", "3"))

DOCS_DIR = "docs"
DATA_DIR = "data"
PUBLISHED_FILE = os.path.join(DATA_DIR, "published_splitters.json")
MONETIZATION_FILE = os.path.join(DATA_DIR, "monetization.json")

_CACHED_MODELS = None

# Format: (Model / Hydraulic Setup Name, Bore Inches, Stroke Inches, Rod Inches, Pump GPM, Max PSI)
SEED_SPLITTERS = [
    ("16 GPM 2-Stage Hydraulic Pump + 4.0\" × 24\" Cylinder", 4.0, 24.0, 1.75, 16.0, 3500),
    ("11 GPM 2-Stage Hydraulic Pump + 4.0\" × 24\" Cylinder", 4.0, 24.0, 1.75, 11.0, 3500),
    ("22 GPM 2-Stage Hydraulic Pump + 4.5\" × 24\" Cylinder", 4.5, 24.0, 2.00, 22.0, 3500),
    ("28 GPM 2-Stage Hydraulic Pump + 5.0\" × 24\" Cylinder", 5.0, 24.0, 2.25, 28.0, 3500),
    ("Champion 27-Ton Log Splitter (4.5\" Bore × 22.6\" Stroke)", 4.5, 22.6, 1.75, 14.0, 3500),
    ("Champion 34-Ton & 37-Ton Log Splitter (5.0\" × 24\" Cylinder)", 5.0, 24.0, 2.00, 16.0, 3500),
    ("Champion 20-Ton & 22-Ton Log Splitter (4.0\" × 22\" Cylinder)", 4.0, 22.0, 1.75, 11.0, 3400),
    ("CountyLine 25-Ton Log Splitter (4.0\" × 24\" Cylinder Upgrade)", 4.0, 24.0, 1.75, 14.0, 3500),
    ("CountyLine 30-Ton & 40-Ton Heavy-Duty Log Splitter", 5.0, 24.0, 2.00, 16.0, 3500),
    ("Predator 20-Ton Rapid-Cycle Log Splitter (Dual-Action)", 3.5, 22.0, 1.75, 14.0, 3500),
    ("Troy-Bilt & Craftsman 27-Ton Log Splitter (4.5\" × 24\")", 4.5, 24.0, 1.75, 13.0, 3500),
    ("Ariens 22-Ton & 27-Ton Subaru/Kohler Log Splitter", 4.5, 24.0, 1.75, 13.0, 3500),
    ("Yardmax 25-Ton, 28-Ton & 35-Ton Full-Beam Log Splitter", 4.5, 24.0, 2.00, 15.0, 3500),
    ("Black Diamond 25-Ton, 27-Ton & 32-Ton Log Splitter", 4.5, 24.0, 1.75, 14.0, 3500),
    ("Boss Industrial 7-Ton & 10-Ton Electric Log Splitter", 3.0, 20.0, 1.50, 6.5, 2800),
    ("3-Point Tractor PTO Log Splitter (12 GPM Tractor Remote)", 4.0, 24.0, 1.75, 12.0, 2500),
    ("3-Point Tractor PTO Pump (21 GPM @ 540 RPM) + 4.5\" Cylinder", 4.5, 24.0, 2.00, 21.0, 3000),
    ("Skid Steer Aux Hydraulic Log Splitter (18 GPM @ 3,000 PSI)", 4.5, 24.0, 2.00, 18.0, 3000),
    ("4.0-Inch Bore × 24-Inch Stroke Double-Acting Cylinder", 4.0, 24.0, 1.75, 16.0, 3500),
    ("4.5-Inch Bore × 24-Inch Stroke Double-Acting Cylinder", 4.5, 24.0, 2.00, 16.0, 3500),
    ("5.0-Inch Bore × 24-Inch Stroke Heavy-Duty Cylinder", 5.0, 24.0, 2.25, 22.0, 3500),
    ("5.0-Inch Bore × 30-Inch Stroke Commercial Firewood Processor", 5.0, 30.0, 2.50, 28.0, 3500),
    ("3.5-Inch Bore × 24-Inch Stroke Fast-Cycle Splitter Cylinder", 3.5, 24.0, 1.75, 16.0, 3500),
    ("Prince LS-3000-1 & Magister 25 GPM Auto-Detent Splitter Valve", 4.5, 24.0, 2.00, 16.0, 3500),
    ("Haldex / Concentric / Magister 16 GPM 2-Stage Hi-Low Pump", 4.0, 24.0, 1.75, 16.0, 3500),
    ("Haldex / Concentric 22 GPM 2-Stage Pump + 10-12 HP Engine", 4.5, 24.0, 2.00, 22.0, 3500),
    ("Predator 212cc (6.5 HP) Engine + 11 GPM vs 13 GPM 2-Stage Pump", 4.0, 24.0, 1.75, 11.0, 3500),
    ("Predator 301cc (8 HP) / Honda GX270 + 16 GPM 2-Stage Pump", 4.5, 24.0, 1.75, 16.0, 3500),
    ("Predator 420cc (13 HP) / Honda GX390 + 22 GPM 2-Stage Pump", 5.0, 24.0, 2.00, 22.0, 3500),
    ("AW-32 vs AW-46 Hydraulic Fluid & Reservoir Tank Sizing", 4.5, 24.0, 2.00, 16.0, 3500)
]


def load_json(filepath, default):
    """Self-healing JSON loader: otomatis pulih jika file korup atau kosong."""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, type(default)) else default
        except Exception as e:
            print(f"[SELF-HEAL] Recovering {filepath} due to read notice: {e}")
    return default


def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    return re.sub(r"[\s-]+", "-", text).strip("-")


def safe_float(val, default=16.0):
    try:
        cleaned = re.sub(r"[^0-9.]", "", str(val))
        return float(cleaned) if cleaned else float(default)
    except Exception:
        return float(default)


def build_amazon_url(search_keywords, mon_cfg):
    domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")
    encoded_q = urllib.parse.quote_plus(search_keywords)
    return f"https://{domain}/s?k={encoded_q}&tag={tag}"


def get_active_gemini_model(api_key):
    """
    LAPIS 1: Mesin Pemindai Versi Otomatis berbasis Regex tanpa angka versi manual.
    Otomatis mendeteksi model Gemini Flash STABIL generasi tertinggi lintas tahun.
    """
    global _CACHED_MODELS
    if _CACHED_MODELS is not None:
        return _CACHED_MODELS

    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        req = urllib.request.Request(list_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            scored_models = []

            for m in data.get("models", []):
                name = m.get("name", "").replace("models/", "")
                methods = m.get("supportedGenerationMethods", [])

                if "generateContent" not in methods or "flash" not in name.lower():
                    continue

                if any(bad in name.lower() for bad in [
                    "preview", "exp", "thinking", "image", "tts", "audio", "vision", "8b"
                ]):
                    continue

                ver_match = re.search(r"gemini-(\d+(?:\.\d+)?)-flash", name.lower())
                if ver_match:
                    ver_num = float(ver_match.group(1))
                    if name.lower() == f"gemini-{ver_match.group(1)}-flash":
                        tier_score = 2
                    elif name.lower() == f"gemini-{ver_match.group(1)}-flash-lite":
                        tier_score = 1
                    else:
                        tier_score = 0
                    scored_models.append((ver_num, tier_score, name))
                elif name.lower() == "gemini-flash-latest":
                    scored_models.append((0.1, 0, name))

            if scored_models:
                scored_models.sort(key=lambda x: (x[0], x[1]), reverse=True)
                _CACHED_MODELS = [item[2] for item in scored_models[:2]]
                print(f"[GEMINI] Future-proof active models locked: {_CACHED_MODELS}")
                return _CACHED_MODELS
    except Exception as e:
        print(f"[WARN] Dynamic model discovery notice: {e}")

    _CACHED_MODELS = ["gemini-flash-latest"]
    return _CACHED_MODELS


def discover_google_splitter_queries(published_slugs):
    """
    LAPIS 4: 3-Tier Infinite Keyword Supply:
    Tier A: Seed List -> Tier B: Google Suggest US -> Tier C: Combinatorial Bore × Stroke × Pump GPM Permutator.
    """
    discovered = []
    seeds = [
        "log splitter pump calculator ",
        "hydraulic cylinder tonnage calculator ",
        "what size engine for hydraulic pump ",
        "champion log splitter pump "
    ]
    for seed in seeds:
        try:
            url = f"http://suggestqueries.google.com/complete/search?client=firefox&hl=en&gl=us&q={urllib.parse.quote(seed)}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for suggestion in data[1]:
                    cleaned = suggestion.lower()
                    for pref in seeds:
                        if "calculator" in pref or "what size" in pref:
                            cleaned = cleaned.replace(pref, "")
                    cleaned = re.sub(
                        r"\b(calculator|size|sizing|chart|manual|review|reddit|for)\b",
                        "",
                        cleaned
                    ).strip()
                    if 5 <= len(cleaned) <= 42:
                        gpm_m = re.search(r"\b(11|13|16|22|28)\s*gpm\b", cleaned)
                        gpm_v = float(gpm_m.group(1)) if gpm_m else 16.0
                        bore_v = 4.0 if gpm_v <= 13 else (4.5 if gpm_v <= 16 else 5.0)
                        discovered.append((cleaned.title(), bore_v, 24.0, 2.0, gpm_v, 3500))
        except Exception as e:
            print(f"[WARN] Google Suggest notice: {e}")

    # Tier C Fallback: Combinatorial Permutator (Anti-Habis Lintas Tahun)
    cylinders = [
        (3.5, 24.0, 1.75, "3.5\" × 24\" Cylinder"),
        (4.0, 24.0, 1.75, "4.0\" × 24\" Cylinder"),
        (4.5, 24.0, 2.00, "4.5\" × 24\" Cylinder"),
        (4.5, 30.0, 2.00, "4.5\" × 30\" Cylinder"),
        (5.0, 24.0, 2.25, "5.0\" × 24\" Cylinder"),
        (5.0, 30.0, 2.50, "5.0\" × 30\" Cylinder")
    ]
    pumps = [
        (11.0, 3000, "11 GPM Pump @ 3,000 PSI"),
        (13.0, 3500, "13 GPM Pump @ 3,500 PSI"),
        (16.0, 3500, "16 GPM Pump @ 3,500 PSI"),
        (22.0, 3500, "22 GPM Pump @ 3,500 PSI"),
        (28.0, 3500, "28 GPM Pump @ 3,500 PSI")
    ]
    for b_in, s_in, r_in, cyl_desc in cylinders:
        for p_gpm, p_psi, pmp_desc in pumps:
            combo_title = f"{cyl_desc} on {pmp_desc}"
            test_slug = slugify(f"{combo_title}-tonnage-cycle-time-calculator")
            if test_slug not in published_slugs:
                discovered.append((combo_title, b_in, s_in, r_in, p_gpm, p_psi))
                if len(discovered) >= 25:
                    return discovered
    return discovered


def build_deterministic_splitter_data(split_tuple):
    """
    LAPIS 3: Mesin Fisika Hidrolika Pascal's Law, Volume Silinder & Engine HP (100% Bebas Gagal).
    """
    model_name, bore_in, stroke_in, rod_in, pump_gpm, max_psi = split_tuple

    # Luas Penampang Piston Extend & Retract (Sq Inches):
    piston_area_sqin = round(math.pi * ((bore_in / 2.0) ** 2), 2)
    rod_area_sqin = round(math.pi * ((rod_in / 2.0) ** 2), 2)
    retract_area_sqin = round(piston_area_sqin - rod_area_sqin, 2)

    # Gaya Dorong (Extend Force in lbs & True Hydraulic Tons):
    extend_force_lbs = int(round(piston_area_sqin * max_psi))
    true_tons = round(extend_force_lbs / 2000.0, 1)

    # Volume Oli Silinder (1 US Gallon = 231 Cubic Inches):
    extend_vol_gal = round((piston_area_sqin * stroke_in) / 231.0, 2)
    retract_vol_gal = round((retract_area_sqin * stroke_in) / 231.0, 2)
    total_cycle_gal = round(extend_vol_gal + retract_vol_gal, 2)

    # Waktu Siklus Maju + Mundur pada Aliran High-Volume Stage 1 (Seconds):
    # Cycle Time (sec) = (Total_Cycle_Gallons / Pump_GPM) * 60
    extend_sec = round((extend_vol_gal / max(1.0, float(pump_gpm))) * 60.0, 1)
    retract_sec = round((retract_vol_gal / max(1.0, float(pump_gpm))) * 60.0, 1)
    total_cycle_sec = round(extend_sec + retract_sec, 1)

    # Kebutuhan Minimum Mesin Bensin (HP) untuk Pompa 2-Tahap (Rule of Thumb: GPM / 2, min 6.5 HP)
    min_engine_hp = max(5.5, round(pump_gpm * 0.52, 1))
    min_engine_cc = 212 if pump_gpm <= 13 else (301 if pump_gpm <= 16 else (420 if pump_gpm <= 22 else 670))
    # Ukuran Tangki Oli Hidrolik (Reservoir = minimal 50% - 65% dari GPM pompa agar oli tidak overheat >180°F)
    min_tank_gal = max(4.0, round(pump_gpm * 0.55, 1))
    suction_hose_in = "1.0-Inch ID" if pump_gpm <= 16 else "1.25-Inch ID"

    return {
        "splitter_name": model_name,
        "seo_title": f"{model_name} Tonnage, Cycle Time & Engine HP Calculator (2026)",
        "meta_description": f"Calculate exact hydraulic splitting force ({true_tons} True Tons @ {max_psi:,} PSI), cycle speed ({total_cycle_sec} sec @ {pump_gpm} GPM), gas engine requirement ({min_engine_hp} HP / {min_engine_cc}cc), and {min_tank_gal}-gal oil tank for {model_name}.",
        "specs": {
            "cylinder_bore_in": bore_in,
            "cylinder_stroke_in": stroke_in,
            "rod_diameter_in": rod_in,
            "piston_area_sqin": piston_area_sqin,
            "max_pressure_psi": max_psi,
            "true_splitting_tons": true_tons,
            "pump_flow_gpm": pump_gpm,
            "extend_volume_gal": extend_vol_gal,
            "total_cycle_sec": total_cycle_sec,
            "min_engine_hp": min_engine_hp,
            "min_engine_cc": min_engine_cc,
            "min_reservoir_gal": min_tank_gal,
            "suction_hose_spec": suction_hose_in
        },
        "hydraulic_verdict": f"With a {bore_in}-inch cylinder bore ({piston_area_sqin} sq. in. piston area) and {rod_in}-inch chrome rod over a {stroke_in}-inch stroke, {model_name} generates {extend_force_lbs:,} lbs ({true_tons} True Hydraulic Tons) of splitting force at {max_psi:,} PSI. Driven by a {pump_gpm:.0f} GPM 2-stage hi-low hydraulic gear pump, the cylinder displaces {extend_vol_gal} gallons on the extend stroke ({total_cycle_gal} gallons round-trip), achieving a {total_cycle_sec}-second no-load cycle time ({extend_sec}s extend / {retract_sec}s retract). Powering this {pump_gpm:.0f} GPM pump without stalling requires at least a {min_engine_hp} HP ({min_engine_cc}cc) gas engine and a {min_tank_gal}-gallon hydraulic oil reservoir.",
        "hardware_bundle": [
            {
                "badge": f"{pump_gpm:.0f} GPM 2-Stage Pump",
                "title": f"{pump_gpm:.0f} GPM Two-Stage Hi-Low Hydraulic Log Splitter Gear Pump (3,500 PSI / 3,600 RPM)",
                "price_range": "$109 - $279",
                "amazon_query": f"{int(pump_gpm)} GPM 2 Stage Hydraulic Log Splitter Pump 3000 PSI",
                "hyd_note": f"Shifts automatically from high-speed {pump_gpm:.0f} GPM low-pressure approach to 3,500 PSI high-force splitting at 650 PSI."
            },
            {
                "badge": f"{bore_in}\" × {stroke_in:.0f}\" Cylinder",
                "title": f"{bore_in}\" Bore × {stroke_in:.0f}\" Stroke Double-Acting Welded Hydraulic Log Splitter Cylinder (3,500 PSI)",
                "price_range": "$189 - $449",
                "amazon_query": f"{bore_in}x{int(stroke_in)} Hydraulic Log Splitter Cylinder Double Acting 3500 PSI",
                "hyd_note": f"Delivers {true_tons} True Tons ({extend_force_lbs:,} lbs) of ram force with a heavy {rod_in}\" hard-chrome piston rod."
            },
            {
                "badge": "Auto-Detent Valve & Mount",
                "title": "25–30 GPM Auto-Return Detent Log Splitter Control Valve + Cast-Iron Pump Mount & Lovejoy Coupler",
                "price_range": "$84 - $199",
                "amazon_query": "Log Splitter Control Valve Auto Detent 25 GPM Pump Mount Lovejoy Coupler",
                "hyd_note": "Pressure-release detent automatically snaps the return lever to neutral once the cylinder fully retracts."
            },
            {
                "badge": "Filter, Hose & AW-32 Oil",
                "title": "10-Micron Spin-On Hydraulic Return Filter Kit + 1/2\" 4,000-PSI Hose & 5-Gal AW-32 Hydraulic Oil",
                "price_range": "$69 - $189",
                "amazon_query": "Log Splitter Hydraulic Filter Assembly 10 Micron 1/2 Hydraulic Hose AW32",
                "hyd_note": f"Protects tight gear-pump tolerances from metal shavings and cools the {min_tank_gal}-gallon fluid circuit."
            }
        ],
        "mechanic_checklist": [
            f"Understand Retail 'Advertised Tonnage' vs. True Hydraulic Tonnage ($F = P \\times A \\div 2000$): a {bore_in}-inch bore cylinder has {piston_area_sqin} sq. in. of surface area, which produces exactly {true_tons} Tons at {max_psi:,} PSI.",
            f"Size your gas engine at a minimum of 0.5 HP per GPM for a 2-stage pump ({pump_gpm:.0f} GPM requires {min_engine_hp}+ HP / {min_engine_cc}cc) and align the Lovejoy L-095/L-100 jaw coupler with a 1/16\" spider gap so axial shaft load never blows out the pump front seal.",
            f"Never restrict the pump suction inlet: run a {suction_hose_in} wire-reinforced suction hose from the reservoir to the pump inlet (never use Teflon tape on hydraulic fittings—use liquid Loctite 545 or JIC 37° flare fittings to prevent valve spool jamming).",
            "Install the 10-Micron spin-on filter strictly on the low-pressure RETURN line between the control valve and tank (never on the pump suction side, which causes pump cavitation and howling)."
        ],
        "faqs": [
            {
                "q": f"How many true tons of force does a {bore_in}-inch cylinder produce at {max_psi:,} PSI?",
                "a": f"Using Pascal's Law, multiply piston area ($\\pi \\times [{bore_in} \\div 2]^2 = {piston_area_sqin}\\text{{ sq. in.}}$) by {max_psi:,} PSI to get {extend_force_lbs:,} lbs of force. Dividing by 2,000 lbs/ton equals {true_tons} True Hydraulic Tons."
            },
            {
                "q": f"What is the cycle time of a {bore_in}\" × {stroke_in:.0f}\" cylinder with a {pump_gpm:.0f} GPM pump?",
                "a": f"The extend stroke holds {extend_vol_gal} gallons and the retract stroke holds {retract_vol_gal} gallons (because the {rod_in}\" rod takes up space), totaling {total_cycle_gal} gallons per full cycle. At {pump_gpm:.0f} GPM, it takes {extend_sec} seconds to extend and {retract_sec} seconds to retract = {total_cycle_sec} seconds total cycle time."
            },
            {
                "q": f"What size gas engine do I need to run a {pump_gpm:.0f} GPM 2-stage hydraulic pump?",
                "a": f"A two-stage hi-low log splitter pump unloads its high-volume stage at ~650 PSI and switches to its low-volume high-pressure stage up to {max_psi:,} PSI. This requires at least {min_engine_hp} HP ({min_engine_cc}cc horizontal-shaft engine) and a {min_tank_gal}+ gallon oil tank."
            }
        ]
    }


def generate_splitter_data(split_tuple):
    """
    LAPIS 2: Memanggil model Gemini stabil dengan proteksi Cooldown HTTP 429 & Fallback Otomatis.
    """
    if not GEMINI_API_KEY:
        return build_deterministic_splitter_data(split_tuple)

    model_name, bore_in, stroke_in, rod_in, pump_gpm, max_psi = split_tuple
    det_fallback = build_deterministic_splitter_data(split_tuple)
    sp = det_fallback["specs"]

    prompt = f"""
You are a Certified Fluid Power Hydraulic Engineer (IFPS Specialist) & Agricultural Equipment Designer. Create an accurate 2026 hydraulic log splitter cylinder tonnage, 2-stage pump GPM cycle time, gas engine HP, and oil reservoir sizing guide for: "{model_name}".
Baseline specs: Cylinder={bore_in}" Bore x {stroke_in}" Stroke ({rod_in}" Rod, {sp['piston_area_sqin']} sq in), Max Pressure={max_psi} PSI, True Force={sp['true_splitting_tons']} Tons, Pump={pump_gpm} GPM 2-Stage, Cycle Time={sp['total_cycle_sec']} sec ({sp['extend_volume_gal']} gal extend), Min Engine={sp['min_engine_hp']} HP ({sp['min_engine_cc']}cc), Min Oil Tank={sp['min_reservoir_gal']} Gal.
Return ONLY a valid JSON object matching this exact schema:
{{
  "splitter_name": "{model_name}",
  "seo_title": "{model_name} Tonnage, Cycle Time & Engine HP Calculator (2026)",
  "meta_description": "Calculate exact hydraulic cylinder tonnage, 2-stage pump cycle time in seconds, required gas engine HP, and oil tank volume for {model_name}.",
  "specs": {{
    "cylinder_bore_in": {bore_in},
    "cylinder_stroke_in": {stroke_in},
    "rod_diameter_in": {rod_in},
    "piston_area_sqin": {sp['piston_area_sqin']},
    "max_pressure_psi": {max_psi},
    "true_splitting_tons": {sp['true_splitting_tons']},
    "pump_flow_gpm": {pump_gpm},
    "extend_volume_gal": {sp['extend_volume_gal']},
    "total_cycle_sec": {sp['total_cycle_sec']},
    "min_engine_hp": {sp['min_engine_hp']},
    "min_engine_cc": {sp['min_engine_cc']},
    "min_reservoir_gal": {sp['min_reservoir_gal']},
    "suction_hose_spec": "{sp['suction_hose_spec']}"
  }},
  "hydraulic_verdict": "3-sentence technical summary stating piston area, true hydraulic tonnage at {max_psi} PSI, full cycle time in seconds at {pump_gpm} GPM, and minimum gas engine HP and oil tank gallons.",
  "hardware_bundle": [
    {{
      "badge": "{pump_gpm:.0f} GPM 2-Stage Pump",
      "title": "{pump_gpm:.0f} GPM Two-Stage Hi-Low Hydraulic Log Splitter Gear Pump",
      "price_range": "$109 - $279",
      "amazon_query": "{int(pump_gpm)} GPM 2 Stage Hydraulic Log Splitter Pump",
      "hyd_note": "1-sentence hi-low unloading pressure and RPM note"
    }},
    {{
      "badge": "{bore_in}\" × {stroke_in:.0f}\" Cylinder",
      "title": "{bore_in}\" Bore × {stroke_in:.0f}\" Stroke Double-Acting Welded Hydraulic Cylinder (3,500 PSI)",
      "price_range": "$189 - $449",
      "amazon_query": "{bore_in}x{int(stroke_in)} Hydraulic Log Splitter Cylinder Double Acting",
      "hyd_note": "1-sentence true tonnage and chrome rod strength note"
    }},
    {{
      "badge": "Detent Valve & Mount Kit",
      "title": "25-30 GPM Auto-Detent Log Splitter Control Valve + Pump Mount & Lovejoy Coupler",
      "price_range": "$84 - $199",
      "amazon_query": "Log Splitter Control Valve Auto Detent Pump Mount Lovejoy",
      "hyd_note": "1-sentence auto-return detent and shaft alignment note"
    }},
    {{
      "badge": "Return Filter & AW-32 Oil",
      "title": "10-Micron Spin-On Hydraulic Return Filter + 1/2\" 4000-PSI Hose & AW-32 Fluid",
      "price_range": "$69 - $189",
      "amazon_query": "Log Splitter Hydraulic Filter Assembly 10 Micron AW32",
      "hyd_note": "1-sentence return-side filtration and cavitation prevention note"
    }}
  ],
  "mechanic_checklist": [
    "Step 1 regarding True Tonnage formula (Piston Area x PSI / 2000) vs retail ratings",
    "Step 2 regarding 0.5 HP per GPM engine rule and Lovejoy jaw coupling spider gap",
    "Step 3 regarding {sp['suction_hose_spec']} suction hose and avoiding Teflon tape in hydraulics",
    "Step 4 regarding installing the 10-micron filter strictly on the return line"
  ],
  "faqs": [
    {{"q": "How many true tons does {model_name} produce at {max_psi} PSI?", "a": "Exact piston sq in, lbs of force, and true tonnage calculation."}},
    {{"q": "How fast is the cycle time on a {bore_in}x{stroke_in:.0f} cylinder with a {pump_gpm:.0f} GPM pump?", "a": "Exact extend/retract gallons and seconds calculation."}},
    {{"q": "Should I use AW-32 or AW-46 hydraulic oil in my log splitter?", "a": "Direct viscosity explanation for winter below-40F vs summer splitting."}}
  ]
}}
"""

    for model_id in get_active_gemini_model(GEMINI_API_KEY):
        for attempt in range(2):
            try:
                endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.2,
                        "responseMimeType": "application/json"
                    }
                }
                req = urllib.request.Request(
                    endpoint,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=40) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                    raw_text = re.sub(r"\s*```$", "", raw_text)
                    parsed = json.loads(raw_text)
                    if "specs" in parsed and "hardware_bundle" in parsed:
                        time.sleep(6)
                        return parsed
            except urllib.error.HTTPError as he:
                if he.code == 429:
                    print(f"[RATE-LIMIT] HTTP 429 on {model_id} (attempt {attempt + 1}). Cooling down 20s...")
                    time.sleep(20)
                else:
                    print(f"[WARN] HTTP {he.code} on {model_id} for '{model_name}': {he}")
                    break
            except Exception as e:
                print(f"[WARN] Gemini ({model_id}) notice for '{model_name}': {e}")
                break

    return det_fallback


def build_splitter_html_page(data, slug, mon_cfg):
    split_name = data.get("splitter_name", "Hydraulic Log Splitter System")
    sp = data.get("specs", {})
    bore_in = round(safe_float(sp.get("cylinder_bore_in", 4.5), 4.5), 1)
    stroke_in = int(safe_float(sp.get("cylinder_stroke_in", 24), 24))
    rod_in = round(safe_float(sp.get("rod_diameter_in", 2.0), 2.0), 2)
    psi = int(safe_float(sp.get("max_pressure_psi", 3500), 3500))
    tons = round(safe_float(sp.get("true_splitting_tons", 27.8), 27.8), 1)
    gpm = round(safe_float(sp.get("pump_flow_gpm", 16.0), 16.0), 1)
    cyc_sec = round(safe_float(sp.get("total_cycle_sec", 10.6), 10.6), 1)
    eng_hp = round(safe_float(sp.get("min_engine_hp", 8.0), 8.0), 1)
    eng_cc = int(safe_float(sp.get("min_engine_cc", 301), 301))
    tank_gal = round(safe_float(sp.get("min_reservoir_gal", 8.5), 8.5), 1)

    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "2+Stage+Hydraulic+Log+Splitter+Pump+Cylinder+Valve"), mon_cfg)

    schema_graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "SoftwareApplication",
                "name": f"{split_name} Tonnage, Cycle Time & Pump Calculator",
                "applicationCategory": "UtilitiesApplication",
                "operatingSystem": "Web Browser",
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": f.get("q", ""),
                        "acceptedAnswer": {"@type": "Answer", "text": f.get("a", "")}
                    } for f in data.get("faqs", [])
                ]
            }
        ]
    }

    bundle_html = ""
    for item in data.get("hardware_bundle", []):
        amz_url = build_amazon_url(item.get("amazon_query", item.get("title", "Hydraulic Log Splitter Pump")), mon_cfg)
        bundle_html += f"""
        <div class="bg-zinc-900 border border-zinc-800 rounded-xl p-5 flex flex-col justify-between hover:border-orange-500/60 transition">
          <div>
            <div class="flex items-center justify-between gap-2 mb-2">
              <span class="text-xs font-bold uppercase tracking-wider bg-orange-500/10 text-orange-400 border border-orange-500/20 px-2.5 py-0.5 rounded">{item.get('badge', 'Hydraulic Gear')}</span>
              <span class="text-sm font-bold text-emerald-400">{item.get('price_range', '$79+')}</span>
            </div>
            <h3 class="text-base font-bold text-white mt-2">{item.get('title', '')}</h3>
            <p class="text-xs text-zinc-400 mt-2 leading-relaxed">🪓 {item.get('hyd_note', '')}</p>
          </div>
          <a href="{amz_url}" target="_blank" rel="nofollow sponsored" class="mt-5 block text-center bg-orange-500 hover:bg-orange-400 text-zinc-950 font-extrabold py-2.5 px-4 rounded-lg text-sm transition shadow-lg">
            Check Price on Amazon →
          </a>
        </div>"""

    # Build Cylinder Bore & Pump GPM Reference Matrix Table
    hyd_tiers = [
        ("3.5\" Bore × 24\" (1.75\" Rod)", "16.8 Tons @ 3,500 PSI", "11 GPM (10.3s Cycle)", "6.5 HP (212cc) Engine", "5.5 Gal Oil Tank"),
        ("4.0\" Bore × 24\" (1.75\" Rod)", "22.0 Tons @ 3,500 PSI", "13 GPM (11.2s Cycle)", "6.5 – 8 HP (212–270cc)", "6.5 Gal Oil Tank"),
        ("4.0\" Bore × 24\" (2.00\" Rod)", "22.0 Tons @ 3,500 PSI", "16 GPM (8.9s Cycle)", "8 – 9 HP (270–301cc)", "8.5 Gal Oil Tank"),
        ("4.5\" Bore × 24\" (2.00\" Rod)", "27.8 Tons @ 3,500 PSI", "16 GPM (11.5s Cycle)", "8 – 10 HP (301cc)", "9.0 Gal Oil Tank"),
        ("4.5\" Bore × 24\" (2.00\" Rod)", "27.8 Tons @ 3,500 PSI", "22 GPM (8.4s Cycle)", "11 – 13 HP (389–420cc)", "12.0 Gal Oil Tank"),
        ("5.0\" Bore × 24\" (2.25\" Rod)", "34.4 Tons @ 3,500 PSI", "28 GPM (8.1s Cycle)", "14 – 16 HP (420–670cc)", "15.0 Gal Oil Tank")
    ]
    matrix_rows_html = ""
    for cy_lbl, to_lbl, gp_lbl, en_lbl, tk_lbl in hyd_tiers:
        matrix_rows_html += f"""
        <tr class="border-b border-zinc-800 hover:bg-zinc-800/40">
          <td class="py-3 px-4 font-bold text-white">{cy_lbl}</td>
          <td class="py-3 px-4 font-bold text-orange-400">{to_lbl}</td>
          <td class="py-3 px-4 text-emerald-400 font-semibold">{gp_lbl}</td>
          <td class="py-3 px-4 text-zinc-300">{en_lbl}</td>
          <td class="py-3 px-4 text-xs text-zinc-300">{tk_lbl}</td>
        </tr>"""

    checklist_html = ""
    for idx, step_text in enumerate(data.get("mechanic_checklist", []), start=1):
        checklist_html += f"""
        <label class="flex items-start gap-3.5 bg-zinc-900 border border-zinc-800 rounded-xl p-4 cursor-pointer hover:border-zinc-700 transition">
          <input type="checkbox" class="mt-1 w-5 h-5 accent-orange-500 rounded cursor-pointer hyd-check">
          <span class="text-sm text-zinc-200 leading-relaxed"><strong>Hydraulic Step {idx}:</strong> {step_text}</span>
        </label>"""

    faqs_html = "".join([
        f"<div class='bg-zinc-900 border border-zinc-800 rounded-xl p-5'><h3 class='font-bold text-white text-base mb-2'>{f.get('q', '')}</h3><p class='text-sm text-zinc-300 leading-relaxed'>{f.get('a', '')}</p></div>"
        for f in data.get("faqs", [])
    ])

    canonical_url = f"{SITE_BASE_URL}/{slug}.html"
    amz_domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    amz_tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")

    html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{data.get('seo_title', split_name)}</title>
  <meta name="description" content="{data.get('meta_description', '')}">
  <link rel="canonical" href="{canonical_url}">
  <meta property="og:title" content="{data.get('seo_title', split_name)}">
  <meta property="og:description" content="{data.get('meta_description', '')}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{canonical_url}">
  <script src="https://cdn.tailwindcss.com"></script>
  <script type="application/ld+json">{json.dumps(schema_graph)}</script>
</head>
<body class="bg-zinc-950 text-zinc-100 antialiased min-h-screen flex flex-col">
  <header class="border-b border-zinc-800 bg-zinc-900/80 backdrop-blur sticky top-0 z-30">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <a href="index.html" class="text-lg font-black tracking-tight text-white flex items-center gap-2">
        <span class="bg-orange-500 text-zinc-950 px-2 py-0.5 rounded font-black">SPLITTER</span>TonIndex
      </a>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-orange-500 hover:bg-orange-400 text-zinc-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Hydraulic Pumps & Cylinders →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-10 flex-1 w-full">
    <div class="mb-8">
      <div class="flex flex-wrap items-center gap-2.5 mb-3">
        <span class="text-xs font-extrabold uppercase tracking-widest bg-orange-500 text-zinc-950 px-3 py-1 rounded-full">{tons} True Tons ({bore_in}" × {stroke_in}")</span>
        <span class="text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1 rounded-full">{gpm:.0f} GPM Pump → {cyc_sec}s Cycle</span>
        <span class="text-xs font-semibold bg-zinc-800 text-zinc-300 px-3 py-1 rounded-full">Engine: {eng_hp}+ HP ({eng_cc}cc) | Tank: {tank_gal} Gal</span>
      </div>
      <h1 class="text-3xl sm:text-4xl font-black text-white leading-tight">{data.get('seo_title', split_name)}</h1>
      <div class="mt-4 bg-zinc-900 border-l-4 border-orange-500 p-4 rounded-r-xl text-sm text-zinc-200 leading-relaxed">
        <strong>IFPS Fluid Power & Tonnage Verdict:</strong> {data.get('hydraulic_verdict', '')}
      </div>
    </div>

    <!-- INTERACTIVE CYLINDER TONNAGE, CYCLE TIME & 2-STAGE PUMP CALCULATOR -->
    <section class="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 sm:p-8 mb-12 shadow-2xl">
      <h2 class="text-xl font-extrabold text-white mb-2">Interactive {split_name} Tonnage & Cycle Time Calculator</h2>
      <p class="text-xs text-zinc-400 mb-6">Adjust your hydraulic cylinder bore diameter, stroke length, 2-stage pump GPM rating, and relief valve PSI to compute exact True Hydraulic Tonnage, round-trip cycle speed, and required gas engine HP.</p>

      <div class="grid md:grid-cols-2 gap-8 items-center">
        <div class="space-y-5">
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label for="boreSelect" class="block text-xs font-medium text-zinc-400 mb-1">Cylinder Bore & Rod Dia</label>
              <select id="boreSelect" class="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-orange-500">
                <option value="3.5|1.75" {"selected" if bore_in <= 3.6 else ""}>3.5" Bore (1.75" Rod)</option>
                <option value="4.0|1.75" {"selected" if 3.6 < bore_in <= 4.1 else ""}>4.0" Bore (1.75" Rod)</option>
                <option value="4.5|2.00" {"selected" if 4.1 < bore_in <= 4.6 else ""}>4.5" Bore (2.00" Rod)</option>
                <option value="5.0|2.25" {"selected" if bore_in > 4.6 else ""}>5.0" Bore (2.25" Rod)</option>
              </select>
            </div>
            <div>
              <label for="pumpSelect" class="block text-xs font-medium text-zinc-400 mb-1">2-Stage Pump Flow (GPM)</label>
              <select id="pumpSelect" class="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-orange-500">
                <option value="11" {"selected" if gpm <= 11.5 else ""}>11 GPM 2-Stage (6.5 HP)</option>
                <option value="13" {"selected" if 11.5 < gpm <= 14.5 else ""}>13–14 GPM 2-Stage (7 HP)</option>
                <option value="16" {"selected" if 14.5 < gpm <= 19.0 else ""}>16 GPM 2-Stage (8–9 HP)</option>
                <option value="22" {"selected" if 19.0 < gpm <= 25.0 else ""}>22 GPM 2-Stage (12–13 HP)</option>
                <option value="28" {"selected" if gpm > 25.0 else ""}>28 GPM 2-Stage (15+ HP)</option>
              </select>
            </div>
          </div>

          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="strokeSlider" class="text-zinc-300">Cylinder Stroke Length (Inches)</label>
              <span class="text-orange-400 font-bold"><span id="strokeVal">{stroke_in}</span>" Stroke</span>
            </div>
            <input id="strokeSlider" type="range" min="18" max="36" step="2" value="{stroke_in}" class="w-full accent-orange-500 cursor-pointer">
          </div>

          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="psiSlider" class="text-zinc-300">Max System Relief Pressure (PSI)</label>
              <span class="text-orange-400 font-bold"><span id="psiVal">{psi:,}</span> PSI</span>
            </div>
            <input id="psiSlider" type="range" min="2200" max="4000" step="100" value="{psi}" class="w-full accent-orange-500 cursor-pointer">
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="bg-zinc-950 border border-orange-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-orange-400 font-bold">True Splitting Force</span>
            <div class="text-2xl sm:text-3xl font-black text-white mt-1"><span id="tonOut">{tons}</span> <span class="text-xs font-normal text-zinc-400">Tons</span></div>
            <p id="lbsNoteOut" class="text-xs text-orange-400 font-semibold mt-1">{int(tons * 2000):,} lbs Ram Force</p>
          </div>

          <div class="bg-zinc-950 border border-emerald-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-emerald-400 font-bold">Cycle Time & Engine</span>
            <div class="text-2xl sm:text-3xl font-black text-emerald-400 mt-1"><span id="secOut">{cyc_sec}</span> <span class="text-xs font-normal text-zinc-400">sec</span></div>
            <p id="hpTankOut" class="text-xs text-zinc-300 font-semibold mt-1">Need {eng_hp}+ HP & {tank_gal} Gal Tank</p>
          </div>
        </div>
      </div>

      <div class="mt-6 bg-orange-950/40 border border-orange-500/30 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div id="hydAdviceBanner" class="text-sm text-orange-100 font-medium"></div>
        <a id="dynamicHydBtn" href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="shrink-0 bg-orange-500 hover:bg-orange-400 text-zinc-950 font-extrabold px-4 py-2.5 rounded-lg text-xs uppercase tracking-wider transition">
          Shop Matched Pump, Cylinder & Valve on Amazon →
        </a>
      </div>
    </section>

    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">Complete {split_name} Pump, Cylinder & Valve Bundle</h2>
        <span class="text-xs text-zinc-400">3,500 PSI Double-Acting & Auto-Detent Rated</span>
      </div>
      <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">{bundle_html}</div>
    </section>

    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-4">Hydraulic Cylinder Bore, True Tonnage, 2-Stage Pump GPM & Engine HP Chart</h2>
      <div class="overflow-x-auto bg-zinc-900 border border-zinc-800 rounded-xl">
        <table class="w-full text-left border-collapse text-sm">
          <thead>
            <tr class="border-b border-zinc-800 bg-zinc-950/60 text-zinc-400 uppercase text-xs">
              <th class="py-3.5 px-4">Cylinder Bore & Stroke</th>
              <th class="py-3.5 px-4 text-orange-400">True Force (@3,500 PSI)</th>
              <th class="py-3.5 px-4 text-emerald-400">2-Stage Pump & Cycle</th>
              <th class="py-3.5 px-4">Min Gas Engine</th>
              <th class="py-3.5 px-4">Min Oil Tank</th>
            </tr>
          </thead>
          <tbody>{matrix_rows_html}</tbody>
        </table>
      </div>
    </section>

    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">IFPS Hydraulic Pump Alignment, Suction Hose & Return Filter Checklist</h2>
        <span id="hydBadge" class="text-xs font-bold bg-zinc-800 text-orange-400 px-3 py-1 rounded-full">0 / 4 Completed</span>
      </div>
      <div class="space-y-3">{checklist_html}</div>
    </section>

    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-5">Frequently Asked Questions ({split_name})</h2>
      <div class="space-y-4">{faqs_html}</div>
    </section>
  </main>

  <footer class="border-t border-zinc-800 py-8 text-center text-xs text-zinc-500 px-4">
    <p>© {datetime.now(timezone.utc).year} SplitterTonIndex. Independent Hydraulic Cylinder Tonnage & Fluid Power Sizing Database. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const amzDomain = "{amz_domain}";
    const amzTag = "{amz_tag}";

    const boreSelect = document.getElementById('boreSelect');
    const pumpSelect = document.getElementById('pumpSelect');
    const strokeSlider = document.getElementById('strokeSlider');
    const psiSlider = document.getElementById('psiSlider');
    const strokeVal = document.getElementById('strokeVal');
    const psiVal = document.getElementById('psiVal');
    const tonOut = document.getElementById('tonOut');
    const lbsNoteOut = document.getElementById('lbsNoteOut');
    const secOut = document.getElementById('secOut');
    const hpTankOut = document.getElementById('hpTankOut');
    const hydAdviceBanner = document.getElementById('hydAdviceBanner');
    const dynamicHydBtn = document.getElementById('dynamicHydBtn');

    function recalculateSplitter() {{
      const boreParts = boreSelect.value.split('|');
      const boreIn = parseFloat(boreParts[0]);
      const rodIn = parseFloat(boreParts[1]);
      const gpm = parseFloat(pumpSelect.value);
      const strokeIn = parseInt(strokeSlider.value, 10);
      const psi = parseInt(psiSlider.value, 10);

      strokeVal.textContent = strokeIn;
      psiVal.textContent = psi.toLocaleString();

      const pistArea = Math.PI * Math.pow(boreIn / 2.0, 2);
      const rodArea = Math.PI * Math.pow(rodIn / 2.0, 2);
      const retArea = pistArea - rodArea;

      const forceLbs = Math.round(pistArea * psi);
      const trueTons = (forceLbs / 2000.0).toFixed(1);

      const extGal = (pistArea * strokeIn) / 231.0;
      const retGal = (retArea * strokeIn) / 231.0;
      const totGal = extGal + retGal;
      const cycleSec = ((totGal / gpm) * 60.0).toFixed(1);

      const minHp = Math.max(5.5, (gpm * 0.52)).toFixed(1);
      const minTank = Math.max(4.5, (gpm * 0.55)).toFixed(1);

      tonOut.textContent = trueTons;
      lbsNoteOut.textContent = `${{forceLbs.toLocaleString()}} lbs Ram Force`;
      secOut.textContent = cycleSec;
      hpTankOut.textContent = `Need ${{minHp}}+ HP & ${{minTank}} Gal Tank`;

      hydAdviceBanner.innerHTML = `🪓 <strong>Hydraulic Spec:</strong> A <strong>${{boreIn}}" × ${{strokeIn}}" Cylinder</strong> at ${{psi.toLocaleString()}} PSI delivers <strong>${{trueTons}} True Tons</strong>. Pair with a <strong>${{gpm}} GPM 2-Stage Hi-Low Pump</strong> (${{cycleSec}}s cycle time), a <strong>25 GPM Auto-Detent Control Valve</strong>, and a ${{minHp}}+ HP gas engine.`;
      dynamicHydBtn.href = `https://${{amzDomain}}/s?k=${{gpm}}+GPM+2+Stage+Hydraulic+Log+Splitter+Pump+${{boreIn}}x${{strokeIn}}+Cylinder+Detent+Valve&tag=${{amzTag}}`;
    }}

    boreSelect.addEventListener('change', recalculateSplitter);
    pumpSelect.addEventListener('change', recalculateSplitter);
    strokeSlider.addEventListener('input', recalculateSplitter);
    psiSlider.addEventListener('input', recalculateSplitter);
    recalculateSplitter();

    const checks = document.querySelectorAll('.hyd-check');
    const badge = document.getElementById('hydBadge');
    checks.forEach(ch => {{
      ch.addEventListener('change', () => {{
        const done = Array.from(checks).filter(c => c.checked).length;
        badge.textContent = `${{done}} / ${{checks.length}} Completed`;
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
        f.write(html)


def rebuild_portal_sitemap_and_rss(published, mon_cfg):
    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "2+Stage+Hydraulic+Log+Splitter+Pump+Cylinder+Valve"), mon_cfg)

    cards_html = ""
    for item in reversed(published):
        cards_html += f"""
        <a href="{item['slug']}.html" class="block bg-zinc-900 border border-zinc-800 hover:border-orange-500/60 rounded-xl p-5 transition group">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-black uppercase bg-orange-500 text-zinc-950 px-2.5 py-0.5 rounded">{item.get('tons', 27.8)} Tons ({item.get('bore', 4.5)}")</span>
            <span class="text-xs text-zinc-400">{item.get('gpm', 16)} GPM | {item.get('sec', 10.6)}s Cycle</span>
          </div>
          <h2 class="text-base font-bold text-white group-hover:text-orange-400 transition">{item['splitter_name']}</h2>
          <p class="text-xs text-zinc-400 mt-2 line-clamp-2">{item['description']}</p>
          <span class="inline-block mt-4 text-xs font-extrabold text-orange-400">Calculate Tonnage, GPM & Cycle Time →</span>
        </a>"""

    index_html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SplitterTonIndex — Hydraulic Log Splitter Tonnage, 2-Stage Pump GPM & Cycle Time Calculator (2026)</title>
  <meta name="description" content="Calculate exact hydraulic log splitter cylinder tonnage, 11 to 28 GPM 2-stage pump cycle time in seconds, gas engine horsepower, and hydraulic oil tank capacity for Champion, CountyLine, Predator, and custom builds.">
  <link rel="canonical" href="{SITE_BASE_URL}/">
  <link rel="alternate" type="application/rss+xml" title="SplitterTonIndex RSS Feed" href="{SITE_BASE_URL}/rss.xml">
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-zinc-950 text-zinc-100 min-h-screen flex flex-col">
  <header class="border-b border-zinc-800 bg-zinc-900/80 sticky top-0 z-30 backdrop-blur">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <div class="text-lg font-black text-white flex items-center gap-2">
        <span class="bg-orange-500 text-zinc-950 px-2 py-0.5 rounded font-black">SPLITTER</span>TonIndex
      </div>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-orange-500 hover:bg-orange-400 text-zinc-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Hydraulic Pumps & Cylinders →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-12 flex-1 w-full">
    <div class="text-center max-w-2xl mx-auto mb-10">
      <h1 class="text-3xl sm:text-5xl font-black text-white tracking-tight">Hydraulic Log Splitter Tonnage, Pump GPM & Cycle Time Database</h1>
      <p class="text-zinc-400 mt-3 text-base sm:text-lg">Select your log splitter model, cylinder bore, or 2-stage hydraulic pump below to calculate true splitting force in tons, extend/retract cycle speed, and engine HP requirements.</p>
      <div class="mt-6">
        <input id="filterInput" type="text" placeholder="Search cylinder, pump, or splitter (e.g. 16 GPM Pump, 22 GPM, 4.5x24 Cylinder, Champion 27 Ton, CountyLine 25 Ton, PTO...)" class="w-full bg-zinc-900 border border-zinc-700 rounded-xl px-4 py-3.5 text-sm text-white focus:outline-none focus:border-orange-500">
      </div>
    </div>

    <div id="hydGrid" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">{cards_html}</div>
  </main>

  <footer class="border-t border-zinc-800 py-8 text-center text-xs text-zinc-500">
    <p>© {datetime.now(timezone.utc).year} SplitterTonIndex. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const filterInput = document.getElementById('filterInput');
    const cards = Array.from(document.getElementById('hydGrid').children);
    filterInput.addEventListener('input', (e) => {{
      const q = e.target.value.toLowerCase();
      cards.forEach(c => {{
        c.style.display = c.textContent.toLowerCase().includes(q) ? 'block' : 'none';
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls_xml = f"""  <url>
    <loc>{SITE_BASE_URL}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>\n"""

    for item in published:
        urls_xml += f"""  <url>
    <loc>{SITE_BASE_URL}/{item['slug']}.html</loc>
    <lastmod>{item.get('date', today)}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.9</priority>
  </url>\n"""

    with open(os.path.join(DOCS_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls_xml}</urlset>""")

    rss_items = ""
    for item in list(reversed(published))[:30]:
        rss_items += f"""    <item>
      <title>{item['title']}</title>
      <link>{SITE_BASE_URL}/{item['slug']}.html</link>
      <guid>{SITE_BASE_URL}/{item['slug']}.html</guid>
      <description>{item['description']}</description>
    </item>\n"""

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>SplitterTonIndex Hydraulic Log Splitter & Cylinder Sizing Database</title>
    <link>{SITE_BASE_URL}/</link>
    <description>Interactive Hydraulic Log Splitter Tonnage, 2-Stage Pump GPM & Cycle Time Calculators</description>
    <atom:link href="{SITE_BASE_URL}/rss.xml" rel="self" type="application/rss+xml" />
    <atom:link href="https://pubsubhubbub.appspot.com/" rel="hub" />
{rss_items}  </channel>
</rss>"""

    with open(os.path.join(DOCS_DIR, "rss.xml"), "w", encoding="utf-8") as f:
        f.write(rss_xml)

    with open(os.path.join(DOCS_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE_BASE_URL}/sitemap.xml\n")

    with open(os.path.join(DOCS_DIR, f"{INDEXNOW_KEY}.txt"), "w", encoding="utf-8") as f:
        f.write(INDEXNOW_KEY)


def notify_search_engines(new_urls):
    """Multi-Endpoint Search Engine Pinger (IndexNow Global + Bing + Google WebSub)."""
    if not SITE_BASE_URL or not new_urls:
        return
    parsed_host = urllib.parse.urlparse(SITE_BASE_URL).netloc
    payload = {
        "host": parsed_host,
        "key": INDEXNOW_KEY,
        "keyLocation": f"{SITE_BASE_URL}/{INDEXNOW_KEY}.txt",
        "urlList": new_urls
    }
    for idx_endpoint in ["https://api.indexnow.org/indexnow", "https://www.bing.com/indexnow"]:
        try:
            req = urllib.request.Request(
                idx_endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                print(f"[INDEXNOW] Pushed {len(new_urls)} URLs to {idx_endpoint} (HTTP {resp.status})")
                break
        except Exception as e:
            print(f"[WARN] IndexNow ({idx_endpoint}) notice: {e}")

    try:
        hub_data = urllib.parse.urlencode({
            "hub.mode": "publish",
            "hub.url": f"{SITE_BASE_URL}/rss.xml"
        }).encode("utf-8")
        req_hub = urllib.request.Request(
            "https://pubsubhubbub.appspot.com/",
            data=hub_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST"
        )
        with urllib.request.urlopen(req_hub, timeout=15) as resp_hub:
            print(f"[WEBSUB] Google PubSubHubbub ping status: {resp_hub.status}")
    except Exception as e:
        print(f"[WARN] WebSub ping notice: {e}")


def main():
    published = load_json(PUBLISHED_FILE, [])
    mon_cfg = load_json(MONETIZATION_FILE, {})
    published_slugs = {item["slug"] for item in published if "slug" in item}

    candidates = []
    if CUSTOM_SPLITTER:
        candidates.append((CUSTOM_SPLITTER.strip(), 4.5, 24.0, 2.00, 16.0, 3500))
    candidates.extend(SEED_SPLITTERS)
    candidates.extend(discover_google_splitter_queries(published_slugs))

    new_urls = []
    count = 0

    for split_tuple in candidates:
        if count >= PAGES_PER_RUN:
            break
        s_name = split_tuple[0]
        slug = slugify(f"{s_name}-tonnage-cycle-time-calculator")
        if slug in published_slugs:
            continue

        print(f"[ENGINE] Generating hydraulic log splitter tonnage & pump calculator for: {s_name}...")
        try:
            data = generate_splitter_data(split_tuple)
            build_splitter_html_page(data, slug, mon_cfg)
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            sp = data.get("specs", {})

            published.append({
                "splitter_name": data.get("splitter_name", s_name),
                "slug": slug,
                "title": data.get("seo_title", f"{s_name} Log Splitter Calculator"),
                "description": data.get("meta_description", ""),
                "bore": round(safe_float(sp.get("cylinder_bore_in", split_tuple[1]), split_tuple[1]), 1),
                "tons": round(safe_float(sp.get("true_splitting_tons", 27.8), 27.8), 1),
                "gpm": int(safe_float(sp.get("pump_flow_gpm", split_tuple[4]), split_tuple[4])),
                "sec": round(safe_float(sp.get("total_cycle_sec", 10.6), 10.6), 1),
                "date": today
            })
            published_slugs.add(slug)
            if SITE_BASE_URL:
                new_urls.append(f"{SITE_BASE_URL}/{slug}.html")
            count += 1
            if count < PAGES_PER_RUN:
                time.sleep(15)
        except Exception as e:
            print(f"[ERROR] Failed building {s_name}: {e}")

    save_json(PUBLISHED_FILE, published)
    rebuild_portal_sitemap_and_rss(published, mon_cfg)
    if new_urls and SITE_BASE_URL:
        new_urls.append(f"{SITE_BASE_URL}/")
        notify_search_engines(new_urls)
    print(f"[DONE] Published {count} new hydraulic log splitter tonnage & pump calculator pages.")


if __name__ == "__main__":
    main()
