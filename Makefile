python3=python3
venv_dir=venv
docker_image_name=pyworking_anketa

# for deployment only - not needed for localhost development
container_name_prefix=pyworking_anketa
live_port=10004
temp_port=10005
docker_deploy_args= \
	--restart unless-stopped \
	--volume /srv/pyworking-anketa/conf:/conf \
	--volume /srv/pyworking-anketa/data:/data

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
		ANKETA_CONF=conf/anketa.localhost.yaml \
		$(venv_dir)/bin/flask run

docker-image:
	docker build -t $(docker_image_name) .

docker-run: docker-image
	docker run \
		--rm -p 5000:8000 \
		--volume $(PWD)/conf:/conf \
		--volume $(PWD):/data \
		-e ANKETA_CONF=/conf/anketa.localhost-docker.yaml \
		$(docker_image_name)

deploy:
	# designed for nginx upstream fallback capability; see sample conf:
	# https://github.com/messa/www.messa.cz/blob/939a38298967e232ffe96389f59b923b86c796e9/nginx.sample.conf
	git pull --ff-only
	make docker-image
	make deploy-temp
	sleep 2
	curl -f http://localhost:$(temp_port)/ || ( make stop-temp; false )
	make deploy-live
	sleep 2
	curl -f http://localhost:$(live_port)/
	make stop-temp
	@echo Done

deploy-live:
	docker stop $(container_name_prefix)_live || true
	docker rm   $(container_name_prefix)_live || true
	docker run -d --name $(container_name_prefix)_live -p $(live_port):8000 $(docker_deploy_args) $(docker_image_name)

deploy-temp:
	docker stop $(container_name_prefix)_temp || true
	docker rm   $(container_name_prefix)_temp || true
	docker run -d --name $(container_name_prefix)_temp -p $(temp_port):8000 $(docker_deploy_args) $(docker_image_name)

stop-temp:
	docker stop $(container_name_prefix)_temp || true

.PHONY: venv
