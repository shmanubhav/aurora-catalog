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
- Times and inspections marked self-reported rest on the author's own records (git commit times, the run's console
  log and working notes); GitHub and OSF server times are the independent record.

Record of what happened (dated; filled in as it happens):

- 2026-10-10, about 17:58 UTC: a no-argument call of an early version of the runner created the empty
  `results/1872/analyses/` folder and the header-only analysis log. It printed its usage message; no analysis ran and
  no 1872 output was read.
- 2026-10-10: AI referee round 1 returned NO-GO (fixed in 5fb4b3c); round 2 returned NO-GO (fixed in 19f6f21); round 3
  returned NO-GO (fixed in e1d6aa4); round 4 returned GO on e1d6aa4. The reprint, OCR and truncation analyses ran on
  e1d6aa4's code (the OCR and truncation start rows record its log-only descendants 577c674 and 31cea8c; `bin/` and
  `paper/` are unchanged between them).
- 2026-10-10: the analysis code was first committed (7ce9342, 17:58:57 UTC) after the main 1872 results were
  computed (`results/1872/results.md`, logged 17:41:48 UTC). Both times are self-reported.
- 2026-10-10: the choices below, including the human-label fallback to a repeat card and the kappa not-estimable
  rule, were made before any audit page was sent to anyone (self-reported), so before any human answer existed. Git
  commit times are self-reported; the public timestamp is the push of this branch, which comes before any page is
  sent.

## Other dated decisions after the download

- **Release of the 1872 outputs (deviation).** Section 7 of the pre-registration says 1872 outputs are added on
  `run-1872` as each stage completes. Only `results/1872/` (summary results, the label-set key and the audit
  sample) was committed; the stage output files under `data/1872/` (labels, checker verdicts, adjudication, flags and
  scores) were published as SHA-256 hashes in `results/1872_stage_log.tsv`, not as files. The author decided on
  2026-10-10 to release those files once the human-audit answers are committed, so that the annotator cannot look up
  the answer key or the checkers' verdicts. Each audited article's stratum, which shows which systems flagged it, is
  already public in `results/1872/sample_1872.tsv`; on that point the 1872 page, like the 1859 page (pre-registration
  section 5), is blind by instruction only. This entry is pushed before any audit page is sent. The stage-log hashes
  let anyone check the released files. The paper lists this as a deviation.
- **Release of the 1859 labels (deviation; 2026-10-10).** Section 7 of the pre-registration says the 1859 labels are
  public from registration. Of the 1859 label files, only the adjudications, the audit sample and the checker outputs
  were: the labelers' files sit under `data/`, which git ignores. They are committed with this entry and pushed on
  2026-10-10, at the paths the code reads:
  - `data/labelset/key.tsv` (id, window line, stratum, weight) and `data/labelset/items.jsonl` (the article text, from
    American Stories, CC BY 4.0);
  - `data/labels/claude/b001.tsv` to `b078.tsv` (Claude Sonnet);
  - `data/labels/gemma.tsv` (Gemma on the GPU host, the labels used) and `data/labels/gemma_m6_partial.tsv` (the
    earlier partial Gemma run on the author's workstation, 155 items, not used);
  - so that the registered reproduction can be re-run from the repository, the other 1859-only inputs it reads:
    `data/laya_scores.tsv` (base Laya scores), `data/rg_strict.lines` and `data/rg_fuzzy.lines` (keyword flags), and
    `data/adjudication/manifest.tsv` (byte-identical to `results/1859-adjudication-manifest.tsv`).

  They were not fingerprinted at registration, so this release cannot be checked against a registered hash. The
  registered `results/score_1872_repro_1859.md` was computed from these files before registration; re-running the
  command on its second line from a clean checkout of this commit reproduces its table byte for byte. That is an
  aggregate consistency check of the key, label, score and flag files, not proof they are unchanged, and it does not
  read `items.jsonl` or `gemma_m6_partial.tsv`.
- **Gemma re-runs.** The first Gemma pass stopped on HTTP 500 from the gateway after 342 of 1,287 items (about 15:37
  UTC). The resume at 16:17 UTC (stage log, attempt 1) hit HTTP 500 again and was stopped at 16:19 UTC, before
  writing a label. The 342 first-pass labels, whose answers had not been read (self-reported), were then moved by
  hand, outside `bin/run_1872.sh`, to `data/1872/attempts/gemma.before_attempt2.tsv` (SHA-256
  `c2c222dd1d8e5e8ee8c6ea0f17a9c56626218c08e4abc8fa52ea9d67cf31f7dd`; this hash was not in the stage log). No server
  setting was changed between attempts, and the cause of the HTTP 500 errors was not identified. The GPU had been
  busy at 16:18 UTC, and what it was processing was not recorded. A fresh pass from the first item started at 16:20
  UTC (attempt 2), after three checks showed the GPU idle (self-reported), and finished without errors. The
  first-pass file and the other attempt files (two logs and a one-line server-version record, copied by hand) will be
  released with the other 1872 outputs; their SHA-256, recorded here because the stage log has none:
  - `gemma_run.attempt1.log` 419f28066b15fc2969cc15db54d0b4dce98278e5e604138dbef92ef86d49f982
  - `gemma_run.before_attempt1.log` 89b08286047fff21334959f17af4418c8bcba1582bbe7ecde65dd3e43534677b
  - `gemma_server.attempt1.txt` bb16e3da24873c2faf9fca6076eaf78af02dd0eea94a47f50cf9ccc3c26d1943
- **Gemma first-pass comparison (2026-10-10, after the run; code run on 1872 outputs after the download, outside the
  four analyses section 7 allows: a deviation; no hypothesis test uses it).** All 342 first-pass labels match the
  final pass (it prints `342 342 0`: 342 compared, 342 the same, 0 different). The command:

  ```
  awk -F'\t' 'NR==FNR {a[$1]=$2; next} ($1 in a) {n++; if (a[$1]==$2) s++; else d++} END {print length(a), s+0, d+0}' data/1872/attempts/gemma.before_attempt2.tsv data/1872/labels/gemma.tsv
  ```

- **What was inspected between the download (07:58 UTC) and the first label (15:14 UTC)** (self-reported, from the
  author's own records of the run): the extraction summary, the per-system flag counts and pool size, H, N and n, the
  line and UNPARSED counts of the checker output files, and the checker agents' completion line. No label, verdict,
  score or article text was opened.
- **GitHub server times.** `results/1872/github_events.tsv` saves GitHub's public event feed for the repository
  (server times; the feed keeps about 90 days and lists only some pushes). The union of two fetches lists 17 of the
  44 one-commit pushes of `run-1872`; every listed push matches the stage log's commit
  order and times. It shows the first 1872 push (the download
  start row) at 07:58:31 UTC, after the OSF registration at 07:51:26 UTC; the Qwen checker's fingerprints at 12:23:51
  UTC; and the Opus checker's fingerprints at 15:14:34 UTC, before the first labeling stage's push at 15:14:36 UTC.
- **1859 route split (development motivation; its reading was later corrected).** On 2026-10-09, in development,
  base Laya's 1859 precision was split ad hoc by scoring route: 58.5% for articles of 300 tokens or fewer, 21.3% for
  longer ones, which go to laya 0.4.1's `predict_long`. It was read then as the max-over-windows drift Laya's
  documentation warns about, and it was part of the recorded reason for fine-tuning the multilingual model (whole
  articles, no windowing).
  `paper/scripts/route_split_1859.py` recomputed it on 2026-10-10 (`route_split_1859.txt`). An AI review (Claude Opus)
  then pointed out that `predict_long` reads an article whole when its serialized state (the article wrapped as laya
  scores it) fits the room the question leaves (464 tokens here), and `paper/scripts/route_subsplit_1859.py`, written
  and run on 2026-10-10 with laya's own `window_budget`,
  splits the long route: read whole 21.6% (25 of 116), windowed 21.3% (131 of 616) (`route_subsplit_1859.txt`). So
  windowing does not explain the gap; this split cannot tell article length apart from the short route's batched
  scoring. The paper reports the split only as the motivation recorded at the time, with this correction, not as
  evidence. Both scripts read 1859 data only, so
  section 7's limit on code written after the download (which concerns 1872 outputs) does not apply. The
  base-Laya scoring ran as registered ("as in 1859"); only its description was imprecise: the pre-registration
  (section 3) and the frozen configs (`freeze/config.json`, `freeze/config_1872.json`) describe the long route as
  scored in windows, but long-route articles whose serialized state fits 464 tokens were read in one pass.
- **Audit-error simulation (2026-10-11 UTC; not pre-registered).** Written and run on 1859 data only, to replace an AI
  review's single uncommitted run with a committed script, and pushed before any audit page is sent. See "Sensitivity
  of the registered audit correction to annotator error" below.

## Choices where the registration left room

1. **Reprint groups.**
   - Shingle frequencies are counted over all labeled items, which is the registration's literal "over the labeled
     items". Union-find never joins pool and net. On 1859, counting within each part gives the same partition (AI
     referee check).
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

## Sensitivity of the registered audit correction to annotator error

The audit-corrected recall is very sensitive to annotator error on items the LLM key calls NO. Each audited stratum's
p0 (the share of LLM-NO items the human calls YES) is applied to every LLM-NO item in that stratum, and the
base-Laya-only stratum and the loose-net stratum (weight H/n) hold most of the labeled items. A few human false alarms
there therefore add many spurious sightings to the denominator, and they look exactly like LLM misses. The effect
follows from the registered estimator; the code implements it as registered.

A simulation measures the effect (`paper/scripts/audit_error_sim_1859.py`, output beside it). It is not
pre-registered. It reads 1859 data only, so section 7's limit on code written after the download (which concerns 1872
outputs) does not apply, and it is pushed before any audit page is sent (the push time is on GitHub; see "GitHub
server times" above for the limits of GitHub's public record). It takes the LLM key as correct and flips a simulated
annotator's answers at random, at the same rate in every stratum and independently of the article (real errors are
probably more frequent on borderline articles). Each answers file is scored by the unmodified `bin/audit_1872.py` (the
hashed version in `results/1872/analysis_scripts.sha256`), the code that will score the real answers. The registered
1859 audit sample (50 YES, 50 NO) gets no corrected H1/H2, so the simulation draws its own 1859 sample of 250 by the
1872 rules (pre-registration section 5). With no flips, the scorer prints the LLM-key numbers (fine-tuned Laya recall
87.0%). Over 200 seeds, the median corrected recall is:

- 83.4% with 1% of answers flipped both ways (2.5-97.5 percentile range 74.0% to 87.0%);
- 77.2% with 2% flipped (66.0% to 86.1%);
- 68.1% with 4% flipped (55.3% to 80.8%);
- 55.2% with 8% flipped (42.3% to 69.9%).

Flipping answers only on items the key calls NO moves recall almost as much (8%: 56.7%). Flipping answers only on
items it calls YES barely moves recall (8%: 86.6%) but lowers precision (8%: 84.8%, from 91.9%). So the recall drop
comes from false YES answers on key-NO items, as described above. An AI review (Claude Opus) earlier ran a single,
uncommitted simulation (8% both ways, seed 7) and reported a recall of 53.7%; that run is one of the 200 here and
gives the same 53.7%. 1872 has far fewer sightings than 1859 (59 weighted sightings, against 354) for about as many
articles the key calls NO, so the same annotator error rate would be expected to move the 1872 corrected recall more
than it moves these 1859 numbers (1872 was not simulated).

The paper reports the corrected numbers as a sensitivity analysis next to the test-retest agreement on the hidden
repeats, which measures the annotator's own consistency. That check has limited power: in the simulation, 135 of 200
simulated annotators with 2% of answers flipped agreed with themselves on all 10 pairs, and it cannot detect an error
the annotator repeats. Per-stratum agreement and kappa are reported as registered (pre-registration section 5). As
registered, the LLM key decides H1.
