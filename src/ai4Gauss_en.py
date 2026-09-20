#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ai4Gauss (English Edition) — Gaussian Input File Generator  v1.0
=================================================================
English-language build. No API credentials are bundled with this
program: the user supplies their own OpenAI-compatible API Key in the
Settings dialog (saved locally to ai4Gauss_en_config.json).

Workflow:
  1. Type a plain-text description of the computational task and click
     "Generate Keywords with AI". The model is called in two steps:
        step 1 — the Gaussian route section (a single line starting with #)
                 plus a short rationale for the level of theory (log only);
        step 2 — the extra input section placed at the end of the file, e.g.
                 the wavefunction file name required by output=wfn, or a
                 gen/genecp basis-set definition (blank when none is needed).
     The route line and the extra section are then cross-checked and anything
     obviously missing is filled in automatically.
  2. Pick a .gjf file from the working directory; its atomic coordinates
     (charge/multiplicity + coordinate block) are extracted automatically.
  3. Set the server parameters (nproc / mem) in the Settings dialog;
     they are written into the link-0 header of the new file.
  4. Assemble everything into a complete .gjf file. The default output
     name is <input name>_<date>.gjf.
  5. Every successful AI call is appended to keywords.txt in the program
     folder; the run log is saved as <timestamp>.log on exit.

Standard library only (tkinter / urllib / json / re / os / datetime).

Developer: chuan437    Email: wangchuan437@126.com
"""

import datetime
import json
import os
import re
import sys
import tkinter as tk
from tkinter import ttk, filedialog
import urllib.request
import urllib.error

APP_NAME = "ai4Gauss"
APP_VERSION = "1.0"
APP_TITLE = "%s v%s — Gaussian Input File Generator" % (APP_NAME, APP_VERSION)
APP_SUBTITLE = "English Edition"
AUTHOR_INFO = "%s v%s (%s)  |  Developer: chuan437  |  Email: wangchuan437@126.com" % (
    APP_NAME,
    APP_VERSION,
    APP_SUBTITLE,
)

# UI font family (Latin-friendly)
UI_FONT = "Segoe UI"
MONO_FONT = "Consolas"


# ---------------------------------------------------------------------------
# Paths (PyInstaller-aware: under a one-file exe, __file__ points to the
# temporary extraction directory, so use the executable's own folder)
# ---------------------------------------------------------------------------
def _resolve_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


BASE_DIR = _resolve_base_dir()
CONFIG_FILE = os.path.join(BASE_DIR, "ai4Gauss_en_config.json")
KEYWORDS_FILE = os.path.join(BASE_DIR, "keywords.txt")


# ---------------------------------------------------------------------------
# Window icon: replaces Tk's default feather logo in the title bar
# ---------------------------------------------------------------------------
ICON_NAME = "ai4Gauss_en.ico"


def _resolve_icon_path():
    """Locate the icon: exe folder -> PyInstaller unpack dir -> source folder."""
    cands = []
    if getattr(sys, "frozen", False):
        cands.append(os.path.join(os.path.dirname(os.path.abspath(sys.executable)), ICON_NAME))
        mei = getattr(sys, "_MEIPASS", "")
        if mei:
            cands.append(os.path.join(mei, ICON_NAME))
    cands.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ICON_NAME))
    for p in cands:
        if p and os.path.isfile(p):
            return p
    return None


def _draw_fallback_icon():
    """Draw a tiny in-program icon when the .ico file is missing (never a feather)."""
    img = tk.PhotoImage(width=32, height=32)
    img.put("#0F4A3C", to=(0, 0, 32, 32))      # brand background
    img.put("#8FD3BC", to=(9, 14, 23, 17))     # bond
    img.put("#FFFFFF", to=(8, 20, 13, 25))     # lower-left atom
    img.put("#FFFFFF", to=(19, 20, 24, 25))    # lower-right atom
    img.put("#E2571C", to=(13, 7, 19, 13))     # top atom
    return img


def set_window_icon(win):
    """Swap the default Tk icon shown at the top-left of a window's title bar.

    On Windows, wm iconbitmap's ``default`` option also applies to Toplevels
    created afterwards; every Toplevel still calls this explicitly so the icon
    is guaranteed to be set on any Tk version.
    """
    path = _resolve_icon_path()
    if path:
        try:
            win.iconbitmap(default=path)       # Windows: .ico
            return True
        except Exception:
            pass
        try:
            img = tk.PhotoImage(file=path)     # other platforms: png/gif
            win.iconphoto(True, img)
            win._icon_ref = img                # keep a reference alive
            return True
        except Exception:
            pass
    try:
        img = _draw_fallback_icon()
        win.iconphoto(True, img)
        win._icon_ref = img
        return True
    except Exception:
        return False


# Uniform width (characters) of the action buttons in the main window
BTN_WIDTH = 26
BTN_WIDTH_DLG = 20

# Placeholders shown in the Settings dialog; NO credentials are bundled.
DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_MODEL = "deepseek-v4-flash"


# Step 1: task description -> route line + rationale
SYSTEM_PROMPT = (
    "You are a senior expert in Gaussian quantum chemistry. The user gives you a "
    "description of a computational task (in English or Chinese) and you reply with "
    "exactly two parts.\n\n"
    "[Part 1] The Gaussian route section: a single line starting with # (#p is also "
    "acceptable). Write it on ONE line — no line continuation, no multiple lines. "
    "Choose an appropriate method, basis set and supplementary keywords (e.g. opt, freq, "
    "nosymm, scrf, field, pop, td). When the request is vague, choose the most standard "
    "and safe defaults.\n"
    "Important: if the task requires a wavefunction or density file to be written, the "
    "corresponding output= keyword MUST be present in the route line, e.g. output=wfn "
    "(AIM wavefunction), output=wfx, output=cube. Such keywords also require a file name "
    "at the end of the input file; that name is determined in a later step, so here you "
    "only need to get the keyword right.\n"
    "[Part 2] One or two sentences (in English) explaining why this level of theory "
    "(method / basis set) was chosen.\n\n"
    "Reply strictly in the following format and output nothing else:\n"
    "# route line\n"
    "\n"
    "[REASON]\n"
    "Short rationale for the chosen level of theory\n\n"
    "Example:\n"
    "User input: Single-point CCSD energy of a water molecule, with wavefunction output\n"
    "Output:\n"
    "# CCSD/aug-cc-pVTZ nosymm density=current output=wfn\n"
    "\n"
    "[REASON]\n"
    "CCSD is a highly accurate coupled-cluster method and aug-cc-pVTZ includes diffuse "
    "and polarization functions, which describes the electronic structure of water well; "
    "output=wfn writes the AIM wavefunction file (density=current is required for post-HF "
    "methods)."
)

# Step 2: task description + route line -> extra input section at the end of the file
TAIL_SYSTEM_PROMPT = (
    "You are a senior expert in Gaussian quantum chemistry. This time you do one thing "
    "only: decide whether the job needs an extra input section placed AFTER the coordinate "
    "block at the very end of the input file, and write it if it is needed.\n\n"
    "You are given: the task description, the already-fixed route line, and the output "
    "file stem.\n\n"
    "Check the route line against these rules:\n"
    "1) output=wfn (or out=wfn): a line giving the wavefunction file name, extension .wfn, "
    "is REQUIRED at the end of the file, e.g. mol.wfn. Without that line Gaussian will not "
    "write the wavefunction file at all.\n"
    "2) output=wfx (or out=wfx): same, a .wfx file name on its own line.\n"
    "3) gen or genecp: a custom basis set (and pseudopotential) definition block is "
    "REQUIRED. Its structure is: first the basis-set sections, each starting with a line "
    "holding the atom list followed by 0 (e.g. Cu 0), the section body below it, and the "
    "sections separated by a line containing only ****; after all basis sections, if an "
    "effective core potential (ECP) is also needed, another line containing only **** "
    "introduces the ECP section. A missing separator makes Gaussian fail to parse the "
    "input.\n"
    "4) ReadIsotopes, opt=ModRedundant, BOMD, etc.: the corresponding input section is "
    "REQUIRED, written exactly as Gaussian expects.\n"
    "5) Anything else (opt, freq, td, scrf, field, nosymm, pop, density, output=cube ...) "
    "needs no trailing content; in that case output only: NONE\n\n"
    "Notes:\n"
    "- If the task description asks for a wavefunction file (wfn/wfx) but the route line "
    "lacks the corresponding output= keyword, still provide the file-name line (the route "
    "line is fixed by the program).\n"
    "- Do not use geom=connectivity together with output=wfn/wfx: a connectivity block "
    "prevents Gaussian from reading the trailing file name.\n"
    "- Name the file after the given output stem plus the proper extension; if no stem is "
    "given, pick a short ASCII name derived from the task.\n\n"
    "Format: output the trailing content only, verbatim, with no explanation and no code "
    "fence. If truly nothing is needed, output exactly one line: NONE\n\n"
    "Example 1:\n"
    "Input: Task: geometry optimization of water with wavefunction output; Route line: "
    "#p B3LYP/6-31G(d) opt output=wfn; Output stem: H2O\n"
    "Output: H2O.wfn\n\n"
    "Example 2:\n"
    "Input: Task: geometry optimization and frequency job on methanol; Route line: "
    "#p B3LYP/6-31G(d) opt freq; Output stem: CH3OH\n"
    "Output: NONE\n\n"
    "Example 3:\n"
    "Input: Task: geometry optimization of [Cu(NH3)4]2+ with the SDD pseudopotential for "
    "Cu and 6-31G(d) for N and H; Route line: #p B3LYP/genecp opt freq; "
    "Output stem: CuNH3\n"
    "Output:\n"
    "Cu 0\n"
    "SDD\n"
    "****\n"
    "N H 0\n"
    "6-31G(d)\n"
    "****\n"
    "\n"
    "Cu 0\n"
    "SDD"
)

CHARGE_RE = re.compile(r"^-?\d+\s+-?\d+$")


# ---------------------------------------------------------------------------
# Theme helper + copyable read-only label
# ---------------------------------------------------------------------------
def _theme_bg(widget=None):
    """Background colour of the current ttk theme (for borderless entries)."""
    try:
        return ttk.Style().lookup("TFrame", "background") or "SystemButtonFace"
    except Exception:
        return "SystemButtonFace"


def _readonly_entry(parent, text, fg="#666666", font=None):
    """A read-only but SELECTABLE / COPYABLE single-line text widget.

    A plain ttk.Label cannot be selected with the mouse. A readonly
    tk.Entry can: drag to select, Ctrl+C, or right-click for the context
    menu. It is styled flat so it still looks like a caption.
    """
    var = tk.StringVar(value=text)
    ent = tk.Entry(
        parent,
        textvariable=var,
        state="readonly",
        relief="flat",
        bd=0,
        highlightthickness=0,
        readonlybackground=_theme_bg(),
        fg=fg,
        font=font or (UI_FONT, 9),
        cursor="xterm",
        takefocus=True,
    )

    def _copy():
        try:
            sel = ent.selection_get()
        except tk.TclError:
            sel = var.get()
        ent.clipboard_clear()
        ent.clipboard_append(sel)

    def _select_all(_event=None):
        ent.selection_range(0, "end")
        ent.icursor("end")
        return "break"

    menu = tk.Menu(ent, tearoff=0)
    menu.add_command(label="Copy", command=_copy)
    menu.add_command(label="Select All", command=_select_all)

    def _popup(event):
        ent.focus_set()
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
        return "break"

    def _double_click(event):
        ent.selection_range(0, "end")
        return "break"

    ent.bind("<Button-3>", _popup)
    ent.bind("<Double-Button-1>", _double_click)
    ent.bind("<Control-c>", lambda e: (_copy(), "break")[1])
    ent.bind("<Control-a>", _select_all)
    # attach for reuse / testing
    ent.context_menu = menu
    ent.copy_to_clipboard = _copy
    return ent


# ---------------------------------------------------------------------------
# Dialogs
#
# tkinter's messagebox falls back to the NATIVE Windows MessageBox, whose
# buttons are localised by the operating system (e.g. "是 / 否" on a Chinese
# Windows). For an all-English user interface this build uses its own dialogs
# whose captions are always English.
# ---------------------------------------------------------------------------
class _EnDialog(tk.Toplevel):
    def __init__(self, parent, title, message, buttons, kind="info"):
        super().__init__(parent)
        self.title(title)
        set_window_icon(self)
        self.resizable(False, False)
        try:
            self.transient(parent.winfo_toplevel() if parent else None)
        except Exception:
            pass
        self.result = None

        colors = {"info": "#0f6e56", "warn": "#b35c00", "error": "#c0392b"}
        glyphs = {"info": "ⓘ", "warn": "⚠", "error": "✖"}
        accent = colors.get(kind, colors["info"])

        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)

        head = ttk.Frame(body)
        head.pack(fill="both", expand=True)
        tk.Label(head, text=glyphs.get(kind, "ⓘ"), fg=accent,
                 font=(UI_FONT, 20)).pack(side="left", padx=(0, 12), anchor="n")
        tk.Label(head, text=message, justify="left", wraplength=400,
                 font=(UI_FONT, 9)).pack(side="left", anchor="w")

        # remember the default (primary) button for Enter / initial focus
        self.default_btn = None
        btns = ttk.Frame(body)
        btns.pack(fill="x", pady=(16, 0))
        for label, value, is_default in buttons:
            b = ttk.Button(btns, text=label, width=12,
                           command=lambda v=value: self._finish(v))
            b.pack(side="right", padx=(8, 0))
            if is_default:
                self.default_btn = b

        # Enter = primary button, Escape / window close = the "safe" button
        # (the first one, which is "No" for a confirmation dialog)
        def _cancel():
            self._finish(buttons[0][1])

        def _accept(_event=None):
            if self.default_btn is not None:
                self.default_btn.invoke()
            else:
                _cancel()
            return "break"

        self.bind("<Return>", _accept)
        self.bind("<KP_Enter>", _accept)
        self.bind("<Escape>", lambda e: (_cancel(), "break")[1])
        self.protocol("WM_DELETE_WINDOW", _cancel)

        self._center_on(parent)

        # take over the grab, then hand it back to the caller if it had one
        prev = None
        try:
            prev = (parent.winfo_toplevel() if parent else None)
            prev = prev.grab_current() if prev else None
        except Exception:
            prev = None
        self.grab_set()
        self.focus_force()
        if self.default_btn is not None:
            self.default_btn.focus_set()
        if parent is not None:
            parent.wait_window(self)
        else:
            self.wait_window(self)
        if prev is not None:
            try:
                if prev.winfo_exists():
                    prev.grab_set()
            except Exception:
                pass

    def _center_on(self, parent):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        try:
            px, py = parent.winfo_rootx(), parent.winfo_rooty()
            pw, ph = parent.winfo_width(), parent.winfo_height()
            if pw <= 1 or ph <= 1:
                raise ValueError
            x, y = px + (pw - w) // 2, py + (ph - h) // 3
        except Exception:
            x = (self.winfo_screenwidth() - w) // 2
            y = (self.winfo_screenheight() - h) // 3
        x = max(0, min(x, self.winfo_screenwidth() - w))
        y = max(0, min(y, self.winfo_screenheight() - h))
        self.geometry("+%d+%d" % (x, y))

    def _finish(self, value):
        self.result = value
        self.destroy()


def msg_info(title, message, parent=None):
    _EnDialog(parent, title, message, [("OK", True, True)], "info")
    return True


def msg_warn(title, message, parent=None):
    _EnDialog(parent, title, message, [("OK", True, True)], "warn")
    return True


def msg_error(title, message, parent=None):
    _EnDialog(parent, title, message, [("OK", True, True)], "error")
    return True


def ask_yes_no(title, message, parent=None):
    d = _EnDialog(parent, title, message,
                  [("No", False, False), ("Yes", True, True)], "warn")
    return bool(d.result)


# ---------------------------------------------------------------------------
# Config I/O
# ---------------------------------------------------------------------------
def load_config(path=None):
    """Read the local settings file (returns {} when missing or corrupt)."""
    path = path or CONFIG_FILE
    cfg = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, ValueError):
        pass
    return cfg


def save_config(cfg, path=None):
    """Write the settings file."""
    path = path or CONFIG_FILE
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def has_credentials(cfg):
    """True when the user has supplied a valid API Key."""
    return bool((cfg or {}).get("api_key", "").strip())


def resolve_credentials(cfg):
    """Return (api_key, base_url, model) for this run.

    This build bundles no credentials: the values come solely from the
    user's settings file. A clear error is raised when the Key is missing.
    """
    cfg = cfg or {}
    api_key = (cfg.get("api_key") or "").strip()
    base_url = (cfg.get("base_url") or DEFAULT_BASE_URL).strip()
    model = (cfg.get("model") or DEFAULT_MODEL).strip()
    if not api_key:
        raise ValueError(
            "No API Key configured. Open Settings and enter your own API Key first."
        )
    return api_key, base_url, model


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------
# Turn off the "thinking" phase of reasoning models: for "pick a route keyword and
# write the trailing input section" tasks thinking is not needed, and disabling it
# makes the reply much faster and cheaper and avoids the reply being eaten by the
# reasoning process (empty content). If the configured endpoint does not accept the
# parameter (HTTP 400/422/404), the request is retried without it.
DISABLE_THINKING = True


def _post_chat(api_key, base_url, model, messages, timeout, max_tokens):
    """Send one chat/completions request and return the parsed JSON dict."""
    url = base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model.strip() or DEFAULT_MODEL,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": max_tokens,
        "stream": False,
    }
    if DISABLE_THINKING:
        payload["thinking"] = {"type": "disabled"}

    def send(body):
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + api_key.strip(),
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            raise RuntimeError("AI request failed (HTTP %s): %s" % (e.code, detail[:300]))
        except urllib.error.URLError as e:
            raise RuntimeError("Network error: %s" % e.reason)

    if "thinking" in payload:
        try:
            return send(payload)
        except RuntimeError as e:
            if "HTTP 400" in str(e) or "HTTP 422" in str(e) or "HTTP 404" in str(e):
                payload.pop("thinking", None)  # endpoint does not support it
            else:
                raise
    return send(payload)


def call_llm_chat(api_key, base_url, model, messages, timeout=120, max_tokens=1024,
                  with_meta=False):
    """Call an OpenAI-compatible chat/completions endpoint and return the reply text.

    If the reply is used up by the length limit (a reasoning model spending all
    tokens on thinking and returning empty content), the request is retried once
    with a larger limit so transient empty replies do not reach the user.
    With with_meta=True returns (text, meta) where meta holds finish_reason / usage.
    """
    if not (api_key or "").strip():
        raise ValueError("API Key is empty. Please check your settings.")

    limits = [max_tokens, max(max_tokens * 2, 4096)]
    for attempt, mt in enumerate(limits):
        result = _post_chat(api_key, base_url, model, messages, timeout, mt)
        try:
            choice = result["choices"][0]
        except (KeyError, IndexError, TypeError):
            raise RuntimeError("Cannot parse the AI response: %s" % str(result)[:300])

        msg = choice.get("message") or {}
        text = (msg.get("content") or "").strip()
        finish = choice.get("finish_reason")
        if text or finish != "length":
            if with_meta:
                return text, {"finish_reason": finish, "usage": result.get("usage")}
            return text
        if attempt + 1 < len(limits):
            continue  # content consumed by reasoning — retry with a larger limit

    raise RuntimeError(
        "The AI returned no usable content (all %s tokens were spent on reasoning). "
        "Please try again or use another model in Settings." % limits[-1]
    )


# ---------------------------------------------------------------------------
# Consistency rules between the route line and the trailing extra section
# ---------------------------------------------------------------------------
# Route forms that REQUIRE a wavefunction file name on the last line of the input
TAIL_FILE_RULES = (
    (re.compile(r"(?:output|out)\s*=\s*wfn\b", re.I), ".wfn", "output=wfn"),
    (re.compile(r"(?:output|out)\s*=\s*wfx\b", re.I), ".wfx", "output=wfx"),
)
# Known "file name -> keyword it requires" pairs
FILE_KW = {".wfn": "output=wfn", ".wfx": "output=wfx"}

# Route forms that REQUIRE an input block at the end of the file
TAIL_BLOCK_RULES = (
    (re.compile(r"\bgenecp\b", re.I), "a custom basis set / pseudopotential block (genecp)"),
    (re.compile(r"(?<![A-Za-z])gen(?![A-Za-z])", re.I), "a custom basis set block (gen)"),
    (re.compile(r"ReadIsotopes", re.I), "an isotope definition block (ReadIsotopes)"),
    (re.compile(r"ModRedundant", re.I), "a redundant-coordinate block (opt=ModRedundant)"),
    (re.compile(r"\bBOMD\b", re.I), "a BOMD input section"),
)

# A single-line file name such as "C:\work\mol.wfn" / "mol.wfx"
FILE_TAIL_RE = re.compile(r"^[^\s*]+\.(?:wfn|wfx|cube|fchk|chk|dens|dat)$", re.I)

# Ways the model may express "no trailing content needed"
NONE_TOKENS = {
    "", "none", "none.", "n/a", "na", "null", "no", "nothing", "not needed",
    "not required", "no extra input", "not applicable", "无", "无。", "不需要", "无需",
}

# Prefixes of explanatory lines that must never end up in the input file
PROSE_PREFIXES = ("note:", "note :", "explanation:", "comment:")


def _is_none_token(text):
    t = (text or "").strip().strip("*`").strip().rstrip("。.").strip().lower()
    return t in NONE_TOKENS


def parse_route_reason(resp):
    """Step-1 reply -> (route line, rationale)."""
    resp = (resp or "").strip()
    resp = re.sub(r"^```[a-zA-Z]*\s*", "", resp)
    resp = re.sub(r"\s*```$", "", resp)

    route, tail = None, resp
    lines = resp.splitlines()
    for idx, line in enumerate(lines):
        s = line.strip()
        if s.startswith("#"):
            route = re.sub(r"\s+", " ", s)
            tail = "\n".join(lines[idx + 1:])
            break
    if route is None:
        route = re.sub(r"\s+", " ", resp)
        if not route.startswith("#"):
            route = "# " + route
        tail = ""

    reason = ""
    for mk in ("[REASON]", "[REASONING]", "REASON:", "RATIONALE:",
               "【理由】", "理由：", "理由:"):
        if mk in tail:
            reason = tail.split(mk, 1)[1].strip()
            break
    return route, reason


def parse_tail_response(resp):
    """Step-2 reply -> trailing extra section (empty string when none is needed).

    Returns (extra, dropped) where dropped counts discarded explanatory lines.
    Gaussian input is pure ASCII, so any line containing CJK characters is a
    remark by the model rather than input, and is dropped.
    """
    text = (resp or "").strip()
    text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    if _is_none_token(text):
        return "", 1 if text else 0

    kept, dropped = [], 0
    for ln in text.splitlines():
        s = ln.strip()
        if not s:
            continue
        if re.search(r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]", s) or \
                s.lower().startswith(PROSE_PREFIXES):
            dropped += 1
            continue
        kept.append(ln.rstrip())
    body = "\n".join(kept).strip()
    if not body or _is_none_token(body.splitlines()[0]):
        return "", dropped + (1 if body else 0)
    return body, dropped


def reconcile_tail(route, extra, stem="", autofix=True):
    """Cross-check the route line against the trailing extra section.

    Returns (route, extra, notes, missing):
      notes   — corrections applied automatically / things worth a look (log)
      missing — items that cannot be filled in automatically (user must act)
    """
    route = (route or "").strip()
    extra = (extra or "").strip()
    notes, missing = [], []

    need_files = [(ext, kw) for rx, ext, kw in TAIL_FILE_RULES if rx.search(route)]
    need_blocks = [desc for rx, desc in TAIL_BLOCK_RULES if rx.search(route)]
    is_file_tail = bool(FILE_TAIL_RE.match(extra)) if extra else False

    # 1) the route asks for a file to be written but no file name is given
    if need_files and not is_file_tail:
        ext, kw = need_files[0]
        if extra:
            notes.append("The route contains %s but the trailing content is not a "
                         "file name — please check: %s" % (kw, extra))
        elif autofix:
            base = (stem or "").strip()
            if not base.isascii():  # non-ASCII names are awkward for Gaussian
                base = "wavefunction"
            name = base + ext
            extra = name
            notes.append("The route contains %s, so the trailing file name %s was "
                         "added automatically" % (kw, name))
        else:
            missing.append("the wavefunction file name at the end of the file "
                           "(route contains %s)" % kw)

    # 2) a file name is given but the route lacks the matching output= keyword
    if is_file_tail and not need_files:
        ext = "." + extra.rsplit(".", 1)[1].lower()
        kw = FILE_KW.get(ext)
        if kw:
            if autofix:
                route = route + " " + kw
                notes.append("The trailing file name %s requires the keyword %s, which "
                             "was added to the route line" % (extra, kw))
            else:
                missing.append("the keyword %s in the route line (a trailing file name "
                               "alone will not write that file)" % kw)
        else:
            notes.append("The trailing content is the file name %s but the route line "
                         "has no matching output= keyword — please check" % extra)

    # 3) the route asks for a trailing input block
    for desc in need_blocks:
        if not extra or is_file_tail:
            missing.append("the trailing input section: %s" % desc)
        elif "basis" in desc and "****" not in extra:
            notes.append("%s: sections are normally separated by **** — please check "
                         "that the block is complete" % desc)
        elif "genecp" in desc and extra.count("****") < 2:
            notes.append("genecp usually needs a basis section and a pseudopotential "
                         "section (at least two **** lines) — please check")

    if (
        extra
        and "genecp" not in route.lower()
        and re.search(r"(?<![A-Za-z])gen(?![A-Za-z])", route, re.I)
        and extra.count("****") >= 2
    ):
        notes.append("The route uses gen while the trailing content has several "
                     "sections; if a pseudopotential (ECP) section is among them, "
                     "change the keyword to genecp")

    return route, extra, notes, missing


def generate_route(api_key, base_url, model, task_desc):
    """Step 1: task description -> (route line, rationale)."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task_desc},
    ]
    resp = call_llm_chat(api_key, base_url, model, messages, max_tokens=2048)
    return parse_route_reason(resp)


def build_tail_user_msg(task_desc, route, stem=""):
    """Compose the step-2 input: task description + fixed route line (+ stem)."""
    parts = [
        "Task: %s" % (task_desc or "").strip(),
        "Route line (already fixed): %s" % (route or "").strip(),
    ]
    if stem and stem.isascii():
        parts.append("Output file stem (without extension): %s" % stem)
    return "\n".join(parts)


def generate_tail(api_key, base_url, model, task_desc, route, stem=""):
    """Step 2: decide and write the trailing extra input section.

    Returns (extra, notes) where notes are messages for the run log.
    """
    messages = [
        {"role": "system", "content": TAIL_SYSTEM_PROMPT},
        {"role": "user", "content": build_tail_user_msg(task_desc, route, stem)},
    ]
    resp, meta = call_llm_chat(
        api_key, base_url, model, messages, max_tokens=3000, with_meta=True
    )
    extra, dropped = parse_tail_response(resp)
    notes = []
    if meta.get("finish_reason") == "length":
        notes.append("WARNING: the AI reply hit the length limit — the extra section "
                     "may be truncated, please check it")
    elif dropped and not extra:
        notes.append("Note: the AI answered with prose, treated as \"no trailing content\"")
    return extra, notes


def append_keyword_record(route, path=None):
    """Append a generated route line to keywords.txt (program folder)."""
    path = path or KEYWORDS_FILE
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(path, "a", encoding="utf-8") as f:
        f.write("[%s] %s\n" % (ts, route))


# ---------------------------------------------------------------------------
# .gjf parsing / building
# ---------------------------------------------------------------------------
def parse_gjf_coordinates(path):
    """Parse a .gjf file; return (charge/multiplicity string, coords, title).

    Coordinates are (symbol, x, y, z). Any connectivity block after the
    coordinates is intentionally dropped.
    """
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = [ln.rstrip("\r\n") for ln in f]

    charge_mult, title = None, ""
    coords = []
    state = "start"  # start -> route -> title -> charge -> coords

    for ln in lines:
        s = ln.strip()
        if state == "start":
            if not s or s.startswith("%"):
                continue
            if s.startswith("#"):
                state = "route"
            elif CHARGE_RE.match(s):
                charge_mult = s
                state = "coords"
            else:
                continue
        elif state == "route":
            if s.startswith("#"):
                continue
            if not s:
                state = "title"
        elif state == "title":
            if not s:
                state = "charge"
            elif CHARGE_RE.match(s):
                charge_mult = s
                state = "coords"
            elif not title:
                title = s
        elif state == "charge":
            if CHARGE_RE.match(s):
                charge_mult = s
                state = "coords"
        elif state == "coords":
            if not s:
                break
            parts = s.split()
            if len(parts) >= 4:
                try:
                    x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                except ValueError:
                    continue
                coords.append((parts[0], x, y, z))

    if charge_mult is None:
        raise ValueError("No charge/multiplicity line found (e.g. '0 1')")
    if not coords:
        raise ValueError("No atomic coordinates could be extracted")
    return charge_mult, coords, title


def format_atom_line(symbol, x, y, z):
    """Format one atom line the way Gaussian expects (8 decimals)."""
    return "%s%16.8f%16.8f%16.8f" % (symbol.ljust(2), x, y, z)


def build_gjf(chk, nproc, mem, route, title, charge_mult, coords_block, extra_block=""):
    """Assemble the complete Gaussian input file text."""
    lines = []
    if chk:
        lines.append("%chk=" + chk)
    if nproc:
        lines.append("%nproc=" + nproc)
    if mem:
        lines.append("%mem=" + mem)
    lines.append(route)
    lines.append("")
    lines.append(title)
    lines.append("")
    lines.append(charge_mult)
    lines.append(coords_block)
    if extra_block and extra_block.strip().lower() not in ("", "none", "n/a"):
        lines.append("")
        lines.append(extra_block.strip())
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Settings dialog
# ---------------------------------------------------------------------------
class SettingsDialog(tk.Toplevel):
    """Server parameters (%nproc / %mem) + the user's own API credentials."""

    def __init__(self, master, cfg, on_save):
        super().__init__(master)
        self.cfg = cfg or {}
        self.on_save = on_save
        self.title("%s — Settings" % APP_NAME)
        set_window_icon(self)
        self.geometry("620x450")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        body = ttk.Frame(self, padding=12)
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)

        # ---- server parameters ----
        ttk.Label(
            body,
            text="Server parameters (written to the link-0 header of the .gjf file)",
            font=(UI_FONT, 9, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))

        self.nproc_var = tk.StringVar(value=str(self.cfg.get("nproc", "36")))
        self.mem_var = tk.StringVar(value=str(self.cfg.get("mem", "60GB")))

        ttk.Label(body, text="%nproc (CPU cores):").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Entry(body, textvariable=self.nproc_var).grid(row=1, column=1, sticky="ew", pady=2)
        ttk.Label(body, text="%mem (memory):").grid(row=2, column=0, sticky="w", pady=2)
        ttk.Entry(body, textvariable=self.mem_var).grid(row=2, column=1, sticky="ew", pady=2)

        # ---- AI service ----
        ttk.Separator(body, orient="horizontal").grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=10
        )
        ttk.Label(body, text="AI Service", font=(UI_FONT, 9, "bold")).grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(0, 4)
        )
        ttk.Label(
            body,
            text="This build contains no bundled credentials. Please enter your own\n"
                 "OpenAI-compatible API Key below; it is stored locally in\n"
                 "ai4Gauss_en_config.json.",
            foreground="#b35c00",
            justify="left",
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(0, 8))

        self.api_key_var = tk.StringVar(value=self.cfg.get("api_key", ""))
        self.base_url_var = tk.StringVar(value=self.cfg.get("base_url", DEFAULT_BASE_URL))
        self.model_var = tk.StringVar(value=self.cfg.get("model", DEFAULT_MODEL))

        ttk.Label(body, text="API Key:").grid(row=6, column=0, sticky="w", pady=2)
        self._key_entry = ttk.Entry(body, textvariable=self.api_key_var, show="*")
        self._key_entry.grid(row=6, column=1, sticky="ew", pady=2)
        ttk.Label(body, text="Base URL:").grid(row=7, column=0, sticky="w", pady=2)
        ttk.Entry(body, textvariable=self.base_url_var).grid(
            row=7, column=1, sticky="ew", pady=2
        )
        ttk.Label(body, text="Model name:").grid(row=8, column=0, sticky="w", pady=2)
        ttk.Entry(body, textvariable=self.model_var).grid(
            row=8, column=1, sticky="ew", pady=2
        )

        self.show_key_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            body, text="Show API Key", variable=self.show_key_var, command=self._toggle_show
        ).grid(row=9, column=1, sticky="w", pady=(2, 0))

        # ---- buttons ----
        btns = ttk.Frame(body)
        btns.grid(row=10, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        ttk.Button(btns, text="Load Settings File…", width=BTN_WIDTH_DLG,
                   command=self._load_file).pack(side="left", padx=(0, 6))
        ttk.Button(btns, text="Save As Settings File…", width=BTN_WIDTH_DLG,
                   command=self._save_as_file).pack(side="left")
        ttk.Button(btns, text="Save Settings", width=BTN_WIDTH_DLG,
                   command=self._save_default).pack(side="right", padx=(6, 0))
        ttk.Button(btns, text="Cancel", width=BTN_WIDTH_DLG,
                   command=self.destroy).pack(side="right")

        self.bind("<Return>", lambda e: self._save_default())

    def _toggle_show(self):
        self._key_entry.config(show="" if self.show_key_var.get() else "*")

    def _collect(self):
        return {
            "nproc": self.nproc_var.get().strip() or "36",
            "mem": self.mem_var.get().strip() or "60GB",
            "api_key": self.api_key_var.get().strip(),
            "base_url": self.base_url_var.get().strip() or DEFAULT_BASE_URL,
            "model": self.model_var.get().strip() or DEFAULT_MODEL,
        }

    def _save_default(self):
        cfg = self._collect()
        if not cfg["api_key"]:
            msg_warn(
                "API Key required",
                "No API Key was entered. This build has no bundled AI service, "
                "so an API Key is required before keywords can be generated.",
                parent=self,
            )
            return
        try:
            save_config(cfg)
        except OSError as e:
            msg_error("Save failed", str(e), parent=self)
            return
        self.on_save(cfg)
        msg_info("Done", "Settings saved.", parent=self)
        self.destroy()

    def _save_as_file(self):
        cfg = self._collect()
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Save parameters as a settings file",
            defaultextension=".json",
            initialfile="ai4Gauss_en_config.json",
            filetypes=[("JSON settings file", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            save_config(cfg, path)
        except OSError as e:
            msg_error("Save failed", str(e), parent=self)
            return
        msg_info("Done", "Saved to:\n%s" % path, parent=self)

    def _load_file(self):
        path = filedialog.askopenfilename(
            parent=self,
            title="Load a settings file",
            filetypes=[("JSON settings file", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        cfg = load_config(path)
        if not cfg:
            msg_warn(
                "Invalid file", "This is not a valid settings file (JSON).", parent=self
            )
            return
        self.nproc_var.set(str(cfg.get("nproc", "36")))
        self.mem_var.set(str(cfg.get("mem", "60GB")))
        self.api_key_var.set(cfg.get("api_key", ""))
        self.base_url_var.set(cfg.get("base_url", DEFAULT_BASE_URL))
        self.model_var.set(cfg.get("model", DEFAULT_MODEL))
        msg_info("Done", "Loaded:\n%s" % path, parent=self)


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------
class App:
    def __init__(self, root):
        self.root = root
        root.title("%s (%s)" % (APP_TITLE, APP_SUBTITLE))
        self._icon_applied = set_window_icon(root)   # replaces Tk's default feather icon
        root.geometry("1180x840")
        root.minsize(1020, 720)

        self.cfg = load_config()
        # Default working directory = program folder (the exe folder when frozen)
        self.workdir = BASE_DIR

        self._build_ui()
        self._log("%s v%s (%s) started" % (APP_NAME, APP_VERSION, APP_SUBTITLE))
        self._log("Window icon: %s" % ("custom icon applied" if self._icon_applied else "not applied (system default)"))
        self._log(
            "AI: %s  |  Server parameters: nproc=%s mem=%s"
            % (
                "custom API Key" if has_credentials(self.cfg) else "NOT CONFIGURED",
                self.cfg.get("nproc", "36"),
                self.cfg.get("mem", "60GB"),
            )
        )
        self._log("Run log will be saved to: %s" % BASE_DIR)
        if not has_credentials(self.cfg):
            self._log(
                "WARNING: no API Key found. Click 'Open Settings…' and enter your own "
                "API Key before generating keywords."
            )
        self._refresh_file_list()

        root.protocol("WM_DELETE_WINDOW", self._on_close)
        if not has_credentials(self.cfg):
            root.after(400, self._first_run_hint)

    # ---------- UI ----------
    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}
        outer = ttk.Frame(self.root, padding=10)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(0, weight=1)

        left = ttk.Frame(outer)
        left.grid(row=0, column=0, sticky="nsew")

        right = ttk.Frame(outer, width=380)
        right.grid(row=0, column=1, sticky="ns", padx=(10, 0))
        right.grid_propagate(False)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        # 0) Settings (top of the right column)
        f0 = ttk.LabelFrame(right, text="Settings (API & server)", padding=8)
        f0.pack(fill="x", **pad)
        ttk.Button(
            f0, text="⚙  Open Settings…", command=self._open_settings
        ).pack(fill="x", pady=2)
        self._cfg_hint = tk.StringVar(value=self._status_text())
        self._cfg_label = ttk.Label(
            f0, textvariable=self._cfg_hint, foreground="#0f6e56", wraplength=330
        )
        self._cfg_label.pack(anchor="w", pady=(2, 0))

        # 1) Task description -> keywords / extra section
        f2 = ttk.LabelFrame(
            left, text="1. Task description → AI keywords & trailing section", padding=8
        )
        f2.pack(fill="x", **pad)
        f2.columnconfigure(0, weight=1)

        ttk.Label(
            f2,
            text='Describe the job in plain text, e.g. "Single-point CCSD energy of water '
                 'with wavefunction output"',
        ).grid(row=0, column=0, sticky="w", pady=(0, 2))

        desc_row = ttk.Frame(f2)
        desc_row.grid(row=1, column=0, sticky="ew", pady=2)
        desc_row.columnconfigure(0, weight=1)
        self.task_text = tk.Text(desc_row, height=5, wrap="word", font=(UI_FONT, 9))
        self.task_text.grid(row=0, column=0, sticky="ew", pady=2)
        ttk.Button(
            desc_row,
            text="Generate Keywords with AI",
            width=BTN_WIDTH,
            command=self._gen_route,
        ).grid(row=0, column=1, sticky="e", padx=(10, 0), pady=2)

        kw = ttk.Frame(f2)
        kw.grid(row=2, column=0, sticky="ew", pady=(4, 0))
        kw.columnconfigure(0, weight=1)
        kw.columnconfigure(1, weight=1)

        ttk.Label(kw, text="Keywords (route, editable):").grid(
            row=0, column=0, sticky="w", pady=(2, 0)
        )
        tail_head = ttk.Frame(kw)
        tail_head.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=(2, 0))
        tail_head.columnconfigure(0, weight=1)
        ttk.Label(tail_head, text="Extra section at end of file (blank if none):").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Button(
            tail_head, text="Infer from route", width=17, command=self._regen_extra
        ).grid(row=0, column=1, sticky="e")
        self.route_text = tk.Text(kw, height=3, wrap="word", font=(MONO_FONT, 10))
        self.route_text.grid(row=1, column=0, sticky="nsew", pady=2)
        self.route_text.insert("1.0", "# B3LYP/6-31G*")
        self.extra_text = tk.Text(kw, height=3, wrap="word", font=(MONO_FONT, 10))
        self.extra_text.grid(row=1, column=1, sticky="nsew", padx=(10, 0), pady=2)

        # 2) Atomic coordinates
        f3 = ttk.LabelFrame(left, text="2. Atomic coordinates & charge / multiplicity", padding=8)
        f3.pack(fill="x", **pad)
        f3.columnconfigure(1, weight=1)

        ttk.Label(f3, text="Working directory:").grid(row=0, column=0, sticky="w", pady=2)
        self.dir_var = tk.StringVar(value=self.workdir)
        dir_entry = ttk.Entry(f3, textvariable=self.dir_var)
        dir_entry.grid(row=0, column=1, sticky="ew", pady=2)
        dir_entry.bind("<Return>", lambda e: self._refresh_file_list())
        ttk.Button(f3, text="Browse…", width=BTN_WIDTH,
                   command=self._browse_dir).grid(row=0, column=2, padx=6)

        body = ttk.Frame(f3)
        body.grid(row=1, column=0, columnspan=3, sticky="nsew", pady=(4, 0))
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        lf = ttk.Frame(body)
        lf.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        lf.columnconfigure(0, weight=1)
        lf.rowconfigure(0, weight=1)
        self.file_list = tk.Listbox(lf, height=9, exportselection=False)
        self.file_list.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(lf, orient="vertical", command=self.file_list.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.file_list.config(yscrollcommand=scroll.set)
        self.file_list.bind("<<ListboxSelect>>", self._on_file_select)

        rf = ttk.Frame(body)
        rf.grid(row=0, column=1, sticky="nsew")
        rf.columnconfigure(0, weight=1)
        rf.rowconfigure(1, weight=1)
        self.charge_var = tk.StringVar(value="0 1")
        ttk.Label(rf, text="Charge / multiplicity:").grid(row=0, column=0, sticky="w")
        self.charge_entry = ttk.Entry(rf, textvariable=self.charge_var, width=14)
        self.charge_entry.grid(row=0, column=1, sticky="w", pady=(0, 2))
        self.coord_text = tk.Text(rf, height=7, wrap="none", font=(MONO_FONT, 10))
        self.coord_text.grid(row=1, column=0, columnspan=2, sticky="nsew")
        cscroll = ttk.Scrollbar(rf, orient="vertical", command=self.coord_text.yview)
        cscroll.grid(row=1, column=2, sticky="ns")
        self.coord_text.config(yscrollcommand=cscroll.set)

        # 3) Generate and save
        f4 = ttk.LabelFrame(left, text="3. Generate & save the input file", padding=8)
        f4.pack(fill="x", **pad)
        f4.columnconfigure(1, weight=1)

        ttk.Label(f4, text="Output directory:").grid(row=0, column=0, sticky="w", pady=2)
        self.outdir_var = tk.StringVar(value=self.workdir)
        ttk.Entry(f4, textvariable=self.outdir_var).grid(
            row=0, column=1, sticky="ew", pady=2
        )
        ttk.Button(f4, text="Choose…", width=BTN_WIDTH,
                   command=self._browse_outdir).grid(row=0, column=2, padx=6)

        out_row = ttk.Frame(f4)
        out_row.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(2, 0))
        out_row.columnconfigure(1, weight=1)
        ttk.Label(out_row, text="Output file name:").grid(row=0, column=0, sticky="w", pady=2)
        self.outfile_var = tk.StringVar(value=self._default_outname())
        ttk.Entry(out_row, textvariable=self.outfile_var).grid(
            row=0, column=1, sticky="ew", pady=2, padx=(0, 6)
        )
        self.gen_btn = tk.Button(
            out_row,
            text="Generate .gjf File",
            width=BTN_WIDTH,
            command=self._generate,
            bg="#e8590c",
            fg="white",
            activebackground="#d84a05",
            activeforeground="white",
            relief=tk.RAISED,
            bd=1,
            font=(UI_FONT, 9, "bold"),
            cursor="hand2",
        )
        self.gen_btn.grid(row=0, column=2, sticky="e")

        # Author / contact line: read-only BUT selectable and copyable
        author_row = ttk.Frame(left)
        author_row.pack(anchor="w", fill="x", **pad)
        self.author_entry = _readonly_entry(
            author_row, AUTHOR_INFO, fg="#888888", font=(UI_FONT, 9)
        )
        self.author_entry.pack(fill="x", side="left", expand=True)

        # Right column: run log
        ttk.Label(right, text="Run log:").pack(anchor="w", padx=2, pady=(0, 4))
        log_frame = ttk.Frame(right)
        log_frame.pack(fill="both", expand=True)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.log_text = tk.Text(log_frame, width=48, state="disabled", wrap="word",
                                font=(UI_FONT, 9))
        log_scroll = ttk.Scrollbar(
            log_frame, orient="vertical", command=self.log_text.yview
        )
        self.log_scroll = log_scroll
        self.log_text.config(yscrollcommand=log_scroll.set)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        log_scroll.grid(row=0, column=1, sticky="ns")

    # ---------- settings ----------
    def _status_text(self):
        if has_credentials(self.cfg):
            return "API Key configured ✓"
        return "No API Key — open Settings to add your own ✗"

    def _refresh_status(self):
        self._cfg_hint.set(self._status_text())
        self._cfg_label.config(
            foreground="#0f6e56" if has_credentials(self.cfg) else "#c0392b"
        )

    def _open_settings(self):
        SettingsDialog(self.root, self.cfg, self._on_settings_saved)

    def _on_settings_saved(self, cfg):
        self.cfg = cfg
        self._refresh_status()
        self._log("Settings saved: nproc=%s mem=%s | model=%s"
                  % (cfg.get("nproc"), cfg.get("mem"), cfg.get("model")))

    def _first_run_hint(self):
        if has_credentials(self.cfg):
            return
        if ask_yes_no(
            "API Key required",
            "This build ships without any built-in AI service.\n\n"
            "Please enter your own OpenAI-compatible API Key in the Settings "
            "dialog before generating keywords.\n\nOpen Settings now?",
            parent=self.root,
        ):
            self._open_settings()

    # ---------- task description -> keywords ----------
    def _current_stem(self):
        """Stem of the current output file name (used to name the .wfn etc.)."""
        name = (self.outfile_var.get() or "").strip()
        name = os.path.basename(name)
        return os.path.splitext(name)[0] if name else ""

    def _apply_route_tail(self, route, extra, stem=""):
        """Write (route, extra) into the UI and cross-check them."""
        route, extra, notes, missing = reconcile_tail(route, extra, stem, autofix=True)
        self.route_text.delete("1.0", "end")
        self.route_text.insert("1.0", route)
        self.extra_text.delete("1.0", "end")
        if extra:
            self.extra_text.insert("1.0", extra)
        for n in notes:
            self._log("Note: %s" % n)
        if missing:
            self._log("WARNING — needs manual input: %s" % "; ".join(missing))
            msg_warn(
                "Please check the trailing extra section",
                "The route line and the trailing section do not fully match. "
                "Please add the following manually:\n\n- " + "\n- ".join(missing),
                parent=self.root,
            )
        return route, extra

    def _gen_route(self):
        """Step 1 generates the route line; step 2 derives the trailing section."""
        task = self.task_text.get("1.0", "end").strip()
        if not task:
            msg_warn("Missing input", "Please describe the task first.", parent=self.root)
            return
        try:
            api_key, base_url, model = resolve_credentials(self.cfg)
        except ValueError as e:
            msg_warn("API Key required", str(e), parent=self.root)
            self._log("Cannot call AI: %s" % e)
            self._open_settings()
            return

        self._log("Calling the AI to generate the route line…")
        try:
            route, reason = generate_route(api_key, base_url, model, task)
        except Exception as e:
            msg_error("AI request failed", str(e), parent=self.root)
            self._log("AI request failed: %s" % e)
            return

        stem = self._current_stem()
        self._log("Deriving the trailing extra section from the task and the route line…")
        extra = ""
        try:
            extra, notes = generate_tail(api_key, base_url, model, task, route, stem)
            for n in notes:
                self._log(n)
        except Exception as e:
            self._log("WARNING: could not derive the trailing section (%s) — "
                      "please check it manually" % e)

        route, extra = self._apply_route_tail(route, extra, stem)
        self._log("Route section: %s" % route)
        if extra:
            self._log("Extra section:\n%s" % extra)
        else:
            self._log("Extra section: none required")
        if reason:
            self._log("Rationale: %s" % reason)
        try:
            append_keyword_record(route)
            self._log("Route line appended to %s" % KEYWORDS_FILE)
        except OSError as e:
            self._log("Could not append to keywords.txt: %s" % e)

    def _regen_extra(self):
        """Re-derive the trailing section from the route line currently in the box."""
        route = self.route_text.get("1.0", "end").strip()
        if not route:
            msg_warn(
                "Missing keywords",
                "Generate or type the route line first.",
                parent=self.root,
            )
            return
        task = self.task_text.get("1.0", "end").strip()
        try:
            api_key, base_url, model = resolve_credentials(self.cfg)
        except ValueError as e:
            msg_warn("API Key required", str(e), parent=self.root)
            self._log("Cannot call AI: %s" % e)
            self._open_settings()
            return
        stem = self._current_stem()
        self._log("Re-deriving the trailing extra section from the current route line…")
        try:
            extra, notes = generate_tail(
                api_key, base_url, model, task or "(no task description given)",
                route, stem,
            )
            for n in notes:
                self._log(n)
        except Exception as e:
            msg_error("AI request failed", str(e), parent=self.root)
            self._log("AI request failed: %s" % e)
            return
        route, extra = self._apply_route_tail(route, extra, stem)
        self._log("Route section: %s" % route)
        if extra:
            self._log("Extra section:\n%s" % extra)
        else:
            self._log("Extra section: none required")
    # ---------- working directory / files ----------
    def _browse_dir(self):
        d = filedialog.askdirectory(
            initialdir=self.dir_var.get().strip() or self.workdir,
            title="Select the working directory",
        )
        if d:
            self.dir_var.set(d)
            self._refresh_file_list()

    def _refresh_file_list(self):
        d = self.dir_var.get().strip() or self.workdir
        if not os.path.isdir(d):
            msg_warn("Not found", "Directory does not exist: %s" % d)
            return
        self.workdir = d
        self.outdir_var.set(d)
        self.file_list.delete(0, "end")
        for fn in sorted(os.listdir(d)):
            if fn.lower().endswith(".gjf"):
                self.file_list.insert("end", fn)
        self._log("Scanned %s — %d .gjf file(s) found" % (d, self.file_list.size()))

    def _on_file_select(self, event=None):
        sel = self.file_list.curselection()
        if not sel:
            return
        name = self.file_list.get(sel[0])
        path = os.path.join(self.workdir, name)
        try:
            charge_mult, coords, title = parse_gjf_coordinates(path)
        except Exception as e:
            msg_error("Parse failed", str(e))
            return
        self.charge_var.set(charge_mult)
        self.coord_text.delete("1.0", "end")
        for sym, x, y, z in coords:
            self.coord_text.insert("end", format_atom_line(sym, x, y, z) + "\n")
        stem = os.path.splitext(name)[0]
        self.outfile_var.set(self._default_outname(stem))
        self._log("Extracted %d atom(s) from %s, charge/multiplicity = %s"
                  % (len(coords), name, charge_mult))
        if title:
            self._log("Original title line: %s" % title)

    def _default_outname(self, stem=None):
        stem = (stem or "output").strip() or "output"
        today = datetime.datetime.now().strftime("%Y%m%d")
        return "%s_%s.gjf" % (stem, today)

    def _browse_outdir(self):
        d = filedialog.askdirectory(
            initialdir=self.outdir_var.get().strip() or self.workdir,
            title="Select the output directory",
        )
        if d:
            self.outdir_var.set(d)

    # ---------- generate ----------
    def _generate(self):
        route = self.route_text.get("1.0", "end").strip()
        if not route:
            msg_warn(
                "Missing keywords",
                "The route section is empty — generate or type it first.",
                parent=self.root,
            )
            return
        charge_mult = self.charge_var.get().strip() or "0 1"
        coords_block = self.coord_text.get("1.0", "end").rstrip("\n")
        if not coords_block:
            msg_warn(
                "Missing coordinates",
                "No coordinates: select a .gjf file on the left or type them in manually.",
                parent=self.root,
            )
            return
        nproc = (self.cfg.get("nproc") or "").strip()
        mem = (self.cfg.get("mem") or "").strip()
        title = self._current_title()

        outname = self.outfile_var.get().strip() or self._default_outname()
        if not outname.lower().endswith(".gjf"):
            outname += ".gjf"
        stem = os.path.splitext(outname)[0]
        chk = "./%s.chk" % stem

        # Final cross-check with the real output file stem: fill in what is missing
        old_extra = self.extra_text.get("1.0", "end").strip()
        extra_block = old_extra
        route, extra_block, notes, missing = reconcile_tail(
            route, extra_block, stem, autofix=True
        )
        for n in notes:
            self._log("Note: %s" % n)
        if route != self.route_text.get("1.0", "end").strip():
            self.route_text.delete("1.0", "end")
            self.route_text.insert("1.0", route)
            self._log("Route line updated in the window to match the generated file")
        if extra_block != old_extra:
            self.extra_text.delete("1.0", "end")
            if extra_block:
                self.extra_text.insert("1.0", extra_block)
            self._log("Extra section updated in the window to match the generated file")
        if missing:
            self._log("WARNING — needs manual input: %s" % "; ".join(missing))
            if not ask_yes_no(
                "Route line and trailing section do not match",
                "It is recommended to add the following first. Generate anyway?\n\n- "
                + "\n- ".join(missing),
                parent=self.root,
            ):
                self._log("Generation cancelled")
                return

        outdir = self.outdir_var.get().strip() or self.workdir
        if not os.path.isdir(outdir):
            try:
                os.makedirs(outdir, exist_ok=True)
            except OSError as e:
                msg_error("Cannot create output directory", str(e), parent=self.root)
                return
        outpath = os.path.join(outdir, outname)

        content = build_gjf(
            chk, nproc, mem, route, title, charge_mult, coords_block, extra_block
        )
        try:
            with open(outpath, "w", encoding="utf-8", newline="\n") as f:
                f.write(content + "\n")
        except OSError as e:
            msg_error("Save failed", str(e), parent=self.root)
            return
        self._log("Input file written: %s" % outpath)
        self._log("-" * 60)
        self._log(content)
        self._log("-" * 60)
    def _current_title(self):
        t = self.task_text.get("1.0", "end").strip()
        first = re.split(r"[\n.;!?]", t)[0].strip() if t else ""
        if len(first) > 60:
            first = first[:60] + "…"
        return first or "Gaussian job"

    # ---------- log / exit ----------
    def _log(self, msg):
        self.log_text.config(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def _log_content(self):
        return self.log_text.get("1.0", "end").rstrip("\n")

    def _on_close(self):
        """Save the run log to the program folder as <timestamp>.log before exiting."""
        path = os.path.join(
            BASE_DIR, datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".log"
        )
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self._log_content() + "\n")
        except Exception as e:
            try:
                msg_warn(
                    "Could not save the log",
                    "The run log could not be written to:\n%s\n\nReason: %s" % (path, e),
                )
            except Exception:
                pass
        self.root.destroy()


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
