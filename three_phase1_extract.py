import os
import json
from dotenv import load_dotenv
from groq import Groq

from two_extract_text import extract_raw_text

load_dotenv()
client = Groq(api_key=os.environ["GROQ_API_KEY"])

PHASE1_MODEL = "qwen/qwen3.6-27b"

# This is now the single source of truth for field names - both this
# script's prompt AND the fill script's SCHEMA_TO_TEMPLATE_FIELDS must
# use these exact keys. No second mapping stage exists anymore, so
# there's no reconciliation step to catch a mismatch - if this changes,
# five_template_cordinates.py / six_to_templete.py must be updated too.
TARGET_SCHEMA = {
    "name": "Customer's full name",
    "address": "Customer's full mailing address",
    "proposal_number": "Proposal/reference number",
    "policy_plan": "Policy name and plan/variant combined into one string (e.g. 'OneHealth Premium Plus - Enhanced Coverage (Plan 1A + 2C)')",
    "premium_value": "Premium amount, digits only, no currency symbol or commas",
    "date": "Letter date, in DD-MM-YYYY format",
    "modification_note": "Reason for any coverage modification, if any",
}

EXTRACTION_PROMPT = """You are extracting structured data from an insurance counter-offer letter.

Read the letter text below and extract the following fields. If a field is not present in the letter, use null as its value - do not guess or invent a value.

Fields to extract, using EXACTLY these key names:
{schema_description}

Return ONLY a valid JSON object with exactly these keys. No explanation, no markdown, no extra text.

Letter text:
---
{letter_text}
---
"""


def _build_schema_description() -> str:
    return "\n".join(f"- {key}: {desc}" for key, desc in TARGET_SCHEMA.items())


def run_phase1_extraction(letter_text: str) -> str:
    prompt = EXTRACTION_PROMPT.format(
        schema_description=_build_schema_description(),
        letter_text=letter_text,
    )

    response = client.chat.completions.create(
        model=PHASE1_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},  # forces valid JSON output
        reasoning_effort="none",                  # skip <think> block, go straight to the answer
        temperature=0,                             # deterministic extraction, not creative
    )

    raw_output = response.choices[0].message.content
    return raw_output


if __name__ == "__main__":
    pdf_path = "D:/Initiatives/AI-Initiatives/AI_shift_lift/Document/Magma_Input.pdf"

    raw_text, method = extract_raw_text(pdf_path)
    print(f"[Step 2] Extracted {len(raw_text)} chars via {method}")
    print("-" * 50)

    raw_json_string = run_phase1_extraction(raw_text)
    print("[Phase 1] Raw model output:")
    print(raw_json_string)
    print("-" * 50)

    try:
        parsed = json.loads(raw_json_string)
        print("[Phase 1] Parsed successfully. Fields found:")
        for key, value in parsed.items():
            print(f"  {key}: {value!r}")

        missing_keys = set(TARGET_SCHEMA.keys()) - set(parsed.keys())
        if missing_keys:
            print(f"\n[WARNING] Target schema keys missing from output: {missing_keys}")
    except json.JSONDecodeError as e:
        print(f"[Phase 1] FAILED to parse as JSON: {e}")