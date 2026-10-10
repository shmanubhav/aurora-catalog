"""The one validator for agent answer files, shared by bin/run_agents.py and bin/collect_agents.py.

An answer file is valid when it has exactly one line per id in the batch's .ids file, in order, no blank lines,
and every line has exactly COLUMNS tab-separated fields with YES or NO in the second.
"""
import hashlib


def valid(path, ids_path, columns):
    try:
        lines = open(path, encoding="utf-8").read().split("\n")
    except (OSError, UnicodeDecodeError):
        return False
    if lines and lines[-1] == "":
        lines = lines[:-1]
    want = open(ids_path, encoding="utf-8").read().split("\n")
    want = want[:-1] if want and want[-1] == "" else want
    if len(lines) != len(want):
        return False
    for line, i in zip(lines, want):
        f = line.split("\t")
        if len(f) != columns or f[0] != i or f[1] not in ("YES", "NO"):
            return False
    return True


def sha256(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def read_labels(path, allowed, columns=None):
    """Strictly read an id<TAB>label[<TAB>...] file into {id: label}: every line non-blank, the label in `allowed`,
    exactly `columns` tab-separated fields when given (at least two otherwise), and no id twice. Raises ValueError."""
    out = {}
    lines = open(path, encoding="utf-8").read().split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    for n, line in enumerate(lines, 1):
        f = line.split("\t")
        if len(f) < 2 or (columns is not None and len(f) != columns) or f[1] not in allowed or not f[0] or f[0] in out:
            raise ValueError(f"{path}:{n}: malformed label line")
        out[f[0]] = f[1]
    return out


# How every agent is launched (bin/run_agents.py and bin/smoke_agents.py use exactly this).
# --restricted: user/project/local settings ignored (no hooks, plugins or settings-file env), file tools confined to
# the working directory, settings files writable only by a person. The environment is an allowlist, so session,
# proxy and messaging variables never reach an agent; auto memory and CLAUDE.md loading are off.
PROXY_VARS = ("ANTHROPIC_BASE_URL", "ANTHROPIC_MODEL", "ANTHROPIC_DEFAULT_SONNET_MODEL", "ANTHROPIC_DEFAULT_OPUS_MODEL",
              "ANTHROPIC_DEFAULT_HAIKU_MODEL", "ANTHROPIC_SMALL_FAST_MODEL", "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX")
ENV_KEEP = ("PATH", "HOME", "USER", "LOGNAME", "TMPDIR", "LANG", "TERM")


def agent_cmd(model):
    return ["claude", "-p", "--restricted", "--strict-mcp-config", "--tools", "Read,Write", "--permission-mode", "acceptEdits",
            "--no-session-persistence", "--output-format", "json", "--model", model]


def agent_env(environ):
    """The agents' whole environment. Refuses to start if a variable could route agents through a proxy or swap models."""
    bad = [v for v in PROXY_VARS if environ.get(v)]
    if bad:
        raise SystemExit(f"{', '.join(bad)} set: agents must reach the Anthropic API directly with the pinned model")
    env = {k: environ[k] for k in ENV_KEEP if k in environ}
    env.update(DISABLE_AUTOUPDATER="1", CLAUDE_CODE_DISABLE_AUTO_MEMORY="1", CLAUDE_CODE_DISABLE_CLAUDE_MDS="1")
    return env
