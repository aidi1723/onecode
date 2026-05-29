.PHONY: test route-test live-smoke validate compile smoke verify

UV ?= uv
UV_CACHE_DIR ?= /private/tmp/uv-cache

test:
	python3 -m unittest discover -s tests -v

route-test:
	UV_CACHE_DIR=$(UV_CACHE_DIR) $(UV) run --with-requirements requirements-gateway.txt python -m unittest tests.test_gateway_server_routes -v

validate:
	python3 -m agent_skill_dictionary.validator
	python3 -m json.tool agent_skill_dictionary/programming-agent-skill-dictionary.json >/dev/null
	python3 -m json.tool agent_skill_dictionary/guard_policy.json >/dev/null

compile:
	python3 -m compileall -q agent_skill_dictionary tests

smoke:
	python3 scripts/smoke_test.py

live-smoke:
	UV_CACHE_DIR=$(UV_CACHE_DIR) $(UV) run --with-requirements requirements-gateway.txt python scripts/live_gateway_smoke.py --proxy-tool-call

verify: test validate compile smoke
