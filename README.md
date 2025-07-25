## Introduction

如果你使用多种语言的输入法，并且希望在英语和另一种语言间快速切换，这个工具可以帮到你。

功能：
- 切换 `<ctrl>+\`
- 强制中文模式（禁止微软拼音输入法的ASCII模式）
- 暂时切换 `<ctrl>+<shfit>+\` (停止输入2s后自动切回)
- 快速切换 `<ctrl>+<alt>+\` (停止输入0.3s后自动切回)

Features:
- Switch between English and another language `<ctrl>+\`
- Temporary switch `<ctrl>+<shift>+\` (automatically switches back after 2 seconds of inactivity)
- Instant switch `<ctrl>+<alt>+\` (automatically switches back after 0.3 seconds of inactivity)

## Configurations
- Edit `config.json`
- Find Keyboard ID [here](https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/windows-language-pack-default-values?view=windows-11)

## Release

https://github.com/manfred-exz/IME-Switcher/releases/latest

## Build

```
python -m nuitka --standalone --windows-console-mode=disable --windows-icon-from-ico=.\icon.ico .\ime_switcher\main.py
```
