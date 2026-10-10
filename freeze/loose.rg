# LOOSE NET: wide enough that almost no real sighting escapes, even with many false hits.
# It only runs over articles that neither the strict pattern nor Laya flagged.
# We label a random 1-in-N sample of its hits to estimate what both searchers missed (decision 8).
# Same rules as strict.rg: one regex per line, case-insensitive, # lines ignored.
\b(sky|skies|heavens|firmament|celestial)\b
\b(glow\w*|crimson|luminous|luminosity|streamers?|coruscat\w*|corruscat\w*)\b
\bphenomen(on|a)\b
\bnorth(ern|ward)?\b.{0,60}\b(light|lights|red|bright|brilliant|illuminat\w*)\b
