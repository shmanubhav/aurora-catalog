# Holdout scores (seed 1872, 2000 bootstrap resamples)

Labeled items: 1287 (pool 933, net sample 354). Weighted positives in pool + net: 59.

| System | Flags (labeled) | True | Precision, weighted | Unweighted, Wilson 95% | Weighted recall (95% bootstrap) | F1 |
|---|---|---|---|---|---|---|
| base_laya | 822 | 45 | 5.5% | 45/822 (4.1%-7.2%) | 76.3% (65.7%-86.4%) | 0.102 |
| strict | 143 | 52 | 36.4% | 52/143 (28.9%-44.5%) | 88.1% (78.8%-96.2%) | 0.515 |
| fuzzy | 146 | 52 | 35.6% | 52/146 (28.3%-43.7%) | 88.1% (78.8%-96.2%) | 0.507 |
| ft_laya | 68 | 51 | 75.0% | 51/68 (63.6%-83.8%) | 86.4% (77.2%-94.4%) | 0.803 |
| ft+qwen | 50 | 50 | 100.0% | 50/50 (92.9%-100.0%) | 84.7% (75.4%-92.9%) | 0.917 |
| ft+opus | 52 | 51 | 98.1% | 51/52 (89.9%-99.7%) | 86.4% (77.2%-94.4%) | 0.919 |

- H2 gain: (strict OR h1) - strict: +8.5% (95% bootstrap +1.7% to +16.7%); lower bound > 0
- H3 diff: h1 - strict: -1.7% (95% bootstrap -13.2% to +9.6%)
- H2' gain: (strict OR fuzzy OR h1) - (strict OR fuzzy): +8.5% (95% bootstrap +1.7% to +16.7%); lower bound > 0
- H1 (ft_laya): precision 75.0%, weighted recall 86.4%, final-YES flags strict missed 5 -> FAIL (point estimates)
- final-YES flagged by base_laya and matched by neither strict nor fuzzy: 7
- final-YES flagged by strict and matched by neither strict nor fuzzy: 0
- final-YES flagged by fuzzy and matched by neither strict nor fuzzy: 0
- final-YES flagged by ft_laya and matched by neither strict nor fuzzy: 5
- final-YES flagged by ft+qwen and matched by neither strict nor fuzzy: 5
- final-YES flagged by ft+opus and matched by neither strict nor fuzzy: 5
- ft+qwen excluding Opus-adjudicated items (35): precision 48/48 = 100.0% (Wilson 92.6%-100.0%)
- ft+opus excluding Opus-adjudicated items (35): precision 49/50 = 98.0% (Wilson 89.5%-99.6%)
- ft+qwen: flags with no checker verdict, kept by rule: 0
- ft+opus: flags with no checker verdict, kept by rule: 0
- adjudication items unanswered, Sonnet label kept by rule: 0
- items with no label (Sonnet batch failed, adjudication unanswered), excluded: 0

Labelers: Claude vs Gemma raw agreement 99.9%, Cohen's kappa 0.99 (1283 items, 4 Gemma UNPARSED). Adjudicator overturned 0 of 30 answered agreed checks (30 drawn).
