# webwright

A tiny SWE-style web agent harness. It drives a Playwright browser through a minimal agent loop with pluggable LLM backends.

Lightweight by design. With the core agent loop in a single ~450-line file and the Playwright environment in ~570 lines. The CLI is ~150 lines, model backends (OpenAI, Anthropic, OpenRouter) are ~150–200 lines each, and there are zero hidden frameworks — just httpx, pydantic, playwright, and typer. No multi-agent, no graph engine, no plugin system, no orchestration layer: a flat prompt → observe → act loop you can read end-to-end in one sitting. If you want a minimal, easy to debug starting point for browser-using agents instead of another heavyweight platform, this is it!

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

## Give back to the accessibility community
web-agent research is now benefiting from infrastructure originally designed for accessibility. Accessibility trees, ARIA metadata, and semantic page representations help assistive technologies expose web content to people with disabilities; today, the same signals also give LLM agents a machine-readable view of pages beyond pixels. As builders, we have a responsibility to bring these advances back to the accessibility community. Webwright could support everyday assistive workflows such as forms, appointments, transportation, and service comparison, while also acting as a repair layer for the web itself: inspecting pages, detecting missing labels, confusing controls, broken navigation, or inaccessible forms, and generating reusable scripts or overlays that make sites easier to understand and operate. We encourage developers to propose ideas of using Webwright to help move us closer to a more accessible and useful web for everyone. 

## Credits

- [SWE-agent/mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent/tree/main) — design inspiration for the minimal agent loop.
- [Playwright](https://playwright.dev/) — browser automation.
