#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v0.24c: merge existing crossword definitions with a separate 103-word draft batch.
No external data import, no fabricated corpus frequencies, no automatic approvals.
Python >=3.9, standard library only.
"""
import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "dictionary_v024b"))
import build_dictionary as base  # noqa: E402

BATCH = HERE / "common_words_batch_001.json"
GRAMMAR_WATCH = {"КОЗНИ", "КУДРИ", "ДАННЫЕ"}
SPELLING_WATCH = {"КОВЕР", "АКТЕР", "ДИРИЖЕР"}


def validate_expansion(existing_seed, batch, pool):
    """Only supplement v0.24b. No changes to original crossword definitions."""
    assert existing_seed["schema_version"] == "0.24b.1"
    assert batch["schema_version"] == "0.24c.1"
    assert batch["release_status"] == "drafts_only_not_approved"
    assert batch["batch_id"] == "v024c_common_batch_001"
    assert len(batch["entries"]) == batch["word_count"] == 103
    known = {e["lemma"] for e in existing_seed["entries"]}
    seen = set()
    allowed_categories = {
        "Животные", "Здоровье", "Дом и быт", "Природа", "Общие знания",
        "Город и транспорт", "Еда и кухня", "Искусство"
    }
    for e in batch["entries"]:
        w = e["lemma"]
        assert w == base.clean_word(w), ("Malformed word", w)
        assert w in pool, ("Word not from cleared MIT lexicon", w)
        assert w not in known and w not in seen, ("Duplicate existing/new word", w)
        seen.add(w)
        assert e["id"] == "ru:" + w and e["length"] == len(w)
        assert e["part_of_speech"] == "noun_candidate" and e["language"] == "ru"
        assert e["sources"] == ["mit_nouns_v021"]
        assert e["topical_categories"] and set(e["topical_categories"]) <= allowed_categories
        assert e["editorial_status"] == "draft"
        assert e["approved_by"] is None and e["approved_at"] is None
        assert e["grammar"]["number"] == "singular_candidate"
        assert e["grammar"]["check_required"] is True
        assert e["frequency_rank"] is None
        assert e["difficulty"] in (None, "easy", "medium", "hard")
        assert e["usage_refs"] == []  # never modify existing crossword placements
        assert isinstance(e["review_flags"], list)
        assert len(e["senses"]) == 1
        s = e["senses"][0]
        assert s["definition"].strip() and s["editorial_status"] == "draft"
        assert s["definition_origin"] == "ai_draft"
        assert s["usage_refs"] == []
        hint = s.get("hint")
        if hint:
            assert set(hint) == {"kind", "text"}
            assert hint["kind"] in base.ALLOWED_HINTS and hint["text"].strip()
            assert w.lower().replace("ё", "е") not in (
                hint["text"].lower().replace("ё", "е")), ("Hint reveals answer", w)
        if w in SPELLING_WATCH:
            assert "ё_spelling_review" in e["review_flags"], w
    return {e["lemma"]: e for e in batch["entries"]}


def build():
    registry = base.load_json(base.REGISTRY)
    puzzle_data = base.load_json(base.SOURCE_PUZZLES)
    old_seed = base.load_json(base.DRAFTS)
    old_entries = base.check_seed(old_seed, puzzle_data, registry)
    candidate_pool = base.read_candidates(registry)
    newcomers = validate_expansion(old_seed, base.load_json(BATCH), candidate_pool)
    combined = dict(old_entries)
    combined.update(newcomers)
    full = base.assemble(combined, candidate_pool)
    assert len(old_entries) == 208
    assert len(newcomers) == 103
    assert len(full) == 2874
    defined = [x for x in full if x["editorial_status"] == "draft"]
    assert len(defined) == 311
    assert all(x["frequency_rank"] is None for x in defined), "No corpus frequencies imported"
    assert all(x["editorial_status"] != "approved" for x in defined), (
        "This batch should never auto-approve entries")
    assert all(
        any(e["lemma"] == w and e["review_flags"] for e in defined)
        for w in GRAMMAR_WATCH
    ), "Plural candidates must stay flagged"
    counts = Counter(x["editorial_status"] for x in full)
    stats = {
        "version": "0.24c.1",
        "total_candidates": len(full),
        "existing_drafts": len(old_entries),
        "new_drafts": len(newcomers),
        "total_drafts_with_clues": len(defined),
        "candidate_only": counts["candidate_only"],
        "total_hinted_lemmas": sum(
            any(s.get("hint") for s in x["senses"]) for x in defined
        ),
        "new_hint_count": sum(
            any(s.get("hint") for s in x["senses"]) for x in newcomers.values()
        ),
        "awaiting_morphology_check": sum(
            bool(x["grammar"]["check_required"]) for x in defined
        ),
        "editorial_flagged": sum(bool(x["review_flags"]) for x in defined),
        "approved": counts["approved"],
        "external_cc_by_sa_imports": 0,
        "release_status": "BLOCKED_PENDING_INDEPENDENT_EDITORIAL_REVIEW"
    }
    assert stats["approved"] == 0 and stats["candidate_only"] == 2563
    return full, defined, stats


def write_queue(path, defined):
    columns = ["word", "category", "length", "definition", "hint_type", "hint",
               "difficulty_draft", "grammar_draft", "review_flags", "source_batch",
               "editorial_decision", "notes"]
    with path.open("w", encoding="utf-8-sig", newline="") as h:
        writer = csv.DictWriter(h, fieldnames=columns)
        writer.writeheader()
        for e in sorted(defined, key=lambda x: x["lemma"]):
            s = e["senses"][0]
            writer.writerow({
                "word": e["lemma"],
                "category": "; ".join(e["topical_categories"]),
                "length": e["length"], "definition": s["definition"],
                "hint_type": (s.get("hint") or {}).get("kind", ""),
                "hint": (s.get("hint") or {}).get("text", ""),
                "difficulty_draft": e["difficulty"] or "",
                "grammar_draft": e["grammar"]["number"],
                "review_flags": "; ".join(e["review_flags"]),
                "source_batch": e.get("batch_id", "v0.24b_legacy"),
                "editorial_decision": "", "notes": ""
            })


def main():
    parser = argparse.ArgumentParser(description="v0.24c offline dictionary expansion + QA")
    parser.add_argument("--verify", action="store_true", help="Check inputs without writing files")
    parser.add_argument("--build", action="store_true", help="Write master data and editorial CSV")
    parser.add_argument("--release", action="store_true", help="Explicitly check publication gate")
    parser.add_argument("--output", default=str(HERE / "build"))
    args = parser.parse_args()
    full, defined, stats = build()
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    if args.release:
        print("RELEASE BLOCKED: new definitions and morphology are unreviewed.", file=sys.stderr)
        return 2
    if args.build:
        out = Path(args.output)
        out.mkdir(parents=True, exist_ok=True)
        (out / "master_dictionary_v024c.json").write_text(
            json.dumps({"schema_version": "0.24c.1", "release_status": "DRAFT_ONLY",
                        "stats": stats, "entries": full}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
        write_queue(out / "editorial_queue_311.csv", defined)
        print("Wrote draft master (2874 candidates) and editorial queue (311 entries) to", out)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (AssertionError, KeyError, ValueError, OSError, TypeError) as err:
        print("V0.24c DICTIONARY QA FAIL:", err, file=sys.stderr)
        sys.exit(1)
