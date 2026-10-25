#!/usr/bin/env python3
# coding: utf-8
"""Regression tests for the 3-word editorial round and short mobile clues.
Run: python -m unittest discover -s dictionary_v024c -p 'test_*.py' -v
"""
import unittest
import build_owner_review_v024d as review


class OwnerBatchEditorialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entries, cls.drafts, cls.stats = review.compile_editorial_view()
        cls.by_word = {e["lemma"]: e for e in cls.entries}

    def test_three_word_selections(self):
        expected = {
            "ЗАЯЦ": "В русской сказке лиса выгнала его из лубяной избушки.",
            "ЛУНА": "Естественный спутник Земли, влияющий на морские приливы и отливы.",
            "КНИГА": "Она бывает настольной, электронной и даже Красной.",
        }
        for word, clue in expected.items():
            with self.subTest(word=word):
                e = self.by_word[word]
                self.assertEqual(e["senses"][0]["definition"], clue)
                self.assertEqual(len(clue), len(e["senses"][0]["definition"]))
                self.assertLessEqual(len(clue), 70)
                self.assertEqual(e["editorial_status"], "draft")

    def test_owner_hint_is_not_lost(self):
        self.assertEqual(self.by_word["ЗАЯЦ"]["senses"][0]["hint"],
                         {"kind": "alternate_meaning", "text": "Безбилетник."})

    def test_categories_are_relevant(self):
        self.assertIn("Сказки и фольклор", self.by_word["ЗАЯЦ"]["topical_categories"])
        self.assertIn("Природа", self.by_word["ЛУНА"]["topical_categories"])
        self.assertIn("Дом и быт", self.by_word["КНИГА"]["topical_categories"])

    def test_existing_mirror_choices_still_work(self):
        sense = self.by_word["ЗЕРКАЛО"]["senses"][0]
        self.assertEqual(len(sense["clue_variants"]), 2)
        self.assertIn("Пушкина", sense["clue_variants"][1]["text"])
        self.assertEqual(sense["hint"]["text"], "Так называют гладкую поверхность воды.")

    def test_second_three_word_choices(self):
        expected = {
            "ЛИСА": "Хитрая плутовка из русских народных сказок.",
            "РАДУГА": "Разноцветная дуга в небе после дождя.",
            "ДОЖДЬ": "Атмосферные осадки из падающих капель воды.",
        }
        for word, definition in expected.items():
            with self.subTest(word=word):
                item = self.by_word[word]
                self.assertEqual(item["senses"][0]["definition"], definition)
                self.assertLessEqual(len(definition), 70)
                self.assertEqual(item["editorial_status"], "draft")

    def test_fox_hint_and_folklore_category(self):
        fox = self.by_word["ЛИСА"]
        self.assertIn("Сказки и фольклор", fox["topical_categories"])
        self.assertEqual(fox["senses"][0]["hint"]["text"],
                         "Так могут назвать очень хитрого человека.")

    def test_third_three_word_choices(self):
        expected = {
            "МОРОЗ": "От него краснеют щёки, а на окнах появляются узоры.",
            "МУЗЕЙ": "Место, где хранят и показывают предметы истории и искусства.",
            "ПИРОГ": "Выпечка с начинкой из ягод, мяса, рыбы или капусты.",
        }
        for word, definition in expected.items():
            with self.subTest(word=word):
                entry = self.by_word[word]
                self.assertEqual(entry["senses"][0]["definition"], definition)
                self.assertLessEqual(len(definition), 70)
                self.assertEqual(entry["editorial_status"], "draft")
                self.assertEqual(len(entry["senses"][0]["clue_variants"]), 1)

    def test_snow_sun_and_cat_paired_clues(self):
        examples = {
            "СНЕГ": [
                "Он укрывает землю белым одеялом и скрипит под ногами.",
                "У Пушкина он лежит „великолепными коврами“.",
            ],
            "СОЛНЦЕ": [
                "Звезда, вокруг которой вращается Земля.",
                "Его проглотил крокодил в сказке Корнея Чуковского.",
            ],
            "КОШКА": [
                "У Киплинга она гуляла сама по себе.",
                "В народе ей приписывают девять жизней.",
            ],
        }
        for word, texts in examples.items():
            with self.subTest(word=word):
                record = self.by_word[word]
                sense = record["senses"][0]
                self.assertEqual([x["text"] for x in sense["clue_variants"]], texts)
                self.assertEqual(sense["definition"], texts[0])
                self.assertTrue(all(len(v) <= 70 for v in texts))
                self.assertEqual(record["editorial_status"], "draft")
                self.assertIsNone(sense["hint"])
                self.assertIn("Литература и классика", record["topical_categories"])
        self.assertIn("Сказки и фольклор", self.by_word["КОШКА"]["topical_categories"])

    def test_wolf_painting_frog_owner_choices(self):
        choices = {
            "ВОЛК": [
                "Дикий хищник, близкий родственник собаки.",
                "В известной пословице его кормят ноги.",
            ],
            "КАРТИНА": [
                "Её можно повесить на стену или представить в воображении.",
            ],
            "ЛЯГУШКА": [
                "В сказке она нашла стрелу Ивана-царевича.",
            ],
        }
        for word, definitions in choices.items():
            with self.subTest(word=word):
                entry = self.by_word[word]
                sense = entry["senses"][0]
                self.assertEqual([v["text"] for v in sense["clue_variants"]], definitions)
                self.assertEqual(sense["definition"], definitions[0])
                self.assertTrue(all(len(text) <= 70 for text in definitions))
                self.assertEqual(entry["editorial_status"], "draft")
                self.assertTrue(entry["grammar"]["check_required"])
        self.assertIn("Пословицы и поговорки", self.by_word["ВОЛК"]["topical_categories"])
        self.assertIn("Сказки и фольклор", self.by_word["ЛЯГУШКА"]["topical_categories"])
        self.assertIn("общее состояние дел", self.by_word["КАРТИНА"]["senses"][0]["hint"]["text"])

    def test_no_publication_and_no_new_words(self):
        self.assertEqual(len(self.entries), 2874)
        self.assertEqual(len(self.drafts), 311)
        self.assertEqual(self.stats["approved"], 0)
        self.assertTrue(all(e["editorial_status"] != "approved" for e in self.entries))


if __name__ == "__main__":
    unittest.main()
