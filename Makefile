.PHONY: init clean build run mypy pytest tox

init:
	pipenv --python 3.6.3
	pipenv install --dev

clean:
	rm -rf .cache
	rm -rf .tox
	rm -rf .mypy_cache
	find . -type f -name "*.py[co]" -delete
	find . -type d -name "__pycache__" -delete

build: clean
	docker build -t xsteadfastx/mossbot .

run:
	docker run --rm -ti --name mossbot -v $(PWD)/config.yml:/opt/mossbot/config.yml xsteadfastx/mossbot

mypy:
	pipenv run mypy --ignore-missing-imports --follow-imports=skip --strict-optional mossbot.py

pytest:
	pipenv run pytest test_mossbot.py

tox:
	pipenv run tox

isort:
	isort conftest.py
	isort deploy.py
	isort mossbot.py
	isort test_mossbot.py
