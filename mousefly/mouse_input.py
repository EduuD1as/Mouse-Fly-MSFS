"""Mouse capture: Raw Input for movement deltas, low-level hook for buttons.

Both run on one background thread that owns a message-only window and a
message loop (required by WH_MOUSE_LL and WM_INPUT).
"""
import ctypes
import threading
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

WM_INPUT = 0x00FF
WM_QUIT = 0x0012
WM_LBUTTONDOWN, WM_LBUTTONUP = 0x0201, 0x0202
WM_RBUTTONDOWN, WM_RBUTTONUP = 0x0204, 0x0205
WM_MBUTTONDOWN, WM_MBUTTONUP = 0x0207, 0x0208
WM_MOUSEWHEEL = 0x020A
WM_XBUTTONDOWN, WM_XBUTTONUP = 0x020B, 0x020C
WH_MOUSE_LL = 14
HWND_MESSAGE = wintypes.HWND(-3)
RIDEV_INPUTSINK = 0x00000100
RID_INPUT = 0x10000003
RIM_TYPEMOUSE = 0
MOUSE_MOVE_ABSOLUTE = 0x01


class WNDCLASSW(ctypes.Structure):
    _fields_ = [("style", wintypes.UINT), ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int), ("hInstance", wintypes.HINSTANCE), ("hIcon", wintypes.HICON),
                ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HBRUSH),
                ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR)]


class RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [("usUsagePage", wintypes.USHORT), ("usUsage", wintypes.USHORT),
                ("dwFlags", wintypes.DWORD), ("hwndTarget", wintypes.HWND)]


class RAWINPUTHEADER(ctypes.Structure):
    _fields_ = [("dwType", wintypes.DWORD), ("dwSize", wintypes.DWORD),
                ("hDevice", wintypes.HANDLE), ("wParam", wintypes.WPARAM)]


class RAWMOUSE(ctypes.Structure):
    _fields_ = [("usFlags", wintypes.USHORT), ("_pad", wintypes.USHORT),
                ("usButtonFlags", wintypes.USHORT), ("usButtonData", ctypes.c_short),
                ("ulRawButtons", wintypes.ULONG), ("lLastX", wintypes.LONG), ("lLastY", wintypes.LONG),
                ("ulExtraInformation", wintypes.ULONG)]


class RAWINPUT(ctypes.Structure):
    _fields_ = [("header", RAWINPUTHEADER), ("mouse", RAWMOUSE)]


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("pt", wintypes.POINT), ("mouseData", wintypes.DWORD), ("flags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.restype = LRESULT
user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
user32.CallNextHookEx.restype = LRESULT
user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
user32.SetWindowsHookExW.restype = wintypes.HHOOK
user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
user32.RegisterClassW.restype = wintypes.ATOM
user32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
                                   ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                   wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID]
user32.CreateWindowExW.restype = wintypes.HWND
user32.DestroyWindow.argtypes = [wintypes.HWND]
user32.RegisterRawInputDevices.argtypes = [ctypes.POINTER(RAWINPUTDEVICE), wintypes.UINT, wintypes.UINT]
user32.GetRawInputData.argtypes = [wintypes.HANDLE, wintypes.UINT, wintypes.LPVOID,
                                   ctypes.POINTER(wintypes.UINT), wintypes.UINT]
user32.GetRawInputData.restype = wintypes.UINT
user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE

# Button names used across the app.
LEFT, RIGHT, MIDDLE, X1, X2 = "left", "right", "middle", "x1", "x2"


class MouseCapture:
    """Calls back into `handler` with:
        handler.on_move(dx, dy)                 raw relative motion
        handler.on_button(name, pressed) -> bool  return True to block the event in Windows
        handler.on_wheel(notches) -> bool          positive = scroll up
    Callbacks run on the capture thread and must be fast.
    """

    def __init__(self, handler):
        self.handler = handler
        self._thread = None
        self._thread_id = None
        self._ready = threading.Event()
        self.error = None

    def start(self):
        self._thread = threading.Thread(target=self._run, name="MouseCapture", daemon=True)
        self._thread.start()
        self._ready.wait(3)
        if self.error:
            raise RuntimeError(self.error)

    def stop(self):
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        if self._thread:
            self._thread.join(2)

    # -- thread body -------------------------------------------------------
    def _run(self):
        self._thread_id = kernel32.GetCurrentThreadId()
        hinst = kernel32.GetModuleHandleW(None)
        self._wndproc = WNDPROC(self._wnd_proc)
        self._hookproc = HOOKPROC(self._hook_proc)
        wc = WNDCLASSW()
        wc.lpfnWndProc = self._wndproc
        wc.hInstance = hinst
        wc.lpszClassName = "MouseFlyMSFSCapture"
        user32.RegisterClassW(ctypes.byref(wc))
        hwnd = user32.CreateWindowExW(0, wc.lpszClassName, "MouseFly", 0, 0, 0, 0, 0,
                                      HWND_MESSAGE, None, hinst, None)
        if not hwnd:
            self.error = f"CreateWindowEx falhou ({ctypes.get_last_error()})"
            self._ready.set()
            return
        rid = RAWINPUTDEVICE(0x01, 0x02, RIDEV_INPUTSINK, hwnd)
        if not user32.RegisterRawInputDevices(ctypes.byref(rid), 1, ctypes.sizeof(rid)):
            self.error = f"RegisterRawInputDevices falhou ({ctypes.get_last_error()})"
        hook = user32.SetWindowsHookExW(WH_MOUSE_LL, self._hookproc, hinst, 0)
        if not hook:
            self.error = f"SetWindowsHookEx falhou ({ctypes.get_last_error()})"
        self._ready.set()
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        if hook:
            user32.UnhookWindowsHookEx(hook)
        user32.DestroyWindow(hwnd)

    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == WM_INPUT:
            try:
                self._handle_raw(lparam)
            except Exception:
                pass
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _handle_raw(self, lparam):
        size = wintypes.UINT(0)
        hdr = ctypes.sizeof(RAWINPUTHEADER)
        user32.GetRawInputData(lparam, RID_INPUT, None, ctypes.byref(size), hdr)
        buf = ctypes.create_string_buffer(max(size.value, ctypes.sizeof(RAWINPUT)))
        if user32.GetRawInputData(lparam, RID_INPUT, buf, ctypes.byref(size), hdr) == 0xFFFFFFFF:
            return
        ri = RAWINPUT.from_buffer(buf)
        if ri.header.dwType != RIM_TYPEMOUSE:
            return
        m = ri.mouse
        if m.usFlags & MOUSE_MOVE_ABSOLUTE:
            return  # tablets / remote desktop: no meaningful relative data
        if m.lLastX or m.lLastY:
            self.handler.on_move(m.lLastX, m.lLastY)

    def _hook_proc(self, ncode, wparam, lparam):
        if ncode == 0:
            block = False
            try:
                info = MSLLHOOKSTRUCT.from_address(lparam)
                block = self._dispatch_hook(wparam, info)
            except Exception:
                block = False
            if block:
                return 1
        return user32.CallNextHookEx(None, ncode, wparam, lparam)

    def _dispatch_hook(self, wparam, info):
        h = self.handler
        if wparam == WM_LBUTTONDOWN:
            return h.on_button(LEFT, True)
        if wparam == WM_LBUTTONUP:
            return h.on_button(LEFT, False)
        if wparam == WM_RBUTTONDOWN:
            return h.on_button(RIGHT, True)
        if wparam == WM_RBUTTONUP:
            return h.on_button(RIGHT, False)
        if wparam == WM_MBUTTONDOWN:
            return h.on_button(MIDDLE, True)
        if wparam == WM_MBUTTONUP:
            return h.on_button(MIDDLE, False)
        if wparam in (WM_XBUTTONDOWN, WM_XBUTTONUP):
            which = (info.mouseData >> 16) & 0xFFFF
            name = X1 if which == 1 else X2
            return h.on_button(name, wparam == WM_XBUTTONDOWN)
        if wparam == WM_MOUSEWHEEL:
            delta = ctypes.c_short((info.mouseData >> 16) & 0xFFFF).value
            return h.on_wheel(delta / 120.0)
        return False
