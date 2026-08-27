import json

from two_extract_text import extract_raw_text
from three_phase1_extract import run_phase1_extraction, TARGET_SCHEMA
from six_to_templete import fill_template

INPUT_PDF = "D:/Initiatives/AI-Initiatives/AI_shift_lift/Document/Magma_Input.pdf"
TEMPLATE_PDF = "D:/Initiatives/AI-Initiatives/AI_shift_lift/Document/Magma_Output.pdf"
OUTPUT_PDF = "D:/Initiatives/AI-Initiatives/AI_shift_lift/pdf_outputs/Magma_Output_FILLED.pdf"


def run_pipeline():
    print("=" * 60)
    print("STEP 2 - Raw text extraction")
    print("=" * 60)
    raw_text, method = extract_raw_text(INPUT_PDF)
    print(f"Method used: {method}")
    print(f"Character count: {len(raw_text)}")
    print()

    print("=" * 60)
    print("PHASE 1 - Structured extraction (Groq)")
    print("=" * 60)
    phase1_raw = run_phase1_extraction(raw_text)
    try:
        phase1_json = json.loads(phase1_raw)
    except json.JSONDecodeError as e:
        print(f"[FATAL] Phase 1 did not return valid JSON: {e}")
        print(f"Raw output was:\n{phase1_raw}")
        return
    print(json.dumps(phase1_json, indent=2))

    missing_keys = set(TARGET_SCHEMA.keys()) - set(phase1_json.keys())
    if missing_keys:
        print(f"[WARNING] Missing target schema keys: {missing_keys}")
    print()

    print("=" * 60)
    print("PHASE 3 - Deterministic fill (PyMuPDF, no AI)")
    print("=" * 60)
    fill_template(
        mapped_json=phase1_json,
        template_path=TEMPLATE_PDF,
        output_path=OUTPUT_PDF,
    )
    print()
    print("=" * 60)
    print(f"PIPELINE COMPLETE. Filled PDF saved to: {OUTPUT_PDF}")
    print("Now open both the source PDF and the filled output side by")
    print("side and check EVERY field for accuracy, not just presence.")
    print("=" * 60)


if __name__ == "__main__":
    run_pipeline()