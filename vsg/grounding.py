"""OWLv2 localization of described objects and the stored crop (224 px, 50% context)."""
from __future__ import annotations

import torch
from PIL import Image


class Grounder:
    def __init__(self, ckpt="google/owlv2-base-patch16-ensemble", device="cuda", threshold=0.15):
        from transformers import Owlv2ForObjectDetection, Owlv2Processor
        self.model = Owlv2ForObjectDetection.from_pretrained(ckpt).to(device).eval()
        self.processor = Owlv2Processor.from_pretrained(ckpt)
        self.device, self.threshold = device, threshold

    @torch.no_grad()
    def __call__(self, img, labels):
        """Best box per label as ((x0, y0, x1, y1) normalized, score); labels without a box are absent."""
        if not labels:
            return {}
        W, H = img.size
        S = max(W, H)        # OWLv2 pads the image to a square
        x = self.processor(text=[[f"a photo of a {l}" for l in labels]], images=img, return_tensors="pt",
                           padding="max_length", truncation=True, max_length=16).to(self.device)
        r = self.processor.post_process_object_detection(self.model(**x), threshold=self.threshold,
                                                         target_sizes=torch.tensor([[S, S]], device=self.device))[0]
        best = {}
        for b, s, i in zip(r["boxes"].tolist(), r["scores"].tolist(), r["labels"].tolist()):
            if s > best.get(labels[i], (None, -1.0))[1]:
                x0, y0, x1, y1 = b
                best[labels[i]] = ((max(0, x0) / W, max(0, y0) / H, min(W, x1) / W, min(H, y1) / H), s)
        return best


def crop(img, box, context=0.5, size=224):
    """Square window of side (1 + 2*context) x the longer box side, centred on the box, longer side resized to size."""
    W, H = img.size
    x0, y0, x1, y1 = box[0] * W, box[1] * H, box[2] * W, box[3] * H
    side = max(x1 - x0, y1 - y0) * (1 + 2 * context)
    side = min(max(side, 0.25 * min(W, H)), max(W, H))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    a0, b0 = max(0, cx - side / 2), max(0, cy - side / 2)
    a1, b1 = min(W, a0 + side), min(H, b0 + side)
    c = img.crop((int(a0), int(b0), int(a1), int(b1)))
    s = size / max(c.size)
    return c.resize((max(1, int(c.size[0] * s)), max(1, int(c.size[1] * s))), Image.BICUBIC)
