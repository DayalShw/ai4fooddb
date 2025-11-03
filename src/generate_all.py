from pathlib import Path
import csv, subprocess, shlex, sys

# ----------------------------
# Config
# ----------------------------
ONTO = "ontology/ontology.ttl"
OUT  = "ai4food_triples.ttl"

# Set to False if we want to append to existing OUT across runs
CLEAN_OUTPUT_ON_START = True

# ----------------------------
# Problematic column overrides
# ----------------------------
# If a column doesn’t exist in ontology, map it to None (skip) or correct label.
MAP_OVERRIDES = {
    "data/anthropometrics.csv": {
        "muscle_mass_perc": None,  # skip or replace with correct ontology label
    },
    "data/biomarkers.csv": {
        "insulin_uui_ml": None,  # skip
    },
    "data/lifestyle.csv": {
        "daily_meals": None,  # skip
    },
    "data/OviedoSleepQuestionnaire.csv": {
        "2_2_remain_asleep": None,  # skip
    },
    "data/A4F_10660_physical_activity_reports.csv": {
        "_lightly_active_minutes": "lightly_active_minutes",  # rename
    },
}

# ----------------------------
# Init
# ----------------------------
if CLEAN_OUTPUT_ON_START:
    try:
        Path(OUT).unlink()
        print(f"🧹 Removed previous {OUT}")
    except FileNotFoundError:
        pass

if not Path(ONTO).exists():
    raise SystemExit(f"❌ Ontology not found at {ONTO}")

# ----------------------------
# Helpers
# ----------------------------
def header_cols(csv_path: str):
    with open(csv_path, newline="", encoding="utf-8") as f:
        return next(csv.reader(f))

def make_map_args(cols, overrides):
    """Create --map arguments, applying per-file overrides."""
    pairs = []
    for c in cols:
        if not c.strip() or c.lower() == "id":
            continue
        if c in overrides:
            target = overrides[c]
            if target is None:
                # skip this column
                continue
            pairs.append(f"{c}={target}")
        else:
            pairs.append(f"{c}={c}")
    return pairs

def run_one(csv_path: str, cls: str, base: str):
    """Run make_triples.py for a single dataset."""
    cols = header_cols(csv_path)
    subj_flag = ["--subject-column", "id"] if any(c.lower() == "id" for c in cols) else []
    overrides = MAP_OVERRIDES.get(csv_path, {})
    map_args = make_map_args(cols, overrides)

    cmd = [
        sys.executable, "src/make_triples.py",
        "--ontology", ONTO,
        "--csv", csv_path,
        "--base", base,
        "--class-label", cls,
        *subj_flag,
        "--map", *map_args,
        "--out", OUT,
    ]

    print("\n>>", " ".join(shlex.quote(x) for x in cmd[:10]), "... (+map)")
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Skipped {csv_path} ({cls}) due to error.\n   Command: {' '.join(cmd)}\n   Return code: {e.returncode}")
    except Exception as e:
        print(f"⚠️  Unexpected error running {csv_path} ({cls}): {e}")

# ----------------------------
# Task list
# ----------------------------
tasks = [
    ("data/participant_information.csv", "participant_information", "http://example.org/participant/"),
    ("data/anthropometrics.csv",         "anthropometrics",        "http://example.org/DS1_AnthropometricMeasurements/"),
    ("data/biomarkers.csv",              "biomarkers",             "http://example.org/DS3_Biomarkers/"),
    ("data/vital_signs.csv",             "vital_signs",            "http://example.org/DS4_VitalSigns/"),
    ("data/health.csv",                  "health",                 "http://example.org/DS2_LifestyleHealth/"),
    ("data/lifestyle.csv",               "lifestyle",              "http://example.org/DS2_LifestyleHealth/"),
    ("data/IPAQ.csv",                    "IPAQ",                   "http://example.org/DS5_PhysicalActivity/"),
    ("data/DASS-21.csv",                 "DASS-21",                "http://example.org/DS7_EmotionalState/"),
    ("data/OviedoSleepQuestionnaire.csv","OviedoSleepQuestionnaire","http://example.org/DS6_SleepActivity/"),

    # A4F_10021
    ("data/A4F_10021_active_minutes.csv",                   "A4F_10021_active_minutes",                   "http://example.org/DS5_PhysicalActivity/"),
    ("data/A4F_10021_additional_physical_activity_data.csv","A4F_10021_additional_physical_activity_data","http://example.org/DS5_PhysicalActivity/"),
    ("data/A4F_10021_additional_sleep_data.csv",            "A4F_10021_additional_sleep_data",            "http://example.org/DS6_SleepActivity/"),
    ("data/A4F_10021_computed_temperature.csv",             "A4F_10021_computed_temperature",            "http://example.org/DS6_SleepActivity/"),
    ("data/A4F_10021_daily_oxygen_saturation.csv",          "A4F_10021_daily_oxygen_saturation",          "http://example.org/DS6_SleepActivity/"),
    ("data/A4F_10021_eda_sessions.csv",                     "A4F_10021_eda_sessions",                     "http://example.org/DS7_EmotionalState/"),
    ("data/A4F_10021_electrocardiogram.csv",                "A4F_10021_electrocardiogram",                "http://example.org/DS4_VitalSigns/"),
    ("data/A4F_10021_estimated_vo2.csv",                    "A4F_10021_estimated_vo2",                    "http://example.org/DS5_PhysicalActivity/"),
    ("data/A4F_10021_glucose_levels.csv",                   "glucose_levels",                             "http://example.org/DS3_Biomarkers/"),
    ("data/A4F_10021_heart_rate.csv",                       "A4F_10021_heart_rate",                       "http://example.org/DS4_VitalSigns/"),
    ("data/A4F_10021_heart_rate_variability.csv",           "A4F_10021_heart_rate_variability",           "http://example.org/DS6_SleepActivity/"),
    ("data/A4F_10021_labeled_data.csv",                     "A4F_10021_labeled_data",                     "http://example.org/DS9_FoodNExtDB/"),
    ("data/A4F_10021_oxygen_saturation_by_minute.csv",      "A4F_10021_oxygen_saturation_by_minute",      "http://example.org/DS6_SleepActivity/"),
    ("data/A4F_10021_respiratory_rate.csv",                 "A4F_10021_respiratory_rate",                 "http://example.org/DS6_SleepActivity/"),
    ("data/A4F_10021_sleep_quality.csv",                    "A4F_10021_sleep_quality",                    "http://example.org/DS6_SleepActivity/"),
    ("data/A4F_10021_stress_score.csv",                     "A4F_10021_stress_score",                     "http://example.org/DS7_EmotionalState/"),
    ("data/A4F_10021_timestamps.csv",                       "A4F_10021_timestamps",                       "http://example.org/DS9_FoodNExtDB/"),
    ("data/A4F_10021_wrist_temperature.csv",                "A4F_10021_wrist_temperature",                "http://example.org/DS6_SleepActivity/"),

    # Fitbit reports
    ("data/A4F_10660_physical_activity_reports.csv",        "A4F_10660_physical_activity_reports",        "http://example.org/DS5_PhysicalActivity/"),
]

# ----------------------------
# Run all
# ----------------------------
for csv_path, cls, base in tasks:
    p = Path(csv_path)
    if p.exists():
        run_one(csv_path, cls, base)
    else:
        print(f"⏩ Skip (not found): {csv_path}")

print(f"\n✅ All triples written to {OUT}")