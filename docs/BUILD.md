# Building a standalone exe (optional)

The program uses the standard library only, so packaging needs no special dependencies — one
PyInstaller command is enough.

## 1. Install PyInstaller

```bash
pip install pyinstaller pillow
```

- `pyinstaller` does the packaging;
- `pillow` is only needed if you want to regenerate the `.ico` icon; packaging itself does not use it.

> **You must use a Python that has tkinter.** Some trimmed distributions (certain conda
> environments, the Windows Store build of Python) ship without it, and the resulting exe fails at
> start-up with `No module named _tkinter`. Check first with `python -c "import tkinter"`.

## 2. Build

From inside `src/`:

```bash
pyinstaller --noconfirm --onefile --windowed --clean ^
  --icon "ai4Gauss_en.ico" ^
  --add-data "ai4Gauss_en.ico;." ^
  --name ai4Gauss_en ^
  ai4Gauss_en.py
```

On Linux / macOS the `--add-data` separator is `:` instead of `;`.

The result is `dist/ai4Gauss_en.exe` — about 11.4 MB, single file, no installation, just
double-click.

## Three easy mistakes

1. **`--add-data` must include the icon.** The window icon is read from disk at run time (see
   `set_window_icon()` in the source). If the `.ico` is not packed in, a standalone exe falls back
   to the default Tk feather logo. The lookup order is: folder of the exe → unpack directory
   (`sys._MEIPASS`) → folder of the source script.

2. **If you pass `--specpath`, use absolute paths.** With `--specpath`, relative paths in `--icon`
   and `--add-data` are resolved against the **spec directory** rather than the current directory,
   which typically fails with `Unable to open icon file`.

3. **Overwriting a running exe fails.** Close the program normally (from the task manager if
   needed) before rebuilding.

## A note on exe builds and source

This repository contains **no API key at all** — `ai4Gauss_en.py` has never had one, and the
program asks you to enter your own key on first run. If you modify the source to ship a key inside
the executable, remember:

- a single-file exe is just a container; `strings` on it reveals the constants in the source;
- obfuscation (XOR + base64) only defeats string search, not decompilation;
- so **never commit an exe that contains a key** — distribute it through Releases or cloud storage
  instead, and be ready to rotate the key.
