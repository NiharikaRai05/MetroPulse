.PHONY: help install ingest transform test export dash build clean

PYTHON ?= python

help:
	@echo "=================================================================="
	@echo "MetroPulse: NYC Multimodal Mobility Analytics Pipeline (Q2 2024)"
	@echo "=================================================================="
	@echo "Usage:"
	@echo "  make install    - Install pinned dependencies"
	@echo "  make ingest     - Ingest raw data from all 5 official sources (Day 1)"
	@echo "  make transform  - Run dbt staging, intermediate, and marts (Day 2-3)"
	@echo "  make test       - Run dbt data tests + pytest test suite (Day 2-3)"
	@echo "  make export     - Export analytical aggregates & manifests (Day 4)"
	@echo "  make dash       - Launch Streamlit mobility dashboard (Day 5)"
	@echo "  make build      - Run full idempotent end-to-end pipeline (ingest -> transform -> test -> export)"
	@echo "  make clean      - Clean transient caches, bytecode, and temp files"
	@echo "=================================================================="

install:
	$(PYTHON) -m pip install -r requirements.txt

ingest:
	$(PYTHON) -m ingestion.pipeline

transform:
	cd dbt_project && dbt run --profiles-dir .

test:
	cd dbt_project && dbt test --profiles-dir .
	pytest tests/ -v

export:
	$(PYTHON) -m export.exporter

dash:
	streamlit run dashboard/app.py

build: ingest transform test export
	@echo "=== Full MetroPulse Build Succeeded! ==="

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
