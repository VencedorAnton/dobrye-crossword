#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compose the canonical v0.24d editorial view from the legacy v0.24c builder
and owner's small override file. Original source files and puzzles stay unchanged.
Run from any directory: python dictionary_v024c/build_owner_review_v024d.py --build
"""
import argparse
import json
from pathlib import Path

import build_enriched as base

HERE = Path(__file__).resolve().parent
OVERRIDES = HERE / "owner_clue_overrides_v024d.json"


def compile_editorial_view():
    all_entries, drafts, stats = base.build()
    patch = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    assert patch["schema_version"] == "0.24d.owner_clue_overrides.1"
    assert patch["release_status"] == "draft_only"
    by_word = {e["lemma"]: e for e in all_entries}
    seen = set()
    for change in patch["changes"]:
        word = change["lemma"]
        assert word not in seen and word in by_word
        seen.add(word)
        e = by_word[word]
        assert e["editorial_status"] == "draft" and e["approved_at"] is None
        assert e["grammar"]["check_required"] is True
        assert change["hint_policy"] in {"preserve_existing", "replace"}
        assert 1 <= len(change["clue_variants"]) <= 3
        ids = [v["id"] for v in change["clue_variants"]]
        assert len(set(ids)) == len(ids) and change["preferred_clue_variant"] in ids
        for v in change["clue_variants"]:
            assert v["text"].strip() and v["editorial_status"] == "owner_selected_draft"
            assert word.lower().replace("ё", "е") not in v["text"].lower().replace("ё", "е")
        if word != "ЗЕРКАЛО":
            assert all(len(v["text"]) <= 70 for v in change["clue_variants"]), (
                "Editorial character budget exceeded", word)
        assert e["editorial_status"] == "draft", word
        e["topical_categories"] = change["categories"]
        sense = e["senses"][0]
        old_hint = sense.get("hint")
        sense["clue_variants"] = change["clue_variants"]
        sense["preferred_clue_variant"] = change["preferred_clue_variant"]
        sense["definition"] = next(v["text"] for v in change["clue_variants"]
                                   if v["id"] == change["preferred_clue_variant"])
        sense["definition_origin"] = "ai_draft_owner_selected"
        sense["editorial_choice"] = {"selected_by": "owner", "status": "draft"}
        if change["hint_policy"] == "replace":
            hint = change["hint_override"]
            assert set(hint) == {"kind", "text"} and hint["text"].strip()
            assert hint["kind"] in {"alternate_meaning", "synonym"}
            assert word.lower().replace("ё", "е") not in hint["text"].lower().replace("ё", "е")
            sense["hint"] = hint
        else:
            assert sense.get("hint") == old_hint
    assert len(seen) == len(patch["changes"]) and len(seen) >= 43
    assert len(all_entries) == 2874 and len(drafts) == 311
    assert all(e["editorial_status"] != "approved" for e in all_entries)
    stats["version"] = "0.24d.1"
    stats["owner_override_count"] = len(seen)
    stats["release_status"] = "BLOCKED_PENDING_EDITORIAL_REVIEW"
    return all_entries, drafts, stats


def main():
    parser = argparse.ArgumentParser(description="Compile non-publishable editorial clues")
    parser.add_argument("--build", action="store_true")
    args = parser.parse_args()
    entries, drafts, stats = compile_editorial_view()
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    if args.build:
        output = HERE / "build"
        output.mkdir(exist_ok=True)
        (output / "master_dictionary_v024d.json").write_text(json.dumps(
            {"schema_version": "0.24d.1", "release_status": "draft_only",
             "stats": stats, "entries": entries}, ensure_ascii=False, indent=2) + "\n",
             encoding="utf-8")
        base.write_queue(output / "editorial_queue_v024d.csv", drafts)


if __name__ == "__main__":
    main()
