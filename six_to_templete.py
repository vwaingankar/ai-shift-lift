import pymupdf

from five_template_cordinates import TEMPLATE_FIELD_COORDS

# Maps the structured extraction script's schema keys -> the coordinate-map
# keys they should be written to. Defined explicitly (not assumed to match
# 1:1) because a single schema field can map to zero, one, or multiple
# positions on the template (e.g. proposal_number appears twice on this
# template).
#
# IMPORTANT: these keys must exactly match TARGET_SCHEMA in
# three_phase1_extract.py, since that script's output is now passed
# directly into fill_template() with no intermediate renaming stage.
SCHEMA_TO_TEMPLATE_FIELDS = {
    "proposal_number": ["proposal_number_header", "proposal_number_inline"],
    "name": ["name"],
    "premium_value": ["premium_value"],
    # address, policy_plan, date, modification_note have no dynamic
    # placeholder on this particular template (confirmed in Step 5) -
    # intentionally left unmapped for now.
}

DEFAULT_FONTSIZE = 14
DEFAULT_COLOR = (0, 0, 0)  # black, matches surrounding template text


def fill_template(mapped_json: dict, template_path: str, output_path: str) -> str:
    doc = pymupdf.open(template_path)
    page = doc[0]

    written_fields = []
    skipped_fields = []

    for schema_key, template_field_names in SCHEMA_TO_TEMPLATE_FIELDS.items():
        value = mapped_json.get(schema_key)

        if value is None or str(value).strip() == "":
            skipped_fields.append(schema_key)
            continue

        for field_name in template_field_names:
            coords = TEMPLATE_FIELD_COORDS[field_name]
            x = coords["x"]
            y = coords["bottom"]  # confirmed correct baseline reference
            fontsize = coords.get("fontsize", DEFAULT_FONTSIZE)

            page.insert_text(
                (x, y),
                str(value),
                fontsize=fontsize,
                color=DEFAULT_COLOR,
            )
            written_fields.append((field_name, value))

    doc.save(output_path)
    doc.close()

    print(f"[Phase 3] Written fields:")
    for field_name, value in written_fields:
        print(f"  {field_name} <- {value!r}")
    if skipped_fields:
        print(f"[Phase 3] Skipped (missing/empty in mapped JSON): {skipped_fields}")
    print(f"[Phase 3] Saved filled PDF to: {output_path}")

    return output_path


if __name__ == "__main__":
    # Sample matching the structured extraction script's TARGET_SCHEMA
    # directly - no separate mapping stage exists anymore.
    sample_extracted_json = {
        "name": "Mr. Ranjeet Sharma",
        "address": "123, Green Park Extension, Sector 15, Gurugram, Haryana - 122001",
        "proposal_number": "PROP/2026/98765",
        "policy_plan": "OneHealth Premium Plus - Enhanced Coverage (Plan 1A + 2C)",
        "premium_value": "25,499",
        "date": "31-03-2026",
        "modification_note": "Higher deductible, considering elevated diastolic values",
    }

    fill_template(
        mapped_json=sample_extracted_json,
        template_path="D:/Initiatives/AI-Initiatives/AI_shift_lift/Document/Magma_Output.pdf",
        output_path="D:/Initiatives/AI-Initiatives/AI_shift_lift/pdf_outputs/Magma_Output_FILLED.pdf",
    )