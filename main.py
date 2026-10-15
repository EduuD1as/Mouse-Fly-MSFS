import ctypes
import sys

# Physical pixel coordinates for cursor mode on scaled displays.
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

# Single instance: two feeders fighting over the same vJoy device makes no sense.
_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "MouseFlyMSFS_SingleInstance")
if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
    ctypes.windll.user32.MessageBoxW(None, "Mouse-Fly MSFS já está aberto.", "Mouse-Fly MSFS", 0x40)
    sys.exit(0)

from mousefly.gui import run  # noqa: E402

if __name__ == "__main__":
    run()
