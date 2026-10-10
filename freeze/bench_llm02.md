llm02 (RX 7900 XTX) speed and parity bench, fixed before it runs.

- Input: the first 2,000 lines of data/window.txt; same laya_score.py, config.json and checkpoint revision as the M6 run.
- Device: LAYA_DEVICE=cuda (ROCm), LAYA_CUDA_AMP=fp16, in the laya-batch image.
- Pass: no article crosses the 0.5 cutoff relative to data/laya_scores.tsv, and max |p_llm02 - p_m6| <= 0.02.
- Ollama: the run refuses to start if /api/ps lists a model. /api/ps and dGPU VRAM are logged before and after.
  If a model loaded during the run, the scores still count but the speed number is discarded and the run repeated.
- Speed: articles/s from the script's own clock (model load excluded) plus wall time.
