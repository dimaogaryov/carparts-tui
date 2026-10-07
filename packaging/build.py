"""Сборка одного исполняемого файла через PyInstaller.

Запуск из корня проекта после `pip install . pyinstaller`:
    python packaging/build.py
Результат: dist/carparts (dist/carparts.exe на Windows).
"""
import PyInstaller.__main__

PyInstaller.__main__.run([
    "packaging/entry.py",
    "--name", "carparts",
    "--onefile",
    "--console",
    "--noconfirm",
    "--clean",
    # theme.tcss и метаданные пакета (для --version)
    "--collect-data", "carparts",
    "--copy-metadata", "carparts",
    # textual.widgets и rich импортируют модули лениво — PyInstaller их не видит
    "--collect-submodules", "textual",
    "--collect-data", "textual",
    "--collect-submodules", "rich",
])
