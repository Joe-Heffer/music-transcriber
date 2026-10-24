.PHONY: setup transcribe clean freeze

PYTHON := .venv/bin/python
# Extra options for scripts/transcribe.py, e.g. make transcribe ARGS="--onset-threshold 0.7"
ARGS ?=
STEMS := $(wildcard stems/*.wav stems/*.WAV)

setup: .venv

.venv: requirements.txt
	uv venv --python 3.10 .venv
	uv pip install --python .venv -r requirements.txt
	@touch .venv

transcribe: .venv
ifeq ($(strip $(STEMS)),)
	@echo "No WAV files in stems/." && exit 1
else
	$(PYTHON) scripts/transcribe.py $(ARGS) $(STEMS)
endif

# Removes generated MIDI and JSON sidecars; keeps midi/.gitkeep.
clean:
	find midi -mindepth 1 ! -name .gitkeep -delete

# Regenerates the pinned requirements.txt from requirements.in.
freeze:
	uv pip compile --python-version 3.10 requirements.in -o requirements.txt
