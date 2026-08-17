import pdfplumber
import pytesseract
from PIL import Image
import pymupdf

MIN_CHARS_TO_TRUST_TEXT_LAYER = 30

def extract_with_pdfplumber(pdf_path: str) -> str:
    """Try native text extraction. Returns '' if nothing usable was found."""
    text_chunks = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_chunks.append(page_text)
    return "\n".join(text_chunks).strip()
 
 
def extract_with_ocr(pdf_path: str, dpi: int = 300) -> str:
    """Fallback: render each page to an image and OCR it with pytesseract."""
    text_chunks = []
    doc = pymupdf.open(pdf_path)
    for page in doc:
        pix = page.get_pixmap(dpi=dpi)
        img_path = "/tmp/_ocr_page.png"
        pix.save(img_path)
        img = Image.open(img_path)
        page_text = pytesseract.image_to_string(img)
        text_chunks.append(page_text)
    doc.close()
    return "\n".join(text_chunks).strip()
 
 
def extract_raw_text(pdf_path: str) -> tuple[str, str]:
    """
    Returns (raw_text, method_used) where method_used is 'pdfplumber' or 'ocr'.
    """
    text = extract_with_pdfplumber(pdf_path)
    if len(text) >= MIN_CHARS_TO_TRUST_TEXT_LAYER:
        return text, "pdfplumber"
 
    # Fallback path - likely a scanned PDF
    text = extract_with_ocr(pdf_path)
    return text, "ocr"
 
 
if __name__ == "__main__":
    pdf_path = "D:/Initiatives/AI-Initiatives/AI_shift_lift/Document/Magma_Input.pdf"
    raw_text, method = extract_raw_text(pdf_path)
 
    print(f"Extraction method used: {method}")
    print(f"Character count: {len(raw_text)}")
    print("---")
    print(raw_text)