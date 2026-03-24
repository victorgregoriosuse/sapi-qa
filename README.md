# SAPI QA Suite

This suite tests the installation of packages from the SUSE AI Package Index (SAPI).

## Prerequisites
-   Python 3.x
-   Docker (running and accessible by the user)
-   Internet connection

## Setup
1.  Create and activate a virtual environment (recommended):
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage
Run the main script:
```bash
python3 sapi_qa.py
```

### Options
-   `--limit N`: Test only the first N packages.
-   `--packages "pkg1,pkg2"`: Test specific packages (comma-separated). Skips fetching the full index. Mutually exclusive with `--limit`.
-   `--dry-run`: Fetch the package list (or use provided packages) but skip Docker tests.
-   `--verbose` or `-v`: Show live output from the `pip install` commands.

## Output
Reports are generated in the `reports/` directory:
-   `sapi_qa_report_YYYYMMDD_HHMMSS.json`: Detailed machine-readable results.
-   `sapi_qa_summary_YYYYMMDD_HHMMSS.md`: Human-readable summary with error logs.

## Configuration
Edit `sapi_qa.py` to modify:
-   `INDEX_URL`: The URL of the simple index.
-   `DOCKER_IMAGE`: The container image used for testing.
-   `PLATFORM`: The Docker platform (e.g., `linux/amd64`).
