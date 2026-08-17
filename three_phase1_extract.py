import os
import json
from dotenv import load_dotenv
from groq import Groq
 
from two_extract_text import extract_raw_text 

load_dotenv()
client = Groq(api_key=os.environ["GROQ_API_KEY"])

PHASE1_MODEL = "qwen/qwen3.6-27b"  # swap to "openai/gpt-oss-120b" to compare

EXTRACTION_PROMPT = """You are extracting structured data from an insurance counter-offer letter.

Read the letter text below and extract the following fields. If a field is not present in the letter, use null as its value - do not guess or invent a value.

Fields to extract:
- customer_name: the recipient's full name
- customer_address: the recipient's full mailing address, as one string
- proposal_number: the proposal / reference number (e.g. "PROP/2026/98765")
- policy_name: the name of the insurance policy/product
- plan: the specific plan or coverage variant (e.g. "1A + 2C")
- premium_amount: the premium amount, digits only, no currency symbol or commas
- letter_date: the date on the letter, in DD-MM-YYYY format
- modification_reason: the reason given for any change/modification, if stated

Return ONLY a valid JSON object with exactly these keys. No explanation, no markdown, no extra text.

Letter text:
---
{letter_text}
---
"""


def run_phase1_extraction(letter_text: str) -> dict:
    prompt = EXTRACTION_PROMPT.format(letter_text=letter_text)

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
    except json.JSONDecodeError as e:
        print(f"[Phase 1] FAILED to parse as JSON: {e}")