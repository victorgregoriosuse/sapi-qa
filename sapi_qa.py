#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import subprocess
import json
import datetime
import os
import sys
import argparse
from pathlib import Path

# Configuration
INDEX_URL = "https://sapi.suse.com/beta/simple/index.html"
BASE_INDEX_URL = "https://sapi.suse.com/beta/simple"
DOCKER_IMAGE = "registry.suse.com/bci/python:3.11"
PLATFORM = "linux/amd64"
REPORT_DIR = "reports"

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

def run_test(package, verbose=False):
    """Run the installation test for a single package."""
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
                    print(f"  {line.strip()}")
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
        
        if failure_count > 0:
            f.write("## Failures\n\n")
            for r in results:
                if r['status'] != 'SUCCESS':
                    f.write(f"### {r['package']}\n")
                    f.write(f"- **Status:** {r['status']}\n")
                    f.write(f"- **Return Code:** {r['return_code']}\n")
                    f.write("#### Stderr:\n")
                    f.write("```\n")
                    # Limit stderr output to avoid huge files
                    f.write(r['stderr'][-1000:] if r['stderr'] else "No stderr output")
                    f.write("\n```\n\n")
    
    print(f"Markdown summary saved to {md_filename}")

def parse_args():
    parser = argparse.ArgumentParser(description="SAPI QA Suite")
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--limit", type=int, help="Limit the number of packages to test")
    group.add_argument("--packages", type=str, help="Comma-separated list of packages to test (skips index fetch)")
    
    parser.add_argument("--dry-run", action="store_true", help="Fetch package list but do not run Docker tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show live output from the installer")
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

    for i, package in enumerate(packages):
        print(f"[{i+1}/{len(packages)}] Processing {package}...")
        result = run_test(package, verbose=args.verbose)
        results.append(result)
        
    generate_report(results)

if __name__ == "__main__":
    main()
