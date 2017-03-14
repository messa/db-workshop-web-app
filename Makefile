python3=python3
venv_dir=venv

venv: $(venv_dir)/packages-installed

$(venv_dir)/packages-installed: requirements.txt
	test -d $(venv_dir) || $(python3) -m venv $(venv_dir)
	$(venv_dir)/bin/pip install -U pip
	$(venv_dir)/bin/pip install -r requirements.txt
	touch $@

run: $(venv_dir)/packages-installed
	env \
		FLASK_APP=anketa.py \
		FLASK_DEBUG=1 \
		$(venv_dir)/bin/flask run

.PHONY: venv
