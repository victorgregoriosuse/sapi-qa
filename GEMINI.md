# SAPI QA Suite - Project Overview

This project is a Quality Assurance (QA) suite designed to verify the installation of packages from the **SUSE AI Package Index (SAPI)**. It uses isolated Docker containers to ensure each package is tested in a clean environment.

## Project Purpose and Architecture

- **Objective:** Systematically test `pip install` for all or specific packages available on the SAPI endpoint.
- **Methodology:**
    1. **Package Discovery:** Fetches the list of available packages from the SAPI simple index HTML (`https://sapi.suse.com/beta/simple/index.html`).
    2. **Isolated Testing:** For each package, a fresh Docker container is launched using the `registry.suse.com/bci/python:3.11` image on the `linux/amd64` platform.
    3. **Installation Verification:** Runs `pip install --no-cache-dir --index-url https://sapi.suse.com/beta/simple <package>` inside the container.
    4. **Reporting:** Captures results (status, duration, output, return codes) and generates both machine-readable (JSON) and human-readable (Markdown) reports in the `reports/` directory.

## Core Technologies
- **Language:** Python 3
- **Containerization:** Docker (specifically SUSE BCI Python images)
- **Libraries:** `requests` (HTTP), `beautifulsoup4` (HTML parsing)
- **Infrastructure:** SAPI (SUSE AI Package Index)

## Building and Running

### Prerequisites
- Python 3.x
- Docker installed and running (with `linux/amd64` support, e.g., via Rosetta 2 on Apple Silicon or native on x86_64).

### Setup
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running Tests
```bash
# Run full suite
python3 sapi_qa.py

# Test specific packages
python3 sapi_qa.py --packages "garak,numpy"

# Test with live output
python3 sapi_qa.py --verbose

# Limit number of packages from index
python3 sapi_qa.py --limit 10

# Dry run (list packages without running Docker)
python3 sapi_qa.py --dry-run
```

## Development Conventions

- **Logic Separation:**
    - `get_packages()`: Handles HTML scraping of the SAPI index.
    - `run_test(package, verbose)`: Orchestrates Docker execution via `subprocess`.
    - `generate_report(results)`: Formats and writes output files.
- **Error Handling:** Subprocess failures are captured and logged as `FAILURE` in reports without stopping the entire suite.
- **Reporting:** 
    - Reports are timestamped: `sapi_qa_report_YYYYMMDD_HHMMSS.json` and `sapi_qa_summary_YYYYMMDD_HHMMSS.md`.
    - Stderr is limited to the last 1000 characters in MD reports to maintain readability.
- **Configuration:** 
    - Defaults are stored in `config.ini` (committed).
    - User overrides can be placed in `config.local.ini` (ignored by git).
    - The system uses `configparser` to load and merge these files.
    - Key settings: `INDEX_URL`, `BASE_INDEX_URL`, `DOCKER IMAGE`, `PLATFORM`, and `REPORT_DIR`.
