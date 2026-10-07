"""
services/pipeline.py — Explicit pipeline stages for the upload→confirm lifecycle.
Each stage is a named, unit-testable function.
Stage logs only metadata (stage name, timing). Never logs content.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models import Record
from app.repositories import medicines_repo, records_repo, tests_repo
from app.services import normalizer, validators
from app.services.files import delete_file, save_file
from app.services.privacy import log_stage
from app.integration import DISCLAIMER
from app.services.summaries import refresh_summaries
import uuid

logger = logging.getLogger(__name__)

FRIENDLY_AI_ERROR = (
    "We couldn't read this document. Please retry or enter the details manually."
)


async def run_upload_pipeline(
    db: Session,
    profile_id: str,
    file_bytes: bytes,
    ext: str,
    sha256: str,
    filename_hint: str,
    lang: str,
    ai_client,
    request_id: str = "",
) -> Record:
    """
    Full upload pipeline:
    Stage 1: Duplicate detection (sha256 per profile)
    Stage 2: Store file (atomic)
    Stage 3: AI extraction (threadpool, timeout)
    Stage 4: Validate & normalize
    Stage 5: Persist draft record
    """
    # Stage 1: Duplicate detection
    with log_stage("duplicate_check", request_id):
        existing = records_repo.find_by_sha256(db, profile_id, sha256)
        if existing:
            logger.info("[%s] Duplicate upload detected, returning existing record", request_id)
            return existing

    # Stage 2: Store file
    file_path_str: Optional[str] = None
    with log_stage("store_file", request_id):
        _, file_path_str = save_file(file_bytes, ext)

    # Stage 3: AI extraction (release DB session before blocking call)
    ai_result: dict[str, Any] = {}
    ai_error: Optional[str] = None
    with log_stage("ai_extract", request_id):
        try:
            ai_result = await ai_client.extract(file_bytes, filename_hint=filename_hint, lang=lang)
        except Exception as exc:
            ai_error = FRIENDLY_AI_ERROR
            logger.warning("[%s] AI extraction error: %s", request_id, type(exc).__name__)
            # Clean up file on AI failure
            if file_path_str:
                try:
                    delete_file(file_path_str)
                except Exception:
                    logger.warning("[%s] Could not clean up file after AI failure", request_id)
                file_path_str = None

    if not isinstance(ai_result, dict):
        ai_result = {}
        ai_error = FRIENDLY_AI_ERROR
    if not ai_error:
        valid, _ = validators.validate_record_json(ai_result)
        if not valid:
            ai_error = FRIENDLY_AI_ERROR
    if ai_result.get("error"):
        ai_error = FRIENDLY_AI_ERROR

    if ai_error:
        # Return a draft record with error state (no file)
        record = records_repo.create_record(
            db,
            profile_id=profile_id,
            doc_type="unknown",
            doc_date=None,
            status="draft",
            file_path=file_path_str,
            file_sha256=None,  # allow retrying a failed extraction
            record_json=json.dumps({"error": {"code": "EXTRACTION_FAILED", "message": ai_error}, "disclaimer": DISCLAIMER}),
            source=ai_result.get("source", "ai"),
            language=lang,
            needs_review=True,
            headline="Document could not be read — please enter manually.",
        )
        return record

    # Stage 4: Validate & normalize
    with log_stage("validate_normalize", request_id):
        normalized = normalizer.normalize_record_json(ai_result)
        normalized["record_id"] = str(uuid.uuid4())
        normalized["disclaimer"] = DISCLAIMER
        refresh_summaries(normalized)
        doc_type = normalized.get("doc_type") or normalized.get("type") or "lab_report"
        normalized["doc_type"] = doc_type
        doc_date = normalized.get("doc_date")
        needs_review = validators.compute_needs_review(normalized)
        headline = validators.generate_headline(normalized, doc_type)
        source = normalized.get("source", "mock")
        language = normalized.get("language", lang)
        normalized["schema_version"] = 1

    # Stage 5: Persist draft record
    with log_stage("persist_draft", request_id):
        record = records_repo.create_record(
            db,
            record_id=normalized["record_id"],
            profile_id=profile_id,
            doc_type=doc_type,
            doc_date=doc_date,
            status="draft",
            file_path=file_path_str,
            file_sha256=sha256,
            record_json=json.dumps(normalized),
            schema_version=1,
            source=source,
            language=language,
            needs_review=needs_review,
            headline=headline,
        )

    return record


def run_confirm_pipeline(
    db: Session,
    record: Record,
    new_record_json: dict,
    request_id: str = "",
) -> Record:
    """
    Confirmation pipeline (PUT):
    Stage 6: Validate confirmed JSON
    Stage 7: Re-normalize child rows (idempotent: delete + reinsert in one transaction)
    """
    # Stage 6: Validate
    with log_stage("validate_confirmed", request_id):
        ok, err = validators.validate_record_json(new_record_json)
        if not ok:
            raise ValueError(err)
        normalized = normalizer.normalize_record_json(new_record_json)
        normalized["record_id"] = record.record_id
        normalized["disclaimer"] = DISCLAIMER
        refresh_summaries(normalized)
        doc_type = normalized.get("doc_type", record.doc_type)
        headline = validators.generate_headline(normalized, doc_type)

    # Stage 7: Re-normalize child rows (atomic)
    with log_stage("renormalize_children", request_id):
        medicines_repo.delete_medicines_by_record(db, record.record_id)
        tests_repo.delete_tests_by_record(db, record.record_id)

        meds_data = normalized.get("medicines", [])
        tests_data = normalized.get("tests", [])
        if isinstance(meds_data, list):
            medicines_repo.bulk_insert_medicines(db, record.record_id, record.profile_id, meds_data)
        if isinstance(tests_data, list):
            tests_repo.bulk_insert_tests(db, record.record_id, record.profile_id, tests_data)

        updated = records_repo.confirm_record(
            db, record.record_id, normalized, headline=headline
        )

    return updated
