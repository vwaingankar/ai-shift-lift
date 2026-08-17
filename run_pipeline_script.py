"""
run_pipeline_script.py

Same pipeline logic as run_pipeline.py (Step 2 -> Phase 1 -> Phase 2 ->
confidence check -> Phase 3), refactored into a single callable function
that accepts file paths as arguments instead of hardcoded constants.

This is what app.py (the Streamlit frontend) imports and calls per
uploaded document. Kept separate from run_pipeline.py so the original
command-line script still works standalone/unchanged.
"""

import json
import traceback

from two_extract_text import extract_raw_text
from three_phase1_extract import run_phase1_extraction
from four_phase2_mapping import run_phase2_mapping, TARGET_SCHEMA
from six_to_templete import fill_template
from log_check import get_document_logger, check_confidence, record_result


def run_pipeline(
    input_pdf_path: str,
    template_pdf_path: str,
    output_pdf_path: str,
    document_id: str,
) -> dict:
    """
    Runs the full pipeline for one document and returns a result dict
    that the Streamlit frontend can render directly:

        {
            "status": "success" | "failed",
            "failed_at": None | "step2" | "phase1" | "phase2" | "phase3",
            "error_message": None | str,
            "raw_text": str | None,
            "extraction_method": str | None,
            "phase1_json": dict | None,
            "phase2_json": dict | None,
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
        "phase1_json": None,
        "phase2_json": None,
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

    # --- Phase 1 ---
    try:
        phase1_raw = run_phase1_extraction(raw_text)
        phase1_json = json.loads(phase1_raw)
        logger.info(f"Phase 1 OK - output: {json.dumps(phase1_json)}")
        result["phase1_json"] = phase1_json
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

    # --- Phase 2 ---
    try:
        phase2_raw = run_phase2_mapping(phase1_json)
        phase2_json = json.loads(phase2_raw)
        logger.info(f"Phase 2 OK - output: {json.dumps(phase2_json)}")
        result["phase2_json"] = phase2_json
    except json.JSONDecodeError as e:
        logger.error(f"Phase 2 FAILED - invalid JSON: {e}. Raw output: {phase2_raw!r}")
        result["failed_at"] = "phase2"
        result["error_message"] = f"Model did not return valid JSON: {e}"
        return result
    except Exception as e:
        logger.error(f"Phase 2 FAILED: {e}\n{traceback.format_exc()}")
        result["failed_at"] = "phase2"
        result["error_message"] = str(e)
        return result

    missing_keys = list(set(TARGET_SCHEMA.keys()) - set(phase2_json.keys()))
    result["missing_schema_keys"] = missing_keys
    if missing_keys:
        logger.warning(f"Phase 2 output missing target schema keys: {missing_keys}")

    # --- Confidence check ---
    confidence_result = check_confidence(phase1_json, phase2_json)
    result["confidence"] = confidence_result["confidence"]
    result["issues"] = confidence_result["issues"]
    if confidence_result["confidence"] == "low":
        logger.warning(f"LOW CONFIDENCE - issues found: {confidence_result['issues']}")
    else:
        logger.info("Confidence check passed - no issues found.")

    # --- Phase 3 ---
    try:
        output_path = fill_template(
            mapped_json=phase2_json,
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

    # --- Record result (audit trail + review queue routing) ---
    record_result(
        document_id=document_id,
        raw_text=raw_text,
        phase1_json=phase1_json,
        phase2_json=phase2_json,
        confidence_result=confidence_result,
        output_pdf_path=result["output_pdf_path"],
    )

    logger.info("Pipeline finished.")
    return result