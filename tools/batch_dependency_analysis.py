#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""
Batch Header Dependency Analysis Tool

This script runs the header dependency diff tool on multiple commit combinations
to analyze how the STL include graph has evolved over time.

Usage:
    python batch_dependency_analysis.py [options]
"""

import argparse
import json
import subprocess
import sys
from itertools import combinations
from pathlib import Path


def get_available_commits(repo_path: str, limit: int = 10) -> list:
    """Get available commits from the repository."""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", f"-{limit}", "--all"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        
        commits = []
        for line in result.stdout.strip().split('\n'):
            if line:
                commit_sha = line.split()[0]
                commit_msg = ' '.join(line.split()[1:])
                commits.append((commit_sha, commit_msg))
        
        return commits
    except subprocess.CalledProcessError as e:
        print(f"Error getting commits: {e.stderr}", file=sys.stderr)
        return []


def run_dependency_diff(commit1: str, commit2: str, repo_path: str, output_dir: str) -> dict:
    """Run the dependency diff tool between two commits."""
    
    script_path = Path(repo_path) / "tools" / "header_dependency_diff.py"
    output_file = Path(output_dir) / f"diff_{commit1}_{commit2}.json"
    
    try:
        result = subprocess.run(
            ["python3", str(script_path), commit1, commit2, "--json", "--output", str(output_file)],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        
        # Load the generated JSON
        with open(output_file, 'r') as f:
            diff_data = json.load(f)
        
        return {
            'success': True,
            'diff_data': diff_data,
            'output_file': str(output_file)
        }
    
    except subprocess.CalledProcessError as e:
        return {
            'success': False,
            'error': f"Failed to run diff: {e.stderr}"
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"Unexpected error: {str(e)}"
        }


def generate_summary_report(results: list, output_file: str):
    """Generate a summary report of all the diffs."""
    
    summary = {
        'total_comparisons': len(results),
        'successful_comparisons': sum(1 for r in results if r['success']),
        'failed_comparisons': sum(1 for r in results if not r['success']),
        'comparisons': []
    }
    
    for result in results:
        if result['success']:
            diff_data = result['diff_data']
            summary['comparisons'].append({
                'commit1': diff_data['commit1'],
                'commit2': diff_data['commit2'],
                'summary': diff_data['summary'],
                'has_changes': (
                    len(diff_data['added_headers']) > 0 or 
                    len(diff_data['removed_headers']) > 0 or 
                    len(diff_data['changed_dependencies']) > 0
                ),
                'output_file': result['output_file']
            })
        else:
            summary['comparisons'].append({
                'commit1': result['commit1'],
                'commit2': result['commit2'],
                'error': result['error'],
                'success': False
            })
    
    with open(output_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    return summary


def print_summary_report(summary: dict):
    """Print a human-readable summary report."""
    
    print("Batch Header Dependency Analysis Summary")
    print("=" * 50)
    print(f"Total comparisons: {summary['total_comparisons']}")
    print(f"Successful: {summary['successful_comparisons']}")
    print(f"Failed: {summary['failed_comparisons']}")
    print()
    
    if summary['successful_comparisons'] > 0:
        print("Comparisons with changes:")
        changes_found = False
        
        for comp in summary['comparisons']:
            if comp.get('success', True) and comp.get('has_changes', False):
                changes_found = True
                print(f"  {comp['commit1']} -> {comp['commit2']}")
                print(f"    Headers: {comp['summary']['total_headers_before']} -> {comp['summary']['total_headers_after']}")
                print(f"    Changed dependencies: {comp['summary']['headers_with_changed_deps']}")
                print(f"    Report: {comp['output_file']}")
                print()
        
        if not changes_found:
            print("  No changes found in any comparisons")
    
    if summary['failed_comparisons'] > 0:
        print("Failed comparisons:")
        for comp in summary['comparisons']:
            if not comp.get('success', True):
                print(f"  {comp['commit1']} -> {comp['commit2']}: {comp['error']}")


def main():
    parser = argparse.ArgumentParser(
        description="Batch analysis of header dependency changes across commits"
    )
    parser.add_argument("--repo", default=".", help="Repository path (default: current directory)")
    parser.add_argument("--output-dir", default="dependency_analysis", 
                       help="Output directory for reports (default: dependency_analysis)")
    parser.add_argument("--max-commits", type=int, default=10, 
                       help="Maximum number of commits to analyze (default: 10)")
    parser.add_argument("--all-pairs", action="store_true", 
                       help="Compare all pairs of commits (default: sequential pairs only)")
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Get available commits
    commits = get_available_commits(args.repo, args.max_commits)
    
    if len(commits) < 2:
        print("Error: Need at least 2 commits to perform comparison", file=sys.stderr)
        sys.exit(1)
    
    print(f"Found {len(commits)} commits")
    for sha, msg in commits:
        print(f"  {sha}: {msg}")
    print()
    
    # Generate commit pairs to compare
    if args.all_pairs:
        # Compare all pairs
        commit_pairs = list(combinations([sha for sha, _ in commits], 2))
    else:
        # Compare sequential pairs (older -> newer)
        commit_pairs = []
        for i in range(len(commits) - 1):
            commit_pairs.append((commits[i+1][0], commits[i][0]))  # older, newer
    
    print(f"Running {len(commit_pairs)} comparisons...")
    
    # Run all comparisons
    results = []
    for i, (commit1, commit2) in enumerate(commit_pairs, 1):
        print(f"[{i}/{len(commit_pairs)}] Comparing {commit1} -> {commit2}")
        
        result = run_dependency_diff(commit1, commit2, args.repo, str(output_dir))
        result['commit1'] = commit1
        result['commit2'] = commit2
        results.append(result)
        
        if result['success']:
            print(f"  ✓ Success: {result['output_file']}")
        else:
            print(f"  ✗ Failed: {result['error']}")
    
    # Generate summary report
    summary_file = output_dir / "summary.json"
    summary = generate_summary_report(results, str(summary_file))
    
    print(f"\nSummary report written to {summary_file}")
    print()
    print_summary_report(summary)


if __name__ == "__main__":
    main()