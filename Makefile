ENV_NAME := lunar-nav
PY ?= python

.PHONY: env data derived test app

env:  ## create the conda env (Python 3.11, GDAL from conda-forge)
	mamba env create -f pipeline/environment.yml || conda env create -f pipeline/environment.yml

data:  ## download raw data into data/raw/
	$(PY) -m pipeline.fetch_data

derived:  ## precompute data/derived/ from data/raw/
	$(PY) -m pipeline.build_all

test:
	$(PY) -m pytest

app:
	streamlit run app/Home.py
