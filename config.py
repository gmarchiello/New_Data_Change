from pathlib import Path

# --- FILE PATHS ---
BASE_DIR = Path(__file__).resolve().parent   # ← changed: config.py is now at root

INPUT_DIR = BASE_DIR / "input"
PDF_PATH  = INPUT_DIR / "templates" / "data_form_editable.pdf"

OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# --- CONFIGURATION ---
CONFIG = {
    "director":           "John Smith",
    "exam_center_city":   "Naples",
    "exam_center_country":"Italy",
    "institute_city":     "Naples",
    "location":           "Naples",
    "chunk_size":         10,
}

# --- PDF CHECKBOX FIELDS → CSV COLUMN NAMES ---
CHECKBOX_MAP = {
    "chk_gender":          "Gender_chk",
    "chk_name":            "Name_chk",
    "chk_surname":         "Surname_chk",
    "chk_date_of_birth":   "Date_of_birth_chk",
    "chk_place_of_birth":  "Place_of_birth_chk",
    "chk_country_of_birth":"Country_of_birth_chk",
    "chk_email":           "Email_chk",
}

# --- PDF TEXT FIELDS → CSV COLUMN NAMES ---
# None = filled from CONFIG or today's date automatically
TEXT_MAP = {
    "txt_director":           None,
    "txt_exam_center_city":   None,
    "txt_exam_center_country":None,
    "txt_institute_city":     None,
    "txt_location":           None,
    "txt_today_date":         None,
    "txt_client_code":        "Client_code",
    "txt_exam_code":          "Exam_code",
    "txt_gender":             "Gender",
    "txt_name":               "Name",
    "txt_surname":            "Surname",
    "txt_country_of_birth":   "Country_of_birth",
    "txt_date_of_birth":      "Date_of_birth",
    "txt_place_of_birth":     "Place_of_birth",
    "txt_email":              "Email",
}

# --- HUMAN-READABLE CHECKBOX LABELS (used in Streamlit UI) ---
CHECKBOX_LABELS = {
    "Gender_chk":          "Gender",
    "Name_chk":            "Name",
    "Surname_chk":         "Surname",
    "Date_of_birth_chk":   "Date of birth",
    "Place_of_birth_chk":  "Place of birth",
    "Country_of_birth_chk":"Country of birth",
    "Email_chk":           "Email",
}