.PHONY: bootstrap doctor install install-kernel start verify verify-core

bootstrap:
	bash scripts/bootstrap-local.sh

doctor:
	bash scripts/doctor-local.sh --skip-shell-deps

install:
	bash scripts/install-local.sh

install-kernel:
	bash scripts/install-local.sh --skip-shell

start:
	bash scripts/start-local.sh

verify:
	bash scripts/verify.sh

verify-core:
	bash scripts/verify-core.sh
