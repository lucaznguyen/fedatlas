.PHONY: setup smoke crawl update build dashboard deploy-shinyapps test quality-report clean-cache

PYTHON ?= python
PIP ?= $(PYTHON) -m pip
PIP_INSTALL_FLAGS ?= --user

setup:
	$(PIP) install $(PIP_INSTALL_FLAGS) -r requirements.txt
	$(PYTHON) scripts/00_smoke_test.py --check-setup
	@echo "R dashboard packages are checked when Rscript is available."

smoke:
	$(PYTHON) scripts/00_smoke_test.py --sample-size 5
	$(PYTHON) -m pytest

crawl:
	$(PYTHON) scripts/01_crawl_openalex.py

update:
	$(PYTHON) scripts/08_weekly_update.py

build:
	$(PYTHON) scripts/run_pipeline.py --skip-crawl

dashboard:
	Rscript -e "shiny::runApp('dashboard', host='0.0.0.0', port=3838)"

deploy-shinyapps:
	Rscript scripts/09_deploy_shinyapps.R

test:
	$(PYTHON) -m pytest
	$(PYTHON) scripts/00_smoke_test.py --r-check

quality-report:
	$(PYTHON) -m fedatlas.data_quality

clean-cache:
	$(PYTHON) -c "from pathlib import Path; import shutil; [shutil.rmtree(p, ignore_errors=True) for p in [Path('data/raw/openalex'), Path('data/raw/paperswithcode'), Path('data/raw/github'), Path('data/interim')]]; [p.mkdir(parents=True, exist_ok=True) for p in [Path('data/raw/openalex'), Path('data/raw/paperswithcode'), Path('data/raw/github'), Path('data/interim')]]"
