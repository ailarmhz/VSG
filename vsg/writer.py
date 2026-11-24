"""Reactive writer (Sec. 3.3): one question-agnostic pass over the stream.

Every `interval` seconds the writer reads the clip C_k of the last `clip_frames` frames (1 fps) and produces
scene-graph triplets G_k and a caption e_k from the clip, and up to `describe` object descriptions D_k from the
current frame. Each described object is localized with OWLv2 and its crop stored.
"""
from __future__ import annotations

import os

from . import prompts
from .grounding import crop
from .memory import Graph, Log


class Writer:
    def __init__(self, vlm, grounder, theta=0.55, clip_frames=5, describe=3, refresh_s=10.0):
        self.vlm, self.grounder = vlm, grounder
        self.theta, self.clip_frames, self.describe, self.refresh_s = theta, clip_frames, describe, refresh_s

    @staticmethod
    def interval_for(duration):
        # TODO: check against the interval schedule used for the benchmark runs.
        return 5.0 if duration <= 300 else 10.0

    def run(self, video, out_dir, until=None, interval=None):
        os.makedirs(out_dir, exist_ok=True)
        T = video.duration if until is None else until
        dt = interval or self.interval_for(video.duration)
        log = Log(out_dir, "w")
        log.add(e="start", video=video.path, interval=dt, t=0.0)
        graph = Graph(self.vlm.embed, self.theta)
        last_desc = {}
        t = dt
        while t <= T + 1e-6:
            secs = [s for s in range(int(t) - self.clip_frames + 1, int(t) + 1) if s >= 0]
            frames = [f for f in (video.frame(s) for s in secs) if f is not None]
            if not frames:
                t += dt
                continue
            triplets = prompts.parse_scene_graph(self.vlm.generate(frames + [prompts.SCENE_GRAPH], 256))
            caption = self.vlm.generate(frames + [prompts.CAPTION], 40)
            ids = graph.write(t, triplets, caption, clip_start=secs[0])
            touched = {nid: graph.nodes[nid].label for nid in dict.fromkeys(ids.values())}
            edges = [[e.subj, e.pred, e.obj, e.first] for e in graph.edges.values() if e.last == t]
            log.add(e="write", t=t, clip=[secs[0], secs[-1]], touched=touched, edges=edges, caption=caption)

            # descriptions: never described first, then the oldest description; at most one per refresh_s
            due = [n for n in touched if t - last_desc.get(n, -1e9) >= self.refresh_s]
            due.sort(key=lambda n: (n in last_desc, last_desc.get(n, -1e9), -graph.nodes[n].count))
            due = due[: self.describe]
            now = frames[-1]
            names = {n: touched[n].replace("_", " ") for n in due}
            boxes = self.grounder(now, sorted(set(names.values()))) if due else {}
            for n in due:
                text = self.vlm.generate([now, prompts.DESCRIPTION.format(label=names[n])], 40)
                log.add(e="desc", t=t, nid=n, label=touched[n], text=text)
                graph.nodes[n].descriptions.append((t, text))
                last_desc[n] = t
                if names[n] in boxes:
                    box, score = boxes[names[n]]
                    key = f"{n}_{int(t)}.jpg"
                    log.add_crop(key, crop(now, box))
                    log.add(e="crop", t=t, nid=n, key=key, box=list(box), score=float(score))
                    graph.nodes[n].crops.append((t, box, key))
            t += dt
        log.add(e="end", t=T, nodes=len(graph.nodes), edges=len(graph.edges), lines=len(graph.events))
        log.close()
        return graph
