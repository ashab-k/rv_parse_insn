import fs from "fs";
import Table from "cli-table3";

const INSTR_PATH = "./instr_dict.json";
const OUTPUT_PATH = "./output.json";
const FORCE_BUILD = process.argv.includes("--build");


function buildOutput() {
  console.log("Parsing Instr_Dictionary.json...");
  const raw = JSON.parse(fs.readFileSync(INSTR_PATH, "utf-8"));

  // ext → { instructions: string[], count: number, example: string }
  const extensions = {};
  // mnemonic → string[] (only those with >1 extension)
  const multiExtension = {};

  for (const [mnemonic, data] of Object.entries(raw)) {
    const exts = data.extension ?? [];

    if (exts.length > 1) {
      multiExtension[mnemonic] = exts;
    }

    for (const ext of exts) {
      if (!extensions[ext]) {
        extensions[ext] = { instructions: [], count: 0, example: mnemonic.toUpperCase() };
      }
      extensions[ext].instructions.push(mnemonic.toUpperCase());
      extensions[ext].count++;
    }
  }

  // Sort extensions alphabetically
  const sortedExtensions = Object.fromEntries(
    Object.entries(extensions).sort(([a], [b]) => a.localeCompare(b))
  );

  const output = {
    meta: {
      totalInstructions: Object.keys(raw).length,
      totalExtensions: Object.keys(extensions).length,
      multiExtensionCount: Object.keys(multiExtension).length,
      builtAt: new Date().toISOString(),
    },
    extensions: sortedExtensions,
    multiExtension,
  };

  fs.writeFileSync(OUTPUT_PATH, JSON.stringify(output, null, 2));
  console.log(`Written to ${OUTPUT_PATH}\n`);
  return output;
}


function printOutput(output) {
  const { meta, extensions, multiExtension } = output;

  // Header
  console.log("═".repeat(70));
  console.log(" RISC-V Instruction Set Analysis");
  console.log("═".repeat(70));
  console.log(`  Total instructions : ${meta.totalInstructions}`);
  console.log(`  Total extensions   : ${meta.totalExtensions}`);
  console.log(`  Multi-ext instrs   : ${meta.multiExtensionCount}`);
  if (meta.builtAt) console.log(`  Built at           : ${meta.builtAt}`);
  console.log("═".repeat(70) + "\n");

  // Extension summary table
  const table = new Table({
    head: ["Extension", "Count", "Example Mnemonic"],
    colWidths: [22, 10, 22],
    style: { head: ["cyan"] },
  });

  for (const [ext, data] of Object.entries(extensions)) {
    table.push([ext, data.count, data.example]);
  }

  console.log(table.toString());

  // Multi-extension instructions
  console.log("\n── Instructions belonging to multiple extensions ──\n");

  if (Object.keys(multiExtension).length === 0) {
    console.log("  None found.");
  } else {
    const multiTable = new Table({
      head: ["Mnemonic", "Extensions"],
      colWidths: [22, 48],
      style: { head: ["yellow"] },
    });

    for (const [mnemonic, exts] of Object.entries(multiExtension)) {
      multiTable.push([mnemonic.toUpperCase(), exts.join(", ")]);
    }

    console.log(multiTable.toString());
  }
}


function main() {
  let output;

  if (FORCE_BUILD || !fs.existsSync(OUTPUT_PATH)) {
    if (FORCE_BUILD) console.log("--build flag set, rebuilding...\n");
    output = buildOutput();
  } else {
    console.log(`output.json found, reading from cache...\n`);
    output = JSON.parse(fs.readFileSync(OUTPUT_PATH, "utf-8"));
  }

  printOutput(output);
}

main();
