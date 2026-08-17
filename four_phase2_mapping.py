"""
Phase 2 - Schema/field-name mapping via Groq.

Takes Phase 1's JSON (arbitrary key names, model's own interpretation) and
maps it onto your exact target schema. This step renames KEYS ONLY - it
must never alter, reformat, or invent VALUES. That's what keeps this step
safe: Phase 1 decides what the values are, Phase 2 only relabels them,
Phase 3 places them with zero AI involvement.
"""

import os
import json
from dotenv import load_dotenv
from groq import Groq

from two_extract_text import extract_raw_text
from three_phase1_extract import run_phase1_extraction

load_dotenv()
client = Groq(api_key=os.environ["GROQ_API_KEY"])

PHASE2_MODEL = "openai/gpt-oss-20b"

# This is the exact schema Phase 3's fill step will expect.
# Update this once you've measured the real placeholder fields on Magma_Output.pdf.
TARGET_SCHEMA = {
    "name": "Customer's full name",
    "address": "Customer's full mailing address",
    "proposal_number": "Proposal/reference number",
    "policy_plan": "Policy name and plan/variant combined",
    "premium_value": "Premium amount, digits only, no currency symbol or commas",
    "date": "Letter date, DD-MM-YYYY",
    "modification_note": "Reason for any coverage modification, if any"
}

MAPPING_PROMPT = """You are reconciling JSON field names to match a target schema.

You will be given:
1. A source JSON object with arbitrary key names and their values.
2. A target schema listing the exact key names required, with a description of what each should contain.

Your ONLY job is to rename/re-key the source JSON so its keys match the target schema exactly.

STRICT RULES:
- Do NOT change, reformat, translate, or rewrite any value. Copy each value exactly as given in the source.
- Do NOT invent values for target keys that have no reasonable match in the source - use null instead.
- If a target key logically combines two source fields (e.g. policy_plan from policy_name + plan), concatenate the original values as given, don't reword them.
- Output ONLY a valid JSON object using exactly the target schema's keys, nothing else.

Target schema:
{target_schema}

Source JSON:
{source_json}
"""


def run_phase2_mapping(source_json: dict) -> str:
    prompt = MAPPING_PROMPT.format(
        target_schema=json.dumps(TARGET_SCHEMA, indent=2),
        source_json=json.dumps(source_json, indent=2),
    )

    response = client.chat.completions.create(
        model=PHASE2_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0,
    )

    return response.choices[0].message.content


if __name__ == "__main__":
    pdf_path = "D:/Initiatives/AI-Initiatives/AI_shift_lift/Document/Magma_Input.pdf"

    # --- Step 2: raw text ---
    raw_text, method = extract_raw_text(pdf_path)
    print(f"[Step 2] Extracted {len(raw_text)} chars via {method}")

    # --- Phase 1: structured extraction ---
    phase1_raw = run_phase1_extraction(raw_text)
    phase1_json = json.loads(phase1_raw)
    print("[Phase 1] Output:")
    print(json.dumps(phase1_json, indent=2))
    print("-" * 50)

    # --- Phase 2: schema mapping ---
    phase2_raw = run_phase2_mapping(phase1_json)
    print("[Phase 2] Raw model output:")
    print(phase2_raw)
    print("-" * 50)

    try:
        phase2_json = json.loads(phase2_raw)
        print("[Phase 2] Parsed successfully. Final mapped fields:")
        for key, value in phase2_json.items():
            print(f"  {key}: {value!r}")

        missing_keys = set(TARGET_SCHEMA.keys()) - set(phase2_json.keys())
        if missing_keys:
            print(f"\n[WARNING] Target schema keys missing from output: {missing_keys}")
    except json.JSONDecodeError as e:
        print(f"[Phase 2] FAILED to parse as JSON: {e}")