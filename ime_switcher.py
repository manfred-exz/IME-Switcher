import asyncio
import ctypes
import logging
import os
import time
from ctypes import wintypes

import win32api
import win32con
import win32gui
import win32process
from infi.systray import SysTrayIcon

IMC_GETOPENSTATUS = 0x0005
IMC_SETOPENSTATUS = 0x0006
user32 = ctypes.windll.user32
imm32 = ctypes.WinDLL('imm32', use_last_error=True)
LANG_ID_CHINESE = '0804'
LANG_ID_ENGLISH = '0409'

user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int


def setup_logger():
    logger = logging.getLogger('ime_switcher')
    logger.setLevel(logging.DEBUG)

    # log_directory = os.path.join(get_executable_directory(), 'logs')
    # if not os.path.exists(log_directory):
    #     os.makedirs(log_directory)
    #
    # current_date = datetime.now().strftime('%Y-%m-%d')
    # log_file = os.path.join(log_directory, f'{current_date}.log')
    # file_handler = logging.FileHandler(log_file, encoding='utf-8')
    # file_handler.setLevel(logging.DEBUG)
    #
    # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)

    # logger.addHandler(file_handler)
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


def get_front_window():
    hwnd = win32gui.GetForegroundWindow()
    return win32gui.GetAncestor(hwnd, win32con.GA_ROOTOWNER)


def get_front_window_langid():
    hwnd = get_front_window()
    return get_window_langid(hwnd)


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
    hwnd = get_front_window()
    title = get_window_text(hwnd) or '[Unknown]'
    lang_id = get_window_langid(hwnd)
    if lang_id == LANG_ID_CHINESE:
        set_input_language_for_window(hwnd, f'0000{LANG_ID_ENGLISH}')
        logger.info(f'{title}: toggled to ENGLISH')
    else:
        set_input_language_for_window(hwnd, f'0000{LANG_ID_CHINESE}')
        logger.info(f'{title}: toggled to CHINESE')


def on_switch_english():
    hwnd = get_front_window()
    title = get_window_text(hwnd) or '[Unknown]'
    set_input_language_for_window(hwnd, f'0000{LANG_ID_ENGLISH}')
    logger.info(f'{title}: switched to ENGLISH')


def on_switch_chinese():
    hwnd = get_front_window()
    title = get_window_text(hwnd) or '[Unknown]'
    set_input_language_for_window(hwnd, f'0000{LANG_ID_CHINESE}')
    logger.info(f'{title}: switched to CHINESE')


last_key_press_time: float = None


async def on_temp_toggle_en_cn(key_press_interval: float):
    # for Chinese, there's a time to select the Chinese character
    if get_front_window_langid() == LANG_ID_ENGLISH:
        key_press_interval = max(key_press_interval, 2)

    await asyncio.sleep(0.1)
    on_toggle_en_cn()

    logger.info(f'Switching back in when key is inactive for {key_press_interval}...')

    global last_key_press_time
    last_key_press_time = None
    while True:
        await asyncio.sleep(0.1)
        logger.info('checking...')
        if last_key_press_time and time.time() - last_key_press_time > key_press_interval:
            break
    on_toggle_en_cn()


class HotKeyTrigger:
    # HOTKEY

    def register_hotkey(self, hwnd, id, modifiers, vk):
        prototype = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.c_int, ctypes.c_uint, ctypes.c_uint)
        paramflags = (1, "hWnd", 0), (1, "id", 0), (1, "fsModifiers", 0), (1, "vk", 0)
        RegisterHotKey = prototype(("RegisterHotKey", user32), paramflags)

        return RegisterHotKey(hWnd=hwnd, id=id, fsModifiers=modifiers, vk=vk)

    def unregister_hotkey(self, hwnd, id):
        prototype = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.c_int)
        paramflags = (1, "hWnd", 0), (1, "id", 0)
        UnregisterHotKey = prototype(("UnregisterHotKey", user32), paramflags)

        return UnregisterHotKey(hWnd=hwnd, id=id)

    def create_window(self):
        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = self.process_message
        wc.lpszClassName = "GlobalHotkeyWindow"
        hinst = win32gui.GetModuleHandle(None)
        wc.hInstance = hinst
        class_atom = win32gui.RegisterClass(wc)
        return win32gui.CreateWindow(class_atom, "Global Hotkey Window", 0, 0, 0, 0, 0, 0, 0, hinst, None)

    def process_message(self, hwnd, msg, wparam, lparam):
        if msg == win32con.WM_HOTKEY:
            hotkey_id = wparam
            if hotkey_id == 1:
                on_toggle_en_cn()
            elif hotkey_id == 2:
                asyncio.create_task(on_temp_toggle_en_cn(key_press_interval=2))
            elif hotkey_id == 3:
                asyncio.create_task(on_temp_toggle_en_cn(key_press_interval=0.3))
            elif hotkey_id == 4:
                on_switch_english()
            elif hotkey_id == 5:
                on_switch_chinese()
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    async def listen_hotkey(self):
        self.hwnd = self.create_window()

        VK_LBRACKET = 0xDB
        VK_RBRACKET = 0xDD
        VK_BACKSLASH = 0xDC

        # Register multiple global hotkeys
        hotkeys = [
            (1, win32con.MOD_CONTROL, VK_BACKSLASH),
            (2, win32con.MOD_CONTROL | win32con.MOD_SHIFT, VK_BACKSLASH),
            (3, win32con.MOD_CONTROL | win32con.MOD_ALT, VK_BACKSLASH),
            # (4, win32con.MOD_CONTROL | win32con.MOD_ALT, VK_LBRACKET),
            # (5, win32con.MOD_CONTROL | win32con.MOD_ALT, VK_RBRACKET),

            # Add more hotkeys here
        ]

        registered_hotkeys = []
        for id, modifiers, vk in hotkeys:
            if self.register_hotkey(self.hwnd, id, modifiers, vk):
                logger.info(f"Global hotkey registered: ID {id}")
                registered_hotkeys.append(id)
            else:
                logger.info(f"Failed to register global hotkey: ID {id}")

        # Message loop
        while True:
            await asyncio.sleep(0.05)
            win32gui.PumpWaitingMessages()

        # # Unregister all hotkeys when done
        # for id in registered_hotkeys:
        #     self.unregister_hotkey(hwnd, id)

    async def do_key_check(self):
        while True:
            for vk in range(256):
                if win32api.GetAsyncKeyState(vk) & 0x0001:  # Key was pressed since last call
                    logger.info('key pressed')
                    global last_key_press_time
                    last_key_press_time = time.time()
                    break
            await asyncio.sleep(0.05)


if __name__ == '__main__':
    trigger = HotKeyTrigger()
    systray = SysTrayIcon("icon.ico", "IME Switcher",
                          on_quit=lambda _: os._exit(1))
    systray.start()
    loop = asyncio.get_event_loop()
    loop.create_task(trigger.do_key_check())
    loop.create_task(trigger.listen_hotkey())
    loop.run_forever()
    systray.shutdown()
