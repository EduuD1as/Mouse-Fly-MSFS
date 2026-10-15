import json
import os
from dataclasses import asdict, dataclass, fields

CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "MouseFlyMSFS")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")


@dataclass
class Settings:
    device_id: int = 1
    mode: str = "cursor"            # "cursor" (screen position) or "relative" (raw mouse deltas)
    sensitivity: float = 1.0
    deadzone: float = 0.02
    curve: float = 1.0              # 1 = linear, >1 = finer control near center
    invert_x: bool = False
    invert_y: bool = False
    auto_center: float = 0.0        # relative mode: return-to-center speed (0 = off)
    wheel_buttons: bool = True      # scroll up/down -> buttons 6/7
    wheel_axis: bool = False        # scroll -> Z axis (throttle)
    wheel_axis_step: float = 0.05
    block_clicks: bool = False      # swallow mouse buttons/scroll in Windows while active
    hotkey: str = "F8"
    start_active: bool = False
    always_on_top: bool = False

    @classmethod
    def load(cls):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            return cls()
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})

    def save(self):
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, indent=2)
        except OSError:
            pass
