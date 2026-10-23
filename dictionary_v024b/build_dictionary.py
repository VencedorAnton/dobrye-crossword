#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dictionary Foundation v0.24b. Offline, Python >= 3.9, stdlib only.
All source entries remain editorial drafts until explicitly approved.
"""
import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "dictionary_v024b"
SOURCE_WORDS = ROOT / "generator_v021/data/mit_russian_nouns.txt"
SOURCE_PUZZLES = ROOT / "generator_v023/filled_ornaments_v023b.json"
DRAFTS = HERE / "draft_entries.json"
REGISTRY = HERE / "source_registry.json"
WORD_RE = re.compile(r"^[А-ЯЁ]{4,9}$")
ALLOWED_HINTS = {"synonym", "alternate_meaning"}
GRAMMAR_FOR_RELEASE = {"singular_verified", "plural_only_verified"}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def clean_word(value):
    value = (value or "").strip().upper()
    return value if WORD_RE.fullmatch(value) else None


def check_seed(seed, source, registry):
    assert seed["schema_version"] == "0.24b.1"
    assert seed["release_status"] == "editorial_drafts_only"
    assert source["release_status"] == "preview_only"
    ids = {item["id"] for item in registry["sources"]}
    entries = seed["entries"]
    assert len({e["lemma"] for e in entries}) == len(entries), "Duplicate lemmas"
    by_word = {}
    usage_to_definition = {}
    for e in entries:
        word = e["lemma"]
        assert clean_word(word) == word, ("Invalid lemma", word)
        assert e["id"] == "ru:" + word
        assert e["length"] == len(word)
        assert e["language"] == "ru" and e["part_of_speech"] == "noun_candidate"
        assert e["editorial_status"] in {"draft", "approved", "rejected"}
        assert e["sources"] and set(e["sources"]) <= ids
        assert e["senses"] and len(e["senses"]) == len({s["definition"] for s in e["senses"]})
        assert len(e["usage_refs"]) == len(set(e["usage_refs"]))
        assert e["frequency_rank"] is None or (
            isinstance(e["frequency_rank"], int) and e["frequency_rank"] >= 1)
        assert e["difficulty"] in (None, "easy", "medium", "hard")
        assert isinstance(e["review_flags"], list)
        assert isinstance(e["grammar"]["check_required"], bool)
        if e["editorial_status"] == "approved":
            assert e["approved_by"] and e["approved_at"], ("Review evidence missing", word)
            assert e["grammar"]["number"] in GRAMMAR_FOR_RELEASE, ("Grammar not verified", word)
            assert not e["grammar"]["check_required"] and not e["review_flags"], (
                "Outstanding editorial flags", word)
        seen_usage = set()
        for s in e["senses"]:
            assert s["sense_id"].startswith(e["id"] + ":sense:")
            assert s["definition"].strip() and s["definition_origin"] == "ai_draft"
            assert s["editorial_status"] in {"draft", "approved", "rejected"}
            if e["editorial_status"] == "approved":
                assert s["editorial_status"] == "approved", word
            hint = s.get("hint")
            if hint is not None:
                assert isinstance(hint, dict) and set(hint) == {"kind", "text"}
                assert hint["kind"] in ALLOWED_HINTS and isinstance(hint["text"], str)
                assert hint["text"].strip(), ("Empty hint", word)
                assert word.lower().replace("ё", "е") not in (
                    hint["text"].lower().replace("ё", "е")), ("Leaking answer", word)
            assert len(s["usage_refs"]) == len(set(s["usage_refs"]))
            for ref in s["usage_refs"]:
                assert ref not in usage_to_definition, ("Duplicate usage ref", ref)
                usage_to_definition[ref] = (word, s["definition"], hint)
                seen_usage.add(ref)
        assert seen_usage == set(e["usage_refs"]), ("Sense usage mismatch", word)
        by_word[word] = e

    from_puzzles = {}
    for p in source["puzzles"]:
        for item in p["placements"]:
            ref = f"{p['id']}:{item['direction']}:{item['row']}:{item['col']}"
            assert ref not in from_puzzles
            from_puzzles[ref] = (item["word"], item["clue"], item.get("hint"))
    assert usage_to_definition == from_puzzles, "Seed/puzzle clue, word or hint mismatch"
    assert len(from_puzzles) == 216, len(from_puzzles)
    assert len(by_word) == 208, len(by_word)
    return by_word


def read_candidates(registry, csv_path=None):
    srcs = {item["id"]: item for item in registry["sources"]}
    assert srcs["mit_nouns_v021"]["allowed_for_candidate_import"]
    candidate_sources = defaultdict(set)
    for line in SOURCE_WORDS.read_text(encoding="utf-8-sig").splitlines():
        lemma = clean_word(line)
        if lemma:
            candidate_sources[lemma].add("mit_nouns_v021")
    if csv_path:
        with Path(csv_path).open(encoding="utf-8-sig", newline="") as inp:
            reader = csv.DictReader(inp)
            assert reader.fieldnames and {"word", "source_id"} <= set(reader.fieldnames)
            for row in reader:
                source_id, lemma = row["source_id"].strip(), clean_word(row["word"])
                assert source_id in srcs, ("Unregistered source", source_id)
                assert srcs[source_id]["allowed_for_candidate_import"], (
                    "Source is not cleared for import", source_id)
                assert lemma, ("Invalid word", row["word"])
                candidate_sources[lemma].add(source_id)
    return candidate_sources


def skeleton(lemma, sources):
    return {
        "id": "ru:" + lemma, "lemma": lemma, "length": len(lemma),
        "language": "ru", "part_of_speech": "noun_candidate",
        "grammar": {"number": "unknown", "case": "unknown", "check_required": True},
        "topical_categories": [], "difficulty": None, "frequency_rank": None,
        "editorial_status": "candidate_only", "approved_by": None, "approved_at": None,
        "review_flags": ["needs_morphology", "needs_definition", "needs_editorial"],
        "sources": sorted(sources), "senses": [], "usage_refs": []
    }


def assemble(seed, candidates):
    records = {w: skeleton(w, sources) for w, sources in candidates.items()}
    for e in seed.values():
        copy = dict(e)
        copy["sources"] = sorted(set(copy["sources"]) | candidates.get(e["lemma"], set()))
        records[e["lemma"]] = copy
    return [records[word] for word in sorted(records)]


def write_review_queue(path, records):
    fields = ["lemma", "length", "status", "grammar_number", "difficulty",
              "frequency_rank", "definition", "hint", "flags", "usages", "decision_notes"]
    with Path(path).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for e in records:
            if not e["senses"]:
                continue
            first = e["senses"][0]
            writer.writerow({
                "lemma": e["lemma"], "length": e["length"], "status": e["editorial_status"],
                "grammar_number": e["grammar"]["number"], "difficulty": e["difficulty"] or "",
                "frequency_rank": e["frequency_rank"] or "",
                "definition": first["definition"],
                "hint": first["hint"]["text"] if first.get("hint") else "",
                "flags": "; ".join(e["review_flags"]),
                "usages": "; ".join(e["usage_refs"]), "decision_notes": ""
            })


def summary(records, raw_total):
    counts = Counter(e["editorial_status"] for e in records)
    return {
        "version": "0.24b.1", "raw_mit_candidates": raw_total,
        "total_unique_candidates": len(records),
        "candidate_only": counts["candidate_only"], "draft_entries": counts["draft"],
        "approved_entries": counts["approved"], "rejected_entries": counts["rejected"],
        "draft_senses": sum(len(e["senses"]) for e in records),
        "hinted_entries": sum(any(s.get("hint") for s in e["senses"]) for e in records),
        "editorial_flags": sum(bool(e["review_flags"]) for e in records
                               if e["editorial_status"] != "candidate_only"),
        "release_gate": "OPEN" if counts["approved"] else "BLOCKED_NO_APPROVED_WORDS"
    }


def main():
    ap = argparse.ArgumentParser(description="Offline Russian crossword dictionary builder v0.24b")
    ap.add_argument("--verify", action="store_true", help="Read-only validation and summary")
    ap.add_argument("--build", action="store_true", help="Write compiled dictionary and editorial queue")
    ap.add_argument("--release", action="store_true", help="Export editor-approved words only")
    ap.add_argument("--candidate-csv", help="Optional CSV: word,source_id (registered cleared source)")
    ap.add_argument("--out-dir", default=str(HERE / "build"), help="Output directory")
    args = ap.parse_args()

    registry = load_json(REGISTRY)
    seed = check_seed(load_json(DRAFTS), load_json(SOURCE_PUZZLES), registry)
    candidates = read_candidates(registry, args.candidate_csv)
    records = assemble(seed, candidates)
    stats = summary(records, len(candidates))
    print(json.dumps(stats, ensure_ascii=False, indent=2))

    if not (args.build or args.release):
        return 0
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.build:
        (out_dir / "master_dictionary.json").write_text(
            json.dumps({"schema_version": "0.24b.1", "release_status": "NOT_PUBLISHED",
                        "stats": stats, "entries": records}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
        write_review_queue(out_dir / "editorial_queue.csv", records)
        print("Compiled draft dictionary and editorial queue:", out_dir)
    if args.release:
        approved = [e for e in records if e["editorial_status"] == "approved"]
        if not approved:
            print("RELEASE BLOCKED: no words have passed independent editorial QA.", file=sys.stderr)
            return 2
        (out_dir / "approved_dictionary.json").write_text(
            json.dumps({"schema_version": "0.24b.1", "approved_count": len(approved),
                        "entries": approved}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
        print("Exported only verified approved words:", len(approved))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (AssertionError, ValueError, KeyError, OSError) as exc:
        print("DICTIONARY QA FAIL:", exc, file=sys.stderr)
        sys.exit(1)
