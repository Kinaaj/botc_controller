import json
import os


class GameState:
    """
    Persists volume and the current evil-color index to a JSON file so they
    survive restarts.
    """

    def __init__(self, state_path, evil_colors, default_volume=0.5):
        if not evil_colors:
            raise ValueError("evil_colors must contain at least one color")

        self.state_path = state_path
        self.evil_colors = [tuple(c) for c in evil_colors]
        self._evil_color_index = 0
        self._volume = default_volume
        self._load()

    def _load(self):
        if not os.path.exists(self.state_path):
            return
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._evil_color_index = data.get("evil_color_index", self._evil_color_index) % len(self.evil_colors)
            self._volume = data.get("volume", self._volume)
        except (json.JSONDecodeError, OSError) as e:
            print(f"[State] Failed to load {self.state_path}: {e}")

    def _save(self):
        data = {"evil_color_index": self._evil_color_index, "volume": self._volume}
        try:
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except OSError as e:
            print(f"[State] Failed to save {self.state_path}: {e}")

    @property
    def evil_color(self):
        return self.evil_colors[self._evil_color_index]

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, level):
        self._volume = max(0.0, min(1.0, level))
        self._save()

    def next_evil_color(self):
        self._evil_color_index = (self._evil_color_index + 1) % len(self.evil_colors)
        self._save()
        return self.evil_color
