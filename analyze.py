import json
from datetime import datetime, timezone
from pathlib import Path

INSTR_PATH = Path("instr_dict.json")
OUTPUT_PATH = Path("output.json")
JSON_PSEUDO = {"system", "s", "u"}


def normalize_tag(tag: str) -> str:
    for prefix in ("rv32_", "rv64_", "rv_"):
        if tag.startswith(prefix):
            return tag[len(prefix):].lower()
    return tag.lower()


def classify(canonical: str) -> str:
    if canonical in JSON_PSEUDO:
        return "pseudo"
    if "_" in canonical:
        return "composite"
    return "extension"


def validate_instruction(mnemonic, data, issues):
    if not isinstance(data, dict):
        issues.append({"mnemonic": mnemonic, "issue": "instruction entry is not an object"})
        return []
    exts = data.get("extension")
    if not isinstance(exts, list):
        issues.append({"mnemonic": mnemonic, "issue": "extension field is missing or is not an array"})
        return []
    if not exts:
        issues.append({"mnemonic": mnemonic, "issue": "extension array is empty"})
    seen = set()
    for ext in exts:
        if not isinstance(ext, str) or not ext:
            issues.append({"mnemonic": mnemonic, "issue": "extension tag is not a non-empty string", "value": ext})
            continue
        if not (ext.startswith("rv_") or ext.startswith("rv32_") or ext.startswith("rv64_")):
            issues.append({"mnemonic": mnemonic, "issue": "extension tag has unexpected shape", "value": ext})
        if ext in seen:
            issues.append({"mnemonic": mnemonic, "issue": "duplicate extension tag on instruction", "value": ext})
        seen.add(ext)
    return exts


def build_output():
    raw = json.loads(INSTR_PATH.read_text())
    issues = []
    extensions = {}
    normalized = {}
    multi_extension = {}

    for mnemonic, data in raw.items():
        exts = validate_instruction(mnemonic, data, issues)
        insn = mnemonic.upper()
        if len(exts) > 1:
            multi_extension[mnemonic] = exts

        for ext in exts:
            ext_entry = extensions.setdefault(ext, {"instructions": [], "count": 0, "example": insn})
            ext_entry["instructions"].append(insn)
            ext_entry["count"] += 1

            canonical = normalize_tag(ext)
            norm_entry = normalized.setdefault(
                canonical,
                {
                    "rawTags": [],
                    "instructions": [],
                    "count": 0,
                    "uniqueInstructionCount": 0,
                    "example": insn,
                    "kind": classify(canonical),
                },
            )
            if ext not in norm_entry["rawTags"]:
                norm_entry["rawTags"].append(ext)
            norm_entry["instructions"].append(insn)
            norm_entry["count"] += 1

    for entry in normalized.values():
        entry["rawTags"].sort()
        entry["instructions"] = sorted(set(entry["instructions"]))
        entry["uniqueInstructionCount"] = len(entry["instructions"])

    extensions = dict(sorted(extensions.items()))
    normalized = dict(sorted(normalized.items()))

    output = {
        "meta": {
            "totalInstructions": len(raw),
            "totalRawExtensionTags": len(extensions),
            "totalExtensions": sum(1 for e in normalized.values() if e["kind"] == "extension"),
            "totalCompositeTags": sum(1 for e in normalized.values() if e["kind"] == "composite"),
            "totalPseudoTags": sum(1 for e in normalized.values() if e["kind"] == "pseudo"),
            "multiExtensionCount": len(multi_extension),
            "validationIssueCount": len(issues),
            "builtAt": datetime.now(timezone.utc).isoformat(),
        },
        "extensions": extensions,
        "normalizedExtensions": normalized,
        "multiExtension": multi_extension,
        "validationIssues": issues,
    }
    OUTPUT_PATH.write_text(json.dumps(output, indent=2))
    return output


if __name__ == "__main__":
    result = build_output()
    meta = result["meta"]
    print(f"Wrote {OUTPUT_PATH}")
    print(
        f"{meta['totalInstructions']} instructions | "
        f"{meta['totalExtensions']} canonical extensions | "
        f"{meta['totalCompositeTags']} composite | "
        f"{meta['validationIssueCount']} validation issues"
    )
