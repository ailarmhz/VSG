"""Write the question-agnostic memory of one video.

  python scripts/write_memory.py --video clip.mp4 --out memory/clip [--until 409]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vsg.grounding import Grounder  # noqa: E402
from vsg.video import Video  # noqa: E402
from vsg.vlm import VLM  # noqa: E402
from vsg.writer import Writer  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--writer", default="Qwen/Qwen3-VL-8B-Instruct")
    ap.add_argument("--detector", default="google/owlv2-base-patch16-ensemble")
    ap.add_argument("--until", type=float, default=None, help="stop writing at this time (s); default: end of video")
    ap.add_argument("--interval", type=float, default=None, help="write interval; default 5 s up to 300 s, else 10 s")
    ap.add_argument("--theta", type=float, default=0.55)
    a = ap.parse_args()
    video = Video(a.video)
    writer = Writer(VLM(a.writer), Grounder(a.detector), theta=a.theta)
    g = writer.run(video, a.out, until=a.until, interval=a.interval)
    print(f"{len(g.nodes)} nodes, {len(g.edges)} relations, {len(g.events)} event lines -> {a.out}")


if __name__ == "__main__":
    main()
