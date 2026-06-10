#!/usr/bin/env python3
"""Fetch antihypertensive drug-safety facts from openFDA and write them into the
evidence corpus as DRUG_SAFETY records, structured by SmPC dimensions.

Why grounded (not LLM recall): regulatory drug labels are an authoritative,
citable primary source. Literature shows bare-LLM contraindication recall is
unreliable (~0.5 accuracy) vs RAG against labels (~0.9). Each record is one
drug, one openFDA label, split into the standard SmPC safety sections so the
Apply agent can fill a cited safety section from retrieved chunks.

Source: openFDA drug/label endpoint (https://open.fda.gov/apis/drug/label/).
No API key needed for our volume (~50 requests). Output: one
`EV-DRUGSAFETY-<year>-<DRUG>-001.md` per drug in EVIDENCE_ROOT.

Usage:
    py -3 hypertension/scripts/fetch_drug_safety.py [--force] [--limit N] [--only DRUG]
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path

import requests
import yaml

# --- make the (worktree) hypertensiondb importable for frontmatter validation ---
_HERE = Path(__file__).resolve()
_SRC = _HERE.parent.parent / "src"
sys.path.insert(0, str(_SRC))
from hypertensiondb.schema.label import LabelFrontmatter  # noqa: E402

EVIDENCE_ROOT = Path(os.getenv("EVIDENCE_ROOT", str(_HERE.parent.parent / "evidence")))
API = "https://api.fda.gov/drug/label.json"

# Curated antihypertensive list. drug_class is OUR label (openFDA's pharm_class
# is unreliable — e.g. it mislabels lisinopril as a thiazide). `search` overrides
# the default generic-name query when needed (combos / awkward names).
DRUGS: list[dict] = [
    # ACE inhibitors
    {"generic": "benazepril", "drug_class": "ACEI"},
    {"generic": "captopril", "drug_class": "ACEI"},
    {"generic": "enalapril", "drug_class": "ACEI"},
    {"generic": "lisinopril", "drug_class": "ACEI"},
    {"generic": "ramipril", "drug_class": "ACEI"},
    {"generic": "perindopril", "drug_class": "ACEI"},
    {"generic": "fosinopril", "drug_class": "ACEI"},
    {"generic": "quinapril", "drug_class": "ACEI"},
    {"generic": "trandolapril", "drug_class": "ACEI"},
    # ARBs
    {"generic": "losartan", "drug_class": "ARB"},
    {"generic": "valsartan", "drug_class": "ARB"},
    {"generic": "candesartan", "drug_class": "ARB"},
    {"generic": "irbesartan", "drug_class": "ARB"},
    {"generic": "telmisartan", "drug_class": "ARB"},
    {"generic": "olmesartan", "drug_class": "ARB"},
    {"generic": "azilsartan", "drug_class": "ARB"},
    {"generic": "eprosartan", "drug_class": "ARB"},
    # ARNI — genuinely a fixed combination; allow it and require both components.
    {"generic": "sacubitril-valsartan", "drug_class": "ARNI",
     "search": 'openfda.brand_name:"entresto"',
     "allow_combo": True, "components": ["sacubitril", "valsartan"]},
    # CCB — dihydropyridine
    {"generic": "amlodipine", "drug_class": "CCB-DHP"},
    {"generic": "nifedipine", "drug_class": "CCB-DHP"},
    {"generic": "felodipine", "drug_class": "CCB-DHP"},
    {"generic": "nicardipine", "drug_class": "CCB-DHP"},
    {"generic": "isradipine", "drug_class": "CCB-DHP"},
    {"generic": "nisoldipine", "drug_class": "CCB-DHP"},
    {"generic": "clevidipine", "drug_class": "CCB-DHP"},
    # CCB — non-dihydropyridine
    {"generic": "diltiazem", "drug_class": "CCB-nonDHP"},
    {"generic": "verapamil", "drug_class": "CCB-nonDHP"},
    # Thiazide / thiazide-like diuretics
    {"generic": "hydrochlorothiazide", "drug_class": "thiazide"},
    {"generic": "chlorthalidone", "drug_class": "thiazide-like"},
    {"generic": "indapamide", "drug_class": "thiazide-like"},
    {"generic": "metolazone", "drug_class": "thiazide-like"},
    # Loop diuretics
    {"generic": "furosemide", "drug_class": "loop-diuretic"},
    {"generic": "torsemide", "drug_class": "loop-diuretic"},
    {"generic": "bumetanide", "drug_class": "loop-diuretic"},
    # K-sparing / MRA
    {"generic": "spironolactone", "drug_class": "MRA"},
    {"generic": "eplerenone", "drug_class": "MRA"},
    {"generic": "amiloride", "drug_class": "K-sparing-diuretic"},
    {"generic": "triamterene", "drug_class": "K-sparing-diuretic"},
    # Beta-blockers
    {"generic": "metoprolol", "drug_class": "beta-blocker"},
    {"generic": "atenolol", "drug_class": "beta-blocker"},
    {"generic": "bisoprolol", "drug_class": "beta-blocker"},
    {"generic": "carvedilol", "drug_class": "beta-blocker"},
    {"generic": "labetalol", "drug_class": "beta-blocker"},
    {"generic": "nebivolol", "drug_class": "beta-blocker"},
    {"generic": "propranolol", "drug_class": "beta-blocker"},
    # Alpha-1 blockers
    {"generic": "doxazosin", "drug_class": "alpha-blocker"},
    {"generic": "prazosin", "drug_class": "alpha-blocker"},
    {"generic": "terazosin", "drug_class": "alpha-blocker"},
    # Central alpha-2 agonists
    {"generic": "clonidine", "drug_class": "central-alpha2-agonist"},
    {"generic": "methyldopa", "drug_class": "central-alpha2-agonist"},
    # Direct vasodilators
    {"generic": "hydralazine", "drug_class": "direct-vasodilator"},
    {"generic": "minoxidil", "drug_class": "direct-vasodilator"},
    # Direct renin inhibitor
    {"generic": "aliskiren", "drug_class": "renin-inhibitor"},
]

# openFDA field -> (SmPC heading, section weight for "best label" scoring).
# pregnancy/nursing/specific-populations are merged into one section.
_HEADING = {
    "boxed_warning": "## 黑框警告 (Boxed Warning)",
    "contraindications": "## 禁忌 (Contraindications)",
    "warnings": "## 警告与注意事项 (Warnings and Precautions)",
    "drug_interactions": "## 药物相互作用 (Drug Interactions)",
    "pregnancy_lactation": "## 妊娠与哺乳·特殊人群 (Pregnancy, Lactation & Specific Populations)",
    "adverse_reactions": "## 不良反应 (Adverse Reactions)",
}
_SECTION_CAP = 4000  # per-section char cap; chunker re-splits at 1500


def _clean(val) -> str:
    """openFDA fields are lists of strings; join, strip, collapse blank runs."""
    if not val:
        return ""
    if isinstance(val, list):
        text = "\n\n".join(str(x).strip() for x in val if str(x).strip())
    else:
        text = str(val).strip()
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) > _SECTION_CAP:
        text = text[:_SECTION_CAP].rstrip() + " …（详见完整说明书）"
    return text


def _sections_from_record(rec: dict) -> dict[str, str]:
    warnings = _clean(rec.get("warnings_and_cautions")) or _clean(rec.get("warnings"))
    preg = "\n\n".join(
        s for s in (
            _clean(rec.get("pregnancy")),
            _clean(rec.get("nursing_mothers")),
            _clean(rec.get("use_in_specific_populations")),
        ) if s
    )
    return {
        "boxed_warning": _clean(rec.get("boxed_warning")),
        "contraindications": _clean(rec.get("contraindications")),
        "warnings": warnings,
        "drug_interactions": _clean(rec.get("drug_interactions")),
        "pregnancy_lactation": preg,
        "adverse_reactions": _clean(rec.get("adverse_reactions")),
    }


# Salt / ester / prodrug suffixes to strip so "amlodipine besylate",
# "olmesartan medoxomil", "perindopril erbumine" all reduce to the base drug.
_SALTS = {
    "besylate", "hydrochloride", "hcl", "maleate", "mesylate", "sodium",
    "potassium", "calcium", "dihydrate", "monohydrate", "trihydrate",
    "hemipentahydrate", "fumarate", "succinate", "tartrate", "hydrobromide",
    "camsylate", "arginine", "medoxomil", "cilexetil", "erbumine", "anhydrous",
    "hemihydrate", "and", "&",
}


def _base_substances(rec: dict) -> set[str]:
    """Reduce a label's active substances to base drug names (salts stripped).

    Combos yield >1 base (e.g. amlodipine + benazepril). Used to reject
    combination products that would mis-attribute the partner drug's risks
    (e.g. a benazepril boxed FETAL-TOXICITY warning landing on amlodipine).
    """
    of = rec.get("openfda", {})
    raw = of.get("substance_name") or of.get("generic_name") or []
    bases: set[str] = set()
    for item in raw:
        words = [w for w in re.split(r"[\s,/]+", str(item).lower()) if w]
        core = [w for w in words if w not in _SALTS]
        if core:
            bases.add(core[0])
    return bases


def _score(rec: dict) -> int:
    """Prefer the label populating the most safety sections (+ brand name)."""
    secs = _sections_from_record(rec)
    n = sum(1 for v in secs.values() if v)
    if rec.get("openfda", {}).get("brand_name"):
        n += 1
    return n


def _is_match(drug: dict, rec: dict) -> bool:
    """True if `rec` is the right product for `drug`.

    Mono drugs: the label must have exactly one active substance and it must be
    the target — this rejects combination products. Combo drugs (allow_combo):
    the label's substances must cover all declared components.
    """
    bases = _base_substances(rec)
    if not bases:
        return False
    if drug.get("allow_combo"):
        return set(drug["components"]).issubset(bases)
    return bases == {drug["generic"]}


def _fetch_best(drug: dict, session: requests.Session) -> dict | None:
    search = drug.get("search") or f'openfda.generic_name:"{drug["generic"]}"'
    try:
        r = session.get(API, params={"search": search, "limit": 50}, timeout=30)
    except requests.RequestException as e:
        print(f"  ! network error: {e}")
        return None
    if r.status_code == 404:
        print("  ! no openFDA label found")
        return None
    if r.status_code != 200:
        print(f"  ! HTTP {r.status_code}")
        return None
    results = r.json().get("results", [])
    candidates = [rec for rec in results if _is_match(drug, rec)]
    if not candidates:
        kinds = sorted({frozenset(_base_substances(r)) for r in results})[:3]
        print(f"  ! no mono-ingredient label among {len(results)} results "
              f"(saw e.g. {[sorted(k) for k in kinds]}) — skipped to avoid combo mis-attribution")
        return None
    return max(candidates, key=_score)


def _year(rec: dict) -> int:
    eff = rec.get("effective_time") or ""
    m = re.match(r"(\d{4})", str(eff))
    return int(m.group(1)) if m else 2024


def _slug(generic: str) -> str:
    return re.sub(r"[^A-Z0-9-]", "", generic.upper().replace(" ", "-"))


def build_record(drug: dict, rec: dict) -> tuple[str, str] | None:
    secs = _sections_from_record(rec)
    if not (secs["contraindications"] or secs["warnings"] or secs["adverse_reactions"]):
        print("  ! label has no usable safety sections — skipped")
        return None

    of = rec.get("openfda", {})
    year = _year(rec)
    slug = _slug(drug["generic"])
    ev_id = f"EV-DRUGSAFETY-{year}-{slug}-001"
    set_id = rec.get("set_id") or (of.get("spl_set_id") or [None])[0]
    url = (f"https://dailymed.nlm.nih.gov/dailymed/spl.cfm?setid={set_id}"
           if set_id else "https://open.fda.gov/apis/drug/label/")
    brands = sorted({b.title() for b in (of.get("brand_name") or [])})[:5]
    disp = drug["generic"].title()

    meta = {
        "id": ev_id,
        "type": "DRUGSAFETY",
        "title": {
            "zh": f"{disp} 药品安全信息（FDA 说明书）",
            "en": f"{disp} — Drug Safety (FDA Label)",
        },
        "authors": ["U.S. FDA"],
        "year": year,
        "language": "en",
        "status": "reviewed",
        "source": "openFDA",
        "url": url,
        "drug_name": drug["generic"],
        "drug_class": drug["drug_class"],
        "brand_names": brands,
        "spl_set_id": set_id,
        "spl_version": str(rec.get("version")) if rec.get("version") else None,
        "effective_time": str(rec.get("effective_time")) if rec.get("effective_time") else None,
        "study_type": "DRUG_LABEL",
        "tags": ["drug_safety", drug["drug_class"], drug["generic"]],
    }
    # Validate against the schema before writing — fail loud on a bad record.
    LabelFrontmatter(**meta)

    body_parts: list[str] = []
    for key in ("boxed_warning", "contraindications", "warnings",
                "drug_interactions", "pregnancy_lactation", "adverse_reactions"):
        if secs[key]:
            body_parts.append(f"{_HEADING[key]}\n\n{secs[key]}")
    body = "\n\n".join(body_parts)

    front = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).strip()
    md = f"---\n{front}\n---\n\n{body}\n"
    return ev_id, md


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="overwrite existing records")
    ap.add_argument("--limit", type=int, default=0, help="cap number of drugs (0=all)")
    ap.add_argument("--only", default="", help="fetch a single generic name")
    args = ap.parse_args()

    EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True)
    drugs = DRUGS
    if args.only:
        drugs = [d for d in DRUGS if d["generic"] == args.only]
    if args.limit:
        drugs = drugs[: args.limit]

    session = requests.Session()
    session.headers["User-Agent"] = "ebm5a-drug-safety-fetch/1.0"
    written = skipped = failed = 0
    for d in drugs:
        slug = _slug(d["generic"])
        existing = list(EVIDENCE_ROOT.glob(f"EV-DRUGSAFETY-*-{slug}-001.md"))
        if existing and not args.force:
            print(f"{d['generic']}: exists ({existing[0].name}) — skip")
            skipped += 1
            continue
        print(f"{d['generic']} [{d['drug_class']}] …")
        rec = _fetch_best(d, session)
        if not rec:
            failed += 1
            continue
        try:
            built = build_record(d, rec)
        except Exception as e:
            print(f"  ! build/validate failed: {type(e).__name__}: {e}")
            failed += 1
            continue
        if not built:
            failed += 1
            continue
        ev_id, md = built
        # Remove a stale differently-yeared file for the same drug on --force.
        for old in existing:
            old.unlink()
        out = EVIDENCE_ROOT / f"{ev_id}.md"
        out.write_text(md, encoding="utf-8")
        print(f"  -> {out.name} ({len(md)} chars)")
        written += 1
        time.sleep(0.3)

    print(f"\nDone. written={written} skipped={skipped} failed={failed} "
          f"(of {len(drugs)} requested)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
