# Pre-registration: machine reading of aurora sighting reports in US newspapers, February 1872 holdout

Registered before any newspaper article from the 1872 test window was downloaded, scored or read by us. Every method is frozen in the files listed in MANIFEST.tsv with their SHA-256. The code, frozen files and 1859 results are public (MIT and CC BY 4.0) in the repository named in the OSF submission; its public history starts at the registration commit, and commit IDs cited below (such as Freeze 1 and Freeze 2) refer to the private development history, whose frozen files are identified exactly by the MANIFEST hashes. All dates are UTC.

## 1. Question and hypotheses

**Question:** on a storm it never trained on, does a fine-tuned text classifier, at its frozen cutoff, reach 80% precision and 80% weighted recall against the answer key, while finding sightings that strict keyword search misses? And does adding it to keyword search find more sightings than keyword search alone?

The classifier was developed and tuned only on US newspapers from August and September 1859 (the Carrington storm). The test is the great aurora of 4-5 February 1872, in US newspapers printed between 1 February and 3 March 1872.

- **H1 (primary, the Freeze 1 bar).**
  - Passes if the unrounded point estimates of precision and weighted recall of fine-tuned Laya at t\* = 0.80 are both >= 0.80, and at least one article it flags with a final YES label is not matched by `freeze/strict.rg`.
  - Intervals are reported but do not decide H1. We predict a pass.
- **H2 (confirmatory secondary).**
  - The weighted recall of (strict keyword search OR fine-tuned Laya) minus that of strict keyword search alone, with a 95% paired stratified bootstrap interval.
  - H2 is supported if the lower bound is > 0.
  - **H2'** (secondary, not confirmatory) repeats this with (strict OR fuzzy keyword search) as the baseline.
  - We predict support. On the 1859 development data the gain was +5.4 points (95% interval +2.5 to +8.9), with the pooling caveat in section 4. That 1859 figure was first computed by the frozen scorer during development; it had no earlier output.
- **H3 (descriptive).** Fine-tuned Laya recall minus strict keyword recall, with the same interval and no predicted direction. In 1859 it was -4.0 points.

## 2. Data

- **Source:** American Stories (Dell et al. 2023; CC BY 4.0), Hugging Face `dell-research-harvard/AmericanStories` at commit `77e27fa69c4788dfaad1c9efd8a226d5a32d3e9a`.
  - The test archive is `faro_1872.tar.gz`, SHA-256 `8b246fb4894f5ce54ed841e3f66dbbcb832b378551ca51f4ba23af75d9087f67` (2,310,675,564 bytes). It is verified on download, before extraction.
  - The 1859 development archive matches the same revision.
- **Window:**
  - Publication date is the YYYY-MM-DD prefix of the scan filename, as parsed by `bin/extract_window.py`, from 1872-02-01 to 1872-03-03 inclusive.
  - Scans that fail to parse or lack an `lccn` are excluded and counted.
  - There is no deduplication beyond the dataset's article segmentation.
- **Scope of YES:** any reported sighting, not only the 4-5 February storm.
- **Status at registration:** none of the window has been downloaded, scored or read by us. A search of local storage, the Hugging Face cache and the GPU host found no 1872 file.

## 3. Systems compared (all frozen; settings in `freeze/config_1872.json`)

| # | System | Flags an article when |
|---|---|---|
| 1 | Strict keyword search, `freeze/strict.rg` (written by hand before any model ran in 1859) | the pattern matches |
| 2 | OCR-tolerant keyword search, `freeze/fuzzy.rg` | the pattern matches |
| 3 | Base Laya, `convaiinnovations/laya` revision `7b928d828b7b0e022f929d9bd2e44165aa270148` (the revision 1859 actually loaded; laya 0.4.1 does not pin by default, so it is enforced with `LAYA_REVISION` and an offline cache), zero-shot, on the M6 (Apple MPS) under the 1859 precision rule, scored once in extraction order; articles over 300 tokens are scored in windows, as in 1859 | score >= 0.5 |
| 4 | **Fine-tuned Laya** (primary), run in image `laya-batch:e974cca5eb42` (ID `sha256:7db9c7e8...`, laya 0.4.1, torch 2.14.1+rocm7.2): `convaiinnovations/laya-multilingual` revision `e4e9ddf2`, fine-tuned on 1,544 labeled 1859 articles plus 3,000 presumed-negative articles (4 epochs, effective batch 64, learning rates 2.5e-5 / 1e-4, RLCD loss, seed 1872). All-data checkpoint `model.safetensors` SHA-256 `687f84e7...`. fp16, whole article. | score >= **t\* = 0.80** |
| 5 | Fine-tuned Laya + Qwen checker (primary checker arm): Qwen3.8 27B (`qwen3.8:27b-q4_K_M`, digest `25b84361...`), Ollama 0.34.4, reasoning on, temperature 0, seed 1872, the frozen labeler prompt. Independent of every labeler. | system 4 flags it and Qwen does not answer NO |
| 6 | Fine-tuned Laya + Opus checker (secondary checker arm): four isolated Claude Opus agents (`claude-opus-5-5`, full ID, see section 4) in blind batches of 60,000 characters. Opus also adjudicates the answer key, so this arm is also reported excluding every Opus-adjudicated item (disagreements, Gemma UNPARSED and agreed checks). | system 4 flags it and Opus does not answer NO |

- **Scores:** flags use the score as written to 4 decimals.
- **Truncation:** for fine-tuned Laya, an article longer than 4,096 tokens keeps its first 4,096 tokens (Laya right-truncates), and such articles are counted.
- **Timing:** checkers run, and their outputs' hashes are committed in the stage log, before any labeling starts. Checker items are keyed by label-set id, as in 1859.

## 4. Answer key

- **Pool:** the union of the articles flagged by systems 1-4. **Every pooled article is labeled; there is no cap.** Checkers only remove flags, so systems 5 and 6 add nothing to the pool.
- **Loose net** (`freeze/loose.rg`): a broad search run over the articles outside the pool. It estimates the sightings every system missed *that the loose net matches*.
  - With H = loose-net hits outside the pool: N = max(5, ceil(H / 400)).
  - n = max(1, round(H / N)) articles (Python round, half to even; no net stratum if H = 0) are drawn by simple random sampling without replacement (`random.Random(1872)`, `bin/draw_labelset.py`). Each sampled article weighs H / n.
  - H, N, n and the label-set key (line numbers and weights, no text) are committed under `results/1872/` before any labeling.
  - Sightings outside both pool and loose net are unobserved, so every recall is an upper bound. The pool is built from the systems being compared, so recall is biased upward for them (pooling bias).
- **Labelers:** each sees only article text and the frozen prompt.
  - **Claude Sonnet** (`claude-sonnet-5-5`, full ID), in batches of 60,000 characters (`freeze/labeler_agent_prompt.md`).
  - **Gemma** (`gemma4:26b-a4b-it-mtp-q4_K_M`, digest `08ae7ec1...`, Ollama 0.34.4 on the GPU host, through the same gateway URL as 1859, now served by LiteLLM on a different host; temperature 0). A reasoning loop is recorded as UNPARSED and goes to adjudication.
  - **Measured before registration:** Gemma reproduced 18 of 20 of its 1859 labels on this path (2 borderline flips), and two runs agreed 20/20.
- **Adjudication:** Claude Opus (`claude-opus-5-5`, full ID, `freeze/adjudicator_prompt.md`, batches of 45,000 characters as in 1859) settles every disagreement, every UNPARSED, and 30 randomly chosen agreements.
  - It is blind: it sees text and prompt only, never either labeler's answer.
  - The final label is Opus's call where it adjudicated, and the consensus elsewhere.
  - Agreed-check overturns are reported and trigger no relabeling.
- **Agent isolation:** every Claude agent is a fresh headless Claude Code run (2.1.296, auto-update off, `bin/run_agents.py`) started in its own directory outside the repository, holding only its own batch files and prompt. It runs with `--restricted` (user, project and local settings, plugins and hooks ignored; file tools confined to its directory; settings files writable only by a person), no MCP servers, only the Read and Write tools, auto memory and CLAUDE.md loading off, and an allowlisted environment; the runner refuses to start if a proxy or model-override variable is set. The full model ID is passed and the resolved model is logged per run. Before registration a real run verified this (`bin/smoke_agents.py`, `results/agent_smoke_test.md`): only the pinned model ran, a read of a sibling folder and a write to `.claude/settings.json` were both denied, a plain file in its own folder could be written, and no memory or transcript was created. (1859 used subagents of an interactive session, isolated by instruction only; this is disclosed as a procedure difference.)
- **Model continuity:** no labeler changes model, build, host or settings after its first 1872 item. A resolved Claude model other than the pinned full ID aborts the stage; the Ollama version and model digests are checked before the Qwen and Gemma stages. If a model becomes unavailable, that role restarts from its first item on a replacement named in a dated amendment.
- **Failures:**
  - An agent whose output fails validation is re-run with a fresh agent, up to three attempts per stage run. Earlier attempts are kept, and an agent's first complete answers for a batch stand; accepted answers are attested with their SHA-256.
  - If any agent is still not done, the stage stops unlogged and is re-run with a stated, published reason; a re-run restarts only agents that still owe a batch, and accepts answers only for batches without an attested answer. An agent stage's third and any later run is final: whatever is still missing goes to the rules below. A run after the third happens only if the third stopped before finishing, and is listed as a deviation.
  - A Sonnet batch still failing on the third stage run gets MISSING labels and goes to adjudication. An item whose Sonnet label is MISSING and whose adjudication is unanswered is excluded from every system and listed.
  - A missing or UNPARSED checker verdict counts as kept.
  - An adjudication item unanswered on the third stage run keeps the Sonnet label and is listed.
  - Any re-run of a stage that has started needs a stated reason, keeps the earlier outputs, and is recorded in the stage log.
- **Label definition:** the full text of `freeze/labeler_prompt_1872.md`:

> You are labeling articles from US newspapers printed between 1 February and 3 March 1872. The text is OCR output and may contain errors.
>
> Question: does this article report that an aurora (northern lights) or a glowing, lit-up night sky was SEEN somewhere?
>
> Answer YES for:
> - A firsthand or relayed account of an aurora, the northern lights, or the night sky glowing, lit up or red, seen at some place (for example "a correspondent at Boston writes that the heavens were illuminated").
> - A short mention of such a sighting inside a longer article.
>
> Answer NO for:
> - Telegraph lines failing or behaving strangely, with no sighting described.
> - General science writing or essays about auroras with no specific sighting.
> - "Aurora" used as a name: a ship, a town such as Aurora, Illinois, a person, a newspaper, a society.
> - Fires, lamps, fireworks, festive illuminations, comets, meteors or sunsets that are not an aurora.
>
> Reply with exactly one word: YES or NO.

## 5. Human audit (validation of the LLM-made answer key)

- **Who:** an independent annotator recruited by the author (not the author, not an AI). If nobody is found within 4 weeks of the 1872 labels being final, the author does it, and that audit is disclosed as not blind to the key.
- **1872 sample (250), drawn by `bin/draw_audit.py` with `random.Random(1872)`:**
  - Every labeled item falls in exactly one stratum, by priority: S1 fine-tuned Laya AND keyword (strict or fuzzy); S2 fine-tuned Laya, no keyword; S3 keyword, no fine-tuned Laya; S4 base Laya only; S5 loose-net sample (sized by n, the articles drawn).
  - Each stratum first gets min(25, its size); the rest of the 250 is allocated proportionally to (size minus that share) by largest remainder, ties to the lower stratum number.
  - The drawn sample is committed before the annotator starts.
- **1859 sample (100):** 50 final-YES and 50 final-NO, drawn separately with `random.Random(1872)` and committed before registration (`results/audit/`).
- **Procedure:**
  - Two blind pages (`bin/make_audit_page.py`), one per year, each showing its year's frozen labeler prompt verbatim (the only change: "Press YES or NO" instead of the reply instruction) and article text only. No highlighting, and no label, stratum or score anywhere in the page source.
  - 10 hidden repeats per page measure consistency.
  - The 1859 development labels are public, so the 1859 page is blind by instruction only: the annotator is asked not to open the project repository, its OSF page or any results until their answers are sent. Disclosed.
  - Partial completion: every completed item is used; a stratum under 80% complete is reported as incomplete.
- **Reported (pre-specified, code may be written after download under section 7):**
  - per stratum: raw agreement with a Wilson interval, Cohen's kappa, positive and negative agreement, and p1 = the share of audited LLM-YES items the human calls YES, p0 = the same for LLM-NO items. A quantity with no audited items is not estimable, and its LLM label stands.
  - sensitivity: every labeled item gets y = p1 or p0 of its stratum according to its LLM label (net items weigh H/n). Precision of a system = sum over its flags of w*y / sum over its flags of w; recall = sum over its flags of w*y / sum over all items of w*y. Intervals from 2,000 bootstrap resamples of audited items within stratum (seed 1872). H1's unmatched-sighting condition stays on the LLM key.
  - The LLM key decides H1, and the paper calls it an LLM-adjudicated key, not ground truth.
- Following Pangakis, Wolken & Fasching (2023), who advise 250-1,250 human-labeled items.

## 6. Measures

- **Precision:** final-YES flags divided by flags, with a 95% Wilson interval. Every system's flags are in the pool, so precision is measured on fully labeled sets.
- **Weighted recall:**
  - Weighted final-YES found, divided by weighted final-YES in pool plus loose-net sample.
  - Pool articles weigh 1; loose-net samples weigh H/n.
  - 95% percentile interval from 2,000 bootstrap resamples (`random.Random(1872)`), with pool and net resampled separately and every system read from the same resamples. Zero-positive resamples are counted, with recall 0.
- **F1** from the point estimates.
- **Also reported:** for each system, the count of final-YES articles it flags that neither strict nor fuzzy keyword search matches.
- **Sensitivity (reprints):** the unit is the article. Reprint groups are built separately within the pool and within the net sample (never spanning both), with the Freeze 1 method of `bin/prep_finetune.py` (5-word shingles, shingle frequencies over the labeled items, max frequency 20, containment 0.5, union-find). A group counts as flagged by a system if any member is, and as final-YES if any member is; net groups weigh H/n. H1 point estimates and the H2/H2' intervals are repeated at group level, with groups resampled within stratum, and the number of distinct groups behind the sightings strict search missed is reported.
- **Exploratory:** recall by OCR-quality tercile. OCR quality is the share of whitespace tokens made only of letters, and the terciles are cut on the 1872 pool.
- **Code:** H1, H2, H2', H3, precision, recall, F1, checker arms and the "neither keyword search" counts are computed by `bin/score_1872.py`. Before any 1872 download it reproduced the 1859 base Laya, strict keyword, fine-tuned Laya and both checker rows and the labeler statistics to the printed digit (`results/score_1872_repro_1859.md`, with its command line), and passed a hand-computed toy case and the failure-rule cases (`bin/test_score_1872.sh`); the agent runner, collector and label check pass offline tests (`bin/test_agents.sh`). Every stage runs through `bin/run_1872.sh` with literal settings, which records each output's SHA-256 in the committed `results/1872_stage_log.tsv`.

## 7. Reporting and deviations

- **No changes after download:** no system, checker, cutoff, prompt, script, sampling rule or setting in `bin/run_1872.sh` is added or changed after any 1872 article is downloaded.
  - Between download and the first label, only these are inspected: the extraction summary (window size, excluded scans, length summary), per-system flag counts, pool size, H, N and n, checker completion and UNPARSED counts, and the per-batch YES counts the Opus checker agents report.
  - Stages run on the branch `run-1872`, cut from the registered commit, which itself stays unchanged. Each stage publishes a start row, and then its outputs' hashes, to `results/1872_stage_log.tsv`, committed and pushed to the public repository (which timestamps them) before the next stage starts; `bin/run_1872.sh` refuses a stage whose predecessor has not completed or is not pushed, and refuses to repeat a started stage without a stated reason.
- **Code written after download** is allowed only for these pre-specified analyses: the reprint-group sensitivity, the OCR-quality terciles, the human-audit agreement and the audit-corrected H1/H2, and the truncation count. Such code must be a pure function of committed stage outputs, implement exactly the choices stated here, and be committed and hashed before it touches any 1872 output.
- **All results reported:** every system and hypothesis is reported, whatever it shows. Any deviation is listed with its reason.
- **Disclosures:**
  - 1859 development tried four checker configurations and two fuzzy keyword versions, and switched the 1859 adjudicator from a human to Opus.
  - Claude Sonnet (first labeler) and Claude Opus (adjudicator and secondary checker) are one model family, so the key may lean toward Sonnet's reading.
  - The 1859 base Laya run loaded Hugging Face's default revision, recorded here after the fact as `7b928d82` from the cache; re-scoring the first 512 1859 articles with that pin reproduced every score to 4 decimals.
  - The 1859 out-of-fold precision used an extrapolated false-alarm formula and is not directly comparable.
  - The language models and base encoder may have seen Chronicling America OCR text in pretraining.
  - AI tools wrote analysis code and drafted this document. The author reviewed and owns every statement.
- **Release:** code, frozen configs, the 1859 labels and the 1859 audit sample are public from registration (code MIT, data CC BY 4.0) and archived on Zenodo with a DOI; 1872 outputs are added on `run-1872` as each stage completes.

## 8. Files

The full list, with hashes and freeze commits, is in MANIFEST.tsv: the freeze files (`finetune.json`, `finetune_freeze2.json`, `checker_arms.json`, `config_1872.json`, `config.json`, the prompts, the keyword patterns) and every pipeline script.
