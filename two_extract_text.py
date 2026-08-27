import pdfplumber

MIN_CHARS_TO_TRUST_TEXT_LAYER = 30


def extract_raw_text(pdf_path: str) -> tuple[str, str]:
    
    text_chunks = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_chunks.append(page_text)

    text = "\n".join(text_chunks).strip()

    if len(text) < MIN_CHARS_TO_TRUST_TEXT_LAYER:
        raise ValueError(
            f"No usable text layer found in '{pdf_path}' "
            f"(only {len(text)} characters extracted). "
            f"This pipeline expects digitally generated PDFs with an "
            f"embedded text layer - scanned/image-only PDFs are not supported."
        )

    return text, "pdfplumber"


if __name__ == "__main__":
    pdf_path = "D:/Initiatives/AI-Initiatives/AI_shift_lift/Document/Magma_Input.pdf"
    raw_text, method = extract_raw_text(pdf_path)

    print(f"Extraction method used: {method}")
    print(f"Character count: {len(raw_text)}")
    print("---")
    print(raw_text)