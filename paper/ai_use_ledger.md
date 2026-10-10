# AI-use ledger (Paper 1)

One row per step where AI did or assisted the work: what it did, the validity risk a reviewer would raise, the mitigation, and the evidence that the mitigation worked. This ledger becomes the paper's AI-use disclosure. Status: ✅ mitigated with evidence, ⚠️ open, 🔄 in progress.

| # | Step | AI role | Validity risk | Mitigation | Evidence | Status |
|---|---|---|---|---|---|---|
| 1 | Keyword baselines | none: written by hand before any model ran (1859) | n/a | n/a | freeze/strict.rg (Freeze 1) | ✅ |
| 2 | First-pass classifier | Laya, open weights, pinned revisions | method under test | frozen, cross-validated, holdout storm | Freeze 1 and Freeze 2 records in freeze/ | ✅ |
| 3 | Checker arms | Qwen3.8 (open weights, pinned digest), Claude Opus 5.5 | proprietary model drift; checker shares a model family with the labelers | open-model primary arm; versions and digests pinned; Opus overlap disclosed and reported excluding Opus-adjudicated items | freeze/checker_arms.json | ✅ |
| 4 | Ground-truth labels | Claude Sonnet and Gemma label; Claude Opus adjudicates | **AI-made ground truth grading AI systems** (circularity); label noise in the gray zone | human audit pre-registered (prereg section 5): independent annotator, author fallback after 4 weeks disclosed; stratified 1872 sample, balanced 1859 sample | results/audit/sample_1859.tsv, items_1859.jsonl | 🔄 |
| 5 | "New sighting" claims | AI finds candidates | a historical claim made without human verification | the author checks each claimed new sighting against the original page scan (Chronicling America) | none yet | ⚠️ |
| 6 | Pre-registration text | Claude drafted it; a Claude Opus agent red-teamed it | AI-written methods text | author reviews and owns every statement; disclosed | prereg/1872_preregistration.md | 🔄 |
| 7 | Literature and policy checks | agents searched and summarized | hallucinated citations | every citation opened and verified before it enters the paper | n/a | 🔄 |
| 8 | Analysis code | Claude wrote the scripts | bugs | frozen before data; Claude Opus review rounds and automated Claude security reviews of each commit; offline tests; public with the pre-registration | bin/*, bin/test_score_1872.sh, bin/test_agents.sh, MANIFEST.tsv | 🔄 |
| 9 | Paper drafting | to come | AI-written claims | author verifies every claim; disclosure per venue policy | n/a | ⚠️ |
| 10 | Authorship | none | AI cannot be an author | the human author is the sole author | n/a | ✅ |
| 11 | Pipeline agents | Sonnet labelers, Opus checker and adjudicator run as headless Claude Code agents | an agent sees other files, answers or memory; another model answers | one folder per agent, --restricted, Read/Write only, allowlisted environment, model verified per run, answers hash-attested (bin/run_agents.py, bin/collect_agents.py) | results/agent_smoke_test.md, bin/test_agents.sh; results/1872_stage_log.tsv on run-1872 | 🔄 |

## Venue AI policies (primary sources, read in Chrome 2026-10-10 UTC unless noted)

| Venue | AI as author | Where to disclose AI use | AI in method/data | Data and code | Cost / barrier |
|---|---|---|---|---|---|
| AGU *Space Weather* ([policies](https://www.agu.org/publications/authors/policies), AI Tools Policy) | not permitted | Materials and Methods: which tool and how, covering writing, images, and data collection and analysis | allowed if disclosed | data availability statement in Open Research; data and software in a DOI repository, not GitHub (agent fetch) | APC not checked |
| *JSWSC* ([EDP AI policy](https://www.edpsciences.org/en/publishing-policies-ethics), Sep 2025; [author instructions](https://www.swsc-journal.org/author-information/instructions-for-authors)) | not permitted | writing use: at submission, with tool, version and role | EDP policy "applies solely to the writing process, not to … data analysis or research activities"; no AI figures unless AI is part of the method | Data Availability section mandatory and specific; FAIR | APC **€1,250**; it has a "Historical events and observations" article type for "hitherto unpublished older data" |
| *MNRAS* ([instructions](https://academic.oup.com/mnras/pages/general_instructions)) | not permitted | cover letter **and** Methods or Acknowledgements, including AI that wrote code or processed data | allowed if disclosed | Data Availability Statement (template) | not checked |
| *Geoscience Data Journal* ([author guidelines](https://rmets.onlinelibrary.wiley.com/hub/journal/20496060/about/author-guidelines)) | per Wiley: not permitted | per Wiley: at submission | RMetS AI policy linked, not read | DAS required; Data Articles need a public repository with a persistent identifier (DOI), and scripts archived where possible | fully OA, APC not checked |
| *JOHD* ([Ubiquity AI policy](https://ubiquitypress.com/ai-policy), Nov 2025) | not permitted | Methods, for anything beyond copyediting | **"We do not permit GenAI tools to be used to create, alter, or manipulate original research data"**: AI-made labels are a risk for a dataset paper; editors judge declared use case by case | FAIR open data in a repository; scripts archived | ask the editor first |
| arXiv ([moderation](https://info.arxiv.org/help/moderation/index.html), [endorsement](https://info.arxiv.org/help/endorsement.html); agent fetch) | not permitted | report significant use as methodology | allowed if reported | none | **needs a personal endorser** without an institutional email |

LLM-annotation validation: Pangakis, Wolken & Fasching 2023 ([arXiv 2306.00176](https://arxiv.org/abs/2306.00176)), p. 4: "the number of samples annotated should range between 250 and 1,250 random text samples", with human labels made from the same codebook. Read in the PDF on 2026-10-10.
