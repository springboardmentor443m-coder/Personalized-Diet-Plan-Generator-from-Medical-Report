"""Output Validator — verifies LLM diet recommendations against trusted sources.

Post-generation validation layer that checks the LLM's diet plan output
against WHO/NIH thresholds and medical knowledge base to catch:
- Unsafe nutrient levels
- Contraindicated foods for specific conditions
- Missing mandatory dietary elements
- Violations of official guideline thresholds

This is a DETERMINISTIC module — no LLM calls, pure rule-based checking.

ALL threshold values are sourced from:
- WHO Guidelines (2012–2024)
- NIH Dietary Reference Intakes (IOM/NASEM)
- ADA Standards of Care (2024)
- KDIGO CKD Guidelines (2024)
- AHA/ACC Lifestyle Management (2019)
- NIH NIDDK Nutrition Management
- ACR Gout Management (2020)
- AASLD Practice Guidelines
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# GROUND-TRUTH THRESHOLDS — every value carries its official citation
# ═══════════════════════════════════════════════════════════════════════════

# ---------------------------------------------------------------------------
# Caloric floors (kcal/day — NEVER prescribe below these)
# ---------------------------------------------------------------------------
CALORIC_FLOORS = {
    "general_female": {
        "min": 1200,
        "source": "NIH/NHLBI Obesity Guidelines (2013)",
        "note": "Minimum safe intake for women under medical supervision",
    },
    "general_male": {
        "min": 1500,
        "source": "NIH/NHLBI Obesity Guidelines (2013)",
        "note": "Minimum safe intake for men under medical supervision",
    },
    "elderly": {
        "min": 1200,
        "source": "ESPEN Geriatric Nutrition Guidelines (2019)",
        "note": "Below this: sarcopenia, micronutrient deficiency risk",
    },
    "underweight": {
        "min": 1500, "restrict": False,
        "source": "WHO BMI Classification + NIH",
        "note": "Caloric restriction is CONTRAINDICATED (BMI <18.5)",
    },
    "pediatric": {
        "min": 1000,
        "source": "WHO/FAO Energy Requirements (2004)",
        "note": "Age-dependent; absolute floor for any child",
    },
    "pregnancy": {
        "min": 1800,
        "source": "ACOG Practice Bulletin (2024)",
        "note": "Never restrict calories during pregnancy",
    },
    "lactation": {
        "min": 1800,
        "source": "IOM DRI for Lactation",
        "note": "Additional 450-500 kcal/day over baseline needed",
    },
}

# ---------------------------------------------------------------------------
# Sodium limits (mg/day)
# ---------------------------------------------------------------------------
SODIUM_LIMITS = {
    "general": {
        "target": 2000, "max": 2300,
        "source_target": "WHO Guideline: Sodium Intake (2012, reaffirmed 2024)",
        "source_max": "US Dietary Guidelines 2020-2025 / NIH CDRR",
        "note": "WHO says <2000 mg; US DGA says <2300 mg; both are valid",
    },
    "hypertension": {
        "target": 1500, "max": 2300,
        "source_target": "AHA/ACC Hypertension Guideline (2017); NIH DASH lower-sodium",
        "source_max": "NIH NHLBI DASH standard",
        "note": "1500 mg is optimal for BP reduction (DASH lower-sodium)",
    },
    "ckd_stage_1_2": {
        "target": 2000, "max": 2300,
        "source_target": "KDIGO CKD Guideline (2024)",
        "source_max": "NIH NIDDK",
    },
    "ckd_stage_3": {
        "target": 2000, "max": 2300,
        "source_target": "KDIGO CKD Guideline (2024)",
        "source_max": "NIH NIDDK",
    },
    "ckd_stage_4_5": {
        "target": 2000, "max": 2000,
        "source_target": "KDIGO CKD Guideline (2024); NIH NIDDK",
        "source_max": "KDIGO CKD Guideline (2024); NIH NIDDK",
        "note": "Hard cap at 2000 mg for eGFR <30",
    },
    "dialysis": {
        "target": 2000, "max": 2000,
        "source_target": "KDOQI Nutrition in CKD (2020)",
        "source_max": "KDOQI Nutrition in CKD (2020)",
    },
    "heart_failure": {
        "target": 1500, "max": 2000,
        "source_target": "AHA/HFSA Heart Failure Guideline (2022)",
        "source_max": "AHA/HFSA Heart Failure Guideline (2022)",
        "note": "<=1500 mg for Stage C/D HF; <2000 for all HF",
    },
    "cirrhosis_ascites": {
        "target": 2000, "max": 2000,
        "source_target": "AASLD/EASL Cirrhosis Guideline (2023)",
        "source_max": "AASLD/EASL Cirrhosis Guideline (2023)",
        "note": "2000 mg daily cap for ascites management",
    },
}

# ---------------------------------------------------------------------------
# Potassium limits (mg/day)
# ---------------------------------------------------------------------------
POTASSIUM_LIMITS = {
    "general": {
        "min": 2600, "target": 3400, "max": None,
        "source": "NIH DRI — AI: 2600 mg (F), 3400 mg (M); WHO: >=3510 mg",
        "note": "No UL established for potassium from food",
    },
    "hypertension_no_ckd": {
        "min": 3510, "target": 4700, "max": None,
        "source": "WHO Potassium Guideline (2012); DASH diet potassium target",
        "note": "DASH target ~4700 mg; WHO minimum 3510 mg; only if kidneys are healthy",
    },
    "ckd_stage_3": {
        "min": None, "target": None, "max": 3000,
        "source": "KDIGO (2024); individualized per serum K levels",
        "note": "Restrict only if hyperkalemia present; otherwise individualized",
    },
    "ckd_stage_4_5": {
        "min": None, "target": None, "max": 2000,
        "source": "NIH NIDDK; KDIGO CKD Guideline (2024)",
        "note": "Hard restriction <2000 mg unless under nephrologist guidance",
    },
    "dialysis": {
        "min": None, "target": None, "max": 3000,
        "source": "KDOQI Nutrition in CKD (2020)",
        "note": "2000-3000 mg individualized; pre-dialysis K levels guide",
    },
}

# ---------------------------------------------------------------------------
# Protein limits (g/kg body weight/day)
# ---------------------------------------------------------------------------
PROTEIN_LIMITS = {
    "general": {
        "min": 0.8, "target": 0.8, "max": 2.0,
        "source_min": "IOM DRI — RDA for adults",
        "source_max": "EFSA/ADA position; no hard UL but >2.0 lacks evidence",
    },
    "elderly": {
        "min": 1.0, "target": 1.2, "max": 1.5,
        "source": "ESPEN (2019); PROT-AGE Study Group; NIH NIA",
        "note": "Higher protein to prevent sarcopenia; 1.0 is absolute floor",
    },
    "ckd_stage_1_2": {
        "min": 0.8, "target": 0.8, "max": 1.0,
        "source": "KDIGO CKD Guideline (2024); NIH NIDDK",
        "note": "No formal restriction but avoid high protein",
    },
    "ckd_stage_3": {
        "min": 0.55, "target": 0.6, "max": 0.8,
        "source": "KDIGO CKD Guideline (2024); NIH NIDDK",
        "note": "Low-protein diet: 0.55-0.60 g/kg; or supplemented very low-protein",
    },
    "ckd_stage_4_5": {
        "min": 0.55, "target": 0.6, "max": 0.6,
        "source": "KDIGO CKD Guideline (2024); NIH NIDDK",
        "note": "Strict low-protein 0.55-0.60 g/kg; do NOT go lower",
    },
    "dialysis": {
        "min": 1.0, "target": 1.2, "max": 1.4,
        "source": "KDOQI Nutrition in CKD (2020)",
        "note": "Increases to compensate for dialysate protein losses",
    },
    "cirrhosis": {
        "min": 1.0, "target": 1.2, "max": 1.5,
        "source": "EASL Clinical Practice Guidelines on Nutrition (2019); AASLD",
        "note": "Old practice of protein restriction is OBSOLETE except for acute HE",
    },
    "diabetes": {
        "min": 0.8, "target": 1.0, "max": 1.5,
        "source": "ADA Standards of Care (2024) Section 5",
        "note": "No benefit to restricting <0.8 in diabetes without CKD",
    },
    "obesity_weight_loss": {
        "min": 1.0, "target": 1.2, "max": 1.5,
        "source": "ESPEN Obesity Guideline; ADA position",
        "note": "Higher protein preserves lean mass during caloric deficit",
    },
}

# ---------------------------------------------------------------------------
# Phosphorus limits (mg/day)
# ---------------------------------------------------------------------------
PHOSPHORUS_LIMITS = {
    "general": {
        "target": 700, "max": 4000,
        "source": "IOM DRI — RDA 700 mg; UL 4000 mg (adults), 3000 mg (>70y)",
    },
    "ckd_stage_3": {
        "target": 800, "max": 1000,
        "source": "KDIGO CKD-MBD Guideline (2017/2024)",
        "note": "Restrict to 800-1000 mg or per serum phosphorus",
    },
    "ckd_stage_4_5": {
        "target": 800, "max": 800,
        "source": "KDIGO CKD-MBD Guideline (2017/2024); NIH NIDDK",
        "note": "Strict 800 mg cap; avoid inorganic phosphorus additives",
    },
    "dialysis": {
        "target": 800, "max": 1000,
        "source": "KDOQI (2020)",
        "note": "800-1000 mg; prioritize organic/plant phosphorus (lower bioavailability)",
    },
}

# ---------------------------------------------------------------------------
# Fat intake thresholds (% of total energy)
# ---------------------------------------------------------------------------
FAT_LIMITS = {
    "total_fat": {
        "general": {"max": 30, "source": "WHO (2023 update)"},
        "infant_6_24m": {"min": 30, "max": 40, "source": "WHO infant feeding guidelines"},
    },
    "saturated_fat": {
        "general": {"max": 10, "source": "WHO (2023); US DGA 2020-2025"},
        "cvd_therapeutic": {"max": 7, "source": "AHA/ACC Lifestyle Management (2019)"},
        "nafld": {"max": 7, "source": "AASLD Practice Guidance (2023)"},
    },
    "trans_fat": {
        "all": {"max": 1, "source": "WHO (2023) — <1% of total energy; eliminate industrial"},
    },
}

# ---------------------------------------------------------------------------
# Sugar limits (% of total energy)
# ---------------------------------------------------------------------------
SUGAR_LIMITS = {
    "general": {
        "max": 10, "conditional_target": 5,
        "source_max": "WHO Strong Recommendation (2015)",
        "source_target": "WHO Conditional Recommendation (2015)",
        "note": "Free sugars only; does NOT include intrinsic sugars in whole fruit/dairy",
    },
    "diabetes": {
        "max": 5, "conditional_target": 0,
        "source": "ADA Standards of Care (2024) + WHO conditional",
        "note": "Minimize all added sugars; zero added sugar is ideal",
    },
    "triglycerides_severe": {
        "max": 0,
        "source": "AHA/ACC TG >500: eliminate simple sugars (2019)",
        "note": "TG >500 mg/dL: zero added sugars + zero alcohol + fat <15% TE",
    },
    "nafld": {
        "max": 5,
        "source": "AASLD/EASL; fructose is primary hepatic lipogenic substrate",
    },
}

# ---------------------------------------------------------------------------
# Fiber targets (g/day)
# ---------------------------------------------------------------------------
FIBER_TARGETS = {
    "general_female": {
        "min": 25, "target": 28,
        "source": "IOM DRI AI — 25 g (F); US DGA 2020-2025 — 28 g (2000 kcal)",
    },
    "general_male": {
        "min": 30, "target": 38,
        "source": "IOM DRI AI — 38 g (M); US DGA 2020-2025 — 34 g (2400 kcal)",
    },
    "diabetes": {
        "min": 25, "target": 35,
        "source": "ADA (2024): >=25 g, ideally 30-35 g; WHO: >=25 g",
    },
    "cvd": {
        "soluble_min": 10, "soluble_target": 25, "total_min": 25,
        "source": "AHA/ACC: 10-25 g soluble fiber for LDL lowering (Portfolio Diet)",
    },
}

# ---------------------------------------------------------------------------
# Fluid/hydration (L/day)
# ---------------------------------------------------------------------------
FLUID_TARGETS = {
    "general_female": {
        "min": 1.5, "target": 2.7,
        "source": "IOM DRI AI — 2.7 L total water (F); incl. food moisture",
    },
    "general_male": {
        "min": 1.5, "target": 3.7,
        "source": "IOM DRI AI — 3.7 L total water (M); incl. food moisture",
    },
    "ckd_stage_4_5": {
        "min": None, "target": None, "max_formula": "1000 mL + urine output",
        "source": "NIH NIDDK; KDIGO",
    },
    "heart_failure": {
        "max": 2.0,
        "source": "AHA/HFSA (2022): 1.5-2.0 L fluid restriction in congestion",
    },
    "gout": {
        "min": 2.5, "target": 3.0,
        "source": "ACR Gout Guideline (2020): >=2.5 L/day for urate clearance",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# CONTRAINDICATED FOODS — condition-specific absolute prohibitions
# ═══════════════════════════════════════════════════════════════════════════
CONTRAINDICATED_FOODS = {
    "ckd_advanced": {
        "foods": ["star fruit", "starfruit", "carambola"],
        "reason": "Caramboxin neurotoxin accumulates with impaired renal clearance — seizures, encephalopathy",
        "severity": "critical",
        "source": "KDIGO; multiple case series (Neto et al., 2003; USRDS reports)",
    },
    "ckd_potassium": {
        "foods": ["potassium chloride salt", "salt substitute", "lo salt", "nu-salt"],
        "reason": "KCl salt substitutes risk fatal hyperkalemia in impaired renal excretion",
        "severity": "critical",
        "source": "KDIGO (2024); FDA warning on KCl salt substitutes in CKD",
    },
    "gout_acute": {
        "foods": ["organ meat", "liver", "kidney", "sweetbread", "brain", "anchovies", "sardines"],
        "reason": "Extremely high purine content (>300 mg/100 g) triggers gout flares",
        "severity": "high",
        "source": "ACR Gout Guideline (2020); Choi et al., NEJM 2004",
    },
    "liver_disease": {
        "foods": [
            "alcohol", "beer", "wine", "spirits", "liquor", "cocktail",
            "rum", "vodka", "whiskey", "gin", "tequila",
        ],
        "reason": "Alcohol is directly hepatotoxic — absolute zero in any liver disease including NAFLD",
        "severity": "critical",
        "source": "AASLD Practice Guidance (2023); EASL (2019); WHO",
    },
    "celiac": {
        "foods": [
            "wheat", "barley", "rye", "semolina", "maida", "sooji",
            "couscous", "bulgur", "seitan", "malt",
        ],
        "reason": "Gluten triggers autoimmune-mediated villous atrophy in celiac disease",
        "severity": "critical",
        "source": "ACG Clinical Guideline: Celiac Disease (2023); AGA",
    },
    "phenylketonuria": {
        "foods": ["aspartame", "nutrasweet", "equal"],
        "reason": "Aspartame metabolizes to phenylalanine — contraindicated in PKU",
        "severity": "critical",
        "source": "NIH NICHD; ACMG Standard (2014)",
    },
    "triglycerides_severe": {
        "foods": ["alcohol", "beer", "wine", "spirits", "liquor"],
        "reason": "Alcohol with TG >500 mg/dL dramatically increases acute pancreatitis risk",
        "severity": "critical",
        "source": "AHA/ACC TG Management Statement (2019); Endocrine Society (2012)",
    },
    "warfarin_therapy": {
        "foods": [],  # Not banned — consistency is key
        "reason": "Vitamin K intake must be CONSISTENT (not restricted/increased) with warfarin",
        "severity": "high",
        "source": "AHA Anticoagulation Guideline; NIH ODS Vitamin K Fact Sheet",
        "special_rule": "CHECK_CONSISTENCY_NOT_EXCLUSION",
    },
    "maoi_therapy": {
        "foods": [
            "aged cheese", "cheddar", "brie", "camembert", "sauerkraut",
            "soy sauce", "miso", "kimchi", "salami", "pepperoni",
        ],
        "reason": "Tyramine-rich foods + MAOIs — hypertensive crisis",
        "severity": "critical",
        "source": "APA Psychopharmacology Guideline; FDA MAOI labeling",
    },
}

# ═══════════════════════════════════════════════════════════════════════════
# MANDATORY DIETARY ELEMENTS by condition
# ═══════════════════════════════════════════════════════════════════════════
MANDATORY_ELEMENTS = {
    "diabetes": {
        "required": ["fiber", "whole grain"],
        "reason": "ADA (2024): fiber >=25 g/day and >=50% whole grains for glycemic control",
        "source": "ADA Standards of Care (2024) Section 5; WHO fiber guideline",
    },
    "hypertension": {
        "required": ["vegetable", "fruit"],
        "reason": "DASH diet: 4-5 servings each of fruits and vegetables daily; proven SBP reduction 8-14 mmHg",
        "source": "NIH NHLBI DASH Eating Plan; AHA/ACC (2017)",
    },
    "anemia_iron": {
        "required": ["iron"],
        "reason": "WHO: iron-rich foods + vitamin C enhancers mandatory; avoid calcium/tannin at iron meals",
        "source": "WHO Iron Supplementation Guideline; NIH ODS Iron Fact Sheet",
    },
    "osteoporosis": {
        "required": ["calcium", "vitamin d"],
        "reason": "Calcium 1000-1200 mg/day + Vitamin D 600-800 IU/day per NIH; NOF recommends same",
        "source": "IOM DRI; National Osteoporosis Foundation; NIH NIAMS",
    },
    "cardiovascular": {
        "required": ["omega-3", "fiber"],
        "reason": "AHA: omega-3 fatty acids for TG reduction; soluble fiber 10-25 g/day for LDL lowering",
        "source": "AHA/ACC Lifestyle Management (2019); Portfolio Diet evidence",
    },
    "gout": {
        "required": ["water", "dairy"],
        "reason": "ACR (2020): >=2.5 L/day hydration for urate clearance; low-fat dairy is urate-protective",
        "source": "ACR Gout (2020); Choi et al., NEJM 2004",
    },
    "ckd": {
        "required": ["calorie"],
        "reason": "KDIGO: adequate calories (25-35 kcal/kg) essential to prevent catabolism on low-protein diet",
        "source": "KDIGO CKD Guideline (2024); KDOQI Nutrition (2020)",
    },
    "cirrhosis": {
        "required": ["protein", "calorie"],
        "reason": "EASL (2019): protein 1.0-1.5 g/kg + 25-35 kcal/kg; protein restriction is OBSOLETE",
        "source": "EASL Clinical Practice Guidelines on Nutrition (2019); AASLD",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# CONDITION DETECTION
# ═══════════════════════════════════════════════════════════════════════════
def _detect_conditions(aggregated_state: dict) -> list[str]:
    """Detect patient conditions from aggregated health state."""
    conditions: list[str] = []

    abnormals = aggregated_state.get("aggregated_abnormal_findings", [])
    for finding in abnormals:
        key = finding.get("canonical_test_key", "").lower()
        category = finding.get("category", "").lower()
        severity = finding.get("severity", "").lower()

        if "glucose" in key or "hba1c" in key or "glucose" in category:
            conditions.append("diabetes")
        if "creatinine" in key or "egfr" in key or "renal" in category:
            # Try to determine CKD stage from eGFR
            if "egfr" in key:
                try:
                    egfr_val = float(finding.get("observed_value", 0))
                    if egfr_val < 15:
                        conditions.append("ckd_stage_5")
                    elif egfr_val < 30:
                        conditions.append("ckd_stage_4_5")
                    elif egfr_val < 60:
                        conditions.append("ckd_stage_3")
                    else:
                        conditions.append("ckd_stage_1_2")
                except (ValueError, TypeError):
                    conditions.append("ckd")
            else:
                conditions.append("ckd")
        if "alt" in key or "ast" in key or "bilirubin" in key or "liver" in category:
            conditions.append("liver_disease")
        if "uric_acid" in key or "urate" in key:
            conditions.append("gout")
        if "cholesterol" in key or "ldl" in key:
            conditions.append("cardiovascular")
        if "triglyceride" in key:
            try:
                tg_val = float(finding.get("observed_value", 0))
                if tg_val > 500:
                    conditions.append("triglycerides_severe")
                else:
                    conditions.append("cardiovascular")
            except (ValueError, TypeError):
                conditions.append("cardiovascular")
        if "hemoglobin" in key or "iron" in key or "ferritin" in key:
            conditions.append("anemia_iron")
        if "tsh" in key or "thyroid" in category:
            conditions.append("thyroid")
        if "calcium" in key and severity in ("low", "critical_low"):
            conditions.append("osteoporosis")

    # Check chronic flags
    chronic = aggregated_state.get("chronic_flags", [])
    for flag in chronic:
        name = flag.get("test_name", "").lower()
        if "hypertens" in name or "blood pressure" in name:
            conditions.append("hypertension")
        if "renal" in name or "kidney" in name:
            conditions.append("ckd")

    # Check BMI
    bmi = aggregated_state.get("bmi", {})
    bmi_cat = bmi.get("category", "").lower()
    if "obese" in bmi_cat:
        conditions.append("obesity")
    if "overweight" in bmi_cat:
        conditions.append("overweight")
    if "underweight" in bmi_cat:
        conditions.append("underweight")

    # Check patient age
    patient = aggregated_state.get("patient_information", {})
    age = patient.get("age_years")
    if age is not None:
        if age >= 65:
            conditions.append("elderly")
        elif age < 18:
            conditions.append("pediatric")

    return list(set(conditions))


def _extract_plan_text(plan: dict) -> str:
    """Flatten the entire diet plan to a searchable string."""
    return str(plan).lower()


# ═══════════════════════════════════════════════════════════════════════════
# VALIDATION CHECKS
# ═══════════════════════════════════════════════════════════════════════════

def _check_contraindicated_foods(
    plan: dict,
    conditions: list[str],
) -> list[dict[str, Any]]:
    """Check if the diet plan contains foods contraindicated for the patient's conditions."""
    violations: list[dict[str, Any]] = []
    plan_text = _extract_plan_text(plan)

    # Map detected conditions to contraindication keys
    condition_map = {
        "ckd": ["ckd_advanced", "ckd_potassium"],
        "ckd_stage_3": ["ckd_potassium"],
        "ckd_stage_4_5": ["ckd_advanced", "ckd_potassium"],
        "ckd_stage_5": ["ckd_advanced", "ckd_potassium"],
        "gout": ["gout_acute"],
        "liver_disease": ["liver_disease"],
        "celiac": ["celiac"],
        "triglycerides_severe": ["triglycerides_severe"],
    }

    for condition in conditions:
        contra_keys = condition_map.get(condition, [])
        for contra_key in contra_keys:
            contra = CONTRAINDICATED_FOODS.get(contra_key)
            if not contra:
                continue

            # Skip special rules (like warfarin consistency check)
            if contra.get("special_rule"):
                continue

            found_foods = [f for f in contra["foods"] if f in plan_text]

            if found_foods:
                violations.append({
                    "type": "contraindicated_food",
                    "severity": contra["severity"],
                    "condition": condition,
                    "foods_found": found_foods,
                    "reason": contra["reason"],
                    "source": contra["source"],
                })

    return violations


def _check_mandatory_elements(
    plan: dict,
    conditions: list[str],
) -> list[dict[str, Any]]:
    """Check if the diet plan includes mandatory dietary elements."""
    violations: list[dict[str, Any]] = []
    plan_text = _extract_plan_text(plan)

    for condition in conditions:
        mandatory = MANDATORY_ELEMENTS.get(condition)
        if not mandatory:
            continue

        missing = [
            elem for elem in mandatory["required"]
            if elem not in plan_text
        ]

        if missing:
            violations.append({
                "type": "missing_mandatory_element",
                "severity": "moderate",
                "condition": condition,
                "missing_elements": missing,
                "reason": mandatory["reason"],
                "source": mandatory["source"],
            })

    return violations


def _check_nutrient_thresholds(
    plan: dict,
    aggregated_state: dict,
    conditions: list[str],
) -> list[dict[str, Any]]:
    """Check if recommended nutrient levels violate official thresholds."""
    violations: list[dict[str, Any]] = []
    guidelines = plan.get("dietary_guidelines", {})

    # ── Sodium check ──────────────────────────────────────────
    sodium_field = guidelines.get("sodium_limit_mg")
    if sodium_field:
        try:
            sodium_val = float(re.findall(r"\d+", str(sodium_field))[0])

            # Select the strictest applicable limit
            if "heart_failure" in conditions:
                lim = SODIUM_LIMITS["heart_failure"]
            elif "cirrhosis_ascites" in conditions or "liver_disease" in conditions:
                lim = SODIUM_LIMITS["cirrhosis_ascites"]
            elif "ckd_stage_4_5" in conditions or "ckd_stage_5" in conditions:
                lim = SODIUM_LIMITS["ckd_stage_4_5"]
            elif "hypertension" in conditions:
                lim = SODIUM_LIMITS["hypertension"]
            elif "ckd_stage_3" in conditions:
                lim = SODIUM_LIMITS["ckd_stage_3"]
            elif "ckd" in conditions:
                lim = SODIUM_LIMITS["ckd_stage_1_2"]
            else:
                lim = SODIUM_LIMITS["general"]

            hard_max = lim["max"]
            target = lim["target"]

            if sodium_val > hard_max:
                violations.append({
                    "type": "sodium_exceeds_hard_max",
                    "severity": "high",
                    "recommended_by_llm": f"{sodium_val} mg/day",
                    "official_max": f"{hard_max} mg/day",
                    "official_target": f"{target} mg/day",
                    "source": lim.get("source_max") or lim.get("source_target", ""),
                    "action": f"Reduce sodium to <={hard_max} mg/day (target: {target} mg)",
                })
            elif sodium_val > target:
                violations.append({
                    "type": "sodium_above_target",
                    "severity": "moderate",
                    "recommended_by_llm": f"{sodium_val} mg/day",
                    "official_target": f"{target} mg/day",
                    "official_max": f"{hard_max} mg/day",
                    "source": lim.get("source_target", ""),
                    "action": f"Consider reducing sodium to target of {target} mg/day",
                })
        except (ValueError, IndexError):
            pass

    # ── Saturated fat check ───────────────────────────────────
    macro = guidelines.get("macronutrient_split", {})
    sat_fat = macro.get("saturated_fat_percent")
    if sat_fat:
        try:
            sf_val = float(sat_fat)
            if "cardiovascular" in conditions:
                lim = FAT_LIMITS["saturated_fat"]["cvd_therapeutic"]
            elif "liver_disease" in conditions:
                lim = FAT_LIMITS["saturated_fat"]["nafld"]
            else:
                lim = FAT_LIMITS["saturated_fat"]["general"]

            if sf_val > lim["max"]:
                violations.append({
                    "type": "saturated_fat_exceeds_threshold",
                    "severity": "high" if "cardiovascular" in conditions else "moderate",
                    "recommended_by_llm": f"{sf_val}%",
                    "official_limit": f"<{lim['max']}% of total energy",
                    "source": lim["source"],
                    "action": f"Reduce saturated fat to <{lim['max']}%",
                })
        except (ValueError, TypeError):
            pass

    # ── Total fat check ───────────────────────────────────────
    total_fat = macro.get("fat_percent")
    if total_fat:
        try:
            tf_val = float(total_fat)
            # TG >500 requires severe fat restriction
            if "triglycerides_severe" in conditions and tf_val > 15:
                violations.append({
                    "type": "fat_exceeds_tg_crisis_limit",
                    "severity": "critical",
                    "recommended_by_llm": f"{tf_val}%",
                    "official_limit": "<15% total energy (TG >500 pancreatitis prevention)",
                    "source": "AHA/ACC TG Management (2019); Endocrine Society (2012)",
                    "action": "Restrict total fat to <15% for severe hypertriglyceridemia",
                })
            elif tf_val > 30:
                violations.append({
                    "type": "total_fat_exceeds_who_limit",
                    "severity": "moderate",
                    "recommended_by_llm": f"{tf_val}%",
                    "official_limit": "<=30% of total energy",
                    "source": FAT_LIMITS["total_fat"]["general"]["source"],
                    "action": "Reduce total fat to <=30%",
                })
        except (ValueError, TypeError):
            pass

    # ── Sugar check ───────────────────────────────────────────
    sugar_notes = str(guidelines.get("sugar_recommendations", "")).lower()
    sugar_nums = re.findall(r"(\d+)\s*%", sugar_notes)
    if sugar_nums:
        try:
            sugar_pct = max(float(n) for n in sugar_nums)
            if "diabetes" in conditions:
                lim = SUGAR_LIMITS["diabetes"]
            elif "triglycerides_severe" in conditions:
                lim = SUGAR_LIMITS["triglycerides_severe"]
            elif "liver_disease" in conditions:
                lim = SUGAR_LIMITS["nafld"]
            else:
                lim = SUGAR_LIMITS["general"]

            smax = lim["max"]
            if sugar_pct > smax:
                violations.append({
                    "type": "sugar_exceeds_limit",
                    "severity": "high" if "diabetes" in conditions else "moderate",
                    "recommended_by_llm": f"{sugar_pct}%",
                    "official_limit": f"<{smax}% of total energy",
                    "source": lim.get("source_max") or lim.get("source", ""),
                    "action": f"Reduce free/added sugars to <{smax}% of total energy",
                })
        except (ValueError, TypeError):
            pass

    # ── Caloric floor check ───────────────────────────────────
    caloric = guidelines.get("caloric_target", {})
    cal_range = str(caloric.get("range_kcal", ""))
    cal_nums = re.findall(r"\d+", cal_range)
    if cal_nums:
        try:
            cal_min = float(cal_nums[0])

            patient = aggregated_state.get("patient_information", {})
            gender = (patient.get("gender") or "").lower()

            if "underweight" in conditions:
                floor_entry = CALORIC_FLOORS["underweight"]
            elif "pregnancy" in conditions:
                floor_entry = CALORIC_FLOORS["pregnancy"]
            elif "elderly" in conditions:
                floor_entry = CALORIC_FLOORS["elderly"]
            elif "pediatric" in conditions:
                floor_entry = CALORIC_FLOORS["pediatric"]
            elif "female" in gender or "woman" in gender:
                floor_entry = CALORIC_FLOORS["general_female"]
            else:
                floor_entry = CALORIC_FLOORS["general_male"]

            floor = floor_entry["min"]

            if cal_min < floor:
                violations.append({
                    "type": "caloric_below_safety_floor",
                    "severity": "critical",
                    "recommended_by_llm": f"{cal_min} kcal/day",
                    "official_floor": f"{floor} kcal/day",
                    "source": floor_entry["source"],
                    "action": f"Increase minimum calories to >={floor} kcal/day",
                    "note": floor_entry.get("note", ""),
                })

            # Underweight: any restriction is a violation
            if "underweight" in conditions and (
                "restrict" in cal_range.lower() or "deficit" in cal_range.lower()
            ):
                violations.append({
                    "type": "caloric_restriction_in_underweight",
                    "severity": "critical",
                    "reason": "Caloric restriction is CONTRAINDICATED for BMI <18.5",
                    "source": CALORIC_FLOORS["underweight"]["source"],
                    "action": "Remove caloric restriction; prescribe caloric surplus",
                })
        except (ValueError, IndexError):
            pass

    return violations


def _check_unsafe_combinations(
    plan: dict,
    conditions: list[str],
) -> list[dict[str, Any]]:
    """Check for dangerous nutrient-condition combinations."""
    violations: list[dict[str, Any]] = []
    plan_text = _extract_plan_text(plan)

    # CKD + high-potassium foods without potassium restriction
    ckd_conditions = {"ckd", "ckd_stage_3", "ckd_stage_4_5", "ckd_stage_5"}
    if ckd_conditions & set(conditions):
        high_k_foods = [
            "banana", "orange juice", "potato", "tomato", "avocado",
            "spinach", "dried apricot", "dried fig", "coconut water",
        ]
        k_foods_found = [f for f in high_k_foods if f in plan_text]

        guidelines_text = str(plan.get("dietary_guidelines", {})).lower()
        acknowledges_k = "potassium" in guidelines_text and (
            "restrict" in guidelines_text or "limit" in guidelines_text
            or "monitor" in guidelines_text
        )

        if k_foods_found and not acknowledges_k:
            # Severity depends on CKD stage
            sev = "critical" if (
                {"ckd_stage_4_5", "ckd_stage_5"} & set(conditions)
            ) else "high"
            violations.append({
                "type": "ckd_potassium_conflict",
                "severity": sev,
                "foods_found": k_foods_found,
                "reason": "High-potassium foods in CKD without potassium monitoring/restriction",
                "source": "KDIGO (2024); NIH NIDDK CKD Nutrition",
                "action": "Remove high-K foods or add explicit potassium restriction/monitoring",
            })

    # Diabetes + high-GI foods
    if "diabetes" in conditions:
        high_gi_foods = [
            "white rice", "white bread", "maida", "cornflakes", "puffed rice",
            "instant oatmeal", "rice cakes", "watermelon",
        ]
        gi_found = [f for f in high_gi_foods if f in plan_text]
        if gi_found:
            violations.append({
                "type": "diabetes_high_gi_foods",
                "severity": "moderate",
                "foods_found": gi_found,
                "reason": "High glycemic index foods (GI >70) worsen postprandial hyperglycemia",
                "source": "ADA (2024) Section 5; WHO glycemic index guidance",
                "action": "Replace with low-GI alternatives (GI <55) or control portions",
            })

    # CKD + high phosphorus
    if {"ckd_stage_3", "ckd_stage_4_5", "ckd_stage_5"} & set(conditions):
        high_phos = ["cola", "processed cheese", "baking powder", "canned fish"]
        phos_found = [f for f in high_phos if f in plan_text]
        if phos_found:
            violations.append({
                "type": "ckd_phosphorus_conflict",
                "severity": "high",
                "foods_found": phos_found,
                "reason": "Foods with inorganic phosphorus additives (90-100% absorbed) in CKD",
                "source": "KDIGO CKD-MBD (2017/2024); NIH NIDDK",
                "action": "Avoid processed foods with phosphorus additives; prefer organic sources",
            })

    # Elderly + excessive protein restriction
    if "elderly" in conditions:
        protein_info = str(
            plan.get("dietary_guidelines", {}).get("macronutrient_split", {})
        ).lower()
        low_protein_flags = ["0.6 g/kg", "0.55 g/kg", "0.5 g/kg", "0.4 g/kg"]
        if any(flag in protein_info for flag in low_protein_flags):
            if not (ckd_conditions & set(conditions)):
                violations.append({
                    "type": "elderly_excessive_protein_restriction",
                    "severity": "high",
                    "reason": "Elderly patients (>=65) need >=1.0 g/kg/day protein for sarcopenia prevention",
                    "source": PROTEIN_LIMITS["elderly"]["source"],
                    "action": "Increase protein to >=1.0 g/kg/day unless CKD stage 3-5",
                })

    return violations


# ═══════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

def validate_diet_output(
    diet_plan: dict,
    aggregated_state: dict,
) -> dict[str, Any]:
    """Run all output validation checks against the generated diet plan.

    Parameters
    ----------
    diet_plan : dict
        The LLM-generated diet plan.
    aggregated_state : dict
        Patient's aggregated health state.

    Returns
    -------
    dict
        Validation result with violations, counts, and an overall validity flag.
    """
    conditions = _detect_conditions(aggregated_state)
    logger.info("Output validation: detected conditions %s", conditions)

    all_violations: list[dict[str, Any]] = []

    all_violations.extend(_check_contraindicated_foods(diet_plan, conditions))
    all_violations.extend(_check_mandatory_elements(diet_plan, conditions))
    all_violations.extend(
        _check_nutrient_thresholds(diet_plan, aggregated_state, conditions)
    )
    all_violations.extend(_check_unsafe_combinations(diet_plan, conditions))

    critical_count = sum(
        1 for v in all_violations if v.get("severity") == "critical"
    )
    high_count = sum(
        1 for v in all_violations if v.get("severity") == "high"
    )

    result = {
        "valid": critical_count == 0,
        "violations": all_violations,
        "violation_count": len(all_violations),
        "critical_violations": critical_count,
        "high_violations": high_count,
        "conditions_checked": conditions,
        "validation_source": "WHO/NIH/ADA/KDIGO/AHA Official Thresholds (deterministic)",
    }

    if all_violations:
        logger.warning(
            "Output validation: %d violation(s) (%d critical, %d high)",
            len(all_violations),
            critical_count,
            high_count,
        )
    else:
        logger.info("Output validation: all checks passed")

    return result
