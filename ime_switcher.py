import ctypes
import logging
import os
import sys
import threading
import time
from ctypes import wintypes
from datetime import datetime

import win32api
import win32con
import win32gui
import win32process
from infi.systray import SysTrayIcon

IMC_GETOPENSTATUS = 0x0005
IMC_SETOPENSTATUS = 0x0006
user32 = ctypes.WinDLL('user32', use_last_error=True)
imm32 = ctypes.WinDLL('imm32', use_last_error=True)
LANG_ID_CHINESE = '0804'
LANG_ID_ENGLISH = '0409'

user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int


def get_executable_directory():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


def setup_logger():
    logger = logging.getLogger('ime_switcher')
    logger.setLevel(logging.DEBUG)

    log_directory = os.path.join(get_executable_directory(), 'logs')
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

    current_date = datetime.now().strftime('%Y-%m-%d')
    log_file = os.path.join(log_directory, f'{current_date}.log')
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


logger = setup_logger()


def get_window_text(hwnd):
    # 定义缓冲区大小
    length = user32.GetWindowTextLengthW(hwnd) + 1
    buf = ctypes.create_unicode_buffer(length)

    # 调用GetWindowTextW获取窗口标题
    user32.GetWindowTextW(hwnd, buf, length)

    return buf.value


def get_window_langid(hwnd):
    """
    Returns the LANGID of the currently active window.
    """
    thread_id = win32process.GetWindowThreadProcessId(hwnd)[0]
    hkl = user32.GetKeyboardLayout(thread_id)
    # Extract the LANGID from the HKL (keyboard layout handle)
    langid = format(hkl & 0x0000FFFF, '04x')
    return langid


def set_input_language_for_window(hwnd, keyboard_layout_id: str):
    """
    Set the input language for the currently active window.
    input_language should be a string representing the LANGID of the layout to load, e.g., '00000409' for English (US).
    """
    # thread_id = win32process.GetWindowThreadProcessId(hwnd)[0]
    # Load and activate the specified keyboard layout for the window's thread.
    locale_id = win32api.LoadKeyboardLayout(keyboard_layout_id, win32con.KLF_ACTIVATE)
    # Post a message to the window to change its input language.
    win32api.PostMessage(hwnd, win32con.WM_INPUTLANGCHANGEREQUEST, 0, locale_id)


def on_toggle_en_cn():
    hwnd = win32gui.GetForegroundWindow()
    hwnd = win32gui.GetAncestor(hwnd, win32con.GA_ROOTOWNER)
    title = get_window_text(hwnd) or '[Unknown]'
    lang_id = get_window_langid(hwnd)
    if lang_id == LANG_ID_CHINESE:
        set_input_language_for_window(hwnd, f'0000{LANG_ID_ENGLISH}')
        logger.info(f'{title}: toggled to ENGLISH')
    else:
        set_input_language_for_window(hwnd, f'0000{LANG_ID_CHINESE}')
        logger.info(f'{title}: toggled to CHINESE')


def on_switch_english():
    hwnd = win32gui.GetForegroundWindow()
    hwnd = win32gui.GetAncestor(hwnd, win32con.GA_ROOTOWNER)
    title = get_window_text(hwnd) or '[Unknown]'
    set_input_language_for_window(hwnd, f'0000{LANG_ID_ENGLISH}')
    logger.info(f'{title}: switched to ENGLISH')


def on_switch_chinese():
    hwnd = win32gui.GetForegroundWindow()
    hwnd = win32gui.GetAncestor(hwnd, win32con.GA_ROOTOWNER)
    title = get_window_text(hwnd) or '[Unknown]'
    set_input_language_for_window(hwnd, f'0000{LANG_ID_CHINESE}')
    logger.info(f'{title}: switched to CHINESE')


class HotkeyListener:
    def __init__(self):
        # Define virtual key codes
        VK_SHIFT = win32con.VK_SHIFT
        VK_CONTROL = win32con.VK_CONTROL
        VK_MENU = win32con.VK_MENU  # ALT key
        VK_BACKSLASH = 0xDC
        VK_COMMA = 0xBC
        VK_SLASH = 0xBF
        VK_LBRACKET = 0xDB
        VK_RBRACKET = 0xDD
        VK_F12 = win32con.VK_F12

        self.HOTKEYS = {
            (VK_CONTROL, VK_MENU, VK_LBRACKET): on_switch_english,
            (VK_CONTROL, VK_MENU, VK_RBRACKET): on_switch_chinese,
            (VK_CONTROL, VK_BACKSLASH): on_toggle_en_cn,
        }

    @classmethod
    def is_key_pressed(cls, vk_code):
        return win32api.GetAsyncKeyState(vk_code) & 0x8000 != 0

    def check_hotkey_combination(self):
        for combination, callback in self.HOTKEYS.items():
            if all(self.is_key_pressed(key) for key in combination):
                callback()
                # Wait for all keys in the combination to be released
                while any(self.is_key_pressed(key) for key in combination):
                    time.sleep(0.01)
                return True
        return False

    def hotkey_listener(self):
        while True:
            if self.check_hotkey_combination():
                time.sleep(0.1)  # Prevent multiple triggers
            time.sleep(0.01)  # Small sleep to reduce CPU usage

    def start_hotkey_listener(self):
        self.thread = threading.Thread(target=self.hotkey_listener, daemon=True)
        self.thread.start()

    def stop(self):
        self.thread.join()


if __name__ == '__main__':
    systray = SysTrayIcon("icon.ico", "IME Switcher",
                          on_quit=lambda _: None)
    systray.start()

    listener = HotkeyListener()
    listener.start_hotkey_listener()

    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    listener.stop()
