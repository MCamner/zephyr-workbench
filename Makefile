.PHONY: generate-js check-js test

generate-js:
	python scripts/generate_js_core.py

check-js:
	python scripts/generate_js_core.py
	git diff --exit-code docs/zephyr-core.js

test:
	pytest -q
