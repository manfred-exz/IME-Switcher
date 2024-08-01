## Introduction

如果你也使用多种语言的输入法，并且希望在中文和英语输入法间快速切换，这个工具可以帮到你。

|               功能                |       快捷键        |
|:-------------------------------:|:----------------:|
|     切换到英文/switch to English     | `<ctrl>+<alt>+[` |
|     切换到中文/switch to Chinese     | `<ctrl>+<alt>+]` |
| 中英文切换快捷键/toggle Chinese-English |    `<ctrl>+\`    |

If you are using multiple(>3) input methods, but you have two main languages to work with,
this tool can to easily switch between them with a shortcut `<ctrl>+\` (you need to modify the code for your language)

## Release

```
python -m nuitka --standalone --windows-disable-console .\main.py
```

## Why

- 切换到微软拼音输入法时，有时会自动进入ASCII模式，导致难以快速进入中文输入模式。
- 中文输入法的ASCII模式下，不能触发部分快捷键。
- 如果你的CJK输入法，含有ASCII模式。那么你通常难以确定当前使用的是English键盘，还是CJK键盘的ASCII模式。