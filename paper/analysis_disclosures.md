# Post-download analyses (1872): choices and disclosures

The four analyses below were written after the 1872 run, under section 7 of the pre-registration, which allows exactly
these. They were tested on 1859 data and toy cases only (`bin/test_analyses_1872.sh`), reviewed by an adversarial AI
referee (Claude Opus) until it returned GO, and committed and pushed before they touched any 1872 output. Each then
ran once through `bin/run_analyses_1872.sh`, which checks every input against the stage log and logs every hash.

Where the registration left a choice open, the choice made is listed here for the methods and limitations sections.

1. **Reprint groups.**
   - Shingle frequencies are counted over all labeled items, which is the registration's literal "over the labeled
     items". Union-find never joins pool and net. On 1859, counting within each part gives the same partition.
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
     tokenizer and config. The config files match their frozen hashes. The tokenizer files are not in the frozen list;
     their hashes matched the GPU host's files on 2026-10-10.
   - Two counts are given: articles longer than 4,096 tokens, and articles the model actually cut. The question
     header uses part of the 4,096-token budget, so the second count can be larger.
   - The encoding shortcut gave the same dropped-token counts as a real `predict_batch` call on 30 long 1859
     articles at two budgets. That check used base Laya, not the fine-tuned checkpoint, and did not compare the local
     transformers version with the GPU container's.
5. **Human audit.**
   - An item's human label is its original card's answer, or its hidden repeat's when only that was answered.
   - Kappa has a percentile bootstrap interval, since the frozen config asks for "95% intervals". Kappa is reported
     as not estimable when a rater gave a single label, because it would read 0 by construction.
   - For 1859, whose strata are defined by the LLM label, a pooled unweighted kappa is added.
   - The corrected intervals cover audit sampling only; the labeled set is not resampled.
   - A resample in which a stratum has no audited LLM-YES (or LLM-NO) item keeps that cell's LLM label, as the
     registration's not-estimable rule says. The number of such resamples is reported. Where a cell has only one or
     two audited items, the interval can be lumpy.
   - A corrected H2' is not computed: the registration names the audit-corrected H1 and H2.
   - The answers file must be the page's own download and be committed and pushed before it is scored.
