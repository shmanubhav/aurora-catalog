"""Split the blind label set into plain-text batch files a Claude agent can read in one call.

Usage: python -I bin/make_batches.py data/labelset/items.jsonl OUTDIR [MAX_CHARS]
Each article is hard-wrapped at 120 columns and fenced by its id. Writes OUTDIR/bNNN.txt and OUTDIR/bNNN.ids.
"""
import json
import os
import sys
import textwrap

items_path, outdir = sys.argv[1:3]
max_chars = int(sys.argv[3]) if len(sys.argv) > 3 else 60000

batches, current, size = [], [], 0
for line in open(items_path):
    item = json.loads(line)
    block = (f"===== {item['id']} =====\n"
             + textwrap.fill(item["text"], 120, break_long_words=True, break_on_hyphens=False)
             + f"\n===== end {item['id']} =====\n\n")
    if current and size + len(block) > max_chars:
        batches.append(current)
        current, size = [], 0
    current.append((item["id"], block))
    size += len(block)
if current:
    batches.append(current)

os.makedirs(outdir, exist_ok=True)
for n, batch in enumerate(batches, 1):
    with open(f"{outdir}/b{n:03d}.txt", "w") as out:
        out.write("".join(block for _, block in batch))
    with open(f"{outdir}/b{n:03d}.ids", "w") as ids:
        ids.write("".join(f"{item_id}\n" for item_id, _ in batch))
print(f"{len(batches)} batches, {sum(len(b) for b in batches)} items, max {max(len(b) for b in batches)} per batch",
      file=sys.stderr)
