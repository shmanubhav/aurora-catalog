# Machine reading of aurora sighting reports in historical US newspapers

Can a fine-tuned text classifier, with a large language model checking what it flags, find newspaper reports of
aurora sightings more completely than keyword search? This repository holds the method, the frozen evaluation plan
and the results for two great storms:

- **1859 (Carrington storm), development:** a classifier ([Laya](https://huggingface.co/convaiinnovations/laya-multilingual))
  fine-tuned on 1,544 labeled articles, measured by grouped cross-validation, plus LLM checkers on its flags.
- **February 1872, held-out test:** pre-registered before any 1872 article was downloaded. The plan is
  `prereg/1872_preregistration.md`; every frozen file is listed with its SHA-256 in `prereg/MANIFEST.tsv`.

Newspaper text comes from American Stories (Dell et al. 2023), built from the Library of Congress Chronicling America
scans.

## Layout

- `freeze/` frozen settings, prompts and keyword patterns
- `bin/` every script; `bin/run_1872.sh STAGE` runs the 1872 test stage by stage on the branch `run-1872` and logs
  each output's hash in `results/1872_stage_log.tsv`
- `results/` result tables, the 1859 adjudications and checker outputs, the 1872 run log and analysis log, and the
  1859 and 1872 audit samples
- `data/` the 1859 labels, label-set key, article text, base Laya scores and keyword flags (on `analysis-1872`)
- `prereg/` the pre-registration and its manifest
- `paper/` the AI-use ledger and its addendum, the post-download analysis disclosures, the 1859 diagnostic scripts in
  `paper/scripts/`, and instructions for the human auditor

## Reproducing

Python 3.14 with `uv sync` for the Laya environment. The 1872 run needs a GPU host for the fine-tuned model and
Ollama for the open-weights checker and second labeler; copy `local.env.example` to `local.env` and fill in your hosts.

Tests: `bin/test_score_1872.sh` checks the scorer on a hand-computed case and the failure rules; `bin/test_agents.sh`
checks the agent runner offline; `bin/smoke_agents.py` is a real isolation check of one agent (a few cents; the
pre-registration run is in `results/agent_smoke_test.md`).

Order for the 1872 test: the registered commit is pushed and cited on OSF first; then `git switch -c run-1872` from it
and run the stages in order, starting with `bin/run_1872.sh download`. Stages commit and push only `run-1872`, so the
registered commit never changes.

Post-download analyses (pre-registration section 7: reprint groups, OCR terciles, truncation count, human audit) are
written after the run, checked by `bin/test_analyses_1872.sh` on 1859 data and toy cases only, and committed and pushed
before they touch any 1872 output. Each then runs once through `bin/run_analyses_1872.sh`, which checks every input
against the stage log and records the hashes in `results/1872/analysis_log.tsv`.

Freeze records mention the author's machines: `llm02` is the GPU host (AMD RX 7900 XTX), `M6` the Apple-silicon
workstation; `/srv` and `/opt` paths are on the GPU host.

## Use of AI

Large language models are part of the method (labelers, adjudicator, checkers) and helped write the code and
documents. Every such use, its validity risk and its mitigation is listed in `paper/ai_use_ledger.md` and its
addendum `paper/ai_use_ledger_addendum.md`. The answer key
is LLM-adjudicated and is validated against a human annotator on a stratified sample (independent; if nobody is found
within 4 weeks the author does it, disclosed; pre-registration section 5).

## License and citation

Code: MIT (LICENSE). Labels and results: CC BY 4.0 (DATA-LICENSE.md). Please cite via CITATION.cff.
