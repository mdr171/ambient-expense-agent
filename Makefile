.PHONY: install playground

install:
	uv pip install -e .

playground:
	uv run python -m expense_agent.fast_api_app

generate-traces:
	uv run python tests/eval/generate_traces.py

grade:
	agents-cli eval grade --config tests/eval/eval_config.yaml
