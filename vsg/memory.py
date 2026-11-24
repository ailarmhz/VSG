"""The Visual-State Graph M_t = (V_t, E_t, L_t) and relational consolidation (Sec. 3.2-3.3).

Every update is appended to a log of timestamped records. `Memory.at(T)` rebuilds the state from the records with
t <= T, so a reader at time T can only see what was written before it.
"""
from __future__ import annotations

import io
import json
import zipfile
from dataclasses import dataclass, field

import numpy as np

from .labels import label_class


@dataclass
class Node:
    nid: str
    label: str                      # c_v
    first: float                    # t^f_v
    last: float                     # t^l_v
    context: np.ndarray             # running mean of relational contexts, r_v
    count: int = 1                  # merged observations
    descriptions: list = field(default_factory=list)   # D_v: [(t, text)]
    crops: list = field(default_factory=list)          # O_v: [(t, box, crop key)]


@dataclass
class Edge:
    subj: str
    pred: str
    obj: str
    first: float
    last: float
    count: int = 1


def cosine(a, b):
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return 0.0 if na == 0 or nb == 0 else float(a @ b / (na * nb))


class Graph:
    """Online graph state. `embed(text) -> vector` is phi in Eq. (6)."""

    def __init__(self, embed, theta=0.55):
        self.embed, self.theta = embed, theta
        self.nodes: dict[str, Node] = {}
        self.edges: dict[tuple, Edge] = {}
        self.events: list[tuple] = []          # L_t: [(t0, t, caption)]
        self._ids: dict[str, int] = {}

    def _new_id(self, cls):
        i = self._ids.get(cls, 0)
        self._ids[cls] = i + 1
        return f"{cls.replace(' ', '_')}_{i}"

    def resolve(self, label, r, t):
        """Eq. (7)-(9): match a mention with context r to a stored node of the same class, or create one."""
        cls = label_class(label)
        cands = [(cosine(n.context, r), n) for n in self.nodes.values() if label_class(n.label) == cls]
        if cands:
            sim, best = max(cands, key=lambda x: x[0])
            if sim > self.theta:
                best.context = (best.context * best.count + r) / (best.count + 1)
                best.count += 1
                best.last = t
                return best.nid
        nid = self._new_id(cls)
        self.nodes[nid] = Node(nid, label, t, t, r.copy())
        return nid

    def write(self, t, triplets, caption, clip_start=None):
        """One writer call: triplets G_k and caption e_k. Returns {label: node id} for the labels of this write."""
        triplets = list(dict.fromkeys((s.lower(), p.lower(), o.lower()) for s, p, o in triplets))
        phi = {tr: self.embed(" ".join(tr)) for tr in triplets}
        by_label = {}
        for tr in triplets:
            by_label.setdefault(tr[0], []).append(phi[tr])
            by_label.setdefault(tr[2], []).append(phi[tr])
        ids = {lab: self.resolve(lab, np.mean(v, axis=0), t) for lab, v in by_label.items()}   # Eq. (6)
        for s, p, o in triplets:
            key = (ids[s], p, ids[o])
            # TODO: predicate refinement for repeated subject-object pairs.
            if key in self.edges:
                self.edges[key].count += 1
                self.edges[key].last = t
            else:
                self.edges[key] = Edge(ids[s], p, ids[o], t, t)
        self.events.append((t if clip_start is None else clip_start, t, caption))
        return ids


class Log:
    """Append-only record of a write pass: events.jsonl plus a zip of crops."""

    def __init__(self, path, mode="r"):
        self.path = path
        if mode == "w":
            self.f = open(f"{path}/events.jsonl", "w")
            self.zip = zipfile.ZipFile(f"{path}/crops.zip", "w", compression=zipfile.ZIP_STORED)

    def add(self, **rec):
        self.f.write(json.dumps(rec) + "\n")

    def add_crop(self, key, img):
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        self.zip.writestr(key, buf.getvalue())

    def close(self):
        self.f.close()
        self.zip.close()


class Memory:
    """Read side: rebuild the memory at any time T from a write log."""

    def __init__(self, path):
        self.records = [json.loads(l) for l in open(f"{path}/events.jsonl") if l.strip()]
        self.zip_path = f"{path}/crops.zip"
        self._zip = None
        start = next((r for r in self.records if r["e"] == "start"), {})
        self.interval = start.get("interval", 10.0)

    def crop(self, key):
        from PIL import Image
        if self._zip is None:
            self._zip = zipfile.ZipFile(self.zip_path)
        return Image.open(io.BytesIO(self._zip.read(key))).convert("RGB")

    def at(self, T):
        nodes, events = {}, []
        for r in self.records:
            if r["e"] in ("start", "end") or r["t"] > T + 1e-6:
                continue
            if r["e"] == "write":
                for nid, lab in r["touched"].items():
                    n = nodes.setdefault(nid, {"nid": nid, "label": lab, "first": r["t"], "seen": [],
                                               "descriptions": [], "crops": []})
                    n["seen"].append(r["t"])
                events.append((r["clip"][0], r["t"], r["caption"]))
            elif r["e"] == "desc" and r["nid"] in nodes:
                nodes[r["nid"]]["descriptions"].append((r["t"], r["text"]))
            elif r["e"] == "crop" and r["nid"] in nodes:
                nodes[r["nid"]]["crops"].append((r["t"], r["key"]))
        return {"T": T, "nodes": nodes, "events": events}
