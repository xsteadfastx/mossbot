.PHONY: init mypy pytest tox

init:
	pipenv --three
	pipenv install --dev

mypy:
	pipenv run mypy --ignore-missing-imports --follow-imports=skip --strict-optional mossbot.py

pytest:
	pipenv run pytest test_mossbot.py

tox:
	pipenv run tox
