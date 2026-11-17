GROUP 02 — RESEARCH PAPER (Overleaf project)
=============================================

Files
  main.tex          the paper (template preamble, sections I–VIII, declarations)
  references.bib    25 IEEE references (all cited)
  figures/          11 vector PDF figures (no screenshots); Fig. 1 is drawn in TikZ inside main.tex
  main.pdf          preview compiled locally (Overleaf will rebuild it; Overleaf uses Times, the preview does not)

Upload to Overleaf
  1. overleaf.com -> New Project -> Upload Project -> choose Group02_Overleaf.zip
  2. Rename the project to:  Group02
  3. Menu -> Compiler: pdfLaTeX (default). Click Recompile.
  4. Share -> add kiran.khatter@bmu.edu.in as Editor ("Can edit").

Things YOU must do before submitting (tonight, 18 Nov 2026, 11:59 pm)
  [ ] Push the code:  in the project folder run   git push -u origin v4-paper
      (needs a GitHub login / personal access token). The paper links to
      https://github.com/drishti55/Q-image/tree/v4-paper
  [ ] main.tex line with "Overleaf Project Link": replace 0123456789abcdef01234567 with your real project id
      (copy it from the browser address bar after creating the project).
  [ ] Contribution Statement (end of main.tex): replace the two [EDIT: ...] lines with what each of you did.
  [ ] AI rule (<=10% AI content): the text is an AI-assisted draft. Rewrite it in your own words,
      section by section, keeping the numbers. Keep the AI-use declaration honest and adjust it to what you did.
  [ ] Read and verify every reference (the template says each must be real and read by you).
      DOIs are in references.bib.
  [ ] Run the similarity check and the AI-content check, attach both reports.
  [ ] Download the compiled PDF from Overleaf and submit it with the project link.

Word counts (main text, excluding tables, captions and references): about 4,900
  Abstract 250 | Intro ~640 | Related Work ~720 | Background ~320 | Methodology ~915
  Setup ~455 | Results ~860 | Discussion ~410 | Conclusion ~230
  If you rewrite, stay inside each section's range (template, Section 2).

Every number in the paper comes from results/qml_v4 and the V2/V3 aggregates; the check script
research_paper_visuals/source/validate_v4_pack.py recomputes the key ones.
