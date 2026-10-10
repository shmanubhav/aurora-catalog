# Weighted recall by OCR-quality tercile (exploratory)

OCR quality = share of whitespace tokens made only of letters. Cut points from the 933 pool articles: 0.7913 and 0.8329.

| Tercile | Articles (pool + net) | Weighted final-YES | base_laya | strict | fuzzy | ft_laya | ft+qwen | ft+opus |
|---|---|---|---|---|---|---|---|---|
| low | 311 + 113 | 18.0 | 55.6% | 88.9% | 88.9% | 77.8% | 72.2% | 77.8% |
| mid | 311 + 106 | 16.0 | 75.0% | 87.5% | 87.5% | 81.2% | 81.2% | 81.2% |
| high | 311 + 135 | 25.0 | 92.0% | 88.0% | 88.0% | 96.0% | 96.0% | 96.0% |
