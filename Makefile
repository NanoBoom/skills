# Maintainer and install entry points. All Python runs through uv; nothing else
# needs installing. `make help` lists the targets.

UV := uv run
HARNESS ?= all
FORCE_FLAG := $(if $(filter 1 true yes,$(FORCE)),--force)
ONLY_FLAG := $(if $(ONLY),--only $(ONLY))
COPY_FLAG := $(if $(filter 1 true yes,$(COPY)),--copy)
comma := ,
PLUGIN_FLAGS := $(foreach p,$(subst $(comma), ,$(PLUGINS)),--plugin $(p))
PROJECT_FLAG := $(if $(PROJECT),--project $(PROJECT))
INSTALL_FLAGS = $(PLUGIN_FLAGS) $(PROJECT_FLAG)

# install-<harness> and uninstall-<harness> are pattern rules, which make skips
# for .PHONY targets, so they are not listed here.
.PHONY: help generate clean-generated validate test lint format check

help:
	@echo "Generate and check"
	@echo "  make generate [HARNESS=codex|pi]     Write harness artifacts into build/ (default: all)"
	@echo "  make clean-generated [HARNESS=...]   Remove the gitignored generated trees"
	@echo "  make validate [STRICT=1]             Repository contract + generated artifacts"
	@echo "  make test                            pytest"
	@echo "  make lint | make format              ruff"
	@echo "  make check                           validate + test + lint, as CI runs them"
	@echo ""
	@echo "Install from this clone (rerun after git pull)"
	@echo "  make install-codex | install-pi [PLUGINS=a,b] [PROJECT=path] [ONLY=kind] [COPY=1] [FORCE=1]"
	@echo "  make uninstall-codex | uninstall-pi [PLUGINS=a,b] [PROJECT=path]"
	@echo "      PLUGINS   only these plugins (default: all)"
	@echo "      PROJECT   into <path>/.codex or <path>/.pi instead of your user configuration;"
	@echo "                use an absolute path, since make runs in this clone"
	@echo "      ONLY      codex: agents|plugins, or skills|agents with PROJECT"
	@echo "                pi: skills|agents|commands|extensions"
	@echo "      COPY=1    copy files instead of symlinking them"
	@echo "      FORCE=1   replace symlinks that point into another checkout"

generate:
	$(UV) tools/generate.py --harness $(HARNESS)

clean-generated:
	$(UV) tools/generate.py --harness $(HARNESS) --clean

validate:
	$(UV) tools/validate.py $(if $(filter 1 true yes,$(STRICT)),--strict)

test:
	$(UV) pytest -q

lint:
	$(UV) ruff check tools
	$(UV) ruff format --check tools

format:
	$(UV) ruff format tools
	$(UV) ruff check --fix tools

check: validate test lint

install-%:
	$(UV) tools/generate.py --harness $*
	$(UV) tools/install.py install $* $(INSTALL_FLAGS) $(ONLY_FLAG) $(COPY_FLAG) $(FORCE_FLAG)

uninstall-%:
	$(UV) tools/install.py uninstall $* $(INSTALL_FLAGS)
