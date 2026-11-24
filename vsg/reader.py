"""Reading under a fixed token budget (Sec. 3.4).

At question time T the memory text is selected first, then object crops, and the remaining budget goes to frames
(Eq. 11). The input is then counted with the reader's own tokenizer and frames are dropped until it fits.
"""
from __future__ import annotations

import numpy as np
import torch

from . import prompts


class ClipText:
    """psi in Eq. (10): CLIP ViT-L/14 text tower, L2-normalized, 77-token limit."""

    def __init__(self, ckpt="openai/clip-vit-large-patch14", device="cuda"):
        from transformers import CLIPModel, CLIPProcessor
        self.model = CLIPModel.from_pretrained(ckpt, torch_dtype=torch.float16).to(device).eval()
        self.processor = CLIPProcessor.from_pretrained(ckpt)
        self.device, self._cache = device, {}

    @torch.no_grad()
    def __call__(self, texts):
        new = [t for t in dict.fromkeys(texts) if t not in self._cache]
        for i in range(0, len(new), 128):
            x = self.processor(text=new[i:i + 128], return_tensors="pt", padding=True, truncation=True,
                               max_length=77).to(self.device)
            f = torch.nn.functional.normalize(self.model.get_text_features(**x).float(), dim=-1).cpu().numpy()
            self._cache.update(zip(new[i:i + 128], f))
        return np.stack([self._cache[t] for t in texts])


def shown(descriptions):
    """First description and the two latest."""
    return descriptions if len(descriptions) <= 3 else [descriptions[0]] + descriptions[-2:]


def select_nodes(state, qv, psi, k):
    nodes = [n for n in state["nodes"].values() if n["descriptions"]]
    if not nodes:
        return []
    keys = [n["label"].replace("_", " ") + ": " + n["descriptions"][-1][1] for n in nodes]
    return [nodes[i] for i in np.argsort(-(psi(keys) @ qv))[:k]]


def select_events(state, qv, psi, max_lines=60, latest=3):
    ev = state["events"]
    if len(ev) <= max_lines:
        return list(ev)
    sim = psi([c for _, _, c in ev]) @ qv
    keep = set(np.argsort(-sim)[: max_lines - latest].tolist()) | set(range(len(ev) - latest, len(ev)))
    return [ev[i] for i in sorted(keep)]


def serialize(nodes, events, interval):
    """sigma_T."""
    lines = []
    if nodes:
        lines.append("Objects (descriptions written when each was seen):")
        for n in nodes:
            lines.append(f"- {n['label'].replace('_', ' ')} (first seen {n['first']:.0f}s, last seen {n['seen'][-1]:.0f}s): "
                         + "; ".join(f"at {t:.0f}s: {d}" for t, d in shown(n["descriptions"])))
    if events:
        lines.append(f"Event log (one line per {interval:.0f}-second clip, in time order):")
        lines += [f"- {a:.0f}-{b:.0f}s: {c}" for a, b, c in events]
    return ("Memory of the video so far:\n" + "\n".join(lines) + "\n\n") if lines else ""


def select_frames(T, n_frames, window, nodes):
    # TODO: decide how slots are used when there are fewer key-frame candidates than free slots.
    """Up to `window` most recent seconds, then key frames at the times the retrieved nodes were last observed or
    described (<= T, at least 2 s apart), in node order."""
    T = int(T)
    W = min(window, n_frames)
    recent = list(range(max(0, T - W + 1), T + 1))
    chosen = set(recent)
    for n in nodes:
        for s in (int(n["seen"][-1]), int(n["descriptions"][-1][0])):
            if len(chosen) >= n_frames:
                break
            if s <= T and s not in chosen and all(abs(s - x) >= 2 for x in chosen):
                chosen.add(s)
    return sorted(chosen), recent


class Reader:
    def __init__(self, vlm, psi, budget=3510, k=8, n_crops=2, window=8, n_max=18, max_lines=60):
        self.vlm, self.psi = vlm, psi
        self.B, self.k, self.n_crops, self.W, self.n_max, self.max_lines = budget, k, n_crops, window, n_max, max_lines

    def turns(self, crops, frames, text):
        out = []
        for lab, t, img in crops:
            out += [f"Stored view of the {lab} at {t:.0f} seconds:", img]
        for s, img in frames:
            out += [f"<{s:.1f} seconds>", img]
        return out + [text]

    def context(self, memory, video, question, options, T):
        state = memory.at(T)
        qv = self.psi([question])[0]
        nodes = select_nodes(state, qv, self.psi, self.k)
        events = select_events(state, qv, self.psi, self.max_lines)
        sigma = serialize(nodes, events, memory.interval)
        crops = []
        for n in nodes:                                     # latest crop of the highest-ranked nodes that have one
            if len(crops) < self.n_crops and n["crops"]:
                t, key = n["crops"][-1]
                crops.append((n["label"].replace("_", " "), t, memory.crop(key)))

        opts = "\n".join(options)
        text = prompts.MCQ.format(memory=sigma, question=question, options=opts)
        # TODO: Eq. (11) counts the question |q| inside B; here the question prompt is outside the budget.
        prompt_only = self.vlm.count([prompts.MCQ.format(memory="", question=question, options=opts)])
        probe = video.frame(int(T))
        kappa_f = self.vlm.count([probe, ""]) - self.vlm.count([""]) if probe is not None else 195
        used = self.vlm.count(self.turns(crops, [], text)) - prompt_only     # memory text + crops
        n_f = max(1, min(self.n_max, (self.B - used) // kappa_f))            # Eq. (11)
        secs, recent = select_frames(T, n_f, self.W, nodes)

        frames = [(s, f) for s in secs if (f := video.frame(s)) is not None]
        drop = sorted(s for s, _ in frames if s not in recent) + sorted(s for s, _ in frames if s in recent)
        while True:                                          # verify with the reader's tokenizer (Eq. 12)
            turns = self.turns(crops, frames, text)
            spent = self.vlm.count(turns) - prompt_only
            if spent <= self.B or len(frames) <= 1:
                break
            gone = drop.pop(0)
            frames = [(s, f) for s, f in frames if s != gone]
        info = {"nodes": len(nodes), "lines": len(events), "crops": len(crops), "frames": [s for s, _ in frames],
                "budget_tokens": spent, "input_tokens": spent + prompt_only}
        return turns, info

    def answer(self, memory, video, question, options, T):
        turns, info = self.context(memory, video, question, options, T)
        return self.vlm.generate(turns, 128), info
