"""
services/ai_client.py — The ONLY place that touches ai_engine.
Defines AIClient Protocol with MockAIClient and RealAIClient.
Runs blocking AI calls in a threadpool to keep the server responsive.
Never logs patient data or file contents.
"""
from __future__ import annotations

import asyncio
import glob
import json
import logging
import os
import sys
import uuid
import tempfile
import mimetypes
from pathlib import Path
from typing import Protocol, Optional

from app.config import get_settings
from app.integration import AI_PROJECT_ROOT, BACKEND_ROOT

logger = logging.getLogger(__name__)

# Path to mock contract files
CONTRACT_DIR = BACKEND_ROOT / "contract"


class AIClient(Protocol):
    async def extract(
        self,
        file_bytes: bytes,
        filename_hint: str,
        lang: str = "en",
    ) -> dict:
        ...


# ---------------------------------------------------------------------------
# Mock AI Client
# ---------------------------------------------------------------------------
_mock_files: list[Path] = []
_mock_index = 0


def _load_mock_files() -> list[Path]:
    """Discover all mock_*.json files in contract/ directory."""
    patterns = [
        CONTRACT_DIR / "mock_*.json",
    ]
    found = []
    for pattern in patterns:
        found.extend(glob.glob(str(pattern)))
    return [Path(p) for p in sorted(set(found))]


def _pick_mock_file(filename_hint: str) -> Optional[Path]:
    """Pick mock file by doc_type hint in filename, or round-robin."""
    global _mock_index
    files = _load_mock_files()
    if not files:
        return None

    # Try to match by hint in filename (e.g. "lab" → mock_lab_report.json)
    hint_lower = filename_hint.lower()
    for keyword in ["lab", "prescription", "discharge", "diagnostic", "radiology"]:
        if keyword in hint_lower:
            for f in files:
                if keyword in f.name.lower():
                    return f

    # Round-robin
    f = files[_mock_index % len(files)]
    _mock_index += 1
    return f


class MockAIClient:
    async def extract(
        self,
        file_bytes: bytes,
        filename_hint: str = "",
        lang: str = "en",
    ) -> dict:
        mock_file = _pick_mock_file(filename_hint)
        if mock_file and mock_file.exists():
            try:
                data = json.loads(mock_file.read_text(encoding="utf-8"))
                data["record_id"] = str(uuid.uuid4())
                data["source"] = "mock"
                if lang and lang != "en":
                    data.setdefault("language", lang)
                else:
                    data.setdefault("language", "en")
                return data
            except Exception as exc:
                logger.warning("Could not read mock file: %s", type(exc).__name__)

        # Absolute fallback
        return {
            "record_id": str(uuid.uuid4()),
            "doc_type": "lab_report",
            "doc_date": "2024-01-01",
            "source": "mock",
            "language": lang or "en",
            "summary": "Mock extraction (no mock file found).",
            "tests": [],
            "medicines": [],
            "diagnoses": [],
        }


# ---------------------------------------------------------------------------
# Real AI Client (wraps Person 1's extract_record)
# ---------------------------------------------------------------------------
class RealAIClient:
    def __init__(self):
        self._extract_fn = None
        self._load_error: Optional[str] = None
        self._try_load()

    def _try_load(self):
        """Try to import ai_engine.extract_record at construction time."""
        repo_root = AI_PROJECT_ROOT
        if str(repo_root) not in sys.path:
            sys.path.append(str(repo_root))
        try:
            from ai_engine import extract_record  # type: ignore
            self._extract_fn = extract_record
            logger.info("ai_engine.extract_record loaded successfully.")
        except ImportError as exc:
            self._load_error = str(exc)
            logger.warning("ai_engine not available: %s", type(exc).__name__)

    async def extract(
        self,
        file_bytes: bytes,
        filename_hint: str = "",
        lang: str = "en",
    ) -> dict:
        settings = get_settings()
        if self._extract_fn is None:
            if settings.allow_mock_fallback:
                logger.info("ai_engine not available, using mock AI client fallback.")
                return await MockAIClient().extract(file_bytes, filename_hint, lang)
            raise RuntimeError(
                f"ai_engine.extract_record is not available: {self._load_error}"
            )

        loop = asyncio.get_event_loop()

        def _call():
            try:
                # Yogesh's interface accepts a file PATH, MIME, and lang_hint.
                suffix = Path(filename_hint).suffix.lower() if filename_hint else ".pdf"
                if suffix not in {".pdf", ".png", ".jpg", ".jpeg", ".jfif", ".webp"}:
                    suffix = ".pdf"
                mime = mimetypes.guess_type("document" + suffix)[0] or "application/pdf"
                with tempfile.TemporaryDirectory(prefix="health-extract-") as temp:
                    path = Path(temp) / ("document" + suffix)
                    path.write_bytes(file_bytes)
                    result = self._extract_fn(str(path), mime, lang_hint=lang)
                if isinstance(result, dict):
                    result["source"] = "ai"
                    return result
                if hasattr(result, "dict"):
                    return result.dict()
                if hasattr(result, "__dict__"):
                    return dict(result.__dict__)
                return dict(result)
            except Exception as exc:
                raise RuntimeError(f"AI extraction failed: {type(exc).__name__}") from exc

        try:
            res = await asyncio.wait_for(
                loop.run_in_executor(None, _call),
                timeout=settings.ai_timeout_seconds,
            )
            if res.get("error") and settings.allow_mock_fallback:
                logger.warning("AI extraction returned error, falling back to mock: %s", res.get("error"))
                return await MockAIClient().extract(file_bytes, filename_hint, lang)
            return res
        except Exception as exc:
            if settings.allow_mock_fallback:
                logger.warning("AI extraction raised exception, falling back to mock: %s", exc)
                return await MockAIClient().extract(file_bytes, filename_hint, lang)
            raise


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
def get_ai_client() -> AIClient:
    settings = get_settings()
    if settings.use_mock_ai:
        return MockAIClient()
    return RealAIClient()


_AI_CLIENT: Optional[AIClient] = None


def get_cached_ai_client() -> AIClient:
    """Return a module-level cached AI client (created once at startup)."""
    global _AI_CLIENT
    if _AI_CLIENT is None:
        _AI_CLIENT = get_ai_client()
    return _AI_CLIENT
