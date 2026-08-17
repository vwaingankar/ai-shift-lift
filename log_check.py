
import json
import logging
import re
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------

LOG_DIR = Path("./pipeline_logs")
REVIEW_DIR = Path("./needs_review")
LOG_DIR.mkdir(exist_ok=True)
REVIEW_DIR.mkdir(exist_ok=True)

# Fields we consider "required" - if these are null/empty after Phase 2,
# it's an automatic low-confidence flag. Adjust as you learn what's
# actually always present across your real 3,000-document batch.
REQUIRED_FIELDS = ["name", "proposal_number", "premium_value"]

# Basic format sanity checks per field - not exhaustive, just cheap
# guardrails to catch obviously malformed extractions.
FIELD_PATTERNS = {
    "proposal_number": re.compile(r"^PROP/\d{4}/\d+$"),
    "premium_value": re.compile(r"^[\d,]+(\.\d+)?$"),
}


def get_document_logger(document_id: str) -> logging.Logger:
    """One log file per document, so each run is independently traceable."""
    logger = logging.getLogger(document_id)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()  # avoid duplicate handlers on repeated runs

    log_path = LOG_DIR / f"{document_id}.log"
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(levelname)s | %(message)s"))
    logger.addHandler(console_handler)

    return logger


# ---------------------------------------------------------------------
# Confidence check
# ---------------------------------------------------------------------

def check_confidence(phase1_json: dict, phase2_json: dict) -> dict:
    """
    Returns a dict:
        {
            "confidence": "high" | "low",
            "issues": [list of human-readable issue strings]
        }
    Never raises - a broken check should not crash the pipeline, it
    should itself be logged as an issue.
    """
    issues = []

    # 1. Required fields present and non-empty in the final mapped JSON
    for field in REQUIRED_FIELDS:
        value = phase2_json.get(field)
        if value is None or str(value).strip() == "":
            issues.append(f"Required field '{field}' is missing or empty in Phase 2 output.")

    # 2. Format sanity checks
    for field, pattern in FIELD_PATTERNS.items():
        value = phase2_json.get(field)
        if value and not pattern.match(str(value).strip()):
            issues.append(f"Field '{field}' value {value!r} does not match expected format.")

    # 3. Value-preservation check between Phase 1 and Phase 2
    #    (cheap heuristic: every non-null Phase 1 value should appear
    #    somewhere in Phase 2's values, since Phase 2 should only rename
    #    keys, never reword values)
    phase1_values = {str(v).strip() for v in phase1_json.values() if v}
    phase2_values = {str(v).strip() for v in phase2_json.values() if v}
    dropped_or_altered = phase1_values - phase2_values
    if dropped_or_altered:
        issues.append(
            f"{len(dropped_or_altered)} value(s) from Phase 1 do not appear in Phase 2 "
            f"output verbatim - possible rewording or data loss: {dropped_or_altered}"
        )

    confidence = "low" if issues else "high"
    return {"confidence": confidence, "issues": issues}


# ---------------------------------------------------------------------
# Result recording
# ---------------------------------------------------------------------

def record_result(document_id: str, raw_text: str, phase1_json: dict,
                   phase2_json: dict, confidence_result: dict, output_pdf_path: str | None):
    """
    Writes a single structured JSON record capturing the full pipeline
    run for this document - used for audit trail and for routing to
    human review.
    """
    record = {
        "document_id": document_id,
        "timestamp": datetime.now().isoformat(),
        "raw_text_char_count": len(raw_text),
        "phase1_output": phase1_json,
        "phase2_output": phase2_json,
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