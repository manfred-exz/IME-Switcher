import asyncio
import contextlib
import ctypes
import json
import logging
import os
import sys
import time
from ctypes import wintypes

import win32api
import win32con
import win32gui
import win32process
from infi.systray import SysTrayIcon

from ime_switcher.shortcut import parse_shortcut
from ime_status_detector import (
    get_ime_status, 
    switch_to_chinese_mode, 
    get_window_title,
)

logger_temp = logging.getLogger('ime_switcher')
logger_temp.info("Successfully imported ime_status_detector module")

IMC_GETOPENSTATUS = 0x0005
IMC_SETOPENSTATUS = 0x0006
user32 = ctypes.windll.user32
imm32 = ctypes.WinDLL('imm32', use_last_error=True)

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

root_dir = os.path.abspath(os.path.dirname(__file__))
config_path = os.path.join(root_dir, '../config.json')

if os.path.exists(config_path):
    with open(os.path.join(root_dir, '../config.json')) as f:
        config = json.load(f)
    logger.info(f'Loaded config from {config_path}')
    logger.info(f'Config: {config}')
else:
    config = {
        "temp_switch_interval": 2.0,
        "instant_switch_interval": 0.6,
        "secondary_keyboard_id": "00000804",
        "force_cn_mode": True,  # 添加自动切换开关
        "auto_switch_interval": 0.2,  # 自动切换检查间隔
        "hotkeys": {
            "toggle": "Ctrl+\\",
            "temp_toggle": "Ctrl+Shift+\\",
            "instant_toggle": "Ctrl+Alt+\\"
        }
    }

english_lang_id = '0409'
english_keyboard_id = f'0000{english_lang_id}'
secondary_keyboard_id = config['secondary_keyboard_id']
assert len(secondary_keyboard_id) == 8
secondary_lang_id = secondary_keyboard_id[4:8]


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


def on_toggle():
    hwnd = get_front_window()
    title = get_window_title(hwnd) or '[Unknown]'
    lang_id = get_window_langid(hwnd)
    if lang_id == secondary_lang_id:
        set_input_language_for_window(hwnd, english_keyboard_id)
        logger.info(f'{title}: toggled to ENGLISH')
    else:
        set_input_language_for_window(hwnd, secondary_keyboard_id)
        logger.info(f'{title}: toggled to secondary keyboard')


def on_switch_english():
    hwnd = get_front_window()
    title = get_window_title(hwnd) or '[Unknown]'
    set_input_language_for_window(hwnd, english_keyboard_id)
    logger.info(f'{title}: switched to ENGLISH')


def on_switch_secondary():
    hwnd = get_front_window()
    title = get_window_title(hwnd) or '[Unknown]'
    set_input_language_for_window(hwnd, secondary_keyboard_id)
    logger.info(f'{title}: switched to secondary keyboard')


last_key_press_time: float = None
is_during_temp_toggling = False


@contextlib.contextmanager
def during_temp_toggling():
    global is_during_temp_toggling
    try:
        is_during_temp_toggling = True
        yield
    finally:
        is_during_temp_toggling = False


async def on_temp_toggle(key_press_interval: float):
    if is_during_temp_toggling:
        return

    with during_temp_toggling():
        # for Chinese, there's a time to select the Chinese character
        is_switching_to_chinese = get_front_window_langid() == english_lang_id and secondary_lang_id == '0804'
        if is_switching_to_chinese:
            key_press_interval = max(key_press_interval, 2)

        await asyncio.sleep(0.2)
        on_toggle()

        logger.info(f'Switching back in when key is inactive for {key_press_interval}...')

        global last_key_press_time
        last_key_press_time = None
        while True:
            await asyncio.sleep(0.1)
            logger.debug('checking key activity...')
            if last_key_press_time and time.time() - last_key_press_time > key_press_interval:
                break
        on_toggle()


async def force_cn_monitor():
    """
    自动切换监控任务：当检测到Microsoft Pinyin输入法且为英文模式时，自动切换到中文模式
    """
    if not config.get('force_cn_mode', True):
        logger.info("Auto switch is disabled in config")
        return
    
    logger.info("Auto switch monitor started")
    interval = config.get('auto_switch_interval', 0.2)
    last_status = None
    
    try:
        while True:
            try:
                # 获取当前IME状态
                is_chinese, symbol_mode, lang_id, is_pinyin, hwnd = get_ime_status()
                
                # 检查是否需要自动切换
                if is_pinyin and not is_chinese:
                    current_status = (is_pinyin, is_chinese, hwnd)
                    
                    # 避免频繁切换，只在状态变化时执行
                    if current_status != last_status:
                        window_title = get_window_title(hwnd)
                        logger.info("Auto switch triggered: Microsoft Pinyin detected in English mode")
                        logger.info(f"Window: {window_title}")
                        
                        # 执行自动切换
                        success = switch_to_chinese_mode(hwnd)
                        if success:
                            logger.info("✅ Auto switched to Chinese mode successfully")
                        else:
                            logger.warning("❌ Auto switch failed")
                        
                        last_status = current_status
                
                # 如果状态变化但不需要切换，也更新last_status
                current_status = (is_pinyin, is_chinese, hwnd)
                if current_status != last_status:
                    last_status = current_status
                
            except Exception as e:
                logger.error(f"Error in auto switch monitor: {e}")
                await asyncio.sleep(interval * 2)  # 出错时等待更长时间
                continue
            
            await asyncio.sleep(interval)
            
    except asyncio.CancelledError:
        logger.info("Auto switch monitor cancelled")
        raise
    except Exception as e:
        logger.error(f"Auto switch monitor error: {e}")


class HotKeyTrigger:
    def __init__(self):
        self.force_cn = None
    
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
                on_toggle()
            elif hotkey_id == 2:
                asyncio.create_task(on_temp_toggle(key_press_interval=config['temp_switch_interval']))
            elif hotkey_id == 3:
                asyncio.create_task(on_temp_toggle(key_press_interval=config['instant_switch_interval']))
            elif hotkey_id == 4:
                on_switch_english()
            elif hotkey_id == 5:
                on_switch_secondary()
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    async def listen_hotkey(self):
        self.hwnd = self.create_window()

        # Register multiple global hotkeys
        hotkeys = [
            (1, 'toggle'),
            (2, 'temp_toggle'),
            (3, 'instant_toggle'),
            (4, 'english'),
            (5, 'secondary'),
        ]

        registered_hotkeys = []
        for id, target in hotkeys:
            hotkey = config['hotkeys'].get(target)
            if hotkey is None:
                continue

            modifiers, vk = parse_shortcut(hotkey)
            if vk is None:
                continue

            if self.register_hotkey(self.hwnd, id, modifiers, vk):
                logger.info(f"Global hotkey registered: ID {id}, hotkey {hotkey}, target {target}")
                registered_hotkeys.append(id)
            else:
                logger.info(f"Failed to register global hotkey: ID {id}, hotkey {hotkey}, target {target}")

        # Message loop
        while True:
            await asyncio.sleep(0.05)
            win32gui.PumpWaitingMessages()

    async def do_key_check(self):
        while True:
            for vk in range(256):
                if win32api.GetAsyncKeyState(vk) & 0x0001:  # Key was pressed since last call
                    logger.info(f'key pressed: {vk}')
                    global last_key_press_time
                    last_key_press_time = time.time()
                    break
            await asyncio.sleep(0.05)

    async def cleanup(self):
        """清理资源"""
        if self.force_cn and not self.force_cn.done():
            self.force_cn.cancel()
            try:
                await self.force_cn
            except asyncio.CancelledError:
                pass
            logger.info("Auto switch task cancelled")


def create_systray_menu():
    """创建系统托盘菜单"""
    menu_options = (
        ("Toggle Force CN Mode", None, toggle_force_cn_mode),
        ("Status", None, show_status),
    )
    return menu_options


def toggle_force_cn_mode(_):
    """切换自动切换功能"""
    global trigger
    current_state = config.get('force_cn_mode', True)
    config['force_cn_mode'] = not current_state
    
    if config['force_cn_mode']:
        logger.info("Auto switch enabled")
        # 重启自动切换任务
        if hasattr(trigger, 'auto_switch_task'):
            if trigger.force_cn is None or trigger.force_cn.done():
                trigger.force_cn = asyncio.create_task(force_cn_monitor())
    else:
        logger.info("Auto switch disabled")
        # 停止自动切换任务
        if hasattr(trigger, 'auto_switch_task') and trigger.force_cn:
            trigger.force_cn.cancel()


def show_status(_):
    """显示当前状态"""
    try:
        is_chinese, symbol_mode, lang_id, is_pinyin, hwnd = get_ime_status()
        window_title = get_window_title(hwnd)
        logger.info("Current Status:")
        logger.info(f"  Window: {window_title}")
        logger.info(f"  Language ID: 0x{lang_id:04x}")
        logger.info(f"  Microsoft Pinyin: {is_pinyin}")
        logger.info(f"  Chinese Mode: {is_chinese}")
        logger.info(f"  Symbol Mode: {symbol_mode}")
        logger.info(f"  Force CN Mode: {config.get('force_cn_mode', True)}")
    except Exception as e:
        logger.error(f"Error getting status: {e}")


if __name__ == '__main__':
    trigger = HotKeyTrigger()
    
    # 创建系统托盘
    menu_options = create_systray_menu()
    systray = SysTrayIcon("icon.ico", "IME Switcher", 
                          menu_options=menu_options,
                          on_quit=lambda _: os._exit(1))
    systray.start()
    
    # 启动异步任务
    loop = asyncio.get_event_loop()
    
    try:
        loop.create_task(trigger.do_key_check())
        loop.create_task(trigger.listen_hotkey())

        # 启动自动切换监控任务
        if config.get('force_cn_mode', True):
            trigger.force_cn = loop.create_task(force_cn_monitor())
            logger.info("Force CN monitor task started")
        
        logger.info("IME Switcher started")
        loop.run_forever()
        
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        # 清理资源
        loop.run_until_complete(trigger.cleanup())
        systray.shutdown()
        loop.close()
