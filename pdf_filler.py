# --- IMPORTS ---
from pdfrw import PdfReader, PdfWriter, PdfName, PdfObject

# --- PDF FILLING FUNCTION ---
# Helper to fill PDF with text values and checkboxes
def fill_pdf(input_pdf_path, output_pdf_path, text_values, checkboxes_to_check):
    input_pdf_path = str(input_pdf_path)
    output_pdf_path = str(output_pdf_path)
    """
    Fills a PDF template with provided text values and selected checkboxes.
    Ensures 'NeedAppearances' is set so form fields display correctly.
    """
    pdf = PdfReader(input_pdf_path)
    pdf.Root.AcroForm.update({PdfName("NeedAppearances"): PdfObject("true")})

    for page in pdf.pages:
        annotations = page.Annots
        if not annotations:
            continue

        for annot in annotations:
            if annot.Subtype == PdfName.Widget and annot.T:
                key = annot.T.to_unicode().strip()
                # Insert text values
                if key in text_values:
                    annot.V = text_values[key]
                    annot.AP = None
                # Mark checkboxes
                elif key in checkboxes_to_check:
                    annot.V = PdfName("Yes")
                    annot.AS = PdfName("Yes")

    PdfWriter().write(output_pdf_path, pdf)
