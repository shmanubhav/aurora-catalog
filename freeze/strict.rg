# STRICT pattern: the best search a careful person would write in five minutes.
# Goal (decision 4): find articles reporting an aurora or a lit-up night sky seen somewhere.
# Rules: one rg regex per line, matched case-insensitively, any line matching flags the article.
#        Lines starting with # are ignored. Text has newlines collapsed to spaces.
# Written without looking at the data; frozen in a commit before Laya runs.
\baurora
\bborealis\b
\bnorthern\s+lights?\b
\bpolar\s+lights?\b
