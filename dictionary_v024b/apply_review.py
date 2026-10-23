#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate review exports and create a NON-PUBLISHABLE proposed draft.
Does not edit existing crossword clues or auto-approve words.
"""
import argparse
import hashlib
import json
import re
import sys
from copy import deepcopy
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEED = HERE / "draft_entries.json"
HINT_TYPES = {"", "synonym", "alternate_meaning"}
DECISIONS = {"pending", "looks_good", "needs_changes"}
GRAMMAR = {"", "singular_verified", "plural_only_verified", "needs_review"}
DIFFICULTY = {"", "easy", "medium", "hard"}
WORD_RE = re.compile(r"^[А-ЯЁ]{4,9}$")


def github_blob_sha(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description="Validate v0.24b local review suggestions")
    parser.add_argument("review_json", help="Exported file from dictionary-review-v024b.html")
    parser.add_argument("--output", default=str(HERE / "build/proposed_entries.json"))
    args = parser.parse_args()

    raw = SEED.read_bytes()
    seed = json.loads(raw.decode("utf-8"))
    review = json.loads(Path(args.review_json).read_text(encoding="utf-8-sig"))
    assert review["schema_version"] == "0.24b.review.1"
    assert review["final_approval"] is False, "Cannot turn local notes into approved content"
    assert review["seed_blob_sha"] == github_blob_sha(raw), (
        "Dictionary seed changed since these reviews were exported")
    assert isinstance(review["changes"], list)
    draft = deepcopy(seed)
    indexed = {e["lemma"]: e for e in draft["entries"]}
    seen = set()
    for row in review["changes"]:
        lemma = row["lemma"]
        assert isinstance(lemma, str) and WORD_RE.fullmatch(lemma)
        assert lemma in indexed and lemma not in seen, ("Unknown or duplicate", lemma)
        seen.add(lemma)
        assert row["hintType"] in HINT_TYPES and row["decision"] in DECISIONS
        assert row["difficulty"] in DIFFICULTY and row["grammar"] in GRAMMAR
        assert isinstance(row["clue"], str) and row["clue"].strip()
        assert isinstance(row["hint"], str) and isinstance(row["notes"], str)
        assert len(row["notes"]) <= 4000
        hint_text, kind = row["hint"].strip(), row["hintType"]
        assert bool(hint_text) == bool(kind), ("Hint type and text must match", lemma)
        if hint_text:
            assert lemma.lower().replace("ё", "е") not in hint_text.lower().replace(
                "ё", "е"), ("Hint reveals answer", lemma)
        entry = indexed[lemma]
        assert len(entry["senses"]) == 1, ("Multi-sense merge requires manual work", lemma)
        entry["senses"][0]["definition"] = row["clue"].strip()
        entry["senses"][0]["hint"] = {"kind": kind, "text": hint_text} if hint_text else None
        entry["senses"][0]["editorial_status"] = "draft"
        entry["difficulty"] = row["difficulty"] or None
        if row["grammar"] in {"singular_verified", "plural_only_verified"}:
            entry["grammar"]["number"] = row["grammar"]
            entry["grammar"]["check_required"] = True  # independent confirmation needed
        elif row["grammar"] == "needs_review":
            entry["grammar"]["number"] = "unverified"
            entry["grammar"]["check_required"] = True
        entry["review_suggestion"] = {
            "decision": row["decision"], "notes": row["notes"],
            "editorial_status": "not_final_approval"
        }
        entry["editorial_status"] = "draft"
        entry["approved_by"] = None
        entry["approved_at"] = None
    draft["release_status"] = "editorial_proposals_not_published"
    draft["review_import"] = {"suggestions": len(seen),
                              "crossword_clues_synced": False,
                              "independent_review_pending": True,
                              "approved_words": 0}
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(draft, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Validated {len(seen)} suggestions; wrote non-publishable proposal: {out}")
    print("No crossword solution, approved status or canonical dictionary was changed.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (AssertionError, KeyError, ValueError, OSError, TypeError) as e:
        print("REVIEW IMPORT REJECTED:", e, file=sys.stderr)
        sys.exit(1)
