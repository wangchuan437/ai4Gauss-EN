# Examples

Two complete runs, from source file to finished `.gjf`. Everything in `outputs/` is a **real
result** produced by `src/ai4Gauss_en.py` talking to a live model — nothing was edited by hand
except the geometries, which are illustrative.

## inputs/ — the source files you feed the program

| File | Description |
|---|---|
| `H2O.gjf` | Water, equilibrium geometry, charge/multiplicity `0 1` |
| `Cu_NH3_4_2plus.gjf` | Tetraamminecopper(II) `[Cu(NH3)4]2+`, charge/multiplicity `2 1`, 17 atoms |

What they have in common: **you do not need a correct route line in them**. The program only takes
the charge/multiplicity and the coordinates; the route line is thrown away.

## outputs/ — what the program produced

### 1. `H2O_opt_wfn.gjf` (demonstrates `output=wfn`)

Task description used:

> Geometry optimization of the water molecule at B3LYP/6-31G(d), and also write the
> wavefunction file (wfn).

```text
%chk=./H2O_opt_wfn.chk
%nproc=36
%mem=60GB
# opt freq B3LYP/6-31G(d) nosymm output=wfn

water, B3LYP/6-31G(d) geometry optimization

0 1
O       0.00000000      0.00000000      0.11926200
H       0.00000000      0.76323900     -0.47704700
H       0.00000000     -0.76323900     -0.47704700

H2O_opt_wfn.wfn
```

Points worth noticing:

- `output=wfn` was added to the route line because the task asked for a wavefunction file;
- the wavefunction file name appears **on its own line after the coordinate block** — in Gaussian
  these two things must both be present, and the trailing name is the part people forget most often;
- `%chk` is derived from the output file stem, so it cannot collide with the source file.

### 2. `Cu_NH3_4_opt.gjf` (demonstrates `genecp`)

Task description used:

> Geometry optimization of [Cu(NH3)4]2+ using the SDD pseudopotential/basis for Cu and 6-31G(d)
> for N and H; a genecp section is required.

The route line becomes `#p opt freq B3LYP/genecp nosymm`, and a full basis-set / pseudopotential
definition block is appended at the end:

```text
Cu 0
SDD
****
N H 0
6-31G(d)
****
Cu 0
SDD
```

Reading the four fields: `Cu 0` + `SDD` (Cu uses general basis set 0, named SDD), `****` as the
separator, `N H 0` + `6-31G(d)` for nitrogen and hydrogen, another `****`, and finally the ECP
pseudopotential block for Cu (`Cu 0` / `SDD`).

> ⚠️ **Check this one yourself.** The basis-set / pseudopotential block is written by the model;
> the program cannot tell whether it suits your system. Equivalent spellings exist for SDD — follow
> your group's usual convention.

## Reproducing these results

```bash
python src/ai4Gauss_en.py
```

1. Copy the files from `inputs/` into an empty folder and set that folder as the **working
   directory**;
2. Click `H2O.gjf` in the list on the left — the coordinates and charge/multiplicity are filled in
   automatically;
3. Paste the task description above into the task box and click **Generate Keywords with AI**
   (two API calls: route line first, trailing section second);
4. Click **Generate .gjf File** to obtain `H2O_<date>.gjf` and compare it with
   `outputs/H2O_opt_wfn.gjf`.

The route lines and the extra section stay editable, so you can correct either one by hand before
generating. After editing the route line, click **Infer from route** next to the extra-section box
to re-derive the trailing content without calling the model again.
