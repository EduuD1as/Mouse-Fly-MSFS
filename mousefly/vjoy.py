"""Minimal ctypes wrapper around vJoyInterface.dll.

The DLL is loaded from the vJoy installation folder so its version always
matches the installed driver (bundling a different version breaks feeding).
"""
import ctypes
import os
import sys
import winreg

AXIS_X = 0x30
AXIS_Y = 0x31
AXIS_Z = 0x32

STAT_OWN = 0
STAT_FREE = 1
STAT_BUSY = 2
STAT_MISS = 3
STAT_UNKN = 4

STATUS_TEXT = {
    STAT_OWN: "em uso por este app",
    STAT_FREE: "livre",
    STAT_BUSY: "ocupado por outro programa",
    STAT_MISS: "não configurado",
    STAT_UNKN: "estado desconhecido",
}


class VJoyError(RuntimeError):
    pass


def _candidate_dirs():
    arch = "x64" if sys.maxsize > 2**32 else "x86"
    dirs = []
    # vJoy writes its install location in the uninstall key.
    for key_path in (
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{8E31F76F-74C3-47F1-9550-E041EEDC5FBB}_is1",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\{8E31F76F-74C3-47F1-9550-E041EEDC5FBB}_is1",
    ):
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                location, _ = winreg.QueryValueEx(key, "InstallLocation")
                dirs.append(os.path.join(location, arch))
        except OSError:
            pass
    for base in (os.environ.get("ProgramFiles", r"C:\Program Files"),
                 os.environ.get("ProgramW6432", r"C:\Program Files")):
        dirs.append(os.path.join(base, "vJoy", arch))
    dirs.append(os.path.dirname(os.path.abspath(sys.argv[0])))
    return dirs


def load_dll():
    for folder in _candidate_dirs():
        path = os.path.join(folder, "vJoyInterface.dll")
        if os.path.isfile(path):
            return ctypes.CDLL(path)
    raise VJoyError("vJoyInterface.dll não encontrada. Instale o vJoy (https://github.com/BrunnerInnovation/vJoy/releases).")


class VJoyDevice:
    def __init__(self):
        self.dll = load_dll()
        d = self.dll
        d.vJoyEnabled.restype = ctypes.c_bool
        d.GetVJDStatus.argtypes = [ctypes.c_uint]
        d.GetVJDStatus.restype = ctypes.c_int
        d.AcquireVJD.argtypes = [ctypes.c_uint]
        d.AcquireVJD.restype = ctypes.c_bool
        d.RelinquishVJD.argtypes = [ctypes.c_uint]
        d.ResetVJD.argtypes = [ctypes.c_uint]
        d.ResetVJD.restype = ctypes.c_bool
        d.SetAxis.argtypes = [ctypes.c_long, ctypes.c_uint, ctypes.c_uint]
        d.SetAxis.restype = ctypes.c_bool
        d.SetBtn.argtypes = [ctypes.c_bool, ctypes.c_uint, ctypes.c_ubyte]
        d.SetBtn.restype = ctypes.c_bool
        d.GetVJDButtonNumber.argtypes = [ctypes.c_uint]
        d.GetVJDButtonNumber.restype = ctypes.c_int
        d.GetVJDAxisExist.argtypes = [ctypes.c_uint, ctypes.c_uint]
        d.GetVJDAxisExist.restype = ctypes.c_bool
        d.GetVJDAxisMax.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.POINTER(ctypes.c_long)]
        d.GetVJDAxisMax.restype = ctypes.c_bool
        d.GetVJDAxisMin.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.POINTER(ctypes.c_long)]
        d.GetVJDAxisMin.restype = ctypes.c_bool
        self.rid = None
        self.axis_range = {}

    def enabled(self):
        return bool(self.dll.vJoyEnabled())

    def status(self, rid):
        return self.dll.GetVJDStatus(rid)

    def acquire(self, rid):
        if not self.enabled():
            raise VJoyError("Driver vJoy desativado ou não instalado.")
        st = self.status(rid)
        if st == STAT_OWN:
            pass
        elif st == STAT_FREE:
            if not self.dll.AcquireVJD(rid):
                raise VJoyError(f"Falha ao adquirir o dispositivo vJoy {rid}.")
        else:
            raise VJoyError(f"Dispositivo vJoy {rid}: {STATUS_TEXT.get(st, st)}.")
        self.rid = rid
        self.axis_range = {}
        for axis in (AXIS_X, AXIS_Y, AXIS_Z):
            if self.dll.GetVJDAxisExist(rid, axis):
                lo, hi = ctypes.c_long(0), ctypes.c_long(0)
                self.dll.GetVJDAxisMin(rid, axis, ctypes.byref(lo))
                self.dll.GetVJDAxisMax(rid, axis, ctypes.byref(hi))
                if hi.value <= lo.value:
                    lo.value, hi.value = 0, 0x8000
                self.axis_range[axis] = (lo.value, hi.value)
        self.dll.ResetVJD(rid)

    def release(self):
        if self.rid is not None:
            self.dll.ResetVJD(self.rid)
            self.dll.RelinquishVJD(self.rid)
            self.rid = None

    def button_count(self):
        return self.dll.GetVJDButtonNumber(self.rid) if self.rid else 0

    def has_axis(self, axis):
        return axis in self.axis_range

    def set_axis(self, axis, value):
        """value in [-1, 1] (or [0, 1] for throttle-like use mapped by caller)."""
        if self.rid is None or axis not in self.axis_range:
            return
        lo, hi = self.axis_range[axis]
        raw = int(round(lo + (value + 1.0) * 0.5 * (hi - lo)))
        self.dll.SetAxis(raw, self.rid, axis)

    def set_button(self, number, pressed):
        if self.rid is None:
            return
        self.dll.SetBtn(bool(pressed), self.rid, number)
