# Changelog

## v1.0 — first public release

**English build (`src/ai4Gauss_en.py`)**

- **Two-step keyword generation**: step 1 turns the plain-English task description into the
  route line plus the rationale for the chosen level of theory; step 2 receives that fixed route
  line and produces the trailing section (the `.wfn`/`.wfx` file name required by
  `output=wfn`/`output=wfx`, or a `gen`/`genecp` basis-set and pseudopotential block);
- **Consistency check** between route line and trailing section, with automatic filling of obvious
  gaps (a missing trailing file name, a missing `output=` keyword). Cases that cannot be filled in
  reliably — `gen`/`genecp` with an empty definition block — raise a log message and a warning
  instead of a silent guess;
- **Coordinate extraction** from an existing `.gjf`: charge / multiplicity plus every atom,
  reformatted to the standard 8-decimal Gaussian layout. Route sections, titles and connectivity
  blocks of the source file are intentionally discarded;
- **Never overwrites**: the generated name carries a date suffix, e.g. `input1_20260920.gjf`;
- **Server parameters** (`%nproc` / `%mem`) configurable in the Settings dialog, stored in
  `ai4Gauss_en_config.json`; **Load / Save As** lets you keep several provider profiles;
- **Self-drawn dialogs** (`_EnDialog`): button captions stay English regardless of the system
  locale, even on a Chinese Windows installation;
- Every generated route line is appended to `keywords.txt`; the full run log is written to
  `<timestamp>.log` when you close the window;
- Custom window icon (`ai4Gauss_en.ico`), embedded into the exe at build time.

**No bundled credentials**

- The English build ships with **no** API key and no AI service. You enter your own
  OpenAI-compatible key once; requests go straight from your machine to the provider you configured.

**Packaging**

- Standard-library only, so `pyinstaller --onefile --windowed` is all it takes
  (see [docs/BUILD.md](docs/BUILD.md));
- `--add-data "ai4Gauss_en.ico;."` is required, otherwise the window title bar falls back to the
  default Tk feather logo when the exe is distributed on its own.

**Known limitations**

- The interface has only been tested on Windows;
- `gen` / `genecp` definition blocks are model-generated — review them before submitting a job;
- Batch generation over a whole working directory, and the externally editable AI prompt
  (`system_prompt`), exist in the Chinese build only and are not yet ported here.
