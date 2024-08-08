## Introduction

如果你也使用多种语言的输入法，并且希望在中文和英语输入法间快速切换，这个工具可以帮到你。

功能：
- 切换中英文 `<ctrl>+\`
- 暂时切换 `<ctrl>+<shfit>+\` (停止输入2s后自动切回)
- 瞬时切换输入 `<ctrl>+<alt>+\` (输入第一个字符后，0.3s后切回)

Features:
- Switch between Chinese and English `<ctrl>+\`
- Temporary switch `<ctrl>+<shift>+\` (automatically switches back after 2 seconds of inactivity)
- Instant switch input `<ctrl>+<alt>+\` (switches back 0.3 seconds after typing the first character)

## Release

https://github.com/manfred-exz/IME-Switcher/releases/latest

## Build

```
python -m nuitka --standalone --windows-disable-console .\main.py
```
