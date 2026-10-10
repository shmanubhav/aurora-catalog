"""Score the human audit.

Usage: python -I bin/score_audit.py audit_key.tsv answers.tsv final_labels.tsv
audit_key.tsv: card_id, source_id, is_repeat (with header). answers.tsv: card_id<TAB>YES|NO.
final_labels.tsv: id<TAB>YES|NO (LLM labels). Agreement stats use non-repeat cards only.
"""
import random
import sys


def read_pairs(path, skip_header=False):
    rows = [line.rstrip("\n").split("\t") for line in open(path) if line.strip()]
    return rows[1:] if skip_header else rows


def kappa(pairs):
    n = len(pairs)
    po = sum(a == b for a, b in pairs) / n
    ya = sum(a == "YES" for a, _ in pairs) / n
    yb = sum(b == "YES" for _, b in pairs) / n
    pe = ya * yb + (1 - ya) * (1 - yb)
    return po, (float("nan") if pe == 1 else (po - pe) / (1 - pe))


key_path, ans_path, lab_path = sys.argv[1:4]
key = {r[0]: (r[1], r[2] == "1") for r in read_pairs(key_path, True)}
ans = {r[0]: r[1] for r in read_pairs(ans_path)}
lab = {r[0]: r[1] for r in read_pairs(lab_path)}
bad = [c for c in ans if c not in key or ans[c] not in ("YES", "NO")]
if bad:
    sys.exit(f"bad answer rows: {bad[:5]}")
print(f"answered {len(ans)} of {len(key)} cards")

# Human label per source: first (non-repeat) answer. LLM label from the final-label file.
human, missing = {}, 0
for card, (src, rep) in key.items():
    if not rep and card in ans:
        if src in lab:
            human[src] = ans[card]
        else:
            missing += 1
if missing:
    print(f"warning: {missing} audited items have no final label")
srcs = sorted(human)
pairs = [(human[s], lab[s]) for s in srcs]  # (human, llm)
n = len(pairs)
if n == 0:
    sys.exit("no scorable items")
po, k = kappa(pairs)
rng = random.Random(1872)
ks = []
for _ in range(2000):
    kk = kappa([pairs[rng.randrange(n)] for _ in range(n)])[1]
    if kk == kk:
        ks.append(kk)
ks.sort()
lo, hi = (ks[int(0.025 * len(ks))], ks[min(len(ks) - 1, int(0.975 * len(ks)))]) if ks else (float("nan"),) * 2
print(f"\nitems compared: {n}")
print(f"raw agreement: {po:.3f} ({sum(a == b for a, b in pairs)}/{n})")
print(f"Cohen's kappa: {k:.3f}  95% bootstrap CI [{lo:.3f}, {hi:.3f}] (2000 resamples, seed 1872, {len(ks)} usable)")

print("\nLLM labels scored against human labels")
for cls in ("YES", "NO"):
    tp = sum(h == cls and m == cls for h, m in pairs)
    pred = sum(m == cls for _, m in pairs)
    real = sum(h == cls for h, _ in pairs)
    prec = f"{tp / pred:.3f}" if pred else "n/a"
    rec = f"{tp / real:.3f}" if real else "n/a"
    print(f"  {cls}: precision {prec} ({tp}/{pred})  recall {rec} ({tp}/{real})")

by_src = {}
for card, (src, rep) in key.items():
    if card in ans:
        by_src.setdefault(src, {})["rep" if rep else "orig"] = ans[card]
rt = [(v["orig"], v["rep"]) for v in by_src.values() if "orig" in v and "rep" in v]
print("\ntest-retest on hidden repeats")
if rt:
    agree = sum(a == b for a, b in rt)
    print(f"  pairs answered: {len(rt)}  agreement: {agree / len(rt):.3f} ({agree}/{len(rt)})")
else:
    print("  no complete repeat pairs")
