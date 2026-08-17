"""
app.py - Streamlit frontend for the Magma template-migration pipeline.

Lets you upload the old filled PDF and the blank new template, run the
full Step 2 -> Phase 1 -> Phase 2 -> Phase 3 pipeline, and inspect every
phase's output before trusting the final filled PDF.
"""

import os
import tempfile
from pathlib import Path

import streamlit as st
import pymupdf

from run_pipeline_script import run_pipeline

st.set_page_config(page_title="Magma Template Migration", layout="wide")

st.title("AI Shift & Lift")
st.caption("Old filled letter → structured extraction → schema mapping → new template, filled.")

# -----------------------------------------------------------------
# Sidebar - config
# -----------------------------------------------------------------
with st.sidebar:
    st.header("Configuration")
    document_id = st.text_input(
        "Document ID",
        value="doc-001",
        help="Used to name log files and the review-queue entry for this run.",
    )
    st.markdown("---")
    st.caption(
        "Requires GROQ_API_KEY to be set as an environment variable "
        "or in a .env file in this project folder."
    )
    groq_key_present = bool(os.environ.get("GROQ_API_KEY"))
    if groq_key_present:
        st.success("GROQ_API_KEY detected")
    else:
        st.error("GROQ_API_KEY not found in environment")

# -----------------------------------------------------------------
# File uploads
# -----------------------------------------------------------------
col1, col2 = st.columns(2)
with col1:
    input_file = st.file_uploader(
        "Old filled letter (source PDF)", type=["pdf"], key="input_pdf"
    )
with col2:
    template_file = st.file_uploader(
        "Blank new template (target PDF)", type=["pdf"], key="template_pdf"
    )

run_clicked = st.button("Run pipeline", type="primary", disabled=not (input_file and template_file))

# -----------------------------------------------------------------
# Run pipeline
# -----------------------------------------------------------------
if run_clicked:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir = Path(tmp_dir)
        input_path = tmp_dir / "input.pdf"
        template_path = tmp_dir / "template.pdf"
        output_path = tmp_dir / f"{document_id}_filled.pdf"

        input_path.write_bytes(input_file.getvalue())
        template_path.write_bytes(template_file.getvalue())

        with st.spinner("Running pipeline - this calls Groq twice (Phase 1, Phase 2)..."):
            result = run_pipeline(
                input_pdf_path=str(input_path),
                template_pdf_path=str(template_path),
                output_pdf_path=str(output_path),
                document_id=document_id,
            )

        # -----------------------------------------------------------------
        # Failure handling - stop early with a clear message
        # -----------------------------------------------------------------
        if result["status"] == "failed":
            st.error(f"Pipeline failed at **{result['failed_at']}**: {result['error_message']}")
            if result["raw_text"]:
                with st.expander("Raw text extracted before failure"):
                    st.text(result["raw_text"])
            st.stop()

        # -----------------------------------------------------------------
        # Success - show every phase's output
        # -----------------------------------------------------------------
        st.success("Pipeline completed.")

        if result["confidence"] == "low":
            st.warning(
                "⚠️ LOW CONFIDENCE - this result has been flagged for human review. "
                "Do not auto-approve."
            )
            for issue in result["issues"]:
                st.markdown(f"- {issue}")
        else:
            st.info("✅ High confidence - no issues detected.")

        tab1, tab2, tab3, tab4 = st.tabs(
            ["Step 2: Raw text", "Phase 1: Extraction", "Phase 2: Mapped schema", "Final PDF"]
        )

        with tab1:
            st.caption(f"Extraction method used: **{result['extraction_method']}**")
            st.text_area("Raw text", result["raw_text"], height=400)

        with tab2:
            st.json(result["phase1_json"])

        with tab3:
            st.json(result["phase2_json"])
            if result["missing_schema_keys"]:
                st.warning(f"Missing target schema keys: {result['missing_schema_keys']}")

        with tab4:
            filled_pdf_bytes = Path(result["output_pdf_path"]).read_bytes()

            st.download_button(
                "Download filled PDF",
                data=filled_pdf_bytes,
                file_name=f"{document_id}_filled.pdf",
                mime="application/pdf",
            )

            # Render first page as an image for a quick visual check
            # without leaving the browser.
            doc = pymupdf.open(result["output_pdf_path"])
            pix = doc[0].get_pixmap(dpi=120)
            preview_path = str(tmp_dir / "preview.png")
            pix.save(preview_path)
            st.image(preview_path, caption="Filled template preview", use_container_width=True)
            doc.close()