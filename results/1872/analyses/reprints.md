# Reprint-group sensitivity (seed 1872, 2000 bootstrap resamples, containment 0.5)

Labeled items: 1287 in 1236 groups (pool 890, net 346); groups with more than one article: 37, largest 8. Weighted final-YES groups: 58.

| System | Flagged groups | Final-YES | Precision, weighted | Weighted recall |
|---|---|---|---|---|
| base_laya | 781 | 44 | 5.6% | 75.9% |
| strict | 141 | 51 | 36.2% | 87.9% |
| fuzzy | 144 | 51 | 35.4% | 87.9% |
| ft_laya | 67 | 50 | 74.6% | 86.2% |
| ft+qwen | 49 | 49 | 100.0% | 84.5% |
| ft+opus | 51 | 50 | 98.0% | 86.2% |

- H2 gain: (strict OR h1) - strict: +8.6% (95% bootstrap +1.8% to +16.7%); lower bound > 0
- H2' gain: (strict OR fuzzy OR h1) - (strict OR fuzzy): +8.6% (95% bootstrap +1.8% to +16.7%); lower bound > 0
- H1 (ft_laya) at group level: precision 74.6%, weighted recall 86.2% (bar: both >= 80%); the 5 final-YES articles it flags that strict missed fall in 5 distinct reprint groups; final-YES groups it flags with no strict-matched member: 5 (point estimates; sensitivity only, the article-level H1 decides)
