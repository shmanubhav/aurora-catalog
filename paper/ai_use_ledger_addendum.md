# AI-use ledger addendum (Paper 1)

`paper/ai_use_ledger.md` is listed in `prereg/MANIFEST.tsv` and stays exactly as registered. This addendum, started on
2026-10-10 after the 1872 run, completes and updates it. Row 3 below adds to registered row 3, and row 9 replaces
registered row 9; rows 12 onward are new (the registered ledger ends at row 11). The columns are those of the
registered ledger.

| # | Step | AI role | Validity risk | Mitigation | Evidence | Status |
|---|---|---|---|---|---|---|
| 3 (adds) | Checker arms, 1859 development | four checker trials on 1859: Claude Haiku 5.5 and Claude Opus 5.5 sub-agents, and Qwen with and without reasoning | trying several set-ups and keeping the best | all four trials disclosed; the two 1872 arms were frozen before the 1872 download | `results/finetune/checkers/`, `freeze/checker_arms.json` | ✅ |
| 9 (replaces) | Paper drafting | Claude Opus 5.5 drafts the text from the plan and the run records; the author writes the abstract and discussion | AI-written text and claims; authorship of the prose | adversarial Claude Opus review rounds with a claim-to-source table; the author reviews and owns every statement; disclosed in the paper's Methods and per venue policy | AI review reports and drafts, kept by the author | 🔄 |
| 12 | Human-audit kit | a Claude Sonnet 5.5 helper agent wrote the first audit-page builder, audit scorer, annotator instructions and outreach messages; Claude Opus 5.5 later rewrote the instructions and edited the builder | labels, strata or scores leaking into the page; instructions that steer answers | the builder reads only the prompt and the articles' ids and text, so labels, strata and scores cannot reach the page (the annotator could still find strata in the public sample file; see `analysis_disclosures.md`, release of the 1872 outputs); the built 1872 and 1859 pages were checked for item ids and stratum tags (none; the words "stratum" and "score" appear only inside article text); builder and scorer frozen in the MANIFEST; Opus review rounds | `bin/make_audit_page.py`, `bin/score_audit.py`, `paper/auditor_instructions.md`, `prereg/MANIFEST.tsv` | ✅ |
| 13 | Why keyword search missed base Laya's 22 finds (1859) | a Claude Sonnet 5.5 agent read the 22 articles and sorted them by cause | misreading; a disputed label presented as fact | descriptive only, used by no hypothesis; disputed items reported as disputed; author check before any claim in the paper | `results/1859-results.md` ("Why rg missed") | ⚠️ |
