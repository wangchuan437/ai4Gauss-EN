# ai4Gauss — Quick Start (English Edition, v1.0)

> **Note for this repository:** the compiled `ai4Gauss_en.exe` is **not** distributed here
> (single-file builds go to the Releases page). To run from source instead, use
> `python src/ai4Gauss_en.py` — the program itself is identical. Everything below still applies;
> just read "the exe's folder" as "the folder of the script".

**Developer**: chuan437 · **Email**: wangchuan437@126.com

**In one sentence**: describe your job in plain English, and the program builds a properly formatted
Gaussian input file (`.gjf`) for you.

> **This build does not bundle an AI service.** You supply your own OpenAI-compatible API Key once
> (see Section 1). After that, the workflow is the same as any other version.

---

## 1. First run (1 minute)

1. Put `ai4Gauss_en.exe` in the folder where your `.gjf` files live (the Desktop is fine too);
2. **Double-click it.** The first launch takes 3–5 seconds to unpack — this is normal, please wait;
3. Click **⚙  Open Settings…** in the top-right panel and fill in:

   | Field | What to enter |
   |---|---|
   | **%nproc (CPU cores)** | Number of cores your server will use, e.g. `36` |
   | **%mem (memory)** | Memory to request, e.g. `60GB` |
   | **API Key** | Your own key from an OpenAI-compatible provider, e.g. `sk-…` |
   | **Base URL** | The provider's endpoint, ending in `/v1`, e.g. `https://api.deepseek.com/v1` |
   | **Model name** | The model used for keyword generation, e.g. `deepseek-v4-flash` |

4. Click **Save Settings**. The status line turns green — **"API Key configured ✓"** — and you are
   ready to go. The file is stored as `ai4Gauss_en_config.json` next to the exe.

> Tip: if Windows Defender or an antivirus flags the program, this is a common false positive for
> PyInstaller-built executables. Choose "Run anyway", or add it to the trusted list.

> Note: with no key configured, the status line stays red
> (*"No API Key — open Settings to add your own ✗"*), and the program offers to open Settings for you
> at launch. Keyword generation is the only feature that needs a key.

---

## 2. Generating an input file (four steps)

| Step | Action |
|---|---|
| **1. Choose the working directory** | The **Working directory:** field defaults to the exe's own folder. All `.gjf` files in it are listed on the left; click **Browse…** to switch folders |
| **2. Take the atomic coordinates** | Click a `.gjf` on the left. The program extracts the **Charge / multiplicity:** line and **all atomic coordinates** and reformats them to the standard layout (8 decimal places). No existing file? Paste the coordinates by hand |
| **3. Let the AI write the keywords** | Describe the job in the large box — e.g. *"Geometry optimization of [Cu(NH3)4]2+ with the SDD pseudopotential for Cu and 6-31G(d) for N and H"* — then click **Generate Keywords with AI** |
| **4. Generate the file** | Check the **Output directory:** and **Output file name:** fields, then click the orange **Generate .gjf File** button |

The generated file **never overwrites** your original: the new name automatically carries a date
suffix, e.g. `input1_20260911.gjf`.

---

## 3. What the AI returns (in two steps)

After you click **Generate Keywords with AI** the model is called **twice**, which makes the trailing
section far more reliable:

1. **Step 1**: task description → the **route line**, plus the reasoning behind it;
2. **Step 2**: task description + the route line from step 1 → the **extra section at the end of the
   file** (e.g. the wavefunction file name `mol.wfn` required by `output=wfn`, or a `gen`/`genecp`
   basis-set definition block).

| AI output | Where it goes | Written into the `.gjf`? |
|---|---|---|
| **Route line** (starts with `#`) | the **Keywords (route, editable):** box | ✅ yes |
| **Extra section** | the **Extra section at end of file:** box | ✅ yes (skipped if empty) |
| **Reasoning** for that level of theory | the **Run log:** panel on the right | ❌ reference only |

**Automatic consistency check**: before the results reach the interface the program cross-checks the
route line against the extra section and fills in obvious gaps, for example:

- route contains `output=wfn` / `out=wfn` (or `wfx`) but no file name is given → the name is added
  automatically from the output file stem, e.g. `xxx.wfn`;
- a trailing `xxx.wfn` is given but the route lacks `output=wfn` → the keyword is added automatically
  (a file name alone will not write that file);
- the route contains `gen` / `genecp` while the extra section is empty (a basis-set definition cannot
  be generated reliably) → you are asked to fill it in.

Every automatic fix or warning is written to the run log on the right.

**"Infer from route" button**: after editing the route line by hand, click it next to the extra-section
box to re-derive the trailing content from the current route line — no need to repeat step 1.

To see *why* the AI picked a particular functional or basis set, read the run log on the right.

---

## 4. Default values in the interface

| Item | Default | Notes |
|---|---|---|
| Keywords | `# B3LYP/6-31G*` | Editable; overwritten once the AI generates new ones |
| Charge / multiplicity | `0 1` | Neutral singlet. Change as needed for ions or radicals (e.g. `1 2`, `-1 1`) |
| Output file name | `<original name>_<date>.gjf` | e.g. `input1_20260911.gjf` |
| `%chk` | Derived from the output file name | `input1_20260911.gjf` → `%chk=./input1_20260911.chk` |
| Output directory | the working directory | Can be changed; created automatically if it does not exist |

---

## 5. Two files the program keeps automatically

* **`keywords.txt`** — every route line generated by the AI is appended here with a timestamp, so you
  can look back at the levels of theory you have used;
* **`<timestamp>.log`** — when you close the window, the entire run log is saved into the folder
  containing the **exe** (e.g. `20260911_155749.log`), not into the working directory.

---

## 6. Frequently asked questions

**Q1: I double-clicked and nothing happened.**
The first launch needs 3–5 seconds to unpack. If there is still no window after 10 seconds, an
antivirus tool has most likely blocked it — check its quarantine list.

**Q2: "AI request failed (HTTP …)" — what now?**
First check that your network is working. Then check the obvious causes:

| Code | Usual cause |
|---|---|
| `401` | Wrong or expired API Key |
| `403` | The key has no permission for that model, or the account has no credit |
| `404` | Wrong **Base URL** — it must point at the `/v1` root, e.g. `https://api.deepseek.com/v1` |

If the key is fine, remember that API usage is billed by **your** provider, and the account must have
a positive balance.

**Q3: The coordinate box is empty, or I get "No atomic coordinates could be extracted".**
Unusual source formats (such as Z-matrix internal coordinates) cannot be parsed. Type the coordinates
into the box manually — one per line, formatted as `element x y z` separated by spaces.

**Q4: I don't want the AI's keywords — can I write my own?**
Yes. Just edit the **Keywords (route, editable):** box directly. The line must start with `#`
(e.g. `#p B3LYP/def2-TZVP opt freq`).

**Q5: Can I use it offline?**
Everything except **Generate Keywords with AI** works completely offline: coordinate parsing, server
parameters and file generation. You can also write the route line by hand.

---

## 7. Please note

* This software is **free** for study and research. Do not resell it or use it commercially;
* This build ships **no** bundled AI service, so AI usage is billed to your own API account — keep an
  eye on your provider's quota and do not hammer the endpoint;
* Always verify the keywords and the coordinates yourself before submitting a job to the server;
* The `.chk` file is produced by Gaussian while the job runs on the server — you do not need to create
  it by hand.

---

**Developer**: chuan437 · **Email**: wangchuan437@126.com