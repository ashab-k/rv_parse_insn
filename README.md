# rv_parse_insn

Compare RISC-V extension tags on instructions (`instr_dict.json`) against extensions named in the [RISC-V ISA manual](https://github.com/riscv/riscv-isa-manual) AsciiDoc sources.

**Report:** [riscv-extensions-landscape.pdf](riscv-extensions-landscape.pdf) (bar charts: extension overlap, landscape categories, instruction-name overlap, top extensions by insn count). Regenerate with `report.py` after the steps below.

## Inputs

| File | What it is |
|------|------------|
| `instr_dict.json` | Instruction dictionary; each entry has an `extension` array (e.g. `rv_i`, `rv64_zba`). |
| `~/riscv-isa-manual` (default) | Cloned ISA manual repo; comparison reads `src/**/*.adoc`. Override with `--manual /path/to/riscv-isa-manual`. |

## Pipeline

```text
instr_dict.json
      │
      ▼  analyze.py
 output.json          ← group by extension tag, normalize names, classify tags
      │
      ▼  compare.py   (+ manual .adoc scan)
 compare_output.json  ← matched / json-only / manual-only extensions
      │
      ▼  report.py
 riscv-extensions-landscape.pdf
```

### 1. Extract extensions from instructions — `analyze.py`

- Read every mnemonic in `instr_dict.json`.
- For each instruction, read `extension` (must be a non-empty list of strings like `rv_*`, `rv32_*`, `rv64_*`).
- Bucket instructions under each raw tag; also bucket under a **canonical** name: strip `rv32_` / `rv64_` / `rv_` prefix and lowercase (e.g. `rv64_zba` → `zba`).
- **Classify** canonical names:
  - `extension` — single-letter or `z*` / `s*` style name
  - `composite` — contains `_` (e.g. `zba_zbb`)
  - `pseudo` — `system`, `s`, `u`
- Write `output.json` (`extensions`, `normalizedExtensions`, validation issues).

### 2. Compare to the manual — `compare.py`

**Manual side** — walk all `src/**/*.adoc` and collect extension names from:

| Source | Pattern / rule |
|--------|----------------|
| Inline anchors | `[[ext:name]]`, `[#ext:name]`, `ext:name[]`, `extlink:name[]` |
| Headings | lines like `=== ext:foo[] … Extension` |
| Preface table | rows in `preface.adoc` between `\|===` (base ISA `i`/`e`, plus listed extensions) |

Names are normalized (lowercase, strip trailing “ Extension(s)”). Junk names (`g`, `x`, `*`, etc.) are dropped. Each hit keeps file, line, and match text.

**Landscape side** — canonical names from `output.json` where `kind == "extension"`.

**Sets:**

- **matched** — in both landscape and manual (manual has a defining hit, not link-only)
- **jsonOnly** — in landscape only
- **manualOnly** — in manual only

Also lists `compositeTags`, `pseudoTags`, and manual mention-only extensions. Writes `compare_output.json`.

### 3. Charts — `report.py`

Loads `instr_dict.json`, `output.json`, `compare_output.json`; optionally counts unique `insn:…` references in the manual. Writes `riscv-extensions-landscape.pdf`.

## Run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python analyze.py
python compare.py                    # needs ~/riscv-isa-manual or --manual PATH
python report.py                     # same --manual if not default path
```

Commit or open [riscv-extensions-landscape.pdf](riscv-extensions-landscape.pdf) in the repo root after `report.py`. GitHub does not embed PDFs inside the README; use the link above or download the file.

## Outputs

| File | Contents |
|------|----------|
| `output.json` | Per-tag and per-canonical-extension instruction lists and counts |
| `compare_output.json` | Extension set diff + manual evidence snippets |
| `riscv-extensions-landscape.pdf` | Summary charts |
