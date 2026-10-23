#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Safely validate v0.24c browser editorial exports (proposal ONLY).
No overwrite of base, expansion batch, or crossword puzzles. Python 3.9+ stdlib.
"""
import argparse
import hashlib
import json
import re
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "dictionary_v024b/draft_entries.json"
BATCH = ROOT / "dictionary_v024c/common_words_batch_001.json"
HERE = Path(__file__).resolve().parent
TYPES = {"", "synonym", "alternate_meaning"}
GRAMMAR = {"", "singular_verified", "plural_only_verified", "needs_review"}
DIFFICULTY = {"", "easy", "medium", "hard"}
DECISION = {"pending", "looks_good", "needs_changes"}
WORD_RE = re.compile(r"^[А-ЯЁ]{4,9}$")


def blob_sha(contents):
    return hashlib.sha1(b"blob " + str(len(contents)).encode() + b"\x00" + contents).hexdigest()


def validate_export(review, seed_bytes, batch_bytes):
    assert review["schema_version"] == "0.24c.review.1"
    assert review["final_approval"] is False
    assert review["seed_blob_sha"] == blob_sha(seed_bytes), "Base changed since export"
    assert review["batch_blob_sha"] == blob_sha(batch_bytes), "Expansion batch changed since export"
    assert isinstance(review["changes"], list)
    base = json.loads(seed_bytes.decode("utf-8"))
    batch = json.loads(batch_bytes.decode("utf-8"))
    entries = {e["lemma"]: deepcopy(e) for e in base["entries"] + batch["entries"]}
    assert len(entries) == 311
    seen = set()
    proposals = []
    for suggestion in review["changes"]:
        lemma = suggestion["lemma"]
        assert isinstance(lemma, str) and WORD_RE.fullmatch(lemma), ("Invalid word", lemma)
        assert lemma in entries and lemma not in seen, ("Unknown/duplicate word", lemma)
        seen.add(lemma)
        for field in ["clue", "hint", "hintType", "difficulty", "grammar", "decision", "notes"]:
            assert isinstance(suggestion[field], str), (lemma, field)
        assert suggestion["clue"].strip(), (lemma, "Empty clue")
        assert suggestion["hintType"] in TYPES and suggestion["grammar"] in GRAMMAR
        assert suggestion["difficulty"] in DIFFICULTY
        assert suggestion["decision"] in DECISION
        assert len(suggestion["notes"]) <= 4000
        hint = suggestion["hint"].strip()
        kind = suggestion["hintType"]
        assert bool(hint) == bool(kind), (lemma, "Hint requires its type and vice versa")
        assert lemma.casefold().replace("ё", "е") not in hint.casefold().replace(
            "ё", "е"), (lemma, "Hint reveals answer")
        original = entries[lemma]
        assert len(original["senses"]) == 1
        proposed = deepcopy(original)
        proposed["senses"][0]["definition"] = suggestion["clue"].strip()
        proposed["senses"][0]["hint"] = {"kind": kind, "text": hint} if hint else None
        proposed["senses"][0]["editorial_status"] = "draft"
        proposed["difficulty"] = suggestion["difficulty"] or None
        proposed["review_suggestion"] = {
            "decision": suggestion["decision"],
            "grammar": suggestion["grammar"],
            "notes": suggestion["notes"],
            "independent_editor_approved": False,
        }
        # Never turn a browser selection into a verified grammar tag or approval.
        proposed["editorial_status"] = "draft"
        proposed["approved_by"] = None
        proposed["approved_at"] = None
        proposed["grammar"]["check_required"] = True
        proposals.append({
            "word": lemma, "existing_crossword_uses": len(original["usage_refs"]),
            "original": original, "proposed": proposed
        })
    return {
        "schema_version": "0.24c.review_proposals.1",
        "status": "PROPOSALS_ONLY_NOT_APPROVED",
        "base_sha": review["seed_blob_sha"],
        "batch_sha": review["batch_blob_sha"],
        "change_count": len(proposals),
        "crossword_puzzles_modified": False,
        "suggestions": proposals,
    }


def main():
    parser = argparse.ArgumentParser(description="Read-only v0.24c editorial import validator")
    parser.add_argument("review_json", help="Export from dictionary-review-v024c.html")
    parser.add_argument("--output", default=str(HERE / "build/proposed_review_v024c.json"))
    args = parser.parse_args()
    submitted = json.loads(Path(args.review_json).read_text(encoding="utf-8-sig"))
    proposal = validate_export(submitted, BASE.read_bytes(), BATCH.read_bytes())
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(proposal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"VALIDATED: {proposal['change_count']} draft editorial suggestions; written to {out}")
    print("Original dictionaries and published puzzles have NOT been changed.")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, ValueError, KeyError, OSError, TypeError) as err:
        print("REVIEW EXPORT REJECTED:", err, file=sys.stderr)
        sys.exit(1)
