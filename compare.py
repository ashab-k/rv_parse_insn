import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

OUTPUT_PATH = Path("output.json")
COMPARE_OUT_PATH = Path("compare_output.json")
MANUAL_PATH = Path(sys.argv[sys.argv.index("--manual") + 1]) if "--manual" in sys.argv else Path.home() / "riscv-isa-manual"
JSON_PSEUDO = {"system", "s", "u"}


def classify(canonical: str) -> str:
    if canonical in JSON_PSEUDO:
        return "pseudo"
    if "_" in canonical:
        return "composite"
    return "extension"


def canonical_manual_name(name: str) -> str:
    return re.sub(r"\s+extensions?$", "", name.lower().replace("{asterisk}", "*").strip())


def is_plausible_extension_name(name: str) -> bool:
    if not name or "*" in name:
        return False
    if name in {"g", "j", "n", "x", "z", "zm"}:
        return False
    return bool(
        re.fullmatch(r"[a-z]", name)
        or re.fullmatch(r"z[a-z0-9]+", name)
        or re.fullmatch(r"s[dmshv][a-z0-9]+", name)
    )


def add_evidence(found, name, kind, file, line, text):
    canonical = canonical_manual_name(name)
    if not is_plausible_extension_name(canonical):
        return
    entry = found.setdefault(canonical, {"evidenceKinds": set(), "references": [], "_seen": set(), "defined": False})
    entry["evidenceKinds"].add(kind)
    if kind != "semantic-link":
        entry["defined"] = True
    rel = str(file.relative_to(MANUAL_PATH / "src")) if file else None
    key = (kind, rel, line, text)
    if key not in entry["_seen"]:
        entry["_seen"].add(key)
        entry["references"].append({"kind": kind, "file": rel, "line": line, "text": text})


def line_number_at(text, index):
    return text[:index].count("\n") + 1


def scan_inline_extensions(found, file, text):
    patterns = [
        ("anchor", re.compile(r"\[\[(?:ext:)([a-z0-9_]+)\]\]", re.I)),
        ("anchor", re.compile(r"\[#(?:ext:)([a-z0-9_]+)\]", re.I)),
        ("semantic-link", re.compile(r"\bext(?:link)?:([a-z][a-z0-9]*)\[\]", re.I)),
    ]
    for kind, pattern in patterns:
        for match in pattern.finditer(text):
            add_evidence(found, match.group(1), kind, file, line_number_at(text, match.start()), match.group(0))


def scan_extension_headings(found, file, lines):
    pattern = re.compile(r"^=+\s+(?:ext:([a-z0-9]+)\[\]\s+)?([A-Z][A-Za-z0-9]+)?(?:\s+and\s+ext:([a-z0-9]+)\[\])?.*\bExtensions?\b")
    for index, line in enumerate(lines, start=1):
        match = pattern.search(line)
        if not match:
            continue
        for name in match.groups():
            if name:
                add_evidence(found, name, "heading", file, index, line.strip())


def split_preface_cell(cell):
    cell = re.sub(r"[*_]", "", cell)
    cell = re.sub(r"\s+ISA$", "", cell, flags=re.I)
    cell = re.sub(r"\s+Extensions?$", "", cell, flags=re.I)
    return [canonical_manual_name(part) for part in cell.split("/")]


def scan_preface_tables(found, file, lines):
    if file.name != "preface.adoc":
        return
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == "|===")
        end = next(i for i, line in enumerate(lines[start + 1 :], start + 1) if line.strip() == "|===")
    except StopIteration:
        return
    for index in range(start + 1, end):
        line = lines[index]
        cells = re.findall(r"\|\*([^*]+)\*", line)
        if not cells:
            continue
        for cell in split_preface_cell(cells[0]):
            base = re.fullmatch(r"rv(?:32|64)([ie])", cell)
            if base:
                add_evidence(found, base.group(1), "preface-base", file, index + 1, line.strip())
            else:
                add_evidence(found, cell, "preface-table", file, index + 1, line.strip())


def scan_manual(manual_path: Path):
    src = manual_path / "src"
    if not src.exists():
        raise SystemExit(f"ERROR: {src} not found")
    found = {}
    for file in sorted(src.rglob("*.adoc")):
        text = file.read_text(errors="ignore")
        lines = text.splitlines()
        scan_inline_extensions(found, file, text)
        scan_extension_headings(found, file, lines)
        scan_preface_tables(found, file, lines)

    manual = {}
    for name, data in sorted(found.items()):
        refs = sorted(data["references"], key=lambda r: (r.get("file") or "", r.get("line") or 0, r.get("kind") or ""))[:8]
        manual[name] = {
            "evidenceKinds": sorted(data["evidenceKinds"]),
            "defined": bool(data["defined"]),
            "references": refs,
        }
    return manual


def json_summary(name, normalized):
    data = normalized[name]
    return {
        "jsonTags": sorted(data.get("rawTags", [])),
        "instructionCount": data.get("uniqueInstructionCount", data.get("count", 0)),
        "rawInstructionCount": data.get("count", 0),
        "kind": data.get("kind", classify(name)),
        "example": data.get("example"),
    }


def main():
    output = json.loads(OUTPUT_PATH.read_text())
    normalized = output["normalizedExtensions"]
    json_ext = sorted(name for name, data in normalized.items() if data.get("kind") == "extension")
    composite = sorted(name for name, data in normalized.items() if data.get("kind") == "composite")
    pseudo = sorted(name for name, data in normalized.items() if data.get("kind") == "pseudo")
    manual = scan_manual(MANUAL_PATH)
    manual_defined = sorted(name for name, data in manual.items() if data["defined"])
    mention_only = sorted(name for name, data in manual.items() if not data["defined"])

    json_set = set(json_ext)
    manual_set = set(manual_defined)
    matched = sorted(json_set & manual_set)
    json_only = sorted(json_set - manual_set)
    manual_only = sorted(manual_set - json_set)

    result = {
        "meta": {
            "builtAt": datetime.now(timezone.utc).isoformat(),
            "manualPath": str(MANUAL_PATH),
            "sourceInstructions": output["meta"]["totalInstructions"],
            "sourceRawExtensionTags": output["meta"]["totalRawExtensionTags"],
            "sourceCanonicalExtensions": len(json_ext),
            "manualExtensionCount": len(manual_defined),
            "matchedCount": len(matched),
            "jsonOnlyCount": len(json_only),
            "compositeTagCount": len(composite),
            "pseudoTagCount": len(pseudo),
            "manualOnlyCount": len(manual_only),
            "manualMentionOnlyCount": len(mention_only),
            "manualExtraction": [
                "AsciiDoc ext anchors: [[ext:name]] and [#ext:name]",
                "AsciiDoc semantic links are evidence only",
                "Extension headings",
                "Current preface module tables",
            ],
        },
        "matched": {name: {**json_summary(name, normalized), "manualEvidence": manual[name]} for name in matched},
        "jsonOnly": {name: json_summary(name, normalized) for name in json_only},
        "manualOnly": {name: manual[name] for name in manual_only},
        "compositeTags": {name: json_summary(name, normalized) for name in composite},
        "pseudoTags": {name: json_summary(name, normalized) for name in pseudo},
        "manualExtensions": manual,
        "manualMentionOnly": {name: manual[name] for name in mention_only},
    }
    COMPARE_OUT_PATH.write_text(json.dumps(result, indent=2))
    print(f"Wrote {COMPARE_OUT_PATH}")
    print(f"{len(matched)} matched | {len(json_only)} landscape-only | {len(manual_only)} manual-only")


if __name__ == "__main__":
    main()
