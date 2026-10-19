// The caller supplies only the Codex bundled Node/artifact-tool runtime.
// XML verification is in local_excel.py; this is the sole XLSX author.
import fs from "node:fs/promises";
import {FileBlob, SpreadsheetFile} from "@oai/artifact-tool";

const plan = JSON.parse(await fs.readFile(process.argv[2], "utf8"));
const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(plan.source));
if (plan.verify_only) {
  console.log(JSON.stringify({provider: "local_xlsx", engine: "@oai/artifact-tool", reopened: true}));
  process.exit(0);
}
const jobHeaders = workbook.worksheets.getItem("Jobs").getRange("A4:AZ4").values[0];
for (const change of plan.changes) {
  const cell = workbook.worksheets.getItem(change.tab).getCell(change.row, change.column);
  const value = change.after;
  if ("formulaValue" in value && value.formulaValue.startsWith("=HYPERLINK(")) cell.values = [["Open job"]];
  else if ("formulaValue" in value) cell.formulas = [[value.formulaValue]];
  else {
    let entered = value.stringValue ?? value.numberValue ?? value.boolValue ?? null;
    // Artifact coerces ISO text to Date even with @ formatting. A constant
    // string formula preserves its exact text, offset and fractional seconds.
    if (typeof entered === "string") {
      cell.setNumberFormat("@");
      if (/^\d{4}-\d{2}-\d{2}(?:T|$)/.test(entered)) {
        cell.formulas = [['="' + entered.replaceAll('"', '""') + '"']];
        continue;
      }
      if (entered.startsWith("=")) entered = "'" + entered;
    }
    cell.values = [[entered]];
  }
  if (change.tab === "Jobs" && ["First Seen", "Last Seen"].includes(jobHeaders[change.column])) cell.setNumberFormat("yyyy-mm-dd");
  if (change.tab === "Jobs" && jobHeaders[change.column] === "Application Status") cell.dataValidation = {rule: {type: "list", values: plan.statuses}};
}
if (plan.initialize) {
  // The stock template supplies the native formatting, validation and panes.
  workbook.worksheets.getItem("How to Use").getRange("B11").values = [["A job is saved only after the configured tracker is reopened/read back and its values and role-specific links are verified."]];
}
workbook.recalculate();
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(plan.destination);
// Reimport the saved output with the authoring engine as well as independent
// OOXML inspection by Python. Never accept an in-memory model as save proof.
const reopened = await SpreadsheetFile.importXlsx(await FileBlob.load(plan.destination));
for (const change of plan.changes) {
  const cell = reopened.worksheets.getItem(change.tab).getCell(change.row, change.column);
  if ("formulaValue" in change.after && !change.after.formulaValue.startsWith("=HYPERLINK(") && cell.formulas[0][0] !== change.after.formulaValue) throw new Error("Saved formula differs from plan");
}
console.log(JSON.stringify({provider: "local_xlsx", engine: "@oai/artifact-tool", reopened: true}));
