// Optional maintainer operation; ordinary setup imports the checked-in XLSX.
// Run with the Codex bundled Node/artifact-tool runtime, not an npm install.
import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const [schemaPath, outputPath, previewDir] = process.argv.slice(2);
if (!schemaPath || !outputPath) throw new Error("Pass schema JSON, output XLSX, and optional preview directory");
const schema = JSON.parse(await fs.readFile(schemaPath, "utf8"));
const wb = Workbook.create();
const navy = "#17324D", teal = "#0D766E", pale = "#EEF6F8", gray = "#536579";
const column = (index) => {
  let name = "";
  for (let n = index + 1; n > 0; n = Math.floor((n - 1) / 26)) name = String.fromCharCode(65 + (n - 1) % 26) + name;
  return name;
};
const descriptions = {
  "Jobs": "All sources share this tracker. Update status and notes; the coordinator preserves your edits.",
  "Daily Summary": "Live counts from the shared Jobs tracker. Source coverage is recorded separately.",
  "Referral Watchlist": "Your referral companies and contacts. Keep personal details in your own workbook.",
  "How to Use": "One place for discoveries. Clear receipts for what was saved and delivered.",
  "Rated Companies": "Your supplied Blind 3.5+ list. Ratings are user-supplied, dated research inputs.",
  "Rated Search Coverage": "Search scope and completeness for each company and run, including blocked sources.",
  "Job Sources": "Provenance for qualified source sightings. Avoid editing these managed rows by hand."
};
for (const tab of schema.tabs) wb.worksheets.add(tab.name);
for (const tab of schema.tabs) {
  const sh = wb.worksheets.getItem(tab.name), last = column(tab.headers.length - 1);
  const bannerLast = column(Math.min(tab.headers.length, 6) - 1);
  sh.showGridLines = false;
  sh.tabColor = ["Jobs", "Daily Summary"].includes(tab.name) ? teal : navy;
  sh.getRange(`A1:${last}25`).format.font = {name: "Arial", size: 10, color: navy};
  sh.getRange(`A1:${last}25`).format.rowHeight = 24;
  sh.getRange(`A:${last}`).format.columnWidth = 24;
  sh.mergeCells(`A1:${bannerLast}1`);
  sh.getRange("A1").values = [[tab.name]];
  sh.getRange(`A1:${bannerLast}1`).format = {fill: navy, font: {name: "Arial", size: 20, bold: true, color: "#FFFFFF"}, rowHeight: 42};
  sh.mergeCells(`A2:${bannerLast}2`);
  sh.getRange("A2").values = [[descriptions[tab.name]]];
  sh.getRange(`A2:${bannerLast}2`).format = {font: {name: "Arial", size: 10, color: gray}, wrapText: true, rowHeight: 36};
  sh.getRange(`A4:${last}4`).values = [tab.headers];
  sh.getRange(`A4:${last}4`).format = {fill: teal, font: {name: "Arial", size: 10, bold: true, color: "#FFFFFF"}, wrapText: true, rowHeight: 32};
  sh.getRange(`A5:${last}1000`).format.verticalAlignment = "top";
  sh.getRange(`A5:${last}1000`).format.wrapText = true;
  sh.freezePanes.freezeRows(4);
  if (tab.name === "Jobs") sh.freezePanes.freezeColumns(3);
  for (const [i, name] of tab.headers.entries()) {
    const col = column(i), range = sh.getRange(`${col}5:${col}1000`);
    if (name.includes("At") || ["First Seen", "Last Seen", "Observed At"].includes(name)) range.setNumberFormat("yyyy-mm-dd");
    if (["Rating", "Seen Count", "Observed Jobs", "Qualified Jobs"].includes(name)) range.setNumberFormat(name === "Rating" ? "0.0" : "0");
    if (["Title", "Fit Reason", "Notes", "Evidence Link", "Instructions"].includes(name)) sh.getRange(`${col}:${col}`).format.columnWidth = name === "Instructions" ? 88 : 42;
    if (name === "Application Status") {
      range.dataValidation = {rule: {type: "list", values: schema.job_statuses}};
      range.conditionalFormats.addCustom(`$${col}5="Interviewing"`, {fill: "#DDF2E5", font: {color: "#17633B", bold: true}});
      range.conditionalFormats.addCustom(`$${col}5="Asked for referral"`, {fill: "#FFF0CC", font: {color: "#7D5700"}});
    }
  }
}
const summary = wb.worksheets.getItem("Daily Summary");
summary.getRange("A:A").format.columnWidth = 34;
summary.getRange("B:B").format.columnWidth = 40;
const metrics = ["Total jobs", "New", "Saved", "Asked for referral", "Applied", "Interviewing", "Rated companies", "Source sightings"];
summary.getRange("A5:A12").values = metrics.map(x => [x]);
summary.getRange("B5:B12").formulas = [
  ["=COUNTA(Jobs!C5:C1000)"], ...metrics.slice(1,6).map(s => [`=COUNTIF(Jobs!F5:F1000,"${s}")`]),
  ["=COUNTA('Rated Companies'!A5:A1000)"], ["=COUNTA('Job Sources'!A5:A1000)"]
];
summary.getRange("B5:B12").setNumberFormat("0");
summary.getRange("B5:B12").format = {fill: pale, font: {name: "Arial", size: 14, color: teal, bold: true}};
const guide = wb.worksheets.getItem("How to Use");
guide.getRange("A:A").format.columnWidth = 27;
guide.getRange("A5:B13").values = [
  ["Start", "Complete Application Workflow/ONBOARDING.md in the repository. This blank file contains no account identifiers or job history."],
  ["Discovery", "Email alerts, referral portals, and the Blind company list feed the same Jobs tab through a private queue."],
  ["Your edits", "Edit Application Status, Referral Contact, and Notes. The coordinator preserves them when a job is seen again."],
  ["Managed fields", "Keep the header names and hidden Job Key column. Do not delete provenance rows or reuse job keys."],
  ["Matching policies", "Main and Blind policies are recorded separately. A Blind stretch match remains labeled stretch in Job Sources."],
  ["Source completeness", "A finished run can still have source gaps. Check Rated Search Coverage and the daily brief for those gaps."],
  ["Saved means verified", "A job is saved only after readback of your chosen tracker confirms its values and working role link."],
  ["Reports", "Saved imports enter one later daily brief. A failed or uncertain delivery stays pending for reconciliation."],
  ["Recovery", "Keep the private instance directory. Follow Application Workflow/docs/upgrade-and-recovery.md before retrying a write with an unknown outcome."]
];
guide.getRange("A5:B13").format.rowHeight = 48;

// Exercise the formulas with one temporary fictional job, then restore blank data.
const jobs = wb.worksheets.getItem("Jobs");
jobs.getRange("C5").values = [["Example fixture only"]];
jobs.getRange("F5").values = [["Interviewing"]];
wb.recalculate();
if (summary.getRange("B5").values[0][0] !== 1 || summary.getRange("B10").values[0][0] !== 1) throw new Error("Summary fixture did not recalculate");
jobs.getRange("C5").clear({applyTo: "contents"});
jobs.getRange("F5").clear({applyTo: "contents"});
wb.recalculate();
if (summary.getRange("B5:B12").values.some(row => row[0] !== 0)) throw new Error("Blank summary is not zero");
console.log((await wb.inspect({kind: "region", sheetId: "Daily Summary", range: "A4:B12", maxChars: 2500})).ndjson);
if (previewDir) {
  await fs.mkdir(previewDir, {recursive: true});
  for (const tab of schema.tabs) {
    const end = tab.headers.length === 2 ? "B" : "F";
    const preview = await wb.render({sheetName: tab.name, range: `A1:${end}13`, scale: 1, format: "png"});
    await fs.writeFile(`${previewDir}/${tab.name.replaceAll(" ", "-")}.png`, new Uint8Array(await preview.arrayBuffer()));
  }
}
const xlsx = await SpreadsheetFile.exportXlsx(wb);
await xlsx.save(outputPath);
console.log(`Saved blank workbook: ${outputPath}`);
