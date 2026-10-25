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

    def test_newest_three_clues(self):
        expected = {
            "ВОРОБЕЙ": "С ним сравнивают слово, которое вылетело и уже не поймать.",
            "ЗОНТ": "Складная защита от дождя и палящего солнца.",
            "МОСТ": "Сооружение, позволяющее пересечь реку или ущелье.",
        }
        for word, definition in expected.items():
            entry = self.by_word[word]
            self.assertEqual(entry["senses"][0]["definition"], definition)
            self.assertLessEqual(len(definition), 70)
            self.assertEqual(entry["editorial_status"], "draft")

    def test_new_four_editorial_choices(self):
        from pathlib import Path
        import json
        overlay = json.loads(
            (Path(__file__).resolve().parent / "owner_clue_overrides_v024d.json")
            .read_text(encoding="utf-8")
        )
        expected = {
            "ВРЕМЯ": "Его тратят, теряют и даже убивают, но вернуть не могут.",
            "ГРЕБЕНЬ": "У петуха он красный, у волны — пенистый, у горы — скалистый.",
            "ПЕРО": "Им писали письма задолго до появления шариковой ручки.",
        }
        self.assertGreaterEqual(len(overlay["changes"]), 28)
        for word, clue in expected.items():
            with self.subTest(word=word):
                entry = self.by_word[word]
                self.assertEqual(entry["senses"][0]["definition"], clue)
                self.assertLessEqual(len(clue), 70)
                self.assertEqual(entry["editorial_status"], "draft")
        bridge = self.by_word["МОСТ"]
        options = [x["text"] for x in bridge["senses"][0]["clue_variants"]]
        self.assertEqual(len(options), 2)
        self.assertEqual(options[1], "В Петербурге его разводят вовсе не из-за ссоры.")
        self.assertEqual(bridge["senses"][0]["definition"], options[0])
        self.assertIn("верхний край горы", self.by_word["ГРЕБЕНЬ"]["senses"][0]["hint"]["text"])

    def test_rooster_pocket_tree_paired_definitions(self):
        expected = {
            "ПЕТУХ": [
                "Носит шпоры, но не всадник; гребень, но не модник.",
                "Его можно встретить в курятнике и «пустить» во время пения.",
            ],
            "КАРМАН": [
                "Его советуют держать шире, но обычно с иронией.",
                "Он бывает накладным, потайным и совершенно пустым.",
            ],
            "ДЕРЕВО": [
                "Его возраст определяют по годовым кольцам на стволе.",
                "Посадить его — одно из трёх дел по старой житейской мудрости.",
            ],
        }
        for word, definitions in expected.items():
            with self.subTest(word=word):
                entry = self.by_word[word]
                sense = entry["senses"][0]
                self.assertEqual(
                    [v["text"] for v in sense["clue_variants"]], definitions)
                self.assertEqual(sense["definition"], definitions[0])
                self.assertTrue(all(len(v) <= 70 for v in definitions))
                self.assertEqual(entry["editorial_status"], "draft")
        self.assertIn("Пословицы и поговорки",
                      self.by_word["ДЕРЕВО"]["topical_categories"])
        self.assertIn("древесину",
                      self.by_word["ДЕРЕВО"]["senses"][0]["hint"]["text"])

    def test_porridge_lamp_horse_owner_choices(self):
        expected = {
            "КАША": [
                "Блюдо из крупы, которое маслом не испортишь.",
                "Её можно заварить, даже не подходя к плите.",
                "Её приходится расхлёбывать после чужих неприятностей.",
            ],
            "ЛАМПА": ["В сказке об Аладдине в ней скрывался джинн."],
            "ЛОШАДЬ": [
                "Её имя носит единица мощности автомобильного двигателя."
            ],
        }
        for word, clues in expected.items():
            with self.subTest(word=word):
                entry = self.by_word[word]
                sense = entry["senses"][0]
                self.assertEqual([v["text"] for v in sense["clue_variants"]], clues)
                self.assertEqual(sense["definition"], clues[0])
                self.assertTrue(all(len(t) <= 70 for t in clues))
                self.assertEqual(entry["editorial_status"], "draft")
        self.assertIn("Пословицы и поговорки",
                      self.by_word["КАША"]["topical_categories"])
        self.assertIn("Сказки и фольклор",
                      self.by_word["ЛАМПА"]["topical_categories"])
        self.assertIn("беспорядок", self.by_word["КАША"]["senses"][0]["hint"]["text"])

    def test_kitchenware_raisin_pine_editorial_round(self):
        expected = {
            "КАСТРЮЛЯ": "Кухонная труженица с двумя ручками и крышкой вместо шляпы.",
            "ИЗЮМ": "Его уменьшительно-ласкательная форма — особенность, шарм, «фишка».",
            "СОСНА": "Её стройные стволы когда-то шли на мачты кораблей.",
        }
        for word, text in expected.items():
            with self.subTest(word=word):
                entry = self.by_word[word]
                sense = entry["senses"][0]
                self.assertEqual(sense["definition"], text)
                self.assertEqual(len(sense["clue_variants"]), 1)
                self.assertLessEqual(len(text), 70)
                self.assertEqual(entry["editorial_status"], "draft")
                self.assertTrue(entry["grammar"]["check_required"])
        self.assertIn("Общие знания",
                      self.by_word["ИЗЮМ"]["topical_categories"])

    def test_bucket_cloud_letter_selected_variants(self):
        expected = {
            "ВЕДРО": [
                "У него есть ручка, но писать оно не умеет.",
            ],
            "ТУЧА": [
                "У Лермонтова они — небесные «вечные странники».",
                "Она бывает грозовой, а над человеком может сгуститься.",
            ],
            "ПИСЬМО": [
                "Оно бывает заказным, любовным и электронным.",
            ],
        }
        for word, clues in expected.items():
            with self.subTest(word=word):
                entry = self.by_word[word]
                sense = entry["senses"][0]
                self.assertEqual([v["text"] for v in sense["clue_variants"]], clues)
                self.assertEqual(sense["definition"], clues[0])
                self.assertTrue(all(len(clue) <= 70 for clue in clues))
                self.assertEqual(entry["editorial_status"], "draft")
                self.assertIsNone(sense["hint"])
        self.assertIn("Литература и классика",
                      self.by_word["ТУЧА"]["topical_categories"])

    def test_giraffe_nut_island_owner_choices(self):
        expected = {
            "ЖИРАФ": [
                "У Гумилёва он «изысканный» и бродит у озера Чад.",
                "Его ближайший ныне живущий родственник — окапи.",
            ],
            "ОРЕХ": [
                "В сказке Андерсена его скорлупа была колыбелью Дюймовочки.",
                "Герой балета Чайковского был создан, чтобы их раскалывать.",
            ],
            "ОСТРОВ": [
                "У Жюля Верна — таинственный, у Стивенсона — сокровищ.",
                "Он бывает материковым, вулканическим и коралловым.",
            ],
        }
        for word, variants in expected.items():
            with self.subTest(word=word):
                entry = self.by_word[word]
                sense = entry["senses"][0]
                self.assertEqual([v["text"] for v in sense["clue_variants"]],
                                 variants)
                self.assertEqual(sense["definition"], variants[0])
                self.assertTrue(all(len(text) <= 70 for text in variants))
                self.assertEqual(entry["editorial_status"], "draft")
                self.assertIsNone(sense["hint"])
        self.assertIn("Литература и классика",
                      self.by_word["ОСТРОВ"]["topical_categories"])

    def test_no_publication_and_no_new_words(self):
        self.assertEqual(len(self.entries), 2874)
        self.assertEqual(len(self.drafts), 311)
        self.assertEqual(self.stats["approved"], 0)
        self.assertTrue(all(e["editorial_status"] != "approved" for e in self.entries))


if __name__ == "__main__":
    unittest.main()
