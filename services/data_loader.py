"""
Loads and unions all CSV files found in the data/ folder.
Each CSV must have the same column structure as the old yearly Excel sheets.
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

def load_candidates(csv_folder: Path) -> tuple:
    """
    Reads all XLSX files in csv_folder, unions them with pandas.
    Returns (combined_dataframe, list_of_warnings).
    """
    xlsx_files = sorted(xlsx_folder.glob("*.xlsx"))

    if not xlsx_files:
        raise FileNotFoundError(
            f"No CSV files found in: {xlsx_folder}\n"
            "Please place at least one XLSX file in the 'data/' folder."
        )

    frames = []
    warnings = []

    for f in csv_files:
        try:
            df = pd.read_excel(f, dtype=str)
            df.columns = df.columns.str.strip()
            df["_source_file"] = f.name  # track which file each row came from
            frames.append(df)
        except Exception as e:
            warnings.append(f"⚠️ Could not read '{f.name}': {e}")

    if not frames:
        raise ValueError("All CSV files failed to load. Check the file contents.")

    combined = pd.concat(frames, ignore_index=True)

    # Validate that all required columns are present
    missing = [c for c in REQUIRED_COLS if c not in combined.columns]
    if missing:
        raise ValueError(
            "The following required columns are missing from your CSV files:\n"
            + "\n".join(f"  • {c}" for c in missing)
        )

    return combined, warnings