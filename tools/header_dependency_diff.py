#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""
Header Dependency Diff Tool

This script analyzes and compares the include graph hierarchies for C++ standard library headers
between two different commits. It helps understand how header inclusion relationships have changed
over time in the Microsoft STL implementation.

Usage:
    python header_dependency_diff.py <commit1> <commit2>
    python header_dependency_diff.py --help

The script uses MSVC's /scanDependencies feature to extract header dependency information
and then compares the dependency graphs between two commits.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple


class HeaderDependencyAnalyzer:
    """Analyzes header dependencies for STL headers at a specific commit."""
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path).resolve()
        self.stl_include_dir = self.repo_path / "stl" / "inc"
        
    def load_json_with_comments(self, filename: str) -> dict:
        """Load JSON file that may contain // comments."""
        comment_pattern = re.compile(r'//.*')
        with open(filename, 'r') as file:
            lines = [re.sub(comment_pattern, '', line) for line in file]
            return json.loads(''.join(lines))
    
    def get_standard_headers(self) -> List[str]:
        """Get the list of standard headers to analyze."""
        header_units_json = self.stl_include_dir / "header-units.json"
        
        if header_units_json.exists():
            # Use header-units.json if available
            data = self.load_json_with_comments(str(header_units_json))
            headers = data.get("BuildAsHeaderUnits", [])
            
            # Add the version headers that are commented out but still important
            headers.extend(["version", "yvals.h", "yvals_core.h"])
            
            return headers
        else:
            # Fallback to discovering headers from filesystem for older commits
            print(f"Warning: {header_units_json} not found, discovering headers from filesystem")
            headers = []
            
            if self.stl_include_dir.exists():
                for item in self.stl_include_dir.iterdir():
                    if item.is_file():
                        # Include standard C++ headers (no extension) and some key headers
                        if ('.' not in item.name or 
                            item.name.endswith('.h') or 
                            item.name in ['version']):
                            headers.append(item.name)
            
            # Filter to likely standard headers (exclude internal implementation files)
            filtered_headers = []
            for header in sorted(headers):
                # Skip obviously internal files
                if (not header.startswith('_') and 
                    not header.startswith('xtr1') and
                    not header.startswith('xtree') and
                    not header.startswith('xhash') and
                    not header.startswith('xstring') and
                    not header.startswith('xutility') and
                    not header.startswith('xmemory')):
                    filtered_headers.append(header)
            
            return filtered_headers
    
    def extract_dependencies_at_commit(self, commit_sha: str) -> Dict[str, List[str]]:
        """Extract header dependencies at a specific commit."""
        print(f"Analyzing dependencies at commit {commit_sha}")
        
        # Create a temporary directory for analysis
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Save current state
            current_branch = self._get_current_branch()
            
            try:
                # Checkout the target commit
                self._git_checkout(commit_sha)
                
                # Get the list of headers to analyze
                headers = self.get_standard_headers()
                
                # Create working directory for dependency scan
                work_dir = temp_path / "deps"
                work_dir.mkdir()
                
                # Copy headers to working directory or use them in place
                # We'll work directly with the repo directory
                deps = self._scan_dependencies(headers, str(work_dir))
                
                return deps
                
            finally:
                # Restore original state
                if current_branch:
                    self._git_checkout(current_branch)
    
    def _get_current_branch(self) -> str:
        """Get the current branch name."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return ""
    
    def _git_checkout(self, ref: str):
        """Checkout a specific git reference."""
        try:
            subprocess.run(
                ["git", "checkout", ref],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to checkout {ref}: {e.stderr}")
    
    def _scan_dependencies(self, headers: List[str], work_dir: str) -> Dict[str, List[str]]:
        """Use MSVC compiler to scan header dependencies."""
        # This is a simplified version that analyzes dependencies manually
        # In a real implementation, we would use MSVC's /scanDependencies
        # For now, we'll parse the headers directly to extract #include statements
        
        dependencies = {}
        
        for header in headers:
            header_path = self.stl_include_dir / header
            if header_path.exists():
                deps = self._parse_includes_from_header(header_path)
                dependencies[header] = deps
            else:
                dependencies[header] = []
        
        return dependencies
    
    def _parse_includes_from_header(self, header_path: Path) -> List[str]:
        """Parse #include statements from a header file."""
        includes = []
        
        try:
            with open(header_path, 'r', encoding='utf-8', errors='ignore') as file:
                for line in file:
                    line = line.strip()
                    # Look for #include <header> or #include "header"
                    if line.startswith('#include'):
                        # Extract the header name
                        match = re.search(r'#include\s*[<"](.*?)[>"]', line)
                        if match:
                            included_header = match.group(1)
                            # Only include STL headers (filter out system headers)
                            if self._is_stl_header(included_header):
                                includes.append(included_header)
        except (IOError, UnicodeDecodeError):
            # Skip files that can't be read
            pass
        
        return includes
    
    def _is_stl_header(self, header_name: str) -> bool:
        """Check if a header is part of the STL we're analyzing."""
        # Check if the header exists in our STL include directory
        header_path = self.stl_include_dir / header_name
        return header_path.exists()


class DependencyComparator:
    """Compares dependency graphs between two commits."""
    
    def __init__(self):
        pass
    
    def compare_dependencies(self, deps1: Dict[str, List[str]], deps2: Dict[str, List[str]], 
                           commit1: str, commit2: str) -> dict:
        """Compare two dependency graphs and return the differences."""
        
        all_headers = set(deps1.keys()) | set(deps2.keys())
        
        # Headers that were added or removed
        added_headers = set(deps2.keys()) - set(deps1.keys())
        removed_headers = set(deps1.keys()) - set(deps2.keys())
        
        # Dependencies that changed
        changed_dependencies = {}
        
        for header in all_headers:
            if header in deps1 and header in deps2:
                deps1_set = set(deps1[header])
                deps2_set = set(deps2[header])
                
                if deps1_set != deps2_set:
                    added_deps = deps2_set - deps1_set
                    removed_deps = deps1_set - deps2_set
                    
                    changed_dependencies[header] = {
                        'added': list(added_deps),
                        'removed': list(removed_deps)
                    }
        
        return {
            'commit1': commit1,
            'commit2': commit2,
            'added_headers': list(added_headers),
            'removed_headers': list(removed_headers),
            'changed_dependencies': changed_dependencies,
            'summary': {
                'total_headers_before': len(deps1),
                'total_headers_after': len(deps2),
                'headers_with_changed_deps': len(changed_dependencies)
            }
        }
    
    def format_diff_report(self, diff: dict) -> str:
        """Format the diff as a human-readable report."""
        lines = []
        lines.append(f"Header Dependency Diff Report")
        lines.append(f"=" * 50)
        lines.append(f"From: {diff['commit1']}")
        lines.append(f"To:   {diff['commit2']}")
        lines.append("")
        
        # Summary
        lines.append("Summary:")
        lines.append(f"  Headers before: {diff['summary']['total_headers_before']}")
        lines.append(f"  Headers after:  {diff['summary']['total_headers_after']}")
        lines.append(f"  Headers with changed dependencies: {diff['summary']['headers_with_changed_deps']}")
        lines.append("")
        
        # Added headers
        if diff['added_headers']:
            lines.append("Added Headers:")
            for header in sorted(diff['added_headers']):
                lines.append(f"  + {header}")
            lines.append("")
        
        # Removed headers
        if diff['removed_headers']:
            lines.append("Removed Headers:")
            for header in sorted(diff['removed_headers']):
                lines.append(f"  - {header}")
            lines.append("")
        
        # Changed dependencies
        if diff['changed_dependencies']:
            lines.append("Changed Dependencies:")
            for header in sorted(diff['changed_dependencies'].keys()):
                changes = diff['changed_dependencies'][header]
                lines.append(f"  {header}:")
                
                if changes['added']:
                    for dep in sorted(changes['added']):
                        lines.append(f"    + includes {dep}")
                
                if changes['removed']:
                    for dep in sorted(changes['removed']):
                        lines.append(f"    - includes {dep}")
                
                lines.append("")
        
        return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze and compare header dependency graphs between STL commits"
    )
    parser.add_argument("commit1", help="First commit SHA or reference")
    parser.add_argument("commit2", help="Second commit SHA or reference")
    parser.add_argument("--repo", default=".", help="Repository path (default: current directory)")
    parser.add_argument("--output", help="Output file for the diff report")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    
    args = parser.parse_args()
    
    try:
        # Initialize analyzer
        analyzer = HeaderDependencyAnalyzer(args.repo)
        comparator = DependencyComparator()
        
        # Extract dependencies for both commits
        deps1 = analyzer.extract_dependencies_at_commit(args.commit1)
        deps2 = analyzer.extract_dependencies_at_commit(args.commit2)
        
        # Compare the dependencies
        diff = comparator.compare_dependencies(deps1, deps2, args.commit1, args.commit2)
        
        # Format and output the result
        if args.json:
            output = json.dumps(diff, indent=2)
        else:
            output = comparator.format_diff_report(diff)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"Diff report written to {args.output}")
        else:
            print(output)
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()