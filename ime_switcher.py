import ctypes
from ctypes import wintypes

import win32api
import win32con
import win32gui
import win32process
from pynput import keyboard

from infi.systray import SysTrayIcon

IMC_GETOPENSTATUS = 0x0005
IMC_SETOPENSTATUS = 0x0006
user32 = ctypes.WinDLL('user32', use_last_error=True)
imm32 = ctypes.WinDLL('imm32', use_last_error=True)
LANG_ID_CHINESE = '0804'
LANG_ID_ENGLISH = '0409'

user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int


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


def auto_switch_foreground_window_ime():
    hwnd = win32gui.GetForegroundWindow()
    hwnd = win32gui.GetAncestor(hwnd, win32con.GA_ROOTOWNER)
    title = get_window_text(hwnd) or '[Unknown]'
    lang_id = get_window_langid(hwnd)
    if lang_id == LANG_ID_CHINESE:
        set_input_language_for_window(hwnd, f'0000{LANG_ID_ENGLISH}')
        print(f'{title}: switched to ENGLISH')
    else:
        set_input_language_for_window(hwnd, f'0000{LANG_ID_CHINESE}')
        print(f'{title}: switched to CHINESE')


def on_activate():
    auto_switch_foreground_window_ime()


hotkey = keyboard.HotKey(
    keyboard.HotKey.parse('<ctrl>+,'),
    on_activate
)

if __name__ == '__main__':
    systray = SysTrayIcon("icon.ico", "IME Switcher",
                          on_quit=lambda _: h.stop())
    systray.start()

    with keyboard.GlobalHotKeys({'<ctrl>+,': on_activate}) as h:
        h.join()
