# -*- coding: utf-8 -*-

import ctypes
import ctypes.wintypes
import time

# --- 定义 Windows API 函数原型 ---
# 使用 ctypes.WinDLL 比 windll 更适合多线程环境
user32 = ctypes.WinDLL('user32', use_last_error=True)
imm32 = ctypes.WinDLL('imm32', use_last_error=True)
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

# 定义函数参数和返回类型
user32.GetForegroundWindow.restype = ctypes.wintypes.HWND
user32.GetWindowThreadProcessId.restype = ctypes.wintypes.DWORD
user32.GetKeyboardLayout.argtypes = [ctypes.wintypes.DWORD]
user32.GetKeyboardLayout.restype = ctypes.wintypes.HKL
imm32.ImmGetDefaultIMEWnd.argtypes = [ctypes.wintypes.HWND]
imm32.ImmGetDefaultIMEWnd.restype = ctypes.wintypes.HWND
user32.SendMessageW.argtypes = [ctypes.wintypes.HWND, ctypes.wintypes.UINT, ctypes.wintypes.WPARAM, ctypes.wintypes.LPARAM]
user32.SendMessageW.restype = ctypes.wintypes.LPARAM

# 添加获取窗口标题的API
user32.GetWindowTextW.argtypes = [ctypes.wintypes.HWND, ctypes.wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int
user32.GetWindowTextLengthW.argtypes = [ctypes.wintypes.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int

# --- 定义常量 ---
# WM_IME_CONTROL 消息和子命令
WM_IME_CONTROL = 0x0283
IMC_GETOPENSTATUS = 0x0005
IMC_SETOPENSTATUS = 0x0006
IMC_GETCONVERSIONMODE = 0x0001
IMC_SETCONVERSIONMODE = 0x0002

# Conversion Mode 的常量 (根据参考资料)
IME_CMODE_NATIVE = 0x0001        # 中/日/韩文输入模式
IME_CMODE_KATAKANA = 0x0002      # 日文片假名 (与 NATIVE 结合使用)
IME_CMODE_LANGUAGE = IME_CMODE_NATIVE | IME_CMODE_KATAKANA
IME_CMODE_FULLSHAPE = 0x0008     # 全角
IME_CMODE_NOCONVERSION = 0x0100  # 关闭输入法转换
IME_CMODE_SYMBOL = 0x0400        # 中文标点模式

# 语言ID
LANG_CHINESE = 0x0804
LANG_ENGLISH_US = 0x0409

# Microsoft Pinyin 的布局ID
PINYIN_LAYOUT_IDS = [0x08040804, 0x00000804, 0xe0010804]

def get_window_title(hwnd):
    """获取窗口标题"""
    if not hwnd:
        return ""
    length = user32.GetWindowTextLengthW(hwnd) + 1
    if length <= 1:
        return ""
    buf = ctypes.create_unicode_buffer(length)
    user32.GetWindowTextW(hwnd, buf, length)
    return buf.value

def is_microsoft_pinyin(lang_id, hkl):
    """检查是否为Microsoft Pinyin输入法"""
    # 检查语言ID是否为中文
    if lang_id != LANG_CHINESE:
        return False
    
    # 检查完整的HKL值是否匹配Microsoft Pinyin
    return hkl in PINYIN_LAYOUT_IDS

def set_ime_mode(hwnd, open_status=True, conversion_mode=None):
    """
    设置IME模式
    
    Args:
        hwnd: 窗口句柄
        open_status: 是否打开IME
        conversion_mode: 转换模式，None表示不修改
    
    Returns:
        bool: 是否设置成功
    """
    hime = imm32.ImmGetDefaultIMEWnd(hwnd)
    if not hime:
        return False
    
    try:
        # 设置IME开启状态
        if open_status is not None:
            user32.SendMessageW(hime, WM_IME_CONTROL, IMC_SETOPENSTATUS, 1 if open_status else 0)
        
        # 设置转换模式
        if conversion_mode is not None:
            user32.SendMessageW(hime, WM_IME_CONTROL, IMC_SETCONVERSIONMODE, conversion_mode)
        
        return True
    except Exception as e:
        print(f"设置IME模式失败: {e}")
        return False

def switch_to_chinese_mode(hwnd):
    """切换到中文模式"""
    # Microsoft Pinyin的中文模式：开启IME + NATIVE模式
    conversion_mode = IME_CMODE_NATIVE
    return set_ime_mode(hwnd, open_status=True, conversion_mode=conversion_mode)

def get_ime_status():
    """
    获取当前活动窗口的输入法状态。
    严格遵循参考资料和流程图的逻辑。

    返回:
        tuple: (is_chinese, symbol_mode_str, lang_id, is_pinyin, hwnd)
        is_chinese (bool): True 表示中文输入模式, False 表示英文模式。
        symbol_mode_str (str): 描述标点符号状态的字符串。
        lang_id (int): 当前键盘布局的语言ID。
        is_pinyin (bool): 是否为Microsoft Pinyin输入法。
        hwnd (int): 窗口句柄
    """
    # 1. 获取活动窗口句柄
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return False, "未知", 0, False, 0

    # 2. 获取键盘布局语言ID
    # 获取窗口线程ID
    thread_id = user32.GetWindowThreadProcessId(hwnd, None)
    # 获取键盘布局句柄
    hkl = user32.GetKeyboardLayout(thread_id)
    # 语言ID是HKL的低16位
    lang_id = hkl & 0xFFFF
    
    # 检查是否为Microsoft Pinyin
    is_pinyin = is_microsoft_pinyin(lang_id, hkl)

    # 3. 获取IME窗口句柄
    hime = imm32.ImmGetDefaultIMEWnd(hwnd)
    if not hime:
        # 如果没有IME窗口，通常是英文模式
        return False, "英文半角", lang_id, is_pinyin, hwnd

    # 4. 获取 opened 和 convMode 状态
    # IMC_GETOPENSTATUS: 输入法是否打开
    opened = user32.SendMessageW(hime, WM_IME_CONTROL, IMC_GETOPENSTATUS, 0)
    
    # IMC_GETCONVERSIONMODE: 获取转换模式
    conv_mode = user32.SendMessageW(hime, WM_IME_CONTROL, IMC_GETCONVERSIONMODE, 0)

    # --- 核心判断逻辑 (根据流程图) ---

    # 规则：如果键盘布局是英文，即使输入法报告'opened'，也应视为关闭
    if opened and lang_id == LANG_ENGLISH_US:
        opened = False
        
    # 规则：罕见情况，NOCONVERSION 标志位表示关闭
    if conv_mode & IME_CMODE_NOCONVERSION:
        opened = False

    # 判断是否为中文输入模式
    # 关键条件: opened为真 且 conv_mode包含NATIVE标志位
    is_chinese = bool(opened and (conv_mode & IME_CMODE_NATIVE))

    # 判断标点符号模式
    symbol_mode_str = "英文半角" # 默认值
    if is_chinese:
        if conv_mode & IME_CMODE_SYMBOL:
            symbol_mode_str = "中文标点"
        else:
            # 在中文模式下，如果不是中文标点，则根据全角/半角判断
            if conv_mode & IME_CMODE_FULLSHAPE:
                symbol_mode_str = "英文全角"
            else:
                symbol_mode_str = "英文半角"
    else: # 英文模式下只判断全半角
        if conv_mode & IME_CMODE_FULLSHAPE:
            symbol_mode_str = "英文全角"
        else:
            symbol_mode_str = "英文半角"

    return is_chinese, symbol_mode_str, lang_id, is_pinyin, hwnd

def auto_switch_to_chinese():
    """
    自动切换功能：当检测到Microsoft Pinyin输入法且为英文模式时，自动切换到中文模式
    
    Returns:
        bool: 是否执行了切换操作
    """
    is_chinese, symbol_mode, lang_id, is_pinyin, hwnd = get_ime_status()
    
    # 检查条件：是Microsoft Pinyin且当前为英文模式
    if is_pinyin and not is_chinese:
        window_title = get_window_title(hwnd)
        print("检测到Microsoft Pinyin处于英文模式，自动切换到中文模式...")
        print(f"窗口: {window_title}")
        
        # 执行切换
        success = switch_to_chinese_mode(hwnd)
        if success:
            print("✅ 已切换到中文模式")
            return True
        else:
            print("❌ 切换失败")
            return False
    
    return False

def main():
    """
    主函数，循环监控并打印输入法状态，并在需要时自动切换。
    """
    print("开始监控输入法状态... 按 Ctrl+C 退出。")
    print("自动切换功能已启用：检测到Microsoft Pinyin英文模式时将自动切换到中文模式")
    print("-" * 60)
    
    last_status_str = ""

    try:
        while True:
            is_chinese, symbol_mode, lang_id, is_pinyin, hwnd = get_ime_status()
            
            # 组合当前状态字符串
            lang_str = "中文" if is_chinese else "英文"
            pinyin_str = " (Microsoft Pinyin)" if is_pinyin else ""
            window_title = get_window_title(hwnd)
            
            status_str = f"输入模式: {lang_str}{pinyin_str} | 标点状态: {symbol_mode} | 语言ID: {hex(lang_id)}"
            
            # 仅在状态变化时打印，避免刷屏
            if status_str != last_status_str:
                print(f"[{time.strftime('%H:%M:%S')}] {status_str}")
                if window_title:
                    print(f"           窗口: {window_title}")
                last_status_str = status_str
                
                # 执行自动切换检查
                auto_switch_to_chinese()
            
            # 每隔一小段时间检查一次
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n监控已停止。")
    except Exception as e:
        print(f"\n发生错误: {e}")

def test_single_check():
    """测试单次检查功能"""
    print("执行单次IME状态检查...")
    print("-" * 40)
    
    is_chinese, symbol_mode, lang_id, is_pinyin, hwnd = get_ime_status()
    window_title = get_window_title(hwnd)
    
    print(f"窗口标题: {window_title}")
    print(f"语言ID: 0x{lang_id:04x}")
    print(f"是否为Microsoft Pinyin: {is_pinyin}")
    print(f"当前输入模式: {'中文' if is_chinese else '英文'}")
    print(f"标点状态: {symbol_mode}")
    
    # 测试自动切换
    if is_pinyin and not is_chinese:
        print("\n检测到Microsoft Pinyin英文模式，尝试切换...")
        if switch_to_chinese_mode(hwnd):
            print("✅ 切换成功")
            # 再次检查状态
            time.sleep(0.1)
            is_chinese_new, symbol_mode_new, _, _, _ = get_ime_status()
            print(f"切换后状态: {'中文' if is_chinese_new else '英文'} | {symbol_mode_new}")
        else:
            print("❌ 切换失败")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_single_check()
    else:
        main()
