"""
run_pipeline_script.py

Same pipeline logic as run_pipeline.py (Step 2 -> Phase 1 (structured
extraction, schema-ready) -> confidence check -> Phase 3), refactored
into a single callable function that accepts file paths as arguments
instead of hardcoded constants.

Note: the schema-mapping stage has been removed. The structured
extraction script now outputs JSON that already matches the target
schema directly, so its output is passed straight to the fill step.
"""

import json
import traceback

from two_extract_text import extract_raw_text
from three_phase1_extract import run_phase1_extraction, TARGET_SCHEMA
from six_to_templete import fill_template
from log_check import get_document_logger, check_confidence, record_result


def run_pipeline(
    input_pdf_path: str,
    template_pdf_path: str,
    output_pdf_path: str,
    document_id: str,
) -> dict:
    """
    Runs the full pipeline for one document and returns a result dict:

        {
            "status": "success" | "failed",
            "failed_at": None | "step2" | "phase1" | "phase3",
            "error_message": None | str,
            "raw_text": str | None,
            "extraction_method": str | None,
            "extracted_json": dict | None,
            "missing_schema_keys": list,
            "confidence": "high" | "low" | None,
            "issues": list,
            "output_pdf_path": str | None,
        }
    """
    logger = get_document_logger(document_id)
    logger.info(f"Pipeline started for document_id={document_id}")

    result = {
        "status": "failed",
        "failed_at": None,
        "error_message": None,
        "raw_text": None,
        "extraction_method": None,
        "extracted_json": None,
        "missing_schema_keys": [],
        "confidence": None,
        "issues": [],
        "output_pdf_path": None,
    }

    # --- Step 2 ---
    try:
        raw_text, method = extract_raw_text(input_pdf_path)
        logger.info(f"Step 2 OK - method={method}, chars={len(raw_text)}")
        result["raw_text"] = raw_text
        result["extraction_method"] = method
    except Exception as e:
        logger.error(f"Step 2 FAILED: {e}\n{traceback.format_exc()}")
        result["failed_at"] = "step2"
        result["error_message"] = str(e)
        return result

    # --- Phase 1 (now schema-ready directly) ---
    try:
        phase1_raw = run_phase1_extraction(raw_text)
        extracted_json = json.loads(phase1_raw)
        logger.info(f"Phase 1 OK - output: {json.dumps(extracted_json)}")
        result["extracted_json"] = extracted_json
    except json.JSONDecodeError as e:
        logger.error(f"Phase 1 FAILED - invalid JSON: {e}. Raw output: {phase1_raw!r}")
        result["failed_at"] = "phase1"
        result["error_message"] = f"Model did not return valid JSON: {e}"
        return result
    except Exception as e:
        logger.error(f"Phase 1 FAILED: {e}\n{traceback.format_exc()}")
        result["failed_at"] = "phase1"
        result["error_message"] = str(e)
        return result

    missing_keys = list(set(TARGET_SCHEMA.keys()) - set(extracted_json.keys()))
    result["missing_schema_keys"] = missing_keys
    if missing_keys:
        logger.warning(f"Output missing target schema keys: {missing_keys}")

    # --- Confidence check (single-JSON version) ---
    confidence_result = check_confidence(extracted_json)
    result["confidence"] = confidence_result["confidence"]
    result["issues"] = confidence_result["issues"]
    if confidence_result["confidence"] == "low":
        logger.warning(f"LOW CONFIDENCE - issues found: {confidence_result['issues']}")
    else:
        logger.info("Confidence check passed - no issues found.")

    # --- Phase 3 ---
    try:
        output_path = fill_template(
            mapped_json=extracted_json,
            template_path=template_pdf_path,
            output_path=output_pdf_path,
        )
        logger.info(f"Phase 3 OK - filled PDF saved to {output_path}")
        result["output_pdf_path"] = output_path
        result["status"] = "success"
    except Exception as e:
        logger.error(f"Phase 3 FAILED: {e}\n{traceback.format_exc()}")
        result["failed_at"] = "phase3"
        result["error_message"] = str(e)
        return result

    record_result(
        document_id=document_id,
        raw_text=raw_text,
        extracted_json=extracted_json,
        confidence_result=confidence_result,
        output_pdf_path=result["output_pdf_path"],
    )

    logger.info("Pipeline finished.")
    return result