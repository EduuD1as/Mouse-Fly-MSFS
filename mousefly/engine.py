"""Feeds vJoy from mouse state on a fixed-rate background loop."""
import ctypes
import math
import threading
import time
from ctypes import wintypes

from . import vjoy
from .mouse_input import LEFT, MIDDLE, RIGHT, X1, X2, MouseCapture

user32 = ctypes.windll.user32

BUTTON_MAP = {LEFT: 1, RIGHT: 2, MIDDLE: 3, X1: 4, X2: 5}
WHEEL_UP_BTN = 6
WHEEL_DOWN_BTN = 7

HOTKEYS = {**{f"F{i}": 0x6F + i for i in range(1, 13)},
           "Scroll Lock": 0x91, "Pause": 0x13, "Insert": 0x2D, "Home": 0x24}

TICK = 1 / 250
PULSE_ON = 0.05
PULSE_OFF = 0.03
RELATIVE_SCALE = 0.002   # raw counts -> axis fraction at sensitivity 1


class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]


user32.MonitorFromPoint.argtypes = [wintypes.POINT, wintypes.DWORD]
user32.MonitorFromPoint.restype = wintypes.HMONITOR
user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(MONITORINFO)]


def shape(v, deadzone, curve):
    a = abs(v)
    if a <= deadzone:
        return 0.0
    a = min(1.0, (a - deadzone) / (1.0 - deadzone))
    return math.copysign(a ** curve, v)


class WheelPulser:
    """Turns scroll notches into discrete button presses."""

    def __init__(self):
        self.pending = 0
        self.pressed = False
        self.until = 0.0

    def add(self, n):
        self.pending = min(self.pending + n, 10)

    def update(self, now):
        if now < self.until:
            return self.pressed
        if self.pressed:
            self.pressed = False
            self.until = now + PULSE_OFF
        elif self.pending > 0:
            self.pending -= 1
            self.pressed = True
            self.until = now + PULSE_ON
        return self.pressed

    def reset(self):
        self.pending, self.pressed, self.until = 0, False, 0.0


class Engine:
    def __init__(self, settings):
        self.s = settings
        self.lock = threading.Lock()
        self.vj = None
        self.capture = None
        self.active = False
        self.running = False
        self.status = "Iniciando..."
        self.error = None
        # live state (read by the GUI)
        self.x = 0.0
        self.y = 0.0
        self.z = 0.0          # throttle, 0..1
        self.buttons = {name: False for name in BUTTON_MAP}
        self.wheel_up = WheelPulser()
        self.wheel_down = WheelPulser()
        self._rel_x = 0.0
        self._rel_y = 0.0
        self._blocked = set()
        self._thread = None
        self._device_dirty = True
        self._last_sent = {}

    # -- lifecycle ---------------------------------------------------------
    def start(self):
        try:
            self.vj = vjoy.VJoyDevice()
        except vjoy.VJoyError as e:
            self.error = str(e)
            self.status = str(e)
        self.capture = MouseCapture(self)
        self.capture.start()
        self.running = True
        self._thread = threading.Thread(target=self._loop, name="VJoyFeeder", daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(1)
        if self.capture:
            self.capture.stop()
        if self.vj:
            self.vj.release()

    def change_device(self):
        self._device_dirty = True

    def set_active(self, value):
        with self.lock:
            if value == self.active:
                return
            self.active = value
            self._rel_x = self._rel_y = 0.0
            for k in self.buttons:
                self.buttons[k] = False
            self._blocked.clear()
            self.wheel_up.reset()
            self.wheel_down.reset()

    def toggle(self):
        self.set_active(not self.active)

    def recenter(self):
        with self.lock:
            self._rel_x = self._rel_y = 0.0

    # -- capture callbacks (capture thread) --------------------------------
    def on_move(self, dx, dy):
        if not self.active or self.s.mode != "relative":
            return
        k = RELATIVE_SCALE * self.s.sensitivity
        with self.lock:
            self._rel_x = max(-1.0, min(1.0, self._rel_x + dx * k))
            self._rel_y = max(-1.0, min(1.0, self._rel_y + dy * k))

    def on_button(self, name, pressed):
        if pressed:
            if not self.active:
                return False
            self.buttons[name] = True
            if self.s.block_clicks:
                self._blocked.add(name)
                return True
            return False
        # release: always clear, block only if the press was blocked
        self.buttons[name] = False
        if name in self._blocked:
            self._blocked.discard(name)
            return True
        return False

    def on_wheel(self, notches):
        if not self.active:
            return False
        steps = max(1, round(abs(notches)))
        with self.lock:
            if self.s.wheel_buttons:
                (self.wheel_up if notches > 0 else self.wheel_down).add(steps)
            if self.s.wheel_axis:
                self.z = max(0.0, min(1.0, self.z + math.copysign(self.s.wheel_axis_step * steps, notches)))
        return self.s.block_clicks

    # -- feeder loop -------------------------------------------------------
    def _open_device(self):
        self._device_dirty = False
        self._last_sent = {}
        if not self.vj:
            return
        self.vj.release()
        try:
            self.vj.acquire(self.s.device_id)
        except vjoy.VJoyError as e:
            self.error = str(e)
            self.status = str(e)
            return
        self.error = None
        missing = [n for n, a in (("X", vjoy.AXIS_X), ("Y", vjoy.AXIS_Y)) if not self.vj.has_axis(a)]
        nbtn = self.vj.button_count()
        warn = []
        if missing:
            warn.append("eixo(s) " + "/".join(missing) + " desativado(s)")
        if nbtn < 7:
            warn.append(f"apenas {nbtn} botões (precisa 7)")
        if self.s.wheel_axis and not self.vj.has_axis(vjoy.AXIS_Z):
            warn.append("eixo Z desativado")
        self.status = f"vJoy #{self.s.device_id} conectado" + (" — atenção: " + ", ".join(warn) +
                                                              ". Ajuste em 'Configure vJoy'." if warn else "")

    def _cursor_axes(self):
        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(mi)
        user32.GetMonitorInfoW(user32.MonitorFromPoint(pt, 2), ctypes.byref(mi))
        r = mi.rcMonitor
        hw = max(1, (r.right - r.left) / 2)
        hh = max(1, (r.bottom - r.top) / 2)
        nx = (pt.x - (r.left + hw)) / hw * self.s.sensitivity
        ny = (pt.y - (r.top + hh)) / hh * self.s.sensitivity
        return max(-1.0, min(1.0, nx)), max(-1.0, min(1.0, ny))

    def _send(self, key, value, fn):
        if self._last_sent.get(key) != value:
            self._last_sent[key] = value
            fn(value)

    def _loop(self):
        winmm = ctypes.windll.winmm
        winmm.timeBeginPeriod(1)
        hotkey_down = False
        last = time.perf_counter()
        try:
            while self.running:
                now = time.perf_counter()
                dt = now - last
                last = now

                vk = HOTKEYS.get(self.s.hotkey)
                if vk:
                    down = bool(user32.GetAsyncKeyState(vk) & 0x8000)
                    if down and not hotkey_down:
                        self.toggle()
                    hotkey_down = down

                if self._device_dirty:
                    self._open_device()

                with self.lock:
                    if not self.active:
                        x = y = 0.0
                    elif self.s.mode == "cursor":
                        x, y = self._cursor_axes()
                    else:
                        if self.s.auto_center > 0:
                            decay = math.exp(-self.s.auto_center * 3.0 * dt)
                            self._rel_x *= decay
                            self._rel_y *= decay
                        x, y = self._rel_x, self._rel_y
                    x = shape(x, self.s.deadzone, self.s.curve)
                    y = shape(y, self.s.deadzone, self.s.curve)
                    if self.s.invert_x:
                        x = -x
                    if self.s.invert_y:
                        y = -y
                    self.x, self.y = x, y
                    z = self.z
                    up = self.wheel_up.update(now)
                    dn = self.wheel_down.update(now)
                    btns = dict(self.buttons)

                vj = self.vj
                if vj and vj.rid is not None:
                    self._send("x", round(x, 4), lambda v: vj.set_axis(vjoy.AXIS_X, v))
                    self._send("y", round(y, 4), lambda v: vj.set_axis(vjoy.AXIS_Y, v))
                    if self.s.wheel_axis:
                        self._send("z", round(z, 4), lambda v: vj.set_axis(vjoy.AXIS_Z, v * 2 - 1))
                    for name, num in BUTTON_MAP.items():
                        self._send(f"b{num}", btns[name], lambda v, n=num: vj.set_button(n, v))
                    self._send("b6", up, lambda v: vj.set_button(WHEEL_UP_BTN, v))
                    self._send("b7", dn, lambda v: vj.set_button(WHEEL_DOWN_BTN, v))

                time.sleep(max(0.0, TICK - (time.perf_counter() - now)))
        finally:
            winmm.timeEndPeriod(1)
