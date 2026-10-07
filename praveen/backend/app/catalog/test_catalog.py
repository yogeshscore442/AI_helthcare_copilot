"""
catalog/test_catalog.py — Canonical test names, aliases, LOINC codes, default ref ranges.
New entries = add to CATALOG dict; no other changes needed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TestEntry:
    __test__ = False
    canonical: str
    loinc: Optional[str]
    default_unit: Optional[str]
    ref_low: Optional[float]
    ref_high: Optional[float]
    aliases: list[str] = field(default_factory=list)



CATALOG: list[TestEntry] = [
    TestEntry(
        canonical="HbA1c",
        loinc="4548-4",
        default_unit="%",
        ref_low=4.0,
        ref_high=5.7,
        aliases=["hba1c", "glycated hemoglobin", "hemoglobin a1c", "a1c", "hb a1c"],
    ),
    TestEntry(
        canonical="Fasting Blood Glucose",
        loinc="1558-6",
        default_unit="mg/dL",
        ref_low=70.0,
        ref_high=100.0,
        aliases=["fbg", "fasting glucose", "blood sugar fasting", "fasting blood sugar", "fbs"],
    ),
    TestEntry(
        canonical="Post-Prandial Blood Glucose",
        loinc="1521-4",
        default_unit="mg/dL",
        ref_low=70.0,
        ref_high=140.0,
        aliases=["ppbg", "post meal glucose", "post prandial glucose", "postprandial blood sugar", "ppbs"],
    ),
    TestEntry(
        canonical="Serum Creatinine",
        loinc="2160-0",
        default_unit="mg/dL",
        ref_low=0.6,
        ref_high=1.2,
        aliases=["creatinine", "serum creat", "s creatinine"],
    ),
    TestEntry(
        canonical="eGFR",
        loinc="62238-1",
        default_unit="mL/min/1.73m²",
        ref_low=60.0,
        ref_high=120.0,
        aliases=["egfr", "estimated gfr", "glomerular filtration rate"],
    ),
    TestEntry(
        canonical="Total Cholesterol",
        loinc="2093-3",
        default_unit="mg/dL",
        ref_low=0.0,
        ref_high=200.0,
        aliases=["cholesterol", "total chol", "tc"],
    ),
    TestEntry(
        canonical="LDL Cholesterol",
        loinc="2089-1",
        default_unit="mg/dL",
        ref_low=0.0,
        ref_high=100.0,
        aliases=["ldl", "ldl-c", "low density lipoprotein"],
    ),
    TestEntry(
        canonical="HDL Cholesterol",
        loinc="2085-9",
        default_unit="mg/dL",
        ref_low=40.0,
        ref_high=200.0,
        aliases=["hdl", "hdl-c", "high density lipoprotein"],
    ),
    TestEntry(
        canonical="Triglycerides",
        loinc="2571-8",
        default_unit="mg/dL",
        ref_low=0.0,
        ref_high=150.0,
        aliases=["tg", "trigs", "triglyceride"],
    ),
    TestEntry(
        canonical="TSH",
        loinc="3016-3",
        default_unit="mIU/L",
        ref_low=0.4,
        ref_high=4.0,
        aliases=["tsh", "thyroid stimulating hormone", "thyrotropin"],
    ),
    TestEntry(
        canonical="Haemoglobin",
        loinc="718-7",
        default_unit="g/dL",
        ref_low=12.0,
        ref_high=17.5,
        aliases=["hb", "hemoglobin", "haemoglobin"],
    ),
    TestEntry(
        canonical="WBC Count",
        loinc="6690-2",
        default_unit="10³/μL",
        ref_low=4.5,
        ref_high=11.0,
        aliases=["wbc", "white blood cell count", "leucocyte count", "leukocyte count"],
    ),
    TestEntry(
        canonical="Platelet Count",
        loinc="777-3",
        default_unit="10³/μL",
        ref_low=150.0,
        ref_high=400.0,
        aliases=["platelets", "platelet", "plt"],
    ),
    TestEntry(
        canonical="Serum ALT",
        loinc="1742-6",
        default_unit="U/L",
        ref_low=7.0,
        ref_high=56.0,
        aliases=["alt", "sgpt", "alanine aminotransferase"],
    ),
    TestEntry(
        canonical="Serum AST",
        loinc="1920-8",
        default_unit="U/L",
        ref_low=10.0,
        ref_high=40.0,
        aliases=["ast", "sgot", "aspartate aminotransferase"],
    ),
    TestEntry(
        canonical="Serum Sodium",
        loinc="2951-2",
        default_unit="mEq/L",
        ref_low=136.0,
        ref_high=145.0,
        aliases=["sodium", "na+", "serum na"],
    ),
    TestEntry(
        canonical="Serum Potassium",
        loinc="2823-3",
        default_unit="mEq/L",
        ref_low=3.5,
        ref_high=5.0,
        aliases=["potassium", "k+", "serum k"],
    ),
    TestEntry(
        canonical="Uric Acid",
        loinc="3084-1",
        default_unit="mg/dL",
        ref_low=2.4,
        ref_high=7.0,
        aliases=["uric acid", "serum uric acid", "sua"],
    ),
    TestEntry(
        canonical="Vitamin D",
        loinc="14635-7",
        default_unit="ng/mL",
        ref_low=20.0,
        ref_high=100.0,
        aliases=["vitamin d", "25-oh vitamin d", "vit d", "25(oh)d"],
    ),
    TestEntry(
        canonical="Vitamin B12",
        loinc="2132-9",
        default_unit="pg/mL",
        ref_low=200.0,
        ref_high=900.0,
        aliases=["vitamin b12", "b12", "cobalamin", "cyanocobalamin"],
    ),
]

# Build lookup index: alias -> entry
_ALIAS_INDEX: dict[str, TestEntry] = {}
for _entry in CATALOG:
    _ALIAS_INDEX[_entry.canonical.lower()] = _entry
    for _alias in _entry.aliases:
        _ALIAS_INDEX[_alias.lower()] = _entry


def lookup(name: str) -> Optional[TestEntry]:
    """Return TestEntry for a given test name (case-insensitive alias match)."""
    return _ALIAS_INDEX.get(name.strip().lower())
