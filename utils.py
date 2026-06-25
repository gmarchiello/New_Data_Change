import os
import re
import pandas as pd
from datetime import datetime
from pytz import timezone
from pathlib import Path


# --- TIMEZONE SETUP ---
italy_tz = timezone("Europe/Rome")

# Helper to safely extract values for PDF fields or filenames
def safe_get(value, for_pdf_field=True, placeholder="UNKNOWN"):
    """
    Safely extracts a value for PDF fields or filenames.
    - Returns an empty string for missing PDF values.
    - Returns 'UNKNOWN' for missing filename values.
    """
    if pd.isna(value) or str(value).strip() in ["", "nan", "NaT"]:
        return "" if for_pdf_field else placeholder
    
    # Convert float into integer if applicable
    if isinstance(value, float) and value.is_integer():
        value = int(value)

    return str(value).strip()

# Creates a timestamped output folder and returns a Path object.
def make_output_folder(base_dir):
    base_dir = Path(base_dir)
    timestamp = datetime.now(italy_tz).strftime("%Y%m%d_%H%M")
    output_dir = base_dir / f"fulfilled_forms_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir

# Helper to create safe filenames
def clean_filename(name, surname, suffix_list):
    suffix_strs = [str(s) for s in suffix_list] # ensure all suffixes are strings
    safe_name = re.sub(
        r"[^a-zA-Z0-9]",
        "_",
        f"{surname}_{name}_change_request_" + "_".join(suffix_strs),
    )
    return safe_name

# Helper to get list of checked fields from a DataFrame row
def get_checked_fields(row,checkbox_map):
    """
    Returns a list of user-friendly names for checkboxes marked 'ON' in the given row.
    """
    changed = []
    for pdf_checkbox, excel_col in checkbox_map.items():
        if str(row.get(excel_col, "")).strip().upper() == "ON":
            friendly_name = excel_col.replace("_chk", "")
            changed.append(friendly_name)
    return changed
