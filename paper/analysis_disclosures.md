# Post-download analyses (1872): choices and disclosures

## Procedure

Section 7 of the pre-registration allows four analyses to be written after the 1872 download: the reprint-group
sensitivity, the OCR-quality terciles, the human-audit agreement with the audit-corrected H1/H2, and the truncation
count. The procedure for them:

- The code is written after the run and tested on 1859 data and toy cases only (`bin/test_analyses_1872.sh`).
- An adversarial AI referee (Claude Opus) reviews each version until it returns GO.
- The code is committed and pushed, with its hashes in `results/1872/analysis_scripts.sha256`, before it reads any
  1872 output. `bin/run_analyses_1872.sh` refuses to run otherwise.
- Every run of an analysis first commits and pushes a start row to `results/1872/analysis_log.tsv`. It then logs the
  hashes of the scripts, inputs and output, or a failed row. Every attempt, including failed ones and any re-run
  (which needs a stated reason and keeps the earlier output), is on the public record.
- The 1872 inputs are checked against the hashes the stage log recorded. The 1859 inputs of the 1859 audit are hashed
  into the analysis log; those in the frozen manifest are also checked against it. The fine-tuned checkpoint files are
  checked against hashes recorded on 2026-10-10 (`results/1872/ft_checkpoint_copy.sha256`).

Record of what happened (dated; filled in as it happens):

- 2026-10-10, about 13:58 local time: a no-argument call of an early version of the runner created the empty
  `results/1872/analyses/` folder and the header-only analysis log. It printed its usage message; no analysis ran and
  no 1872 output was read.
- 2026-10-10: referee round 1 returned NO-GO (fixed in 5fb4b3c); round 2 returned NO-GO (fixed in the next commit).
- 2026-10-10: the choices below, including the human-label fallback to a repeat card and the kappa not-estimable
  rule, were committed before any audit page was sent to an annotator, so before any human answer existed.

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
     agreement is 0%, the same degenerate case in which kappa is marked not estimable.
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
