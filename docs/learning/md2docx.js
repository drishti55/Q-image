// Combine the docs/learning/*.md study guides into one formatted Word document.
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, AlignmentType, HeadingLevel,
  BorderStyle, ShadingType, PageNumber, Footer, LevelFormat, PageBreak, TableLayoutType,
} = require("docx");

const DIR = process.argv[2];
const OUT = process.argv[3];
const FILES = [
  ["PROJECT_MASTER_GUIDE.md", "Project Master Guide"],
  ["QUANTUM_COMPUTING_FROM_ZERO.md", "Quantum Computing from Zero"],
  ["FRQI_NEQR_DEEP_DIVE.md", "FRQI and NEQR Deep Dive"],
  ["MOBILENET_AND_CLASSICAL_ML.md", "MobileNetV3 and Classical ML"],
  ["EXPERIMENTS_EXPLAINED.md", "Experiments Explained"],
  ["CIRCUIT_ARCHITECTURE_GUIDE.md", "Circuit Architecture Guide"],
  ["FRONTEND_BACKEND_WALKTHROUGH.md", "Frontend and Backend Walkthrough"],
  ["RESULTS_AND_RESEARCH_DEFENCE.md", "Results and Research Defence"],
  ["TECHNICAL_VIVA_QUESTIONS.md", "Technical Viva Questions (150)"],
  ["QUICK_REVISION_CHEATSHEET.md", "Quick Revision Cheat Sheet"],
];
const FONT = "Calibri", MONO = "Consolas", TW = 9026;
const border = { style: BorderStyle.SINGLE, size: 4, color: "A8B0BA" };
const borders = { top: border, bottom: border, left: border, right: border };

// inline markdown: **bold**, *italic*, `code`
function inline(text, o = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`|\*[^*\s][^*]*\*)/g;
  let last = 0, m;
  const push = (t, extra = {}) => t && out.push(new TextRun({ text: t, font: extra.mono ? MONO : FONT, size: extra.mono ? (o.size || 22) - 2 : (o.size || 22), bold: extra.bold || o.bold, italics: extra.italics || o.italics, color: extra.mono ? "8A2B2B" : o.color }));
  while ((m = re.exec(text))) {
    push(text.slice(last, m.index));
    const s = m[0];
    if (s.startsWith("**")) push(s.slice(2, -2), { bold: true });
    else if (s.startsWith("`")) push(s.slice(1, -1), { mono: true });
    else push(s.slice(1, -1), { italics: true });
    last = m.index + s.length;
  }
  push(text.slice(last));
  return out;
}

function table(rows) {
  const n = Math.max(...rows.map((r) => r.length));
  const lens = Array.from({ length: n }, (_, i) => Math.max(12, ...rows.map((r) => Math.min(55, (r[i] || "").length))));
  const sum = lens.reduce((a, b) => a + b, 0);
  const W = lens.map((l) => Math.round((l / sum) * TW)); W[n - 1] += TW - W.reduce((a, b) => a + b, 0);
  const size = n >= 6 ? 16 : n >= 4 ? 18 : 20;
  return new Table({
    width: { size: TW, type: WidthType.DXA }, columnWidths: W, layout: TableLayoutType.FIXED,
    rows: rows.map((r, k) => new TableRow({
      tableHeader: k === 0, cantSplit: true,
      children: Array.from({ length: n }, (_, i) => new TableCell({
        width: { size: W[i], type: WidthType.DXA }, borders, margins: { top: 40, bottom: 40, left: 80, right: 80 },
        shading: k === 0 ? { fill: "DCE6F2", type: ShadingType.CLEAR, color: "auto" } : k % 2 === 0 ? { fill: "F6F8FA", type: ShadingType.CLEAR, color: "auto" } : undefined,
        children: [new Paragraph({ children: inline((r[i] || "").replace(/\\\|/g, "|"), { size, bold: k === 0 || undefined }) })],
      })),
    })),
  });
}

const splitRow = (line) => line.trim().replace(/^\|/, "").replace(/\|$/, "").split(/(?<!\\)\|/).map((c) => c.trim());

function convert(md, part, title) {
  const out = [];
  out.push(new Paragraph({ children: [new PageBreak()] }));
  out.push(new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: `Part ${part}: ${title}`, font: FONT, size: 36, bold: true, color: "1F3B63" })], spacing: { after: 240 } }));
  const lines = md.split("\n");
  let i = 0, firstH1 = true;
  while (i < lines.length) {
    let line = lines[i];
    if (line.startsWith("```")) {                       // code block
      const code = []; i++;
      while (i < lines.length && !lines[i].startsWith("```")) code.push(lines[i++]);
      i++;
      code.forEach((c, k) => out.push(new Paragraph({
        shading: { fill: "F3F4F6", type: ShadingType.CLEAR, color: "auto" }, spacing: { after: 0, line: 240 },
        children: [new TextRun({ text: c || " ", font: MONO, size: 15 })],
      })));
      out.push(new Paragraph({ children: [], spacing: { after: 120 } }));
      continue;
    }
    if (/^\|/.test(line.trim()) && i + 1 < lines.length && /^\|[\s:|-]+\|?\s*$/.test(lines[i + 1].trim())) {   // table
      const rows = [];
      while (i < lines.length && /^\|/.test(lines[i].trim())) {
        if (!/^\|[\s:|-]+\|?\s*$/.test(lines[i].trim())) rows.push(splitRow(lines[i]));
        i++;
      }
      out.push(table(rows)); out.push(new Paragraph({ children: [], spacing: { after: 120 } }));
      continue;
    }
    const h = line.match(/^(#{1,4})\s+(.*)$/);
    if (h) {
      const lvl = h[1].length;
      if (lvl === 1 && firstH1) { firstH1 = false; i++; continue; }   // the doc title is the Part heading
      const size = { 1: 32, 2: 28, 3: 24, 4: 22 }[lvl];
      out.push(new Paragraph({ heading: lvl <= 2 ? HeadingLevel.HEADING_2 : HeadingLevel.HEADING_3, keepNext: true, spacing: { before: 240, after: 100 },
        children: inline(h[2], { size, bold: true, color: "1F3B63" }) }));
      i++; continue;
    }
    if (/^---+\s*$/.test(line)) {                        // rule
      out.push(new Paragraph({ border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "C8CDD3", space: 1 } }, spacing: { after: 160 }, children: [] }));
      i++; continue;
    }
    if (/^\s*>/.test(line)) {                            // blockquote
      const q = [];
      while (i < lines.length && /^\s*>/.test(lines[i])) q.push(lines[i++].replace(/^\s*>\s?/, ""));
      out.push(new Paragraph({ indent: { left: 360 }, border: { left: { style: BorderStyle.SINGLE, size: 18, color: "2A78D6", space: 8 } },
        shading: { fill: "EEF4FC", type: ShadingType.CLEAR, color: "auto" }, spacing: { after: 160 }, children: inline(q.join(" "), { italics: true }) }));
      continue;
    }
    const b = line.match(/^(\s*)[*-]\s+(.*)$/);
    if (b) {                                             // bullet (with continuation lines)
      let t = b[2]; i++;
      while (i < lines.length && /^\s{2,}\S/.test(lines[i]) && !/^\s*[*-]\s/.test(lines[i])) t += " " + lines[i++].trim();
      out.push(new Paragraph({ numbering: { reference: "bul", level: b[1].length >= 2 ? 1 : 0 }, spacing: { after: 40 }, children: inline(t) }));
      continue;
    }
    const nm = line.match(/^\s*(\d+)\.\s+(.*)$/);
    if (nm) {
      out.push(new Paragraph({ indent: { left: 540, hanging: 360 }, spacing: { after: 40 }, children: [new TextRun({ text: nm[1] + ".\t", font: FONT, size: 22 }), ...inline(nm[2])] }));
      i++; continue;
    }
    if (!line.trim()) { i++; continue; }
    const LBL = { S: "Simple", T: "Technical", E: "Our project", F: "Follow-up" };
    const qa = (t) => {
      const parts = t.split(/\s(?=[STEF]: )/);
      const head = parts[0].match(/^[STEF]: /) ? null : parts.shift();
      if (head) out.push(new Paragraph({ spacing: { before: 160, after: 40 }, keepNext: true, children: inline(head) }));
      parts.forEach((pt) => out.push(new Paragraph({ indent: { left: 360 }, spacing: { after: 30, line: 276 },
        children: [new TextRun({ text: LBL[pt[0]] + ": ", font: FONT, size: 21, bold: true, color: "1F6F4A" }), ...inline(pt.slice(3), { size: 21 })] })));
    };
    if (/^[STEF]: /.test(line) || /^\*\*Q\d+\./.test(line)) {
      const block = [line.trim()]; i++;
      while (i < lines.length && lines[i].trim() && /^[STEF]: /.test(lines[i])) block.push(lines[i++].trim());
      qa(block.join(" "));
      continue;
    }
    const para = [line.trim()]; i++;                     // paragraph (merge wrapped lines)
    while (i < lines.length && lines[i].trim() && !/^(#|\||```|>|\s*[*-]\s|\s*\d+\.\s|---)/.test(lines[i])) para.push(lines[i++].trim());
    out.push(new Paragraph({ spacing: { after: 120, line: 300 }, children: inline(para.join(" ")) }));
  }
  return out;
}

const body = [];
FILES.forEach(([f, t], k) => body.push(...convert(fs.readFileSync(path.join(DIR, f), "utf8"), k + 1, t)));
const front = [
  ...Array.from({ length: 6 }, () => new Paragraph({ children: [] })),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240 }, children: [new TextRun({ text: "Q-ImageLab", font: FONT, size: 56, bold: true, color: "1F3B63" })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 480 }, children: [new TextRun({ text: "Complete Project Study Guide — from Absolute Beginner to Technical Expert", font: FONT, size: 30 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 }, children: [new TextRun({ text: "Quantum image representations (FRQI, NEQR), quantum kernels, MobileNetV3 and classical baselines,", font: FONT, size: 22, color: "5B6470" })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 600 }, children: [new TextRun({ text: "experiments, circuits, dashboard, results and 150 viva questions", font: FONT, size: 22, color: "5B6470" })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Grounded in the repository code and saved results (audited 19 November 2026)", font: FONT, size: 20, italics: true, color: "5B6470" })] }),
  new Paragraph({ children: [new PageBreak()] }),
  new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: "Contents", font: FONT, size: 36, bold: true, color: "1F3B63" })], spacing: { after: 240 } }),
  ...FILES.map(([, t], k) => new Paragraph({ spacing: { after: 100 }, children: [new TextRun({ text: `Part ${k + 1}.  ${t}`, font: FONT, size: 24 })] })),
  new Paragraph({ spacing: { before: 240 }, children: [new TextRun({ text: "How to use this guide: read Parts 1–8 in order as a course; use Part 9 to practise for the viva and Part 10 for last-minute revision.", font: FONT, size: 22, italics: true })] }),
];
const doc = new Document({
  creator: "Q-ImageLab", title: "Q-ImageLab Complete Project Study Guide",
  styles: { default: { document: { run: { font: FONT, size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FONT, size: 36, bold: true }, paragraph: { spacing: { before: 0, after: 240 }, keepNext: true, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FONT, size: 28, bold: true }, paragraph: { spacing: { before: 240, after: 100 }, keepNext: true, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FONT, size: 24, bold: true }, paragraph: { spacing: { before: 200, after: 80 }, keepNext: true, outlineLevel: 2 } },
    ] },
  numbering: { config: [{ reference: "bul", levels: [
    { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 300 } } } },
    { level: 1, format: LevelFormat.BULLET, text: "◦", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 1000, hanging: 300 } } } }] }] },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1300, bottom: 1300, left: 1440, right: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 18 })] })] }) },
    children: [...front, ...body],
  }],
});
Packer.toBuffer(doc).then((b) => { fs.writeFileSync(OUT, b); console.log("wrote", OUT); });
