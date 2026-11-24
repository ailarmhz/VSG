"""Prompts used by the writer and the reader."""

SCENE_GRAPH = """As a scene graph analysis expert, please analyze the current video clip and generate a focused Scene Graph.
**Analysis Guidelines:**
- First, objectively describe what is actually present in the clip
- Never invent objects or relationships that are not actually visible
- Do NOT include duplicate triples with identical meaning
**Scene Graph**
- Format: [Subject, Relation, Object]
- Include: Objects, their spatial relationships (near, left_of, right_of, above, below, etc), and actions (holding, walking, running, hitting, etc)
Please only output the scene graph triplets in the following format:
Scene Graph:
    1. [person, holding, cup]
    2. [dog, running_towards, park]
    3. [car, parked_near, building]
..."""

SCENE_GRAPH_QUERY = SCENE_GRAPH.replace(
    "generate a focused Scene Graph.",
    "generate a focused Scene Graph that is most relevant to the user's query.\n\n**User Query:** \"{query}\"")

CAPTION = ("In one sentence of at most 20 words, say what happens in these frames: who or what is shown, what they do, "
           "and whether the scene or shot changes.")

DESCRIPTION = ("In one sentence of at most 20 words, describe the {label} in this image: its color, size, state, and "
               "position. If the {label} is not visible, say so.")

DESCRIPTION_PROACTIVE = ("In one sentence, describe the {label} in this image: its color, its size relative to its "
                         "surroundings, its state, and its position in the image. If the {label} is not visible, say so.")

MCQ = ("{memory}Question: {question}\nOptions:\n{options}\nRespond only with the letter corresponding to your chosen "
       "option (e.g., A, B, C). Do not include any additional text or explanation in your response.")

PROACTIVE = ("You are an advanced image question-answering AI assistant. You have been provided with images and a "
             "question related to the images. Your task is to carefully analyze the images and provide the answer to "
             "the question. You need to carefully confirm whether the images content meet the conditions of the "
             "question, and then output the correct content.\n\nQuestion: {question}\n\nThe answer is:\n")

TRIGGER = "{instruction} Is it the right time to output \"{output}\"?{memory} You can only answer yes or no."


def parse_scene_graph(text):
    """Triplets from the writer's numbered "[s, p, o]" lines."""
    out, on = [], False
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("Scene Graph"):
            on = True
            continue
        if line == "...":
            on = False
            continue
        if not on or not line:
            continue
        head, _, rest = line.partition(".")
        if head.isdigit():
            line = rest.strip()
        if line.startswith("[") and line.endswith("]"):
            parts = [" ".join(p.split()) for p in line[1:-1].split(",")][:3]
            if len(parts) == 3 and all(parts):
                out.append(tuple(parts))
    return out
