# ai4Gauss v1.0 — Gaussian Input File Generator

*Developer: chuan437 · Email: wangchuan437@126.com*

**English Edition**

`ai4Gauss` helps you build a complete Gaussian (`.gjf`) input file in a few clicks. You describe
the job in plain English, the AI proposes an appropriate route section, and the program combines it
with atomic coordinates taken from an existing `.gjf` file and with your server parameters.

> **Note for this repository:** the compiled `ai4Gauss_en.exe` is **not** distributed here
> (single-file builds go to the Releases page). To run from source instead, use
> `python src/ai4Gauss_en.py` — the program itself is identical. Read "the exe's folder" below as
> "the folder of the script".

> **This build contains no bundled AI service.** You must supply your own OpenAI-compatible API Key
> the first time you run the program (see [Step 1](#step-1--enter-your-api-key-one-time)).

---

## 1. Running the program

| | |
|---|---|
| **`ai4Gauss_en.exe`** | Standalone, 64-bit Windows. No Python installation needed. Just double-click. |
| **`src/ai4Gauss_en.py`** | Source code (standard library only). Run with `python src/ai4Gauss_en.py` — Python 3.8+ with tkinter. |

The folder that contains the `.exe` is used as the **default working directory** at start-up, so the
simplest setup is: put `ai4Gauss_en.exe` in (or next to) the folder holding your `.gjf` files.

Files the program may create — all in the exe's own folder, never in a hidden cache:

| File | Created when | Notes |
|---|---|---|
| `ai4Gauss_en_config.json` | You save Settings | Your API Key, Base URL, model, `nproc`, `mem`. Treat it as a secret. |
| `keywords.txt` | After every successful AI call | Timestamped history of generated route lines. Safe to delete. |
| `<timestamp>.log` | When you close the window | The full run log of that session. |

---

## 2. Step 1 — Enter your API Key (one time)

Click **⚙ Open Settings…** in the top-right panel.

| Field | Meaning | Typical value |
|---|---|---|
| `%nproc (CPU cores)` | Written to the `.gjf` header as `%nproc=` | `36` |
| `%mem (memory)` | Written to the `.gjf` header as `%mem=` | `60GB` |
| **API Key** | Your own key from any OpenAI-compatible provider | `sk-…` |
| **Base URL** | The provider's endpoint (must end with `/v1`) | `https://api.deepseek.com/v1` |
| **Model name** | The model identifier for keyword generation | `deepseek-v4-flash` |

Then click **Save Settings** (stored as `ai4Gauss_en_config.json`) — or use
**Save As Settings File…** to keep several profiles (e.g. one per provider) and
**Load Settings File…** to switch between them later.

Notes:

* The API key is **required**: the status line under the button stays red
  (*"No API Key — open Settings to add your own ✗"*) until a key is saved.
* If you start the program with no key configured, it offers to open Settings for you.
* The keystrokes are sent directly to the provider you configured. Nothing is routed through
  any third-party server.
* **Show API Key** reveals what you typed, in case of a copy-paste mistake.

---

## 3. Step 2 — Describe the job, let the AI write the keywords

1. Type a plain-language description into the large box, for example:

   > Geometry optimization and frequency calculation of [Cu(NH3)4]2+ with the SDD
   > pseudopotential for Cu and 6-31G(d) for N and H

2. Click **Generate Keywords with AI**. The program calls the model **twice**, so that the trailing
   section is derived from the finished route line instead of being guessed at the same time:

   * **step 1** — task description → the **route line** + the rationale;
   * **step 2** — task description + that route line → the **extra section at the end of the file**
     (e.g. the wavefunction file name required by `output=wfn`, or a `gen`/`genecp` definition block).

| AI output | Where it goes |
|---|---|
| **Route line** (starts with `#`) | → the **Keywords (route)** box |
| **Extra section** | → the **Extra section at end of file** box |
| **Rationale** for the chosen level of theory | → the **run log** only (not written into the file) |

   The two results are then cross-checked and obvious gaps are filled in automatically: a route with
   `output=wfn`/`output=wfx` but no file name gets `xxx.wfn` added from the output file stem, and a
   trailing file name whose `output=` keyword is missing from the route line gets the keyword added.
   Cases that cannot be filled in reliably (for example `gen`/`genecp` with an empty definition
   block) raise a message in the run log and a warning dialog. All of this is logged.

3. Everything is editable. If you prefer to write the route line yourself, just type it in —
   the default is `# B3LYP/6-31G*` — and then click **Infer from route** next to the extra-section
   box to derive the trailing content from your route line.

The rationale is a useful sanity check before you spend CPU hours: if the model explains that it
chose `B3LYP/6-31G(d)` because it assumed a closed-shell singlet, and that is not your system,
adjust the route line or make the task description more specific.

---

## 4. Step 3 — Load the atomic coordinates

* **Working directory** — defaults to the exe's folder. Type a path and press **Enter**, or click
  **Browse…**. All `.gjf` files in that folder are listed on the left.
* Click a file name: the program extracts the **charge / multiplicity** line and the
  **coordinate block**, reformats the coordinates to the standard 8-decimal Gaussian layout, and
  pre-fills the output file name as `<input name>_<today's date>.gjf`.

Both the charge/multiplicity field and the coordinate box can be edited by hand. If there is no
suitable `.gjf` to start from, paste the coordinates in directly.

> Only the geometry is taken over. Any original route section, title, connectivity or extra block
> is intentionally discarded, because you are creating a **new** job.

---

## 5. Step 4 — Generate the file

| Field | Meaning |
|---|---|
| **Output directory** | Where the new `.gjf` is written (defaults to the working directory; created automatically if missing) |
| **Output file name** | Default `<input name>_<date>.gjf`. The `%chk` name is derived from it: `input1_20260911.gjf` → `%chk=./input1_20260911.chk`. Rename the file if you want a different checkpoint name. |

Click **Generate .gjf File**. The complete content is echoed into the run log so you can verify it
before submitting the job.

The generated file has this structure:

```
%chk=./input1_20260911.chk        ← derived from the output file name
%nproc=36                         ← Settings
%mem=60GB                         ← Settings
#p B3LYP/gen opt freq             ← Keywords box (AI)
                                  ← blank line (required)
Optimize [Cu(NH3)4]2+ at B3LYP    ← first line of your task description
                                  ← blank line (required)
0 1                               ← charge / multiplicity
Cu       0.00000000    0.00000000    0.00000000
N        ...                          ← coordinate block (8 decimals)
...
                                  ← blank line before the extra section
Cu 0                              ← Extra section box (AI), only if non-empty
SDD
****
N H 0
6-31G(d)
****
```

---

## 6. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| *"No API Key configured"* | Open Settings and save a key. |
| `AI request failed (HTTP 401)` | Wrong or expired API Key. |
| `AI request failed (HTTP 403)` | Key has no permission for that model, or the account has no credit. |
| `AI request failed (HTTP 404)` | Wrong **Base URL** — it must point at the `/v1` root, e.g. `https://api.deepseek.com/v1`. |
| `Network error` | No internet access, a proxy, or a firewall blocking outbound HTTPS. |
| The file list is empty | No `.gjf` files in that folder, or the path is wrong. Type a correct path and press Enter. |
| *"No atomic coordinates could be extracted"* | The selected file has no recognisable coordinate block (needs `element x y z`). Paste the coordinates manually instead. |
| No `.log` file after closing | The log is written next to the **exe**, not in the working directory. If the window cannot be closed cleanly, check that the folder is writable. |
| The route line is not what you expected | Make the task description more specific (functional, basis set, charge/multiplicity, environment), or overwrite the route line by hand. |

---

## 7. Practical advice

* **Check the AI's route line before submitting a long job.** The model's choice is a suggestion,
  not a peer-reviewed protocol.
* **Keep one `.gjf` that already has correct coordinates.** It is the fastest way to reuse an
  optimised geometry for a new property calculation.
* **Read the rationale in the log.** It is the cheapest way to catch a mis-specified system.
* **Do not share your `ai4Gauss_en_config.json`.** It contains your API Key in plain text.

---

*Developer: chuan437 · Email: wangchuan437@126.com*