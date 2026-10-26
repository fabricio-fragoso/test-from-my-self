import ctypes
import os
import threading
import unittest
from unittest.mock import Mock

from shop9 import WindowsDriver
from windows_native import INPUT, KEYBDINPUT, MOUSEINPUT, NativeWindows, key_input


class NativeInputTests(unittest.TestCase):
    def setUp(self):
        self.native = NativeWindows.__new__(NativeWindows)
        self.native.dll = Mock()
        self.batches = []

        def send(count, events, size):
            self.assertEqual(size, ctypes.sizeof(INPUT))
            self.batches.append([INPUT.from_buffer_copy(bytes(event)) for event in events])
            return count

        self.native.dll.SendInput.side_effect = send

    def test_windows_input_abi_uses_correct_sizes(self):
        is_64bit = ctypes.sizeof(ctypes.c_void_p) == 8
        self.assertEqual(ctypes.sizeof(INPUT), 40 if is_64bit else 28)
        self.assertEqual(ctypes.sizeof(KEYBDINPUT), 24 if is_64bit else 16)
        self.assertEqual(ctypes.sizeof(MOUSEINPUT), 32 if is_64bit else 24)
        self.assertEqual(INPUT.data.offset, 8 if is_64bit else 4)

    def test_digit_is_sent_as_real_key_down_and_up(self):
        self.native.type_character('7')
        down, up = self.batches[0]
        self.assertEqual((down.type, down.ki.wVk, down.ki.dwFlags), (1, 0x37, 0))
        self.assertEqual((up.ki.wVk, up.ki.dwFlags), (0x37, 2))

    def test_path_special_characters_are_literal_unicode(self):
        for char in '{}+%á':
            self.native.type_character(char)
            down, up = self.batches[-1]
            self.assertEqual((down.ki.wVk, down.ki.wScan, down.ki.dwFlags), (0, ord(char), 4))
            self.assertEqual((up.ki.wScan, up.ki.dwFlags), (ord(char), 6))

    def test_select_all_releases_control(self):
        self.native.select_all()
        self.assertEqual([(event.ki.wVk, event.ki.dwFlags) for event in self.batches[0]],
                         [(0x11, 0), (0x41, 0), (0x41, 2), (0x11, 2)])

    def test_click_moves_cursor_and_releases_mouse_button(self):
        self.native.click(-100, 200)
        self.native.dll.SetCursorPos.assert_called_once_with(-100, 200)
        self.assertEqual([(event.type, event.mi.dwFlags) for event in self.batches[0]], [(0, 2), (0, 4)])

    def test_blocked_input_releases_modifiers_and_reports_failure(self):
        self.native.dll.SendInput.side_effect = [0, 3]
        with self.assertRaisesRegex(RuntimeError, 'bloqueou'):
            self.native.send([key_input(0x41)])
        self.assertEqual(self.native.dll.SendInput.call_count, 2)


class DriverTests(unittest.TestCase):
    def driver(self):
        driver = WindowsDriver.__new__(WindowsDriver)
        driver.native = Mock()
        driver.native.pressed.return_value = False
        driver.stop = threading.Event()
        driver.pid = None
        driver.pause = Mock()
        return driver

    def test_click_uses_window_origin_and_recorded_offsets(self):
        driver = self.driver()
        driver.locate = Mock(return_value=123)
        driver.native.foreground.return_value = 123
        driver.native.rectangle.return_value = (-500, 100, 500, 800)
        driver.click({'x': 30, 'y': 40})
        driver.native.click.assert_called_once_with(-470, 140)

    def test_no_click_when_windows_refuses_focus(self):
        driver = self.driver()
        driver.locate = Mock(return_value=123)
        driver.native.foreground.return_value = 456
        with self.assertRaisesRegex(RuntimeError, 'ativar'):
            driver.click({'x': 30, 'y': 40})
        driver.native.click.assert_not_called()

    def test_typing_stops_if_focus_changes_mid_text(self):
        driver = self.driver()
        driver.click = Mock(return_value=123)
        driver.native.foreground.side_effect = [123, 123, 456]
        with self.assertRaisesRegex(RuntimeError, 'durante'):
            driver.fill({}, '01')
        driver.native.type_character.assert_called_once_with('0')
        driver.native.tab.assert_not_called()

    @unittest.skipUnless(os.name == 'nt', 'Requer Windows para consultar user32.dll')
    def test_native_library_loads_and_enumerates_windows(self):
        native = NativeWindows()
        self.assertIsInstance(native.windows(), list)


if __name__ == '__main__':
    unittest.main()
