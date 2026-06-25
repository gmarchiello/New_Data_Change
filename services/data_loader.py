"""
Loads and unions all XLSX files found in the data/candidates folder.
Each XLSX must have the expected column structure.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from pathlib import Path

REQUIRED_COLS = [
    "Client_code", "Exam_code", "Gender", "Name", "Surname",
    "Country_of_birth", "Date_of_birth", "Place_of_birth", "Email",
    "Gender_chk", "Name_chk", "Surname_chk", "Date_of_birth_chk",
    "Place_of_birth_chk", "Country_of_birth_chk", "Email_chk",
]

def load_candidates(xlsx_folder: Path) -> tuple:
    """
    Reads all XLSX files in xlsx_folder and unions them with pandas.
    Returns (combined_dataframe, list_of_warnings).
    """
    xlsx_files = sorted(xlsx_folder.glob("*.xlsx"))

    if not xlsx_files:
        raise FileNotFoundError(
            f"No XLSX files found in: {xlsx_folder}\n"
            "Please place at least one XLSX file in the 'data/candidates/' folder."
        )

    frames = []
    warnings = []

    for f in xlsx_files:
        try:
            df = pd.read_excel(f, dtype=str)
            df.columns = df.columns.str.strip()
            df["_source_file"] = f.name
            frames.append(df)
        except Exception as e:
            warnings.append(f"⚠️ Could not read '{f.name}': {e}")

    if not frames:
        raise ValueError("All XLSX files failed to load. Check the file contents.")

    combined = pd.concat(frames, ignore_index=True)

    missing = [c for c in REQUIRED_COLS if c not in combined.columns]
    if missing:
        raise ValueError(
            "The following required columns are missing from your XLSX files:\n"
            + "\n".join(f"  • {c}" for c in missing)
        )

    return combined, warnings