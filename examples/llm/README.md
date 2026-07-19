# Live LLM Examples

Fifteen executable examples exercise MatSimPy AI from single calls through pipelines, multi-turn state, and error recovery. Each scenario stores sanitized requests, tool traces, final responses, deterministic validation, LLM-judge analysis, and artifact inventories in its own `results/` directory.

```bash
python -m examples.llm.01_water_xyz.run
python -m examples.llm.run_all --repetitions 3  # skips complete passing scenarios
python -m examples.llm.run_all --run-all --repetitions 3  # intentional full rerun
```

`DEEPSEEK_API_KEY` must be available in the process environment. Generated result folders and `stability-report.json` may contain model output and should be reviewed before publication.
