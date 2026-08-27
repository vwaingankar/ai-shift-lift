"""
Logging and confidence-check module - single-stage version.

Previously this compared the extraction stage's output against a
separate schema-mapping stage's output, to catch values that had been
reworded rather than just renamed between the two. With the mapping
stage removed, there is only one JSON object to validate - so the
confidence check now inspects that one output directly, checking for
missing required fields and malformed values.
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path

LOG_DIR = Path("./pipeline_logs")
REVIEW_DIR = Path("./needs_review")
LOG_DIR.mkdir(exist_ok=True)
REVIEW_DIR.mkdir(exist_ok=True)

REQUIRED_FIELDS = ["name", "proposal_number", "premium_value"]

FIELD_PATTERNS = {
    "proposal_number": re.compile(r"^PROP/\d{4}/\d+$"),
    "premium_value": re.compile(r"^[\d,]+(\.\d+)?$"),
}


def get_document_logger(document_id: str) -> logging.Logger:
    logger = logging.getLogger(document_id)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    log_path = LOG_DIR / f"{document_id}.log"
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(levelname)s | %(message)s"))
    logger.addHandler(console_handler)

    return logger


def check_confidence(extracted_json: dict) -> dict:
    """
    Validates the structured extraction script's output directly - no
    second JSON to compare against anymore.

    Returns: {"confidence": "high" | "low", "issues": [str, ...]}
    """
    issues = []

    for field in REQUIRED_FIELDS:
        value = extracted_json.get(field)
        if value is None or str(value).strip() == "":
            issues.append(f"Required field '{field}' is missing or empty.")

    for field, pattern in FIELD_PATTERNS.items():
        value = extracted_json.get(field)
        if value and not pattern.match(str(value).strip()):
            issues.append(f"Field '{field}' value {value!r} does not match expected format.")

    confidence = "low" if issues else "high"
    return {"confidence": confidence, "issues": issues}


def record_result(document_id: str, raw_text: str, extracted_json: dict,
                   confidence_result: dict, output_pdf_path: str | None):
    record = {
        "document_id": document_id,
        "timestamp": datetime.now().isoformat(),
        "raw_text_char_count": len(raw_text),
        "extracted_output": extracted_json,
        "confidence": confidence_result["confidence"],
        "issues": confidence_result["issues"],
        "output_pdf_path": output_pdf_path,
    }

    record_path = LOG_DIR / f"{document_id}_record.json"
    with open(record_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)

    if confidence_result["confidence"] == "low":
        review_path = REVIEW_DIR / f"{document_id}_REVIEW_NEEDED.json"
        with open(review_path, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2)

    return record