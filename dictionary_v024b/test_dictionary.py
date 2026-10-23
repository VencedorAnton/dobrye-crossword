#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression tests for Dictionary Foundation v0.24b; no third-party modules."""
import copy
import csv
import tempfile
import unittest
from pathlib import Path

import build_dictionary as b


class DictionaryFoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seed = b.load_json(b.DRAFTS)
        cls.crosswords = b.load_json(b.SOURCE_PUZZLES)
        cls.registry = b.load_json(b.REGISTRY)

    def test_seed_crossword_sync(self):
        result = b.check_seed(self.seed, self.crosswords, self.registry)
        self.assertEqual(len(result), 208)
        self.assertEqual(sum(len(x["usage_refs"]) for x in result.values()), 216)
        self.assertEqual(sum(any(s.get("hint") for s in x["senses"])
                             for x in result.values()), 12)

    def test_candidate_pool_preserves_manual_correction(self):
        source = b.read_candidates(self.registry)
        self.assertEqual(len(source), 2873)
        self.assertNotIn("ЛАДОНЬ", source)
        merged = b.assemble({x["lemma"]: x for x in self.seed["entries"]}, source)
        self.assertEqual(len(merged), 2874)
        self.assertIn("ЛАДОНЬ", {x["lemma"] for x in merged})

    def test_unreviewed_dictionary_cannot_release(self):
        base = b.check_seed(self.seed, self.crosswords, self.registry)
        merged = b.assemble(base, b.read_candidates(self.registry))
        stats = b.summary(merged, 2873)
        self.assertEqual(stats["approved_entries"], 0)
        self.assertEqual(stats["release_gate"], "BLOCKED_NO_APPROVED_WORDS")
        self.assertEqual(stats["candidate_only"], 2666)

    def test_answer_leak_rejected(self):
        sample = copy.deepcopy(self.seed)
        word = sample["entries"][0]["lemma"]
        sample["entries"][0]["senses"][0]["hint"] = {
            "kind": "synonym", "text": "Это " + word.lower()
        }
        with self.assertRaises(AssertionError):
            b.check_seed(sample, self.crosswords, self.registry)

    def test_untracked_clue_change_rejected(self):
        sample = copy.deepcopy(self.seed)
        sample["entries"][0]["senses"][0]["definition"] += " Изменено без проверки."
        with self.assertRaises(AssertionError):
            b.check_seed(sample, self.crosswords, self.registry)

    def test_no_copyleft_import_without_clearance(self):
        with tempfile.TemporaryDirectory() as tmp:
            source_csv = Path(tmp) / "new_words.csv"
            with source_csv.open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["word", "source_id"])
                writer.writeheader()
                writer.writerow({"word": "СОЛНЦЕ", "source_id": "openrussian"})
            with self.assertRaises(AssertionError):
                b.read_candidates(self.registry, source_csv)

    def test_missing_approval_evidence_blocks_release(self):
        sample = copy.deepcopy(self.seed)
        sample["entries"][0]["editorial_status"] = "approved"
        with self.assertRaises(AssertionError):
            b.check_seed(sample, self.crosswords, self.registry)


if __name__ == "__main__":
    unittest.main(verbosity=2)
