# Post-download analyses (1872): choices and disclosures

## Procedure

Section 7 of the pre-registration allows four analyses to be written after the 1872 download: the reprint-group
sensitivity, the OCR-quality terciles, the human-audit agreement with the audit-corrected H1/H2, and the truncation
count. The procedure for them:

- The code is written after the run and tested on 1859 data and toy cases only (`bin/test_analyses_1872.sh`).
- An adversarial AI referee (Claude Opus) reviews each version until it returns GO.
- The code is committed and pushed, with its hashes in `results/1872/analysis_scripts.sha256`, before it reads any
  1872 output. `bin/run_analyses_1872.sh` refuses to run otherwise.
- Every run of an analysis first commits and pushes a start row to `results/1872/analysis_log.tsv`, before it reads
  any 1872 file. It then logs the hashes of the scripts, inputs and output, or a failed row. Every attempt that gets
  that far, failed ones included, is on the public record. Any repeat of an analysis, after a failure too, needs a
  stated reason, and an earlier output is kept beside the new one. Refusals before the start row (wrong branch, code
  not committed and pushed, something else staged, a misnamed or uncommitted answers file) read no data and are not
  logged.
- The 1872 inputs are checked against the hashes the stage log recorded. The 1859 inputs of the 1859 audit are hashed
  into the analysis log; those in the frozen manifest are also checked against it. The fine-tuned checkpoint files are
  checked against hashes recorded on 2026-10-10 (`results/1872/ft_checkpoint_copy.sha256`).

Record of what happened (dated; filled in as it happens):

- 2026-10-10, about 17:58 UTC: a no-argument call of an early version of the runner created the empty
  `results/1872/analyses/` folder and the header-only analysis log. It printed its usage message; no analysis ran and
  no 1872 output was read.
- 2026-10-10: referee round 1 returned NO-GO (fixed in 5fb4b3c); round 2 returned NO-GO (fixed in 19f6f21); round 3
  returned NO-GO (fixed in e1d6aa4); round 4 returned GO on e1d6aa4. The reprint, OCR and truncation analyses ran on
  e1d6aa4's code (the OCR and truncation start rows record its log-only descendants 577c674 and 31cea8c; `bin/` and
  `paper/` are unchanged between them).
- 2026-10-10: the analysis code was first committed (7ce9342, 17:58:57 UTC) after the main 1872 results were
  computed (`results/1872/results.md`, logged 17:41:48 UTC). Both times are self-reported.
- 2026-10-10: the choices below, including the human-label fallback to a repeat card and the kappa not-estimable
  rule, were made before any audit page was sent to anyone (the author confirmed this on 2026-10-10), so before any
  human answer existed. Git commit times are self-reported; the public timestamp is the push of this branch, which
  comes before any page is sent.

## Other dated decisions after the download

- **Release of the 1872 outputs (deviation).** Section 7 of the pre-registration says 1872 outputs are added on
  `run-1872` as each stage completes. Only `results/1872/` (summary results, the label-set key and the audit
  sample) was committed; the stage output files under `data/1872/` (labels, checker verdicts, adjudication, flags and
  scores) were published as SHA-256 hashes in `results/1872_stage_log.tsv`, not as files. The author decided on
  2026-10-10 to release those files once the human-audit answers are committed, so that the annotator cannot look up
  the models' answers. This entry is pushed before any audit page is sent. The stage-log hashes let anyone check the
  released files. The paper lists this as a deviation.
- **Release of the 1859 labels (deviation; 2026-10-10).** Section 7 of the pre-registration says the 1859 labels are
  public from registration. Of the 1859 label files, only the adjudications, the audit sample and the checker outputs
  were: the labelers' files sit under `data/`, which git ignores. They are committed with this entry and pushed on
  2026-10-10, at the paths the code reads:
  - `data/labelset/key.tsv` (id, window line, stratum, weight) and `data/labelset/items.jsonl` (the article text, from
    American Stories, CC BY 4.0);
  - `data/labels/claude/b001.tsv` to `b078.tsv` (Claude Sonnet);
  - `data/labels/gemma.tsv` (Gemma on the GPU host, the labels used) and `data/labels/gemma_m6_partial.tsv` (the
    earlier partial Gemma run on the M6, 155 items, not used);
  - so that the registered reproduction can be re-run from the repository, the other 1859-only inputs it reads:
    `data/laya_scores.tsv` (base Laya scores), `data/rg_strict.lines` and `data/rg_fuzzy.lines` (keyword flags), and
    `data/adjudication/manifest.tsv` (byte-identical to `results/1859-adjudication-manifest.tsv`).

  They were not fingerprinted at registration, so this release cannot be checked against a registered hash. The
  registered `results/score_1872_repro_1859.md` was computed from these files before registration; re-running the
  command on its second line from a clean checkout of this commit reproduces its table byte for byte. That is an
  aggregate consistency check of the key, label, score and flag files, not proof they are unchanged, and it does not
  read `items.jsonl` or the M6 partial.
- **Gemma re-runs.** The first Gemma pass stopped on HTTP 500 from the gateway after 342 of 1,287 items (about
  15:37 UTC). The resume at 16:17 UTC (stage log, attempt 1) hit HTTP 500 again and was interrupted before writing a
  label. The 342 first-pass labels, which nobody had looked at at the time of the move (self-reported), were then
  moved aside by hand, outside
  `bin/run_1872.sh`, to `data/1872/attempts/gemma.before_attempt2.tsv` (SHA-256
  `c2c222dd1d8e5e8ee8c6ea0f17a9c56626218c08e4abc8fa52ea9d67cf31f7dd`; this hash was not in the stage log), and a
  fresh pass from the first item started at 16:20 UTC (attempt 2) and finished without errors. The first-pass file
  and the other attempt files will be released with the other 1872 outputs; their SHA-256, recorded here because the
  stage log has none: `gemma_run.attempt1.log` 419f28066b15fc2969cc15db54d0b4dce98278e5e604138dbef92ef86d49f982,
  `gemma_run.before_attempt1.log` 89b08286047fff21334959f17af4418c8bcba1582bbe7ecde65dd3e43534677b,
  `gemma_server.attempt1.txt` bb16e3da24873c2faf9fca6076eaf78af02dd0eea94a47f50cf9ccc3c26d1943.
- **Gemma first-pass comparison (2026-10-10, after the run; code run on 1872 outputs after the download, outside the
  four analyses section 7 allows; a small deviation that touches no hypothesis).** Compared with
  `awk -F'\t' 'NR==FNR {a[$1]=$2; next} ($1 in a) {n++; if (a[$1]==$2) s++; else d++} END {print length(a), s+0, d+0}' data/1872/attempts/gemma.before_attempt2.tsv data/1872/labels/gemma.tsv`,
  all 342 labels match the final pass (342 same, 0 different).
- **What was inspected between the download (07:58 UTC) and the first label (15:14 UTC)** (self-reported, from the run's console log and
  the author's session transcript): the extraction summary, the per-system flag counts and pool size, H, N and n, the
  line and UNPARSED counts of the checker output files, and the checker agents' completion line. No label, verdict,
  score or article text was opened.
- **GitHub server times.** `results/1872/github_events.tsv` saves GitHub's public event feed for the repository
  (server times; the feed keeps about 90 days and can omit pushes). It shows the first 1872 push (the download start
  row) at 07:58:31 UTC, after the OSF registration at 07:51:26 UTC, and the Opus checker's fingerprints pushed at
  15:14:34 UTC, before the first labeling stage's push at 15:14:36 UTC.
- **1859 route split.** `paper/scripts/route_split_1859.py` (1859 data only, written and run on 2026-10-10 after the
  1872 download) gives base Laya's 1859 precision by scoring route, quoted in the paper as development motivation
  (`paper/scripts/route_split_1859.txt`). It reads no 1872 file, so section 7's limit on code written after the
  download (which concerns 1872 outputs) does not apply; it is a post-hoc 1859 diagnostic and is labeled as one.

## Choices where the registration left room

1. **Reprint groups.**
   - Shingle frequencies are counted over all labeled items, which is the registration's literal "over the labeled
     items". Union-find never joins pool and net. On 1859, counting within each part gives the same partition (referee
     check).
   - Shingles are kept as strings, not as Python's per-process string hash: the same sets barring a hash collision.
   - A net group weighs H/n (one net weight); a pool group weighs 1.
2. **Group-level H1.**
   - Precision and recall are recomputed per group.
   - Sightings strict search missed are reported two ways: the distinct groups behind the article-level misses (the
     registration's wording), and the final-YES groups the classifier flags with no strict-matched member.
   - No group-level pass or fail is stated: the article-level H1 decides. H3 is not repeated (not registered).
3. **OCR quality.**
   - Share of whitespace tokens for which `str.isalpha` is true (Unicode letters; a token with attached punctuation
     does not count as letters). An empty article scores 0.
   - Cut points are `statistics.quantiles(pool, n=3)` with the default 'exclusive' method. Ties go to the lower
     tercile, and net articles use the pool's cut points.
   - Point estimates only: the registration names no interval for this exploratory measure.
4. **Truncation count.**
   - Counted with laya 0.4.1's own encoding code (`Agent._encode_state`) on copies of the fine-tuned checkpoint's
     tokenizer and config. The config files match their frozen hashes. The tokenizer files are not in the frozen
     list; their hashes on the GPU host and in the copy are recorded in `results/1872/ft_checkpoint_copy.sha256`.
   - Two counts are given: articles longer than 4,096 tokens, and articles the model actually cut. The question
     header uses part of the 4,096-token budget, so the second count can be larger. Token counts are of the serialized
     state, a few tokens more than the article text.
   - The encoding shortcut gave the same dropped-token counts as a real `predict_batch` call on the 30 longest 1859
     articles at two budgets (`bin/check_truncation_encoder.py`, output in
     `results/1872/truncation_encoder_check.txt`). That check used base Laya, not the fine-tuned checkpoint, and did
     not compare the local transformers version with the GPU container's.
5. **Human audit.**
   - An item's human label is its original card's answer, or its hidden repeat's when only that was answered.
   - Kappa has a percentile bootstrap interval, since the frozen config asks for "95% intervals". Kappa is reported as
     not estimable when a rater gave a single label, because it would read 0 by construction; resamples where it is
     not estimable are left out of its interval, and their number is shown.
   - Positive and negative agreement are reported as computed. When one rater never said YES in a stratum, positive
     agreement is 0% (or not estimable if neither rater said YES), the same degenerate case in which kappa is marked
     not estimable; negative agreement likewise.
   - For 1859, whose strata are defined by the LLM label, a pooled unweighted kappa is added.
   - The corrected intervals cover audit sampling only; the labeled set is not resampled.
   - The registration's not-estimable rule is applied within each resample: a resample in which a stratum has no
     audited LLM-YES (or LLM-NO) item keeps that cell's LLM label. The number of such resamples is reported. Where a
     cell has only one or two audited items, the interval can be lumpy.
   - A corrected H2' is not computed: the registration names the audit-corrected H1 and H2.
   - The answers file must be the page's own download and be committed and pushed before it is scored.

## Known weakness of the registered audit correction

The audit-corrected recall is very sensitive to annotator error on items the LLM key calls NO. Each audited stratum's
p0 (the share of LLM-NO items the human calls YES) is applied to every LLM-NO item in that stratum, and the base-Laya-only
stratum and the loose-net stratum (weight H/n) hold most of the labeled items. A few human false alarms there therefore
add many phantom sightings to the denominator, and they look exactly like LLM misses. In a simulation the referee ran
on the 1859 sample (not committed; to be redone with a committed script before the paper quotes a number), flipping 8%
of answers at random moved fine-tuned Laya's recall from 87.0% (LLM key) to 53.7% (audit-corrected). This comes from
the registered estimator, not from the code. The paper reports the corrected numbers
as a sensitivity analysis next to the test-retest agreement on the hidden repeats, which measures the annotator's own
consistency. As registered, the LLM key decides H1.
