.PHONY: init clean build run mypy pytest tox

init:
	pipenv --three
	pipenv install --dev

clean:
	rm -rf .cache
	rm -rf .tox
	rm -rf .mypy_cache
	find . | grep -E "(__pycache__|\.pyc$)" | xargs rm -rf

build: clean
	docker build -t mossbot .

run:
	docker run --rm -ti -v $(PWD)/config.yml:/opt/mossbot/config.yml mossbot

mypy:
	pipenv run mypy --ignore-missing-imports --follow-imports=skip --strict-optional mossbot.py

pytest:
	pipenv run pytest test_mossbot.py

tox:
	pipenv run tox
