#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dobrye Crosswords v0.21. Rotationally symmetric 11x11 templates + CSP fill.
Only generated layouts with known, reviewed clues should enter the game.
Python >=3.9; standard library only. Third-party lexicon is MIT; see data/.
"""
import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
N = 11
WHITE, BLACK = "□", "■"
ORBIT = [
    tuple(sorted({(r, c), (N - 1 - r, N - 1 - c)}))
    for r in range(N) for c in range(N)
    if (r, c) <= (N - 1 - r, N - 1 - c)
]


def inspect_grid(rows):
    """Return slot positions and intersections; reject invalid geometry."""
    if len(rows) != N or any(len(row) != N for row in rows):
        return None
    if any(ch not in (WHITE, BLACK) for row in rows for ch in row):
        return None
    if any(rows[r][c] != rows[N - 1 - r][N - 1 - c]
           for r in range(N) for c in range(N)):
        return None
    white = {(r, c) for r in range(N) for c in range(N) if rows[r][c] == WHITE}
    if not 47 <= len(white) <= 85:
        return None
    if any(all((r + dr, c + dc) in white
               for dr in range(2) for dc in range(2))
           for r in range(N-1) for c in range(N-1)):
        return None  # no joined 2x2 whitespace blocks

    slots = []
    by_cell = defaultdict(list)
    for direction in ("across", "down"):
        for lane in range(N):
            run = []
            for i in range(N+1):
                pos = (lane, i) if direction == "across" else (i, lane)
                if i < N and pos in white:
                    run.append(pos)
                else:
                    if len(run) in (2, 3):
                        return None  # minimum word length = 4
                    if len(run) >= 4:
                        if len(run) > 9:
                            return None  # matches permitted lexicon length
                        ix = len(slots)
                        slots.append((direction, run))
                        for cell in run:
                            by_cell[cell].append(ix)
                    run = []

    if not 17 <= len(slots) <= 25 or set(by_cell) != white:
        return None
    graph = [set() for _ in slots]
    edges = [[] for _ in slots]
    crossings = 0
    for cell, ids in by_cell.items():
        if len(ids) > 2:
            return None
        if len(ids) == 2:
            a, b = ids
            if slots[a][0] == slots[b][0]:
                return None
            pos_a, pos_b = slots[a][1].index(cell), slots[b][1].index(cell)
            edges[a].append((b, pos_a, pos_b))
            edges[b].append((a, pos_b, pos_a))
            graph[a].add(b)
            graph[b].add(a)
            crossings += 1
    if crossings < 17 or not all(graph):
        return None
    seen = {0}
    queue = [0]
    for node in queue:
        for neighbor in graph[node]:
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append(neighbor)
    if len(seen) != len(slots):
        return None
    return {"slots": slots, "edges": edges, "crossings": crossings,
            "white": len(white), "black": N*N-len(white)}


def flip_orbit(rows, which):
    out = [list(s) for s in rows]
    for r, c in ORBIT[which]:
        out[r][c] = WHITE if out[r][c] == BLACK else BLACK
    return tuple("".join(s) for s in out)


def generate_masks(base_rows, max_depth=3, max_masks=350, seed=20261021):
    """Grow a bank of genuine new legal masks by symmetric orbit flips."""
    rng = random.Random(seed)
    base = tuple(base_rows)
    if inspect_grid(base) is None:
        raise ValueError("The source template is invalid")
    found = {base: 0}
    frontier = [base]
    for depth in range(1, max_depth+1):
        expanded = []
        for rows in frontier:
            orbit_order = list(range(len(ORBIT)))
            rng.shuffle(orbit_order)
            for k in orbit_order:
                child = flip_orbit(rows, k)
                if child in found or inspect_grid(child) is None:
                    continue
                found[child] = depth
                expanded.append(child)
                if len(found) >= max_masks:
                    break
            if len(found) >= max_masks:
                break
        rng.shuffle(expanded)
        frontier = expanded[:250]
        if not frontier or len(found) >= max_masks:
            break
    return list(found.items())


def read_wordbank(path):
    """Raw noun candidates, not automatically approved crossword entries."""
    words = set()
    for raw in Path(path).read_text(encoding="utf-8-sig").splitlines():
        word = raw.strip().upper().replace("Ё", "Ё")
        if 4 <= len(word) <= 9 and all("А" <= ch <= "Я" or ch == "Ё" for ch in word):
            words.add(word)
    return sorted(words)


def make_indexes(words):
    groups = defaultdict(list)
    positions = {}
    for word in words:
        groups[len(word)].append(word)
    for length, ws in groups.items():
        positions[length] = [defaultdict(list) for _ in range(length)]
        for word in ws:
            for pos, char in enumerate(word):
                positions[length][pos][char].append(word)
    return groups, positions


def solve(mask_info, groups, indexes, rng, max_nodes=40000):
    """MRV backtracking with indexed crossing constraints and no duplicate words."""
    slots, edges = mask_info["slots"], mask_info["edges"]
    values = [None] * len(slots)
    used = set()
    nodes = 0

    def options(i):
        required = [(a, values[j][b]) for j, a, b in edges[i] if values[j]]
        length = len(slots[i][1])
        if not required:
            pool = groups.get(length, ())
        else:
            candidates = [indexes[length][p].get(letter, ())
                          for p, letter in required] if length in indexes else [[]]
            pool = min(candidates, key=len)
        return [word for word in pool
                if word not in used and
                all(word[p] == letter for p, letter in required)]

    def backtrack():
        nonlocal nodes
        nodes += 1
        if nodes > max_nodes:
            return False
        best, domain = None, None
        for i, value in enumerate(values):
            if value is not None:
                continue
            opts = options(i)
            if not opts:
                return False
            if domain is None or len(opts) < len(domain):
                best, domain = i, opts
                if len(opts) == 1:
                    break
        if best is None:
            return True
        rng.shuffle(domain)
        for word in domain:
            values[best] = word
            used.add(word)
            if backtrack():
                return True
            values[best] = None
            used.remove(word)
            if nodes > max_nodes:
                break
        return False

    return (list(values) if backtrack() else None), nodes


def assemble(rows, info, words, clues, identifier):
    """Build the app-friendly crossword data and attach only known definitions."""
    assert len(words) == len(info["slots"])
    starts = sorted({coords[0] for _, coords in info["slots"]})
    numbering = {cell: i+1 for i, cell in enumerate(starts)}
    filled, placements = {}, []
    if len(set(words)) != len(words):
        raise ValueError("Repeated crossword answer")
    for i, ((direction, coords), word) in enumerate(zip(info["slots"], words)):
        if len(coords) != len(word):
            raise ValueError("Answer length mismatch")
        for cell, letter in zip(coords, word):
            if cell in filled and filled[cell] != letter:
                raise ValueError("Conflicting crossing")
            filled[cell] = letter
        r, c = coords[0]
        placements.append({
            "id": f"{identifier}_w{i+1:02}", "word": word,
            "clue": clues.get(word, ""), "row": r, "col": c,
            "direction": direction, "number": numbering[coords[0]],
            "length": len(word)
        })
    if len(filled) != info["white"]:
        raise ValueError("Unfilled white cells")
    solution = ["".join(filled.get((r, c), BLACK) for c in range(N))
                for r in range(N)]
    missing = [w for w in words if w not in clues]
    return {
        "id": identifier, "size": N, "rows": N, "cols": N,
        "symmetry": "rot180", "pattern": list(rows), "solution": solution,
        "placements": placements, "placed_words": len(placements),
        "crossings": info["crossings"], "white_cells": info["white"],
        "black_cells": info["black"],
        "editorial_status": "ready_for_review" if not missing else "needs_clues",
        "missing_clues": missing,
        "publishable_without_review": False
    }


def reviewed_clues(examples_path):
    doc = json.loads(Path(examples_path).read_text(encoding="utf-8"))
    return {entry["word"]: entry["clue"]
            for puzzle in doc["examples"] for entry in puzzle["placements"]
            if entry.get("clue")}


def validate_ready_examples(examples_path):
    doc = json.loads(Path(examples_path).read_text(encoding="utf-8"))
    signatures = set()
    for p in doc["examples"]:
        info = inspect_grid(p["pattern"])
        assert info is not None, f"{p['id']}: bad pattern"
        assert "".join(p["pattern"]) not in signatures, "Duplicate pattern"
        signatures.add("".join(p["pattern"]))
        slots = info["slots"]
        assert len(slots) == len(p["placements"]) == p["placed_words"]
        assert info["crossings"] == p["crossings"]
        slots_by_id = {(d, tuple(cells)) for d, cells in slots}
        seen_words, filled = set(), {}
        for w in p["placements"]:
            assert w["word"] not in seen_words and w.get("clue"), f"{p['id']}: missing/duplicate clue"
            seen_words.add(w["word"])
            cells = [(w["row"] + (i if w["direction"] == "down" else 0),
                      w["col"] + (i if w["direction"] == "across" else 0))
                     for i in range(len(w["word"]))]
            assert (w["direction"], tuple(cells)) in slots_by_id
            for cell, letter in zip(cells, w["word"]):
                assert filled.get(cell, letter) == letter
                filled[cell] = letter
        reconstructed = ["".join(filled.get((r, c), BLACK) for c in range(N))
                         for r in range(N)]
        assert reconstructed == p["solution"]
        assert len(filled) == info["white"]
    return len(signatures)


def main():
    cli = argparse.ArgumentParser(description="Dobrye Crosswords v0.21 experimental mask-first generator")
    cli.add_argument("--count", type=int, default=5, help="Target number of auto-filled candidate puzzles")
    cli.add_argument("--seed", type=int, default=20261021)
    cli.add_argument("--attempts", type=int, default=100)
    cli.add_argument("--max-nodes", type=int, default=40000)
    cli.add_argument("--max-depth", type=int, default=3)
    cli.add_argument("--require-clues", action="store_true",
                     help="Only use words with already written clues; may yield zero puzzles")
    cli.add_argument("--verify", action="store_true", help="Validate all manually assembled examples")
    cli.add_argument("--output", default=str(HERE / "generated_candidates_v021.json"))
    args = cli.parse_args()

    examples = HERE / "examples.json"
    checked = validate_ready_examples(examples)
    print(f"Verified reviewed examples: {checked}")
    if args.verify:
        return
    base = json.loads(examples.read_text(encoding="utf-8"))["examples"][0]["pattern"]
    clues = reviewed_clues(examples)
    wordlist = HERE / "data" / "mit_russian_nouns.txt"
    vocabulary = read_wordbank(wordlist)
    if args.require_clues:
        vocabulary = [word for word in vocabulary if word in clues]
    groups, indexes = make_indexes(vocabulary)
    rng = random.Random(args.seed)
    masks = generate_masks(base, args.max_depth, seed=args.seed)
    rng.shuffle(masks)

    accepted, tries, nodes = [], 0, 0
    for rows, depth in masks:
        if tries >= args.attempts or len(accepted) >= args.count:
            break
        tries += 1
        info = inspect_grid(rows)
        words, visited = solve(info, groups, indexes, rng, args.max_nodes)
        nodes += visited
        if words is None:
            continue
        entry = assemble(rows, info, words, clues, f"v021_auto_{len(accepted)+1:03}")
        entry["mutation_depth"] = depth
        accepted.append(entry)
    output = {"version": "v0.21", "published": False,
              "note": "Experimental candidates; manual clue/lexical review REQUIRED before game release.",
              "metrics": {"masks_discovered": len(masks), "attempted": tries,
                          "filled": len(accepted), "visited_search_nodes": nodes,
                          "wordbank_size": len(vocabulary)},
              "puzzles": accepted}
    Path(args.output).write_text(json.dumps(output, ensure_ascii=False, indent=2)+"\n",
                                 encoding="utf-8")
    print(json.dumps(output["metrics"], ensure_ascii=False))
    print(f"Draft candidates written to: {args.output}")


if __name__ == "__main__":
    main()
