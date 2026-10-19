import json
import glob
import os
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(ROOT, "data", "raw")
OUTPUT_PATH = os.path.join(ROOT, "output", "profiles.json")

N_SAMPLES = 3
MAX_SAMPLE_LEN = 50


def read_csv(path):
    """Read a CSV as UTF-8, falling back to latin-1 if that fails."""
    try:
        return pd.read_csv(path)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="latin-1")


def sample_values(s):
    """Return up to N_SAMPLES distinct non-null values as short strings."""
    values = s.dropna().unique()[:N_SAMPLES]
    return [str(v)[:MAX_SAMPLE_LEN] for v in values]


def profile_table(path):
    name = os.path.splitext(os.path.basename(path))[0]
    df = read_csv(path)
    row_cnt, col_cnt = df.shape
    col_names = list(df.columns)

    columns = []
    for col in col_names:
        s = df[col]
        columns.append({
            "name": col,
            "dtype": str(s.dtype),
            "null_ratio": round(float(s.isna().mean()), 3),
            "n_unique": int(s.nunique()),
            "samples": sample_values(s),
        })

    return {
        "table_name": name,
        "n_rows": row_cnt,
        "n_cols": col_cnt,
        "columns": columns
    }


if __name__ == "__main__":
    csv_files = sorted(glob.glob(os.path.join(RAW_DIR, "*.csv")))

    profiles = []
    for file in csv_files:
        try:
            profile = profile_table(file)
        except Exception as e:
            print(f"Skipped {os.path.basename(file)}: {e}")
            continue
        profiles.append(profile)
        print(f"{profile['table_name']}: {profile['n_rows']} rows, {profile['n_cols']} cols")

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(profiles)} profiles to {OUTPUT_PATH}")