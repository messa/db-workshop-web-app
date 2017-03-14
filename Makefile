python3=python3
venv_dir=venv

default: check

venv: $(venv_dir)/packages-installed

$(venv_dir)/packages-installed: requirements.txt
	test -d $(venv_dir) || $(python3) -m venv $(venv_dir)
	$(venv_dir)/bin/pip install -U pip
	$(venv_dir)/bin/pip install -r requirements.txt
	touch $@

check: $(venv_dir)/packages-installed
	$(venv_dir)/bin/pytest -v tests.py

run: $(venv_dir)/packages-installed
	env \
		FLASK_APP=anketa.py \
		FLASK_DEBUG=1 \
		$(venv_dir)/bin/flask run


.PHONY: venv
