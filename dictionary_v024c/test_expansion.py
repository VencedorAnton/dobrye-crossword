#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v0.24c regression tests: no third-party dependencies.
Run: python -m unittest discover -s dictionary_v024c -p 'test_*.py' -v
"""
import copy
import json
import unittest

from pathlib import Path
import build_enriched as exp
import apply_review as review


class DictionaryExpansionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = exp.base.load_json(exp.base.DRAFTS)
        cls.batch = exp.base.load_json(exp.BATCH)
        cls.registry = exp.base.load_json(exp.base.REGISTRY)
        cls.pool = exp.base.read_candidates(cls.registry)
        for raw, correct in exp.CANONICAL_SPELLINGS.items():
            cls.pool[correct] = cls.pool.pop(raw)

    def test_batch_is_clean_and_from_mit(self):
        verified = exp.validate_expansion(self.base, self.batch, self.pool)
        self.assertEqual(len(verified), 103)
        self.assertEqual(len({v["lemma"] for v in verified.values()}), 103)
        self.assertEqual(sum(bool(x["senses"][0]["hint"]) for x in verified.values()), 21)

    def test_combined_dictionary_has_no_auto_approvals(self):
        full, drafts, stats = exp.build()
        self.assertEqual(len(full), 2874)
        self.assertEqual(len(drafts), 311)
        self.assertEqual(stats["candidate_only"], 2563)
        self.assertEqual(stats["new_drafts"], 103)
        self.assertEqual(stats["total_hinted_lemmas"], 33)
        self.assertEqual(stats["approved"], 0)
        self.assertEqual(stats["release_status"], "BLOCKED_PENDING_INDEPENDENT_EDITORIAL_REVIEW")

    def test_plural_cases_remain_flagged(self):
        full, _, stats = exp.build()
        lookup = {e["lemma"]: e for e in full}
        for word in ["КУДРИ", "КОЗНИ", "ДАННЫЕ"]:
            with self.subTest(word=word):
                self.assertTrue(lookup[word]["review_flags"])
                self.assertTrue(lookup[word]["grammar"]["check_required"])

    def test_reject_unsupported_word(self):
        poisoned = copy.deepcopy(self.batch)
        poisoned["entries"][0]["lemma"] = "ФФФФФФФ"
        with self.assertRaises(AssertionError):
            exp.validate_expansion(self.base, poisoned, self.pool)

    def test_reject_answer_in_hint(self):
        poisoned = copy.deepcopy(self.batch)
        w = poisoned["entries"][0]["lemma"]
        poisoned["entries"][0]["senses"][0]["hint"] = {
            "kind": "synonym", "text": w.lower()
        }
        with self.assertRaises(AssertionError):
            exp.validate_expansion(self.base, poisoned, self.pool)

    def test_owner_added_hints_still_present(self):
        lookup = {e["lemma"]: e for e in self.base["entries"]}
        self.assertIn("компьютерных игр", lookup["АРКАДА"]["senses"][0]["hint"]["text"])
        self.assertIn("водки", lookup["АБСОЛЮТ"]["senses"][0]["hint"]["text"])

    def test_review_import_is_proposal_only(self):
        from hashlib import sha1

        def blob(raw):
            return sha1(b"blob " + str(len(raw)).encode() + b"\x00" + raw).hexdigest()

        before = exp.base.DRAFTS.read_bytes()
        batch = exp.BATCH.read_bytes()
        payload = {
            "schema_version": "0.24c.review.1",
            "seed_blob_sha": blob(before),
            "batch_blob_sha": blob(batch),
            "final_approval": False,
            "changes": [{
                "lemma": "ЗОНТ",
                "clue": "Складной предмет для защиты от дождя.",
                "hint": "",
                "hintType": "",
                "difficulty": "easy",
                "grammar": "singular_verified",
                "decision": "looks_good",
                "notes": "Owner suggested, NOT independently approved."
            }]
        }
        result = review.validate_export(payload, before, batch)
        self.assertEqual(result["change_count"], 1)
        edited = result["suggestions"][0]["proposed"]
        self.assertEqual(edited["editorial_status"], "draft")
        self.assertTrue(edited["grammar"]["check_required"])
        self.assertIsNone(edited["approved_by"])
        self.assertEqual(before, exp.base.DRAFTS.read_bytes())

    def test_review_rejects_stale_export(self):
        base = exp.base.DRAFTS.read_bytes()
        batch = exp.BATCH.read_bytes()
        payload = {
            "schema_version": "0.24c.review.1",
            "seed_blob_sha": "0" * 40,
            "batch_blob_sha": "0" * 40,
            "final_approval": False,
            "changes": []
        }
        with self.assertRaises(AssertionError):
            review.validate_export(payload, base, batch)


if __name__ == "__main__":
    unittest.main(verbosity=2)
