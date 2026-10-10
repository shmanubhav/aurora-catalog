<!-- Reproduction of the 1859 development results by bin/score_1872.py (sha256 434a34ee388c10acddfa3a0b6bc5ce94ea01572e9f35b25ddb2f70a6f971c5f5, the frozen scorer), run 2026-10-10 UTC before any 1872 download:
python3 -I bin/score_1872.py data OUT --seed 1859 --drop-zero-positive --adjudication results/1859-adjudication-opus.tsv --system base_laya=scores:data/laya_scores.tsv:0.5 --system strict=lines:data/rg_strict.lines --system fuzzy=lines:data/rg_fuzzy.lines --system ft_laya=scores3:results/finetune/oof.tsv:0.80 --checker ft+qwen=ft_laya:results/finetune/checkers/1859_qwen_think.tsv --checker ft+opus=ft_laya:results/finetune/checkers/1859_opus.tsv --h1 ft_laya --strict strict --fuzzy fuzzy
Reproduced to the printed digit: the base_laya, strict, ft_laya, ft+qwen and ft+opus rows and the labeler line (results/1859-results.md, results/finetune/checkers/1859_summary.txt, freeze/finetune_freeze2.json). The H2/H2prime/H3 lines and the "neither" counts have no earlier 1859 output: they were first computed here. seed 1859 and --drop-zero-positive reproduce bin/score.py; the 1872 run uses seed 1872 without that flag. -->
# Holdout scores (seed 1859, 2000 bootstrap resamples)

Labeled items: 1544 (pool 1229, net sample 315). Weighted positives in pool + net: 354.

| System | Flags (labeled) | True | Precision, weighted | Unweighted, Wilson 95% | Weighted recall (95% bootstrap) | F1 |
|---|---|---|---|---|---|---|
| base_laya | 927 | 270 | 29.1% | 270/927 (26.3%-32.1%) | 76.3% (71.0%-81.5%) | 0.422 |
| strict | 584 | 322 | 55.1% | 322/584 (51.1%-59.1%) | 91.0% (86.5%-95.0%) | 0.687 |
| fuzzy | 587 | 325 | 55.4% | 325/587 (51.3%-59.3%) | 91.8% (87.4%-95.8%) | 0.691 |
| ft_laya | 327 | 304 | 91.9% | 304/327 (89.7%-95.3%) | 87.0% (82.8%-90.9%) | 0.894 |
| ft+qwen | 296 | 295 | 99.7% | 295/296 (98.1%-99.9%) | 84.5% (80.1%-88.8%) | 0.914 |
| ft+opus | 306 | 303 | 99.0% | 303/306 (97.2%-99.7%) | 86.7% (82.6%-90.7%) | 0.925 |

- H2 gain: (strict OR h1) - strict: +5.4% (95% bootstrap +2.5% to +8.9%); lower bound > 0
- H3 diff: h1 - strict: -4.0% (95% bootstrap -8.5% to +0.8%)
- H2' gain: (strict OR fuzzy OR h1) - (strict OR fuzzy): +4.8% (95% bootstrap +2.0% to +8.3%); lower bound > 0
- H1 (ft_laya): precision 91.9%, weighted recall 87.0%, final-YES flags strict missed 15 -> PASS (point estimates)
- final-YES flagged by base_laya and matched by neither strict nor fuzzy: 19
- final-YES flagged by strict and matched by neither strict nor fuzzy: 0
- final-YES flagged by fuzzy and matched by neither strict nor fuzzy: 0
- final-YES flagged by ft_laya and matched by neither strict nor fuzzy: 13
- final-YES flagged by ft+qwen and matched by neither strict nor fuzzy: 11
- final-YES flagged by ft+opus and matched by neither strict nor fuzzy: 13
- ft+qwen excluding Opus-adjudicated items (68): precision 277/277 = 100.0% (Wilson 98.6%-100.0%)
- ft+opus excluding Opus-adjudicated items (68): precision 282/283 = 99.6% (Wilson 98.0%-99.9%)
- ft+qwen: flags with no checker verdict, kept by rule: 0
- ft+opus: flags with no checker verdict, kept by rule: 0
- adjudication items unanswered, Sonnet label kept by rule: 0
- items with no label (Sonnet batch failed, adjudication unanswered), excluded: 0

Labelers: Claude vs Gemma raw agreement 98.0%, Cohen's kappa 0.94 (1536 items, 8 Gemma UNPARSED). Adjudicator overturned 0 of 30 answered agreed checks (30 drawn).
