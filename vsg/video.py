"""Frame access at 1 fps."""
from __future__ import annotations

from PIL import Image


class Video:
    def __init__(self, path):
        import cv2
        self.path = path
        cap = cv2.VideoCapture(path)
        self.fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / self.fps
        cap.release()
        self._cache = {}

    def frame(self, s):
        """RGB frame at second s; falls back to s-1, s-2 if the seek fails, else None."""
        import cv2
        for t in (s, s - 1, s - 2):
            if t < 0:
                break
            if t in self._cache:
                return self._cache[t]
            cap = cv2.VideoCapture(self.path)
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(t * self.fps))
            ok, fr = cap.read()
            cap.release()
            if ok:
                img = Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB))
                if len(self._cache) > 64:
                    self._cache.pop(next(iter(self._cache)))
                self._cache[t] = img
                return img
        return None
