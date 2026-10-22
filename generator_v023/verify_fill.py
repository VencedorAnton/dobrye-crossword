#!/usr/bin/env python3
# coding: utf-8
"""Read-only QA for v0.23b word-filled ornamental crossword drafts."""
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILLED = ROOT / "generator_v023" / "filled_ornaments_v023b.json"
GEOMETRY = ROOT / "ornament-scaling-v022.json"


def slots_for(mask):
    n = len(mask)
    slots = []
    for direction in ("across", "down"):
        for line in range(n):
            k = 0
            while k < n:
                def at(t):
                    return mask[line][t] if direction == "across" else mask[t][line]
                if at(k) == "■":
                    k += 1
                    continue
                stop = k
                while stop < n and at(stop) == "□":
                    stop += 1
                if stop - k >= 2:
                    cells = [(line, t) if direction == "across" else (t, line)
                             for t in range(k, stop)]
                    slots.append((direction, cells))
                k = stop
    return slots


def verify():
    docs = json.loads(FILLED.read_text(encoding="utf-8"))
    geos = json.loads(GEOMETRY.read_text(encoding="utf-8"))
    by_id = {x["id"]: x for x in geos["templates"]}
    puzzles = docs["puzzles"]
    assert len(puzzles) == len(by_id) == 9
    assert len({p["id"] for p in puzzles}) == len(puzzles)
    assert docs["release_status"] == "preview_only"
    total_clues = 0
    for puzzle in puzzles:
        name = puzzle["id"]
        template = by_id[name]
        mask, solved = puzzle["pattern"], puzzle["solution"]
        n = puzzle["size"]
        assert n in (11, 13, 15), name
        assert template["size"] == n and template["pattern"] == mask, name
        assert template["validation"]["passed"], name
        assert len(mask) == len(solved) == n, name
        assert all(len(row) == n for row in mask + solved), name
        assert puzzle["is_published"] is False, name
        for r in range(n):
            for c in range(n):
                ch = mask[r][c]
                assert ch in ("□", "■"), name
                # D4: vertical, horizontal, two diagonals
                assert ch == mask[n - 1 - r][c], name
                assert ch == mask[r][n - 1 - c], name
                assert ch == mask[c][r], name
                assert ch == mask[n - 1 - c][n - 1 - r], name
                if ch == "■":
                    assert solved[r][c] == "■", (name, r, c)
                else:
                    assert solved[r][c] in "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ", (name, r, c)
        slots = slots_for(mask)
        starts = sorted({cells[0] for _, cells in slots})
        numbers = {cell: i + 1 for i, cell in enumerate(starts)}
        placements = puzzle["placements"]
        assert len(slots) == len(placements) == puzzle["word_count"], name
        assert len({p["word"] for p in placements}) == len(placements), name
        coverage = defaultdict(int)
        for (direction, cells), p in zip(slots, placements):
            word = p["word"]
            assert p["direction"] == direction, (name, word)
            assert (p["row"], p["col"]) == cells[0], (name, word)
            assert p["number"] == numbers[cells[0]], (name, word)
            assert p["length"] == len(cells) == len(word), (name, word)
            assert len(word) >= {11: 4, 13: 5, 15: 6}[n], (name, word)
            assert p.get("clue", "").strip(), (name, word)
            actual = "".join(solved[r][c] for r, c in cells)
            assert actual == word, (name, word, actual)
            for cell in cells:
                coverage[cell] += 1
            total_clues += 1
        whites = {(r, c) for r in range(n) for c in range(n)
                  if mask[r][c] == "□"}
        assert set(coverage) == whites, name
        assert all(1 <= v <= 2 for v in coverage.values()), name
        assert sum(v == 2 for v in coverage.values()) == puzzle["crossings"], name
        print(f"PASS: {name:14} {n}x{n} · {len(placements)} слов · {len(whites)} клеток")
    # Неполная автоматическая проверка: список известных плюральных форм,
    # для остальных необходим редакторский разбор по значению.
    known_forbidden = {"ЛАДОНИ"}
    pending_review = {"КУДРИ", "КОЗНИ", "ДАННЫЕ"}
    allowed_plural_only = {"ЧАСЫ", "НОЖНИЦЫ", "ОБОИ", "ГУСЛИ"}
    all_answers = {item["word"] for puzzle in puzzles for item in puzzle["placements"]}
    assert not (all_answers & known_forbidden), "Non-singular nominative answers found"
    for puzzle in puzzles:
        for item in puzzle["placements"]:
            if item["word"] in pending_review:
                assert item.get("editorial_flag"), (puzzle["id"], item["word"])
    print("Singular QA: no known forbidden ЛАДОНИ; flagged for editorial review:",
          ", ".join(sorted(all_answers & pending_review)) or "none")
    print("Plural-only exceptions in current puzzles:",
          ", ".join(sorted(all_answers & allowed_plural_only)) or "none")
    assert total_clues == 216, total_clues
    print(f"PASS: {len(puzzles)}/9 сеток; {total_clues}/216 слов и определений.")
    print("NOTE: editor-approved word quality and definition accuracy are NOT verified.")


if __name__ == "__main__":
    try:
        verify()
    except (AssertionError, OSError, ValueError, KeyError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
