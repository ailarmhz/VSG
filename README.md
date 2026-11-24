# VSG: Visual-State Graph Memory for Streaming Video Understanding

[Project page](https://ailarmhz.github.io/VSG/) · Paper (soon)

VSG is a training-free memory for streaming video. A frozen VLM, the *writer*, describes the stream as it arrives and
builds a graph of persistent objects, their relations and a timestamped event log. Repeated mentions of an object
are merged into one node by comparing the relations they take part in. When a question arrives, a second frozen VLM,
the *reader*, receives the relevant object histories and event lines, object crops and recent frames within a fixed
token budget.

## Setup

```bash
pip install -r requirements.txt
```

Default models: Qwen3-VL-8B-Instruct (writer and reader), OWLv2 base-patch16-ensemble (localization) and the CLIP
ViT-L/14 text encoder (retrieval). Any Hugging Face VLM that supports `AutoModelForImageTextToText` can be used as the
reader.

## Usage

Write the memory once per video. The writer does not see any question.

```bash
python scripts/write_memory.py --video clip.mp4 --out memory/clip
```

Answer a multiple-choice question asked at time `T` (seconds):

```bash
python scripts/answer.py --video clip.mp4 --memory memory/clip --time 409 \
    --question "What tool did I use to tighten the screw?" \
    --options "A. screwdriver" "B. hammer" "C. pliers" "D. wrench"
```

The memory is stored as an append-only log (`events.jsonl`) and the object crops (`crops.zip`). `Memory.at(T)` rebuilds
the state from records written up to `T`, so one write pass serves every question on the video and every reader.

Proactive instructions use a separate memory per instruction (`vsg/proactive.py`): the writer runs every second with
the instruction in its prompt, and the reader answers yes or no each second until the first yes, which triggers the
response.

## Layout

```
vsg/
  memory.py      graph, relational consolidation (Eq. 6–9), write log, causal rebuild
  writer.py      reactive writer (Sec. 3.3)
  reader.py      retrieval and budgeted reading (Sec. 3.4)
  proactive.py   instruction-conditioned memory and trigger loop (Sec. 3.5)
  grounding.py   OWLv2 boxes and 224-px crops
  prompts.py     writer and reader prompts, triplet parser
  labels.py      synonym map for label classes
  vlm.py         Hugging Face VLM wrapper
  video.py       1 fps frame access
scripts/         command-line entry points
tests/           unit tests (CPU, stand-in models)
docs/            project page
```

## Tests

```bash
python -m pytest tests
```

## Citation

```bibtex
@inproceedings{vsg2027,
  title     = {Visual-State Graph Memory for Streaming Video Understanding},
  author    = {Anonymous},
  booktitle = {Under review},
  year      = {2027}
}
```
