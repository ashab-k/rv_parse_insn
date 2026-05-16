# Comparing riscv-isa-manual with instructions listed in RISC-V Extensions Landscape

This is my solution for the coding challenge listed for the LFX mentorshit application.

We take extension tags from `instr_dict.json` (the Extensions Landscape instruction list) and check them against extension names in a local clone of [riscv-isa-manual](https://github.com/riscv/riscv-isa-manual).

Charts are in [riscv-extensions-landscape.pdf](riscv-extensions-landscape.pdf).

## How it works

```
instr_dict.json → analyze.py → output.json → compare.py → compare_output.json → report.py → PDF
```

**`analyze.py`** — For each instruction, read its `extension` list (e.g. `rv_i`, `rv64_zba`). Group instructions by tag, normalize names (`rv64_zba` → `zba`), and tag each as a real extension, a composite (`zba_zbb`), or a pseudo tag (`system`, `s`, `u`). Writes `output.json`.

**`compare.py`** — Scan the manual’s `src/**/*.adoc` for extension names: `ext:foo[]` / `[[ext:foo]]`, extension headings, and the preface table in `preface.adoc`. Compare those to canonical extensions from the landscape. Result buckets: matched, landscape-only, manual-only. Writes `compare_output.json`.

**`report.py`** — Builds the PDF from the JSON outputs (extension overlap, categories, instruction-name overlap, top extensions by count).

## Run

Clone the manual somewhere (default path is `~/riscv-isa-manual`).

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python analyze.py
python compare.py              # or: python compare.py --manual /path/to/riscv-isa-manual
python report.py
```

## Files

- `instr_dict.json` — input (landscape instructions + extension tags)
- `output.json`, `compare_output.json` — intermediate results
- `riscv-extensions-landscape.pdf` — summary report
