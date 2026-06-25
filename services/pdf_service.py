"""
Orchestrates PDF generation for a list of selected candidate rows.
Returns results and a zipped bytes object ready for Streamlit download.
"""
import sys, os, io, zipfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from datetime import datetime
from pathlib import Path
from pytz import timezone

from config import CONFIG, CHECKBOX_MAP, TEXT_MAP
from utils import safe_get, make_output_folder, clean_filename
from pdf_filler import fill_pdf

italy_tz = timezone("Europe/Rome")


def _build_text_values(row: pd.Series) -> dict:
    text_values = {}
    for pdf_field, excel_col in TEXT_MAP.items():
        if excel_col:
            value = row.get(excel_col)
            if pdf_field == "txt_date_of_birth":
                birth_date = pd.to_datetime(value, errors="coerce")
                text_values[pdf_field] = (
                    birth_date.strftime("%d/%m/%Y") if pd.notnull(birth_date) else ""
                )
            else:
                text_values[pdf_field] = safe_get(value)
        else:
            if pdf_field in [
                "txt_director", "txt_exam_center_city", "txt_exam_center_country",
                "txt_institute_city", "txt_location",
            ]:
                text_values[pdf_field] = CONFIG[pdf_field.replace("txt_", "")]
            elif pdf_field == "txt_today_date":
                text_values[pdf_field] = datetime.now(italy_tz).strftime("%d %B %Y")
    return text_values


def process_rows(selected_df: pd.DataFrame, pdf_template_path: Path, output_dir: Path) -> tuple:
    """
    Generates one PDF per row in selected_df.
    Returns (results_list, output_folder_path).

    Each item in results_list is a dict with:
      name, surname, status ('ok'|'warning'|'error'),
      filename, filepath, checked_fields, missing_text, missing_checkbox, error
    """
    output_folder = make_output_folder(output_dir)
    results = []

    for idx, row in selected_df.iterrows():
        # Which fields are ticked for change?
        checked_fields = [
            excel_col.replace("_chk", "")
            for _, excel_col in CHECKBOX_MAP.items()
            if str(row.get(excel_col, "")).strip().upper() == "ON"
        ]
        missing_checkbox = not bool(checked_fields)

        # Which required text fields are empty?
        missing_text = [
            excel_col for excel_col in TEXT_MAP.values()
            if excel_col is not None and not safe_get(row.get(excel_col))
        ]

        # Build a safe filename
        name    = safe_get(row.get("Name"),    for_pdf_field=False)
        surname = safe_get(row.get("Surname"), for_pdf_field=False)
        suffix_list = []
        if checked_fields:
            suffix_list.append("_".join(checked_fields))
        if missing_text:
            suffix_list.append("MISSING_" + "_".join(missing_text))
        if missing_checkbox:
            suffix_list.append("MISSING_CHECKBOX")
        safe_name = clean_filename(name, surname, suffix_list)
        output_pdf_path = output_folder / f"{safe_name}.pdf"

        # Fill the PDF
        text_values = _build_text_values(row)
        checkboxes_to_check = [
            pdf_field for pdf_field, excel_col in CHECKBOX_MAP.items()
            if str(row.get(excel_col, "")).strip().upper() == "ON"
        ]

        error = None
        try:
            fill_pdf(str(pdf_template_path), str(output_pdf_path), text_values, checkboxes_to_check)
        except Exception as e:
            error = str(e)

        status = "error" if error else ("warning" if (missing_text or missing_checkbox) else "ok")

        results.append({
            "name":             name,
            "surname":          surname,
            "status":           status,
            "filename":         output_pdf_path.name,
            "filepath":         output_pdf_path,
            "checked_fields":   checked_fields,
            "missing_text":     missing_text,
            "missing_checkbox": missing_checkbox,
            "error":            error,
        })

    return results, output_folder


def zip_results(results: list) -> bytes:
    """Packs all successfully generated PDFs into a ZIP, returned as bytes."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for r in results:
            if r["status"] != "error" and Path(r["filepath"]).exists():
                zf.write(r["filepath"], r["filename"])
    buf.seek(0)
    return buf.read()


def build_email_summary(results: list, chunk_size: int = 10) -> list:
    """
    Returns a list of {subject, body} dicts for copy-paste email sending.
    One message per chunk_size candidates.
    """
    lines = []
    for r in results:
        changed = ", ".join(r["checked_fields"]) if r["checked_fields"] else "No changes"
        line = f"{r['surname']} {r['name']} ({changed})"
        if r["missing_text"]:
            line += " ⚠️ MISSING: " + ", ".join(r["missing_text"])
        if r["missing_checkbox"]:
            line += " ❗ NO CHECKBOX SELECTED"
        lines.append((r["surname"], r["name"], line))

    lines.sort()
    chunks = [lines[i:i+chunk_size] for i in range(0, len(lines), chunk_size)]
    messages = []
    for chunk in chunks:
        subject = "Change Request: " + ", ".join(f"{e[1]} {e[0]}" for e in chunk)
        body = (
            "Good morning,\n"
            "I kindly ask you to update the data of the following candidates:\n\n"
            + "\n".join(f"- {e[2]}" for e in chunk)
        )
        messages.append({"subject": subject, "body": body})
    return messages