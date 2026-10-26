"""Acesso às APIs do Windows usando somente a biblioteca padrão do Python.

Nenhum módulo pywin32/pywinauto ou runtime MFC é necessário.
"""

import ctypes
import os


DWORD = ctypes.c_uint32
WORD = ctypes.c_uint16
LONG = ctypes.c_int32
BOOL = ctypes.c_int32
HWND = ctypes.c_void_p
ULONG_PTR = ctypes.c_size_t


class POINT(ctypes.Structure):
    _fields_ = [('x', LONG), ('y', LONG)]


class RECT(ctypes.Structure):
    _fields_ = [('left', LONG), ('top', LONG), ('right', LONG), ('bottom', LONG)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [('dx', LONG), ('dy', LONG), ('mouseData', DWORD), ('dwFlags', DWORD),
                ('time', DWORD), ('dwExtraInfo', ULONG_PTR)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [('wVk', WORD), ('wScan', WORD), ('dwFlags', DWORD),
                ('time', DWORD), ('dwExtraInfo', ULONG_PTR)]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [('uMsg', DWORD), ('wParamL', WORD), ('wParamH', WORD)]


class INPUTUNION(ctypes.Union):
    _fields_ = [('mi', MOUSEINPUT), ('ki', KEYBDINPUT), ('hi', HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ('data',)
    _fields_ = [('type', DWORD), ('data', INPUTUNION)]


def key_input(code, up=False, unicode=False):
    event = INPUT()
    event.type = 1  # INPUT_KEYBOARD
    event.ki = KEYBDINPUT(0 if unicode else code, code if unicode else 0,
                          (0x0004 if unicode else 0) | (0x0002 if up else 0), 0, 0)
    return event


class NativeWindows:
    def __init__(self):
        if os.name != 'nt':
            raise RuntimeError('A automação do Shop9 está disponível somente no Windows.')
        self.dll = ctypes.WinDLL('user32', use_last_error=True)
        self.callback_type = ctypes.WINFUNCTYPE(BOOL, HWND, ctypes.c_ssize_t)
        signatures = {
            'GetAsyncKeyState': ([ctypes.c_int], ctypes.c_int16),
            'GetCursorPos': ([ctypes.POINTER(POINT)], BOOL),
            'WindowFromPoint': ([POINT], HWND),
            'GetAncestor': ([HWND, ctypes.c_uint], HWND),
            'GetForegroundWindow': ([], HWND),
            'GetWindowThreadProcessId': ([HWND, ctypes.POINTER(DWORD)], DWORD),
            'GetWindowTextLengthW': ([HWND], ctypes.c_int),
            'GetWindowTextW': ([HWND, ctypes.c_wchar_p, ctypes.c_int], ctypes.c_int),
            'GetClassNameW': ([HWND, ctypes.c_wchar_p, ctypes.c_int], ctypes.c_int),
            'GetWindowRect': ([HWND, ctypes.POINTER(RECT)], BOOL),
            'EnumWindows': ([self.callback_type, ctypes.c_ssize_t], BOOL),
            'IsWindowVisible': ([HWND], BOOL),
            'IsIconic': ([HWND], BOOL),
            'ShowWindow': ([HWND, ctypes.c_int], BOOL),
            'SetForegroundWindow': ([HWND], BOOL),
            'SetCursorPos': ([ctypes.c_int, ctypes.c_int], BOOL),
            'SendInput': ([ctypes.c_uint, ctypes.POINTER(INPUT), ctypes.c_int], ctypes.c_uint),
        }
        for name, (arguments, result) in signatures.items():
            function = getattr(self.dll, name)
            function.argtypes, function.restype = arguments, result

    def pressed(self, key):
        return bool(self.dll.GetAsyncKeyState(key) & 0x8000)

    def cursor(self):
        point = POINT()
        if not self.dll.GetCursorPos(ctypes.byref(point)):
            raise ctypes.WinError(ctypes.get_last_error())
        return point.x, point.y

    def root_at(self, x, y):
        return self.dll.GetAncestor(self.dll.WindowFromPoint(POINT(x, y)), 2)

    def foreground(self):
        return self.dll.GetForegroundWindow()

    def pid(self, handle):
        value = DWORD()
        if not self.dll.GetWindowThreadProcessId(handle, ctypes.byref(value)):
            raise ctypes.WinError(ctypes.get_last_error())
        return value.value

    def title(self, handle):
        buffer = ctypes.create_unicode_buffer(self.dll.GetWindowTextLengthW(handle) + 1)
        self.dll.GetWindowTextW(handle, buffer, len(buffer))
        return buffer.value

    def window_class(self, handle):
        buffer = ctypes.create_unicode_buffer(256)
        if not self.dll.GetClassNameW(handle, buffer, len(buffer)):
            raise ctypes.WinError(ctypes.get_last_error())
        return buffer.value

    def rectangle(self, handle):
        rectangle = RECT()
        if not self.dll.GetWindowRect(handle, ctypes.byref(rectangle)):
            raise ctypes.WinError(ctypes.get_last_error())
        return rectangle.left, rectangle.top, rectangle.right, rectangle.bottom

    def windows(self):
        handles = []

        @self.callback_type
        def collect(handle, _):
            if self.dll.IsWindowVisible(handle):
                handles.append(handle)
            return True

        if not self.dll.EnumWindows(collect, 0):
            raise ctypes.WinError(ctypes.get_last_error())
        return handles

    def restore(self, handle):
        if self.dll.IsIconic(handle):
            self.dll.ShowWindow(handle, 9)  # SW_RESTORE

    def activate(self, handle):
        self.dll.SetForegroundWindow(handle)

    def send(self, events):
        if not events:
            return
        array = (INPUT * len(events))(*events)
        count = self.dll.SendInput(len(array), array, ctypes.sizeof(INPUT))
        if count != len(array):
            # Libera modificadores caso o Windows tenha aceitado só parte do lote.
            releases = (INPUT * 3)(*(key_input(key, up=True) for key in (0x10, 0x11, 0x12)))
            self.dll.SendInput(3, releases, ctypes.sizeof(INPUT))
            raise RuntimeError('O Windows bloqueou a simulação de entrada. '
                               'Execute o app e o Shop9 com o mesmo nível de permissão.')

    def click(self, x, y):
        if not self.dll.SetCursorPos(x, y):
            raise ctypes.WinError(ctypes.get_last_error())
        down, up = INPUT(), INPUT()
        down.type = up.type = 0  # INPUT_MOUSE
        down.mi.dwFlags, up.mi.dwFlags = 0x0002, 0x0004
        self.send([down, up])

    def select_all(self):
        self.send([key_input(0x11), key_input(0x41),
                   key_input(0x41, up=True), key_input(0x11, up=True)])

    def type_character(self, char):
        if char.isascii() and char.isdigit():
            # Teclas reais para compatibilidade com a máscara de data do Shop9.
            self.send([key_input(ord(char)), key_input(ord(char), up=True)])
            return
        encoded = char.encode('utf-16-le')
        events = []
        for index in range(0, len(encoded), 2):
            code = int.from_bytes(encoded[index:index + 2], 'little')
            events.extend([key_input(code, unicode=True), key_input(code, up=True, unicode=True)])
        self.send(events)

    def tab(self):
        self.send([key_input(0x09), key_input(0x09, up=True)])


def enable_dpi_awareness():
    """Chamar antes de criar a janela Tk para usar coordenadas consistentes."""
    if os.name != 'nt':
        return
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    try:
        function = user32.SetProcessDpiAwarenessContext
    except AttributeError:
        user32.SetProcessDPIAware()
    else:
        function.argtypes, function.restype = [ctypes.c_void_p], BOOL
        function(ctypes.c_void_p(-4))  # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
