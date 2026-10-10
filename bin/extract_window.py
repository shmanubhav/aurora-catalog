"""Stream an American Stories year archive and keep articles dated inside a window.

Usage: python -I bin/extract_window.py ARCHIVE START END OUT.jsonl
Mirrors the field mapping in the dataset's AmericanStories.py without running it.
"""
import json
import statistics
import sys
import tarfile

archive, start, end, out_path = sys.argv[1:5]

scans_total = scans_window = articles_total = excluded_unparsed = excluded_no_lccn = excluded_window = 0
lengths = []

with tarfile.open(archive, "r|gz") as tf, open(out_path, "w") as out:
    for member in tf:
        if not member.isfile() or not member.name.endswith(".json"):
            continue
        scans_total += 1
        filename = member.name.split("/")[-1]
        scan_id = filename.rsplit(".", 1)[0]
        date = filename.split("_")[0]
        try:
            data = json.load(tf.extractfile(member))
        except (json.JSONDecodeError, UnicodeDecodeError):
            excluded_unparsed += 1
            excluded_window += start <= date <= end
            continue
        if "lccn" not in data:
            excluded_no_lccn += 1
            excluded_window += start <= date <= end
            continue
        articles = data.get("full articles", [])
        articles_total += len(articles)
        if not (start <= date <= end):
            continue
        scans_window += 1
        for a in articles:
            text = a.get("article") or ""
            lengths.append(len(text))
            out.write(json.dumps({
                "article_id": f"{a['full_article_id']}_{scan_id}",
                "newspaper_name": data["lccn"].get("title"),
                "edition": filename.split("_")[-2][8:],
                "date": date,
                "page": filename.split("_")[1],
                "headline": a.get("headline") or "",
                "byline": a.get("byline") or "",
                "article": text,
            }) + "\n")

q = statistics.quantiles(lengths, n=20) if len(lengths) > 1 else [0] * 19
print(json.dumps({
    "scans_year": scans_total,
    "excluded_unparsed": excluded_unparsed,
    "excluded_no_lccn": excluded_no_lccn,
    "excluded_in_window": excluded_window,
    "articles_year": articles_total,
    "scans_window": scans_window,
    "articles_window": len(lengths),
    "chars_median": int(statistics.median(lengths)) if lengths else 0,
    "chars_p90": int(q[17]),
    "share_over_2000_chars": round(sum(n > 2000 for n in lengths) / max(len(lengths), 1), 3),
}, indent=2))
