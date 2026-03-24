#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import subprocess
import json
import datetime
import os
import sys
import argparse
import configparser
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Load Configuration
config = configparser.ConfigParser()
config_files = ['config.ini', 'config.local.ini']
read_files = config.read(config_files)

# Ensure base config is present
if 'config.ini' not in read_files and not os.path.exists('config.ini'):
    print("Error: config.ini not found. Please ensure the default configuration exists.")
    sys.exit(1)

try:
    INDEX_URL = config.get('SAPI', 'INDEX_URL')
    BASE_INDEX_URL = config.get('SAPI', 'BASE_INDEX_URL')
    DOCKER_IMAGE = config.get('DOCKER', 'IMAGE')
    PLATFORM = config.get('DOCKER', 'PLATFORM')
    REPORT_DIR = config.get('REPORTING', 'DIR')
except (configparser.NoSectionError, configparser.NoOptionError) as e:
    print(f"Configuration Error: {e}")
    sys.exit(1)

def setup_reports():
    """Ensure the reports directory exists."""
    Path(REPORT_DIR).mkdir(parents=True, exist_ok=True)

def get_packages():
    """Fetch the list of packages from the simple index."""
    try:
        print(f"Fetching package list from {INDEX_URL}...")
        response = requests.get(INDEX_URL)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        packages = [a.text for a in soup.find_all('a')]
        print(f"Found {len(packages)} packages.")
        return packages
    except requests.RequestException as e:
        print(f"Error fetching package list: {e}")
        sys.exit(1)

def run_test(package, verbose=False, use_prefix=False):
    """Run the installation test for a single package."""
    prefix = f"[{package}] " if use_prefix else ""
    if not use_prefix:
        print(f"Testing package: {package}...")
    
    command = [
        "docker", "run", "--rm",
        "--platform", PLATFORM,
        DOCKER_IMAGE,
        "pip", "install", "--no-cache-dir",
        "--index-url", BASE_INDEX_URL,
        package
    ]
    
    start_time = datetime.datetime.now().isoformat()
    stdout_lines = []
    
    try:
        # We combine stdout and stderr to simplify live logging
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        if process.stdout:
            for line in process.stdout:
                if verbose:
                    print(f"{prefix}{line.strip()}")
                stdout_lines.append(line)
            
        process.wait()
        end_time = datetime.datetime.now().isoformat()
        
        status = "SUCCESS" if process.returncode == 0 else "FAILURE"
        return {
            "package": package,
            "status": status,
            "start_time": start_time,
            "end_time": end_time,
            "stdout": "".join(stdout_lines),
            "stderr": "",  # Captured in stdout for simplicity
            "return_code": process.returncode
        }
    except Exception as e:
        end_time = datetime.datetime.now().isoformat()
        return {
            "package": package,
            "status": "ERROR",
            "start_time": start_time,
            "end_time": end_time,
            "stdout": "".join(stdout_lines),
            "stderr": str(e),
            "return_code": -1
        }

def generate_report(results):
    """Generate JSON and Markdown reports."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    json_filename = f"{REPORT_DIR}/sapi_qa_report_{timestamp}.json"
    md_filename = f"{REPORT_DIR}/sapi_qa_summary_{timestamp}.md"
    
    # Write JSON report
    with open(json_filename, 'w') as f:
        json.dump(results, f, indent=4)
    print(f"JSON report saved to {json_filename}")
    
    # Write Markdown summary
    success_count = sum(1 for r in results if r['status'] == 'SUCCESS')
    failure_count = sum(1 for r in results if r['status'] != 'SUCCESS')
    total_count = len(results)
    
    with open(md_filename, 'w') as f:
        f.write(f"# SAPI QA Report - {timestamp}\n\n")
        f.write(f"- **Total Packages:** {total_count}\n")
        f.write(f"- **Success:** {success_count}\n")
        f.write(f"- **Failures:** {failure_count}\n\n")

        f.write("## Test Summary\n\n")
        f.write("| Package | Status | Duration (s) |\n")
        f.write("| :--- | :--- | :--- |\n")
        for r in results:
            start = datetime.datetime.fromisoformat(r['start_time'])
            end = datetime.datetime.fromisoformat(r['end_time'])
            duration = (end - start).total_seconds()
            f.write(f"| {r['package']} | {r['status']} | {duration:.2f} |\n")
        f.write("\n")
        
        if failure_count > 0:
            f.write("## Detailed Failure Logs\n\n")
            for r in results:
                if r['status'] != 'SUCCESS':
                    f.write(f"### {r['package']}\n")
                    f.write(f"- **Status:** {r['status']}\n")
                    f.write(f"- **Return Code:** {r['return_code']}\n")
                    f.write("#### Logs (last 1000 characters):\n")
                    f.write("```\n")
                    # Combined output is in 'stdout'
                    output = r['stdout'] if r['stdout'] else r['stderr']
                    f.write(output[-1000:] if output else "No output captured")
                    f.write("\n```\n\n")
    
    print(f"Markdown summary saved to {md_filename}")

def parse_args():
    parser = argparse.ArgumentParser(description="SAPI QA Suite")
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--limit", type=int, help="Limit the number of packages to test")
    group.add_argument("--packages", type=str, help="Comma-separated list of packages to test (skips index fetch)")
    
    parser.add_argument("--dry-run", action="store_true", help="Fetch package list but do not run Docker tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show live output from the installer")
    parser.add_argument("--parallel", "-p", type=int, default=1, help="Number of concurrent tests to run")
    return parser.parse_args()

def main():
    args = parse_args()
    setup_reports()
    
    if args.packages:
        packages = [p.strip() for p in args.packages.split(',') if p.strip()]
        print(f"Testing {len(packages)} specified package(s): {', '.join(packages)}")
    else:
        packages = get_packages()
        if args.limit:
            packages = packages[:args.limit]
            print(f"Limiting to first {args.limit} packages.")
    
    results = []
    
    if args.dry_run:
        print("Dry run enabled. Skipping Docker tests.")
        for package in packages:
             print(f"[DRY RUN] Would test package: {package}")
        return

    if args.parallel > 1:
        num_workers = min(args.parallel, len(packages))
        print(f"Running {num_workers} tests in parallel...")
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            future_to_pkg = {executor.submit(run_test, pkg, args.verbose, True): pkg for pkg in packages}
            for i, future in enumerate(as_completed(future_to_pkg)):
                pkg = future_to_pkg[future]
                print(f"[{i+1}/{len(packages)}] Finished testing {pkg}")
                results.append(future.result())
    else:
        for i, package in enumerate(packages):
            print(f"[{i+1}/{len(packages)}] Processing {package}...")
            result = run_test(package, verbose=args.verbose)
            results.append(result)
        
    generate_report(results)

if __name__ == "__main__":
    main()
