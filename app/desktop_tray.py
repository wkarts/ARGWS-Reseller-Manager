import ctypes
from ctypes import wintypes as w

class Tray:
    """Ícone e menu nativos da área de notificação, sem processo de console."""
    def __init__(self, root, icon, callbacks, identity):
        self.root, self.callbacks = root, callbacks
        self.user = ctypes.WinDLL('user32', use_last_error=True)
        self.shell = ctypes.WinDLL('shell32', use_last_error=True)
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.kernel.GetModuleHandleW.restype = w.HMODULE
        self.user.DefWindowProcW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
        self.user.DefWindowProcW.restype = ctypes.c_ssize_t
        self.user.CreateWindowExW.argtypes = [w.DWORD, w.LPCWSTR, w.LPCWSTR, w.DWORD, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, w.HWND, w.HMENU, w.HINSTANCE, ctypes.c_void_p]
        self.user.CreateWindowExW.restype = w.HWND
        self.user.LoadImageW.argtypes = [w.HINSTANCE, w.LPCWSTR, w.UINT, ctypes.c_int, ctypes.c_int, w.UINT]
        self.user.LoadImageW.restype = w.HANDLE
        self.user.CreatePopupMenu.restype = w.HMENU
        self.user.AppendMenuW.argtypes = [w.HMENU, w.UINT, ctypes.c_size_t, w.LPCWSTR]
        self.user.TrackPopupMenu.argtypes = [w.HMENU, w.UINT, ctypes.c_int, ctypes.c_int, ctypes.c_int, w.HWND, ctypes.c_void_p]
        self.user.SetForegroundWindow.argtypes = [w.HWND]
        self.user.DestroyMenu.argtypes = [w.HMENU]
        self.user.DestroyWindow.argtypes = [w.HWND]
        self.user.DestroyIcon.argtypes = [w.HICON]
        self.user.PostMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
        self.user.PeekMessageW.argtypes = [ctypes.POINTER(w.MSG), w.HWND, w.UINT, w.UINT, w.UINT]
        self.user.DispatchMessageW.argtypes = [ctypes.POINTER(w.MSG)]
        self.user.DispatchMessageW.restype = ctypes.c_ssize_t
        self.user.RegisterWindowMessageW.argtypes = [w.LPCWSTR]
        self.taskbar_created = self.user.RegisterWindowMessageW('TaskbarCreated')
        self.proc_type = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, w.HWND, w.UINT, w.WPARAM, w.LPARAM)
        class WindowClass(ctypes.Structure):
            _fields_ = [('style', w.UINT), ('proc', self.proc_type), ('extra_class', ctypes.c_int), ('extra_window', ctypes.c_int), ('instance', w.HINSTANCE), ('icon', w.HICON), ('cursor', w.HANDLE), ('background', w.HBRUSH), ('menu', w.LPCWSTR), ('name', w.LPCWSTR)]
        class Notify(ctypes.Structure):
            _fields_ = [('size', w.DWORD), ('window', w.HWND), ('id', w.UINT), ('flags', w.UINT), ('message', w.UINT), ('icon', w.HICON), ('tip', w.WCHAR * 128), ('state', w.DWORD), ('mask', w.DWORD), ('info', w.WCHAR * 256), ('timeout', w.UINT), ('title', w.WCHAR * 64), ('infoflags', w.DWORD), ('guid', ctypes.c_byte * 16), ('balloon', w.HICON)]
        self.shell.Shell_NotifyIconW.argtypes = [w.DWORD, ctypes.POINTER(Notify)]
        self.proc = self.proc_type(self.handle)
        self.instance = self.kernel.GetModuleHandleW(None)
        self.class_name = 'ResellerManagerTray_' + identity
        wc = WindowClass(0, self.proc, 0, 0, self.instance, None, None, None, None, self.class_name)
        self.user.RegisterClassW.argtypes = [ctypes.POINTER(WindowClass)]
        if not self.user.RegisterClassW(ctypes.byref(wc)): raise ctypes.WinError(ctypes.get_last_error())
        self.window = self.user.CreateWindowExW(0, self.class_name, 'ResellerManager', 0, 0, 0, 0, 0, None, None, self.instance, None)
        if not self.window: raise ctypes.WinError(ctypes.get_last_error())
        self.icon = self.user.LoadImageW(None, str(icon), 1, 0, 0, 0x10 | 0x40)
        if not self.icon: raise ctypes.WinError(ctypes.get_last_error())
        self.data = Notify()
        self.data.size, self.data.window, self.data.id = ctypes.sizeof(Notify), self.window, 1
        self.data.flags, self.data.message, self.data.icon = 1 | 2 | 4, 0x8001, self.icon
        self.data.tip = 'ResellerManager - Administração'
        self.available = bool(self.shell.Shell_NotifyIconW(0, ctypes.byref(self.data)))
        self.closed = False
        self.root.after(100, self.pump)

    def handle(self, window, message, wp, lp):
        if message == self.taskbar_created and hasattr(self, 'data'):
            self.available = bool(self.shell.Shell_NotifyIconW(0, ctypes.byref(self.data)))
            return 0
        if message == 0x8002:
            self.root.after(0, self.callbacks[1][1]); return 0
        if message == 0x8001:
            if lp == 0x0203:
                self.root.after(0, self.callbacks[1][1])
            elif lp in (0x0205, 0x007B):
                menu = self.user.CreatePopupMenu()
                for key, (label, callback) in self.callbacks.items(): self.user.AppendMenuW(menu, 0, key, label)
                point = w.POINT(); self.user.GetCursorPos(ctypes.byref(point))
                self.user.SetForegroundWindow(window)
                selected = self.user.TrackPopupMenu(menu, 0x100 | 2, point.x, point.y, 0, window, None)
                self.user.DestroyMenu(menu)
                if selected in self.callbacks: self.root.after(0, self.callbacks[selected][1])
                self.user.PostMessageW(window, 0, 0, 0)
            return 0
        return self.user.DefWindowProcW(window, message, wp, lp)

    def notify(self, text):
        self.data.flags = 1 | 2 | 4 | 16
        self.data.title, self.data.info, self.data.infoflags = 'ResellerManager', text[:255], 1
        self.shell.Shell_NotifyIconW(1, ctypes.byref(self.data))
        self.data.flags = 1 | 2 | 4

    def pump(self):
        if self.closed: return
        message = w.MSG()
        while self.user.PeekMessageW(ctypes.byref(message), self.window, 0, 0, 1):
            self.user.TranslateMessage(ctypes.byref(message)); self.user.DispatchMessageW(ctypes.byref(message))
        self.root.after(100, self.pump)

    def close(self):
        self.closed = True
        self.shell.Shell_NotifyIconW(2, ctypes.byref(self.data))
        self.user.DestroyWindow(self.window)
        self.user.DestroyIcon(self.icon)

