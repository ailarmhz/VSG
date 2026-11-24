"""End-to-end run of writer and reader with stand-in models (no GPU)."""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test_memory import embed  # noqa: E402
from vsg.memory import Memory  # noqa: E402
from vsg.reader import Reader  # noqa: E402
from vsg.writer import Writer  # noqa: E402

IMG_TOK = 195


class FakeVLM:
    embed = staticmethod(embed)

    def generate(self, turns, max_new_tokens=128):
        text = turns[-1]
        if text.startswith("As a scene graph"):
            return "Scene Graph:\n 1. [person, holding, screwdriver]\n 2. [screwdriver, on, workbench]\n..."
        if text.startswith("In one sentence of at most 20 words, say"):
            return "A mechanic uses a screwdriver."
        if text.startswith("In one sentence"):
            return "Orange screwdriver on a metal bench."
        return "A"

    def count(self, turns):
        return sum(IMG_TOK if isinstance(x, Image.Image) else len(x.split()) for x in turns)


class FakeVideo:
    path, duration = "fake.mp4", 120.0

    def frame(self, s):
        return Image.new("RGB", (64, 36), (int(s) % 255, 0, 0))


def grounder(img, labels):
    return {l: ((0.1, 0.1, 0.5, 0.5), 0.4) for l in labels}


def test_write_then_read(tmp_path):
    g = Writer(FakeVLM(), grounder).run(FakeVideo(), str(tmp_path), until=100)
    assert len(g.events) == 20                      # interval 5 s for a 120 s video
    assert len([n for n in g.nodes.values() if n.label == "screwdriver"]) == 1
    mem = Memory(str(tmp_path))
    assert len(mem.at(50)["events"]) == 10          # causal rebuild
    reader = Reader(FakeVLM(), lambda xs: np.ones((len(xs), 4)), budget=3510)
    pred, info = reader.answer(mem, FakeVideo(), "Which tool?", ["A. screwdriver", "B. wrench"], 100)
    assert pred == "A"
    assert info["budget_tokens"] <= 3510 and max(info["frames"]) <= 100
    assert info["crops"] >= 1 and 1 <= len(info["frames"]) <= 18
