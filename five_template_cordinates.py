TEMPLATE_FIELD_COORDS = {
    "proposal_number_header": {
        "x": 240.0,
        "top": 226.3,
        "bottom": 259.0,
        "notes": "Sits right after 'Proposal no.' in the header block.",
    },
    "name": {
        "x": 115.0,
        "top": 350.0,
        "bottom": 366.0,
        "notes": "Sits right after 'Hello,' greeting.",
    },
    "proposal_number_inline": {
        "x": 360.0,
        "top": 442.0,
        "bottom": 458.0,
        "notes": (
            "Sits inline in the paragraph, between 'your proposal' "
            "(ends x=355.0) and 'for' (starts x=531.7). Wide gap - "
            "confirm actual text width needed once real proposal "
            "numbers are tested, in case of overflow into 'for'."
        ),
    },
    "premium_value": {
        "x": 135.0,
        "top": 809.0,
        "bottom": 836.4,
        "notes": "Sits right after the '₹' symbol under 'YOUR PREMIUM'.",
    },
}


if __name__ == "__main__":
    for field, coords in TEMPLATE_FIELD_COORDS.items():
        print(f"{field}: x={coords['x']}, top={coords['top']}, bottom={coords['bottom']}")