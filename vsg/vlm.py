"""Thin wrapper around a Hugging Face VLM: greedy generation on images + text, and token embeddings for phi."""
from __future__ import annotations

import numpy as np
import torch


class VLM:
    def __init__(self, ckpt, device="cuda", max_pixels=448 * 448, dtype=torch.bfloat16):
        from transformers import AutoModelForImageTextToText, AutoProcessor
        self.model = AutoModelForImageTextToText.from_pretrained(ckpt, torch_dtype=dtype).to(device).eval()
        self.processor = AutoProcessor.from_pretrained(ckpt, max_pixels=max_pixels)
        self.device = device

    def messages(self, turns):
        """turns: list of str or PIL images in order; each item becomes one content entry of a single user turn."""
        content = [{"type": "image", "image": x} if not isinstance(x, str) else {"type": "text", "text": x}
                   for x in turns]
        return [{"role": "user", "content": content}]

    def inputs(self, turns):
        return self.processor.apply_chat_template(self.messages(turns), tokenize=True, add_generation_prompt=True,
                                                  return_dict=True, return_tensors="pt").to(self.device)

    def count(self, turns):
        return int(self.inputs(turns)["input_ids"].shape[1])

    @torch.no_grad()
    def generate(self, turns, max_new_tokens=128):
        x = self.inputs(turns)
        out = self.model.generate(**x, max_new_tokens=max_new_tokens, do_sample=False)
        return self.processor.batch_decode(out[:, x["input_ids"].shape[1]:], skip_special_tokens=True)[0].strip()

    @torch.no_grad()
    def embed(self, text):
        """phi: mean of the model's input token embeddings for `text` (no special tokens)."""
        ids = self.processor.tokenizer(text, add_special_tokens=False, return_tensors="pt")["input_ids"].to(self.device)
        return self.model.get_input_embeddings()(ids)[0].float().mean(0).cpu().numpy().astype(np.float32)
