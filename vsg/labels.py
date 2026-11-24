"""Synonym map kappa (Eq. 7): labels in the same class may be matched to the same node.

Labels that are not in the table form their own class.
"""
import re

_CLASSES = {
    "person": ["person", "people", "man", "men", "woman", "women", "boy", "girl", "child", "children", "kid", "kids",
               "adult", "individual", "spectator", "spectators", "other_person", "another_person", "giant"],
    "cup": ["cup", "mug", "glass", "tumbler"],
    "vehicle": ["car", "automobile", "vehicle", "truck", "van"],
    "building": ["building", "house", "store"],
    "tree": ["tree", "trees"],
    "ground": ["ground", "floor"],
    "chair": ["chair", "chairs"],
    "table": ["table"],
    "shelf": ["shelf", "shelves"],
    "dog": ["dog", "puppy"],
    "cat": ["cat", "kitten"],
    "plate": ["plate"],
    "bowl": ["bowl"],
    "bottle": ["bottle"],
    "bag": ["bag"],
}
_TABLE = {w: c for c, ws in _CLASSES.items() for w in ws}


def label_class(label):
    s = re.sub(r"^[\s\-_]+|[\s\-_]+$", "", str(label).strip().lower())
    if s in _TABLE:
        return _TABLE[s]
    if s.endswith("s") and s[:-1] in _TABLE:
        return _TABLE[s[:-1]]
    return s
