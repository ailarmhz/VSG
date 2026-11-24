"""Instruction-conditioned memory and the trigger loop (Sec. 3.5).

The writer runs every second on the current frame with the instruction in its prompt. At each second the reader
gets the most relevant nodes, recent relations, a short summary of relation changes, up to two crops and the recent
frames, and answers yes or no. The first yes triggers a second call that writes the response.
"""
from __future__ import annotations

import numpy as np

from . import prompts
from .grounding import crop
from .memory import Graph, cosine


class ProactiveVSG:
    def __init__(self, vlm, grounder, theta=0.55, k=4, n_relations=8, relation_window=10.0, n_crops=2, window=16,
                 describe=3, refresh_s=10.0, max_obs=3):
        self.vlm, self.grounder, self.theta = vlm, grounder, theta
        self.k, self.n_rel, self.rel_window, self.n_crops, self.W = k, n_relations, relation_window, n_crops, window
        self.describe, self.refresh_s, self.max_obs = describe, refresh_s, max_obs

    def _write(self, graph, t, img, instruction, qv, last_desc, crops):
        text = self.vlm.generate([img, prompts.SCENE_GRAPH_QUERY.format(query=instruction)], 256)
        triplets = prompts.parse_scene_graph(text)
        if not triplets:
            return set()
        before = {k: e.count for k, e in graph.edges.items()}
        ids = graph.write(t, triplets, caption="")
        touched = list(dict.fromkeys(ids.values()))
        due = [n for n in touched if t - last_desc.get(n, -1e9) >= self.refresh_s]
        due.sort(key=lambda n: -cosine(self.vlm.embed(graph.nodes[n].label.replace("_", " ")), qv))
        due = due[: self.describe]
        boxes = self.grounder(img, sorted({graph.nodes[n].label.replace("_", " ") for n in due})) if due else {}
        for n in due:
            lab = graph.nodes[n].label.replace("_", " ")
            graph.nodes[n].descriptions.append((t, self.vlm.generate([img, prompts.DESCRIPTION_PROACTIVE.format(label=lab)], 48)))
            last_desc[n] = t
            if lab in boxes:
                obs = crops.setdefault(n, [])
                obs.append((t, crop(img, boxes[lab][0])))
                if len(obs) > 1 + self.max_obs:             # first + latest max_obs
                    del obs[1]
        return {k for k, e in graph.edges.items() if e.count != before.get(k, 0)}

    def _memory(self, graph, t, qv, changed, crops):
        # TODO: node ranking with the writer input embeddings (Tab. S1); placeholder ranks by relational context.
        nodes = sorted(graph.nodes.values(), key=lambda n: -cosine(n.context, qv))[: self.k]
        ids = {n.nid for n in nodes}
        lab = {nid: n.label.replace("_", " ") for nid, n in graph.nodes.items()}
        lines = []
        for n in nodes:
            d = n.descriptions if len(n.descriptions) <= 3 else [n.descriptions[0]] + n.descriptions[-2:]
            lines.append(f"- {lab[n.nid]} (first seen {n.first:.0f}s, last seen {n.last:.0f}s)"
                         + ("".join(f"; at {a:.0f}s: {b}" for a, b in d)))
        rel = [e for e in graph.edges.values() if t - e.last <= self.rel_window and (e.subj in ids or e.obj in ids)]
        rel = sorted(rel, key=lambda e: -e.last)[: self.n_rel]
        if rel:
            lines.append("Recent relations: " + "; ".join(f"{lab[e.subj]} {e.pred} {lab[e.obj]}" for e in rel))
        new = [graph.edges[k] for k in changed if graph.edges[k].count == 1]
        rec = [graph.edges[k] for k in changed if graph.edges[k].count > 1]
        if new or rec:
            lines.append("Changes now: " + "; ".join([f"new: {lab[e.subj]} {e.pred} {lab[e.obj]}" for e in new]
                                                     + [f"again: {lab[e.subj]} {e.pred} {lab[e.obj]}" for e in rec]))
        images = []
        for n in nodes:
            if len(images) < self.n_crops and crops.get(n.nid):
                images.append(crops[n.nid][-1][1])
        return (" Memory:\n" + "\n".join(lines)) if lines else "", images

    def run(self, video, instruction, output, start, end):
        """Returns (time, response) at the first positive trigger in [start, end], else (None, None)."""
        graph = Graph(self.vlm.embed, self.theta)
        qv = self.vlm.embed(instruction)
        last_desc, crops = {}, {}
        for t in range(0, int(end) + 1):
            img = video.frame(t)
            if img is None:
                continue
            changed = self._write(graph, float(t), img, instruction, qv, last_desc, crops)
            if t < start:
                continue
            mem, images = self._memory(graph, t, qv, changed, crops)
            frames = [f for f in (video.frame(s) for s in range(max(0, t - self.W + 1), t + 1)) if f is not None]
            q = prompts.TRIGGER.format(instruction=instruction, output=output, memory=mem)
            if "yes" in self.vlm.generate(images + frames + [prompts.PROACTIVE.format(question=q)], 128).lower():
                return t, self.vlm.generate(images + frames + [prompts.PROACTIVE.format(question=instruction)], 128)
        return None, None
