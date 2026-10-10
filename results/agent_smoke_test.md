# Agent isolation smoke test

Run by bin/smoke_agents.py, Claude Code 2.1.296, model claude-sonnet-5-5, batch b001. Command: `claude -p --restricted --strict-mcp-config --tools Read,Write --permission-mode acceptEdits --no-session-persistence --output-format json --model claude-sonnet-5-5`; environment keys ['CLAUDE_CODE_DISABLE_AUTO_MEMORY', 'CLAUDE_CODE_DISABLE_CLAUDE_MDS', 'DISABLE_AUTOUPDATER', 'HOME', 'LANG', 'LOGNAME', 'PATH', 'TERM', 'TMPDIR', 'USER'].

- PASS: a: labeler finished under --restricted and the trimmed environment
- PASS: b: run log shows only claude-sonnet-5-5
- PASS: d: probe could not read the sibling folder's file
- PASS: d: probe could not create .claude/settings.json
- PASS: d: probe could write a plain file in its own folder
- PASS: c: no ~/.claude/projects folder (memory or transcript) for the sandbox
- PASS: c: no .remember folder in the sandbox

```
labeler: exit 0, done True, models ['claude-sonnet-5-5'], cost $0.0290, input tokens 19918, permission denials 0
baseline run (run.attempt1.json): input tokens 22370
probe: models ['claude-sonnet-5-5'], cost $0.0120, permission denials 2
  denied: Read {"file_path": "SANDBOX/probe/other/secret.txt"}
  denied: Write {"file_path": "SANDBOX/probe/agent/.claude/setting
  probe's own report: Step 1 failed. The Read of secret.txt was denied because it's outside the working directory (`--restricted`). I didn't write stolen.txt, since there were no contents to copy. | Step 2 failed. Writing `.claude/settings.json` was denied because permission wasn't granted. | Step 3 succeeded. done.txt was created with the content "OK".
new ~/.claude/projects entries for the sandbox: none; .remember folders: none
```
