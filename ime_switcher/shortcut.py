import win32con

# Define a mapping from human-friendly key names to virtual key codes
key_mapping = {
    'A': 0x41, 'B': 0x42, 'C': 0x43, 'D': 0x44, 'E': 0x45, 'F': 0x46, 'G': 0x47,
    'H': 0x48, 'I': 0x49, 'J': 0x4A, 'K': 0x4B, 'L': 0x4C, 'M': 0x4D, 'N': 0x4E,
    'O': 0x4F, 'P': 0x50, 'Q': 0x51, 'R': 0x52, 'S': 0x53, 'T': 0x54, 'U': 0x55,
    'V': 0x56, 'W': 0x57, 'X': 0x58, 'Y': 0x59, 'Z': 0x5A,
    '0': 0x30, '1': 0x31, '2': 0x32, '3': 0x33, '4': 0x34, '5': 0x35, '6': 0x36,
    '7': 0x37, '8': 0x38, '9': 0x39,
    'F1': 0x70, 'F2': 0x71, 'F3': 0x72, 'F4': 0x73, 'F5': 0x74, 'F6': 0x75,
    'F7': 0x76, 'F8': 0x77, 'F9': 0x78, 'F10': 0x79, 'F11': 0x7A, 'F12': 0x7B,
    'ESC': 0x1B, 'TAB': 0x09, 'CAPSLOCK': 0x14, 'SHIFT': win32con.MOD_SHIFT,
    'CTRL': win32con.MOD_CONTROL, 'ALT': win32con.MOD_ALT, 'WIN': win32con.MOD_WIN,
    'SPACE': 0x20, 'ENTER': 0x0D, 'BACKSPACE': 0x08, 'DELETE': 0x2E,
    'LEFT': 0x25, 'UP': 0x26, 'RIGHT': 0x27, 'DOWN': 0x28,
    '\\': 0xDC, '/': 0xBF, '.': 0xBE, ',': 0xBC, ';': 0xBA, '\'': 0xDE,
    '[': 0xDB, ']': 0xDD, '-': 0xBD, '=': 0xBB, '`': 0xC0,
    # Add more key mappings as needed
}


def parse_shortcut(shortcut):
    keys = shortcut.upper().split('+')
    mod = 0
    vk = None

    for key in keys:
        if key in key_mapping:
            if key in ['CTRL', 'SHIFT', 'ALT', 'WIN']:
                mod |= key_mapping[key]
            else:
                vk = key_mapping[key]

    return mod, vk


if __name__ == '__main__':
    # Example human-friendly configuration
    example_shortcuts = [
        "Ctrl+\\",
        "Ctrl+Shift+\\",
        "Ctrl+Alt+\\",
        "Ctrl+Alt+Delete",
        "Ctrl+Shift+F1",
        "Alt+F4",
        "Win+D",
        "Ctrl+Alt+Shift+S",
    ]

    # Print the result
    for hotkey in example_shortcuts:
        print(hotkey)
        print(parse_shortcut(hotkey))
