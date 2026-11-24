"""Answer a multiple-choice question at time T from a written memory.

  python scripts/answer.py --video clip.mp4 --memory memory/clip --time 409 \
      --question "What tool did I use to tighten the screw?" \
      --options "A. screwdriver" "B. hammer" "C. pliers" "D. wrench"
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vsg.memory import Memory  # noqa: E402
from vsg.reader import ClipText, Reader  # noqa: E402
from vsg.video import Video  # noqa: E402
from vsg.vlm import VLM  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--memory", required=True)
    ap.add_argument("--time", type=float, required=True)
    ap.add_argument("--question", required=True)
    ap.add_argument("--options", nargs="+", required=True)
    ap.add_argument("--reader", default="Qwen/Qwen3-VL-8B-Instruct")
    ap.add_argument("--budget", type=int, default=3510)
    a = ap.parse_args()
    reader = Reader(VLM(a.reader), ClipText(), budget=a.budget)
    pred, info = reader.answer(Memory(a.memory), Video(a.video), a.question, a.options, a.time)
    print(pred)
    print(json.dumps(info))


if __name__ == "__main__":
    main()
