# webwright

A tiny SWE-style web agent harness. It drives a Playwright browser through a minimal prompt/observe/act loop with pluggable LLM backends.

## Project map

```
webwright/
├── pyproject.toml           # package: webwright
├── src/webwright/
│   ├── run/cli.py           # CLI entrypoint (`webwright`)
│   ├── agents/default.py    # core agent loop
│   ├── environments/        # Playwright browser workspace
│   ├── tools/               # image_qa, self_reflection
│   ├── models/              # openai_model, anthropic_model, base
│   ├── config/              # base.yaml, model_openai.yaml, model_claude.yaml
│   └── utils/
├── tests/
└── outputs/                 # run artifacts (trajectories, screenshots)
```

## Install

```bash
# Python >= 3.10
pip install -e .
playwright install chromium
```

## Use

Export credentials for the chosen backend (e.g. `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`), then:

```bash
python -m webwright.run.cli \
    -c base.yaml -c model_openai.yaml \
    -t "Find the cheapest economy flight from SEA to JFK on 2026-05-15" \
    --start-url https://www.google.com/flights \
    --task-id demo_openai \
    -o outputs/default
```

Flags:
- `-c` — config file(s) from `src/webwright/config/` (stackable).
- `-t` — task instruction.
- `--start-url` — initial page.
- `--task-id` — output subfolder name.
- `-o` — output directory.

## Credits

- [SWE-agent/mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent/tree/main) — design inspiration for the minimal agent loop.
- [Playwright](https://playwright.dev/) — browser automation.
