import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd
from pathlib import Path

from config import CONFIG, CHECKBOX_MAP, TEXT_MAP, CHECKBOX_LABELS
from services.data_loader import load_candidates
from services.pdf_service import process_rows, zip_results, build_email_summary

# ─── PAGE CONFIG ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Candidate Change Request",
    page_icon="📋",
    layout="centered",
)

# ─── PATHS ───────────────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).resolve().parent
CSV_FOLDER   = BASE_DIR / "data"
PDF_TEMPLATE = BASE_DIR / "input" / "templates" / "data_form_editable.pdf"
OUTPUT_DIR   = BASE_DIR / "output"

# ─── SESSION STATE INIT ──────────────────────────────────────────────────────
if "df"               not in st.session_state: st.session_state.df               = None
if "queue"            not in st.session_state: st.session_state.queue            = []
if "results"          not in st.session_state: st.session_state.results          = None
if "zip_bytes"        not in st.session_state: st.session_state.zip_bytes        = None
if "email_msgs"       not in st.session_state: st.session_state.email_msgs       = None
if "found_candidate"  not in st.session_state: st.session_state.found_candidate  = None
if "search_done"      not in st.session_state: st.session_state.search_done      = False

# ─── HELPERS ─────────────────────────────────────────────────────────────────
FIELD_LABELS = {
    "Client_code":      "Client code",
    "Exam_code":        "Exam code",
    "Gender":           "Gender",
    "Name":             "Name",
    "Surname":          "Surname",
    "Date_of_birth":    "Date of birth",
    "Place_of_birth":   "Place of birth",
    "Country_of_birth": "Country of birth",
    "Email":            "Email",
}

CHK_COLS = list(CHECKBOX_MAP.values())

def find_by_email(df, email):
    mask = df["Email"].str.strip().str.lower() == email.strip().lower()
    matches = df[mask]
    return matches.iloc[0].to_dict() if not matches.empty else None

def search_candidates(df, name="", surname="", dob=""):
    result = df.copy()
    if name.strip():
        result = result[result["Name"].str.lower().str.contains(name.strip().lower(), na=False)]
    if surname.strip():
        result = result[result["Surname"].str.lower().str.contains(surname.strip().lower(), na=False)]
    if dob.strip():
        result = result[result["Date_of_birth"].str.contains(dob.strip(), na=False)]
    return result

def candidate_label(c):
    return f"{c.get('Surname','')} {c.get('Name','')} — {c.get('Email','')} ({c.get('_source_file','')})"

# ─── LOAD DATA ────────────────────────────────────────────────────────────────
st.title("📋 Candidate Change Request")

if st.session_state.df is None:
    with st.spinner("Loading candidate data…"):
        try:
            df, warns = load_candidates(CSV_FOLDER)
            st.session_state.df = df
            for w in warns:
                st.warning(w)
            st.success(f"✅ {len(df):,} candidates loaded from {CSV_FOLDER.name}/")
        except Exception as e:
            st.error(f"❌ Could not load data:\n\n{e}")
            st.stop()
else:
    df = st.session_state.df

st.divider()

# ════════════════════════════════════════════════════════════════════════════
# STEP 1 — FIND CANDIDATE
# ════════════════════════════════════════════════════════════════════════════
st.subheader("🔍 Step 1 — Find a candidate")

email_input = st.text_input("Search by email address", placeholder="e.g. mario.rossi@email.com")

found = None
show_fallback = False

if email_input.strip():
    found = find_by_email(df, email_input)
    if found:
        st.success(f"✅ Found: **{found.get('Surname')} {found.get('Name')}**")
        st.session_state.found_candidate = found
        st.session_state.search_done = True
    else:
        st.warning("⚠️ No candidate found with that email. Search by other details below.")
        show_fallback = True

if show_fallback or (not email_input.strip() and not st.session_state.search_done):
    with st.expander("🔎 Search by Name / Surname / Date of birth", expanded=show_fallback):
        col1, col2, col3 = st.columns(3)
        s_name    = col1.text_input("Name",         key="s_name")
        s_surname = col2.text_input("Surname",       key="s_surname")
        s_dob     = col3.text_input("Date of birth", key="s_dob", placeholder="e.g. 1990")

        if s_name or s_surname or s_dob:
            results_df = search_candidates(df, s_name, s_surname, s_dob)
            if results_df.empty:
                st.info("No candidates match your search.")
            else:
                st.write(f"**{len(results_df)} result(s) found:**")
                display_cols = ["Surname", "Name", "Date_of_birth", "Email", "_source_file"]
                st.dataframe(
                    results_df[display_cols].rename(columns={
                        "Date_of_birth": "Date of birth",
                        "_source_file": "Source file"
                    }),
                    use_container_width=True,
                    hide_index=True,
                )
                options = [candidate_label(r) for _, r in results_df.iterrows()]
                chosen = st.selectbox("Select the correct candidate", ["— select —"] + options)
                if chosen != "— select —":
                    idx = options.index(chosen)
                    st.session_state.found_candidate = results_df.iloc[idx].to_dict()
                    st.session_state.search_done = True

# ════════════════════════════════════════════════════════════════════════════
# STEP 2 — EDIT + CHECKBOXES
# ════════════════════════════════════════════════════════════════════════════
if st.session_state.found_candidate:
    cand = st.session_state.found_candidate
    st.divider()
    st.subheader("✏️ Step 2 — Edit candidate data")
    st.caption("Pre-filled with current data. Change only what needs correcting.")

    edited = {}
    auto_chk = {}

    col_a, col_b = st.columns(2)
    field_list = list(FIELD_LABELS.items())
    half = len(field_list) // 2 + len(field_list) % 2

    for i, (col, label) in enumerate(field_list):
        container = col_a if i < half else col_b
        original = str(cand.get(col, "")).strip()
        if original in ("nan", "NaT"):
            original = ""
        new_val = container.text_input(label, value=original, key=f"edit_{col}")
        edited[col] = new_val
        chk_col = col + "_chk"
        if chk_col in CHK_COLS:
            auto_chk[chk_col] = "ON" if new_val.strip() != original.strip() else cand.get(chk_col, "")

    st.divider()
    st.subheader("☑️ Step 3 — Confirm what is changing")
    st.caption("Auto-ticked when you edit a field. Adjust manually if needed.")

    final_chk = {}
    chk_cols_display = st.columns(len(CHECKBOX_LABELS))
    for i, (chk_col, label) in enumerate(CHECKBOX_LABELS.items()):
        default = auto_chk.get(chk_col, cand.get(chk_col, "")) == "ON"
        checked = chk_cols_display[i].checkbox(label, value=default, key=f"chk_{chk_col}")
        final_chk[chk_col] = "ON" if checked else ""

    st.divider()

    if st.button("➕ Add to queue", type="primary", use_container_width=True):
        row_data = {**edited, **final_chk}
        for col in df.columns:
            if col not in row_data:
                row_data[col] = cand.get(col, "")
        st.session_state.queue.append(row_data)
        st.session_state.found_candidate = None
        st.session_state.search_done = False
        st.rerun()

# ════════════════════════════════════════════════════════════════════════════
# STEP 3 — QUEUE
# ════════════════════════════════════════════════════════════════════════════
if st.session_state.queue:
    st.divider()
    st.subheader(f"🗂️ Queue — {len(st.session_state.queue)} candidate(s) ready")

    to_remove = []
    for i, c in enumerate(st.session_state.queue):
        changed = [CHECKBOX_LABELS.get(k, k) for k, v in c.items() if k in CHK_COLS and v == "ON"]
        with st.container(border=True):
            col1, col2 = st.columns([6, 1])
            col1.markdown(
                f"**{c.get('Surname','')} {c.get('Name','')}** &nbsp;·&nbsp; "
                f"`{c.get('Email','')}` &nbsp;·&nbsp; "
                f"Changes: {', '.join(changed) if changed else '⚠️ none selected'}"
            )
            if col2.button("✕ Remove", key=f"remove_{i}"):
                to_remove.append(i)

    for i in reversed(to_remove):
        st.session_state.queue.pop(i)
        st.rerun()

    st.caption("Add more candidates above, or generate when ready.")

# ════════════════════════════════════════════════════════════════════════════
# STEP 4 — GENERATE
# ════════════════════════════════════════════════════════════════════════════
if st.session_state.queue:
    st.divider()
    st.subheader("🚀 Step 4 — Generate PDFs")

    if not PDF_TEMPLATE.exists():
        st.error(f"❌ PDF template not found at:\n`{PDF_TEMPLATE}`")
    else:
        if st.button("📄 Generate all PDFs", type="primary", use_container_width=True):
            queue_df = pd.DataFrame(st.session_state.queue)
            with st.spinner("Generating PDFs…"):
                try:
                    results, out_folder = process_rows(queue_df, PDF_TEMPLATE, OUTPUT_DIR)
                    st.session_state.results    = results
                    st.session_state.zip_bytes  = zip_results(results)
                    st.session_state.email_msgs = build_email_summary(results, CONFIG["chunk_size"])
                except Exception as e:
                    st.error(f"❌ Generation failed: {e}")

# ════════════════════════════════════════════════════════════════════════════
# STEP 4b — RESULTS
# ════════════════════════════════════════════════════════════════════════════
if st.session_state.results:
    st.divider()
    st.subheader("✅ Results")

    ok   = [r for r in st.session_state.results if r["status"] == "ok"]
    warn = [r for r in st.session_state.results if r["status"] == "warning"]
    err  = [r for r in st.session_state.results if r["status"] == "error"]

    col1, col2, col3 = st.columns(3)
    col1.metric("✅ Success",  len(ok))
    col2.metric("⚠️ Warnings", len(warn))
    col3.metric("❌ Errors",   len(err))

    for r in st.session_state.results:
        icon = "✅" if r["status"] == "ok" else ("⚠️" if r["status"] == "warning" else "❌")
        msg = f"{icon} **{r['surname']} {r['name']}** — `{r['filename']}`"
        if r["missing_text"]:
            msg += f"  \n&nbsp;&nbsp;&nbsp;Missing data: {', '.join(r['missing_text'])}"
        if r["missing_checkbox"]:
            msg += "  \n&nbsp;&nbsp;&nbsp;No checkbox selected"
        if r["error"]:
            msg += f"  \n&nbsp;&nbsp;&nbsp;Error: {r['error']}"
        st.markdown(msg)

    if st.session_state.zip_bytes:
        st.download_button(
            label="⬇️ Download all PDFs as ZIP",
            data=st.session_state.zip_bytes,
            file_name="change_requests.zip",
            mime="application/zip",
            use_container_width=True,
            type="primary",
        )

# ════════════════════════════════════════════════════════════════════════════
# STEP 5 — EMAIL SUMMARY
# ════════════════════════════════════════════════════════════════════════════
if st.session_state.email_msgs:
    st.divider()
    st.subheader("✉️ Step 5 — Email summary")
    st.caption("Copy and paste each message to send via your email client.")

    for i, msg in enumerate(st.session_state.email_msgs):
        with st.expander(f"📧 Message {i+1} — {msg['subject'][:60]}…", expanded=(i == 0)):
            st.text_input("Subject", value=msg["subject"], key=f"subj_{i}")
            st.text_area("Body", value=msg["body"], height=200, key=f"body_{i}")

    st.divider()
    if st.button("🔄 Start over", use_container_width=True):
        for key in ["queue", "results", "zip_bytes", "email_msgs", "found_candidate", "search_done"]:
            st.session_state[key] = [] if key == "queue" else None
        st.rerun()