import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vsg.labels import label_class  # noqa: E402
from vsg.memory import Graph  # noqa: E402
from vsg.prompts import parse_scene_graph  # noqa: E402
from vsg.reader import select_events, select_frames, serialize, shown  # noqa: E402

WORDS = {}


def embed(text):
    """Bag of words: triplets that share words have positive cosine."""
    v = np.zeros(64, np.float32)
    for w in text.split():
        v[WORDS.setdefault(w, len(WORDS) % 64)] += 1
    return v


def test_shared_relations_merge():
    g = Graph(embed)
    g.write(10, [("person", "holding", "screwdriver"), ("screwdriver", "on", "workbench")], "c1")
    g.write(20, [("person", "holding", "screwdriver"), ("person", "using", "screwdriver")], "c2")
    sd = [n for n in g.nodes.values() if n.label == "screwdriver"]
    assert len(sd) == 1 and sd[0].count == 2 and sd[0].first == 10 and sd[0].last == 20


def test_different_context_creates_node():
    g = Graph(embed, theta=0.9)
    g.write(10, [("person", "holding", "screwdriver")], "c1")
    g.write(20, [("screwdriver", "lying", "drawer")], "c2")
    assert len([n for n in g.nodes.values() if n.label == "screwdriver"]) == 2


def test_classes():
    assert label_class("man") == label_class("person")
    assert label_class("belt") != label_class("championship belt")
    g = Graph(embed)
    g.write(10, [("man", "holding", "cup")], "c")
    g.write(20, [("person", "holding", "cup")], "c")
    assert sum(1 for n in g.nodes.values() if label_class(n.label) == "person") == 1


def test_edges_counted():
    g = Graph(embed)
    g.write(10, [("person", "holding", "cup")], "c")
    g.write(20, [("person", "holding", "cup")], "c")
    (e,) = g.edges.values()
    assert e.count == 2 and e.first == 10 and e.last == 20
    assert [x[2] for x in g.events] == ["c", "c"]


def test_parse():
    text = "Scene Graph:\n    1. [person, holding, cup]\n    2. [dog,running_towards, park]\n    3. [bad]\n..."
    assert parse_scene_graph(text) == [("person", "holding", "cup"), ("dog", "running_towards", "park")]


def test_reading_helpers():
    assert shown([(1, "a"), (2, "b"), (3, "c"), (4, "d")]) == [(1, "a"), (3, "c"), (4, "d")]
    st = {"events": [(i, i, f"line {i}") for i in range(70)]}
    psi = lambda xs: np.array([[1.0 if x.endswith(" 5") else 0.0] for x in xs])  # noqa: E731
    ev = select_events(st, np.array([1.0]), psi, max_lines=60)
    assert len(ev) == 60 and ev[-1][2] == "line 69" and ev == sorted(ev)
    node = {"label": "cup", "first": 10, "seen": [10, 40], "descriptions": [(10, "red"), (40, "on table")], "crops": []}
    secs, recent = select_frames(100, 10, 8, [node])
    assert recent == list(range(93, 101)) and 40 in secs and len(secs) == 9
    assert "cup (first seen 10s, last seen 40s): at 10s: red; at 40s: on table" in serialize([node], [], 10)
