MAP = maps/easy/01_linear_path.txt 

run:
	python3 fly_in.py $(MAP)

install:
	pip install mypy flake8

debug:
	python3 -m pdb fly_in.py $(MAP)

clean:
	find . -type d \( -name "__pycache__" -o -name ".mypy_cache" \) -exec rm -rf {} +

lint:
	flake8 .
	mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs