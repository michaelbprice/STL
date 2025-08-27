#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""
Demo script to show header dependency analysis functionality with synthetic data.

This script creates sample dependency data to demonstrate how the analysis tools
would work with commits that have actual header inclusion changes.
"""

import json
import tempfile
from pathlib import Path
import sys
import os

# Add the tools directory to Python path to import our modules
sys.path.insert(0, str(Path(__file__).parent))

from header_dependency_diff import DependencyComparator


def create_sample_dependencies():
    """Create sample dependency data showing typical STL header relationships."""
    
    # Sample dependencies representing "before" state
    deps_before = {
        "vector": ["memory", "iterator", "algorithm"],
        "algorithm": ["iterator", "functional"],
        "memory": ["type_traits", "utility"],
        "string": ["memory", "iterator", "algorithm"],
        "iostream": ["ios", "istream", "ostream"],
        "map": ["memory", "functional", "utility"],
        "set": ["memory", "functional"],
        "list": ["memory", "iterator"],
        "deque": ["memory", "iterator", "algorithm"]
    }
    
    # Sample dependencies representing "after" state with some changes
    deps_after = {
        "vector": ["memory", "iterator", "algorithm", "ranges"],  # Added ranges
        "algorithm": ["iterator", "functional", "concepts"],       # Added concepts
        "memory": ["type_traits", "utility"],                      # No change
        "string": ["memory", "iterator", "algorithm", "string_view"],  # Added string_view
        "iostream": ["ios", "istream", "ostream"],                 # No change
        "map": ["memory", "functional", "utility"],                # No change
        "set": ["memory", "functional", "utility"],                # Added utility
        "list": ["memory", "iterator"],                            # No change
        "deque": ["memory", "iterator", "algorithm"],              # No change
        "span": ["iterator", "type_traits"],                       # New header
        "ranges": ["iterator", "concepts", "functional"]           # New header
        # Note: "unordered_map" was removed
    }
    
    # Add the missing header in before state
    deps_before["unordered_map"] = ["memory", "functional", "utility"]
    
    return deps_before, deps_after


def demonstrate_diff_functionality():
    """Demonstrate the diff functionality with sample data."""
    
    print("Header Dependency Analysis Demo")
    print("=" * 50)
    print()
    
    # Create sample data
    deps_before, deps_after = create_sample_dependencies()
    
    print("Sample 'before' state headers:")
    for header in sorted(deps_before.keys()):
        print(f"  {header}: {deps_before[header]}")
    print()
    
    print("Sample 'after' state headers:")
    for header in sorted(deps_after.keys()):
        print(f"  {header}: {deps_after[header]}")
    print()
    
    # Create comparator and analyze differences
    comparator = DependencyComparator()
    diff = comparator.compare_dependencies(deps_before, deps_after, "demo_before", "demo_after")
    
    # Display human-readable report
    report = comparator.format_diff_report(diff)
    print("Difference Analysis:")
    print("-" * 30)
    print(report)
    
    # Also save JSON output
    output_dir = Path("demo_output")
    output_dir.mkdir(exist_ok=True)
    
    json_file = output_dir / "demo_diff.json"
    with open(json_file, 'w') as f:
        json.dump(diff, f, indent=2)
    
    print(f"\nJSON output saved to: {json_file}")
    
    return diff


def create_sample_analysis_files():
    """Create sample analysis files showing realistic STL evolution."""
    
    # Create more comprehensive sample data
    samples = [
        {
            "name": "cpp17_to_cpp20",
            "commit1": "cpp17_release",
            "commit2": "cpp20_release", 
            "before": {
                "algorithm": ["iterator", "functional"],
                "vector": ["memory", "iterator", "algorithm"],
                "string": ["memory", "iterator", "algorithm"],
                "memory": ["type_traits", "utility"],
                "optional": ["type_traits", "utility"],
                "variant": ["type_traits", "utility"],
            },
            "after": {
                "algorithm": ["iterator", "functional", "concepts"],  # C++20 concepts
                "vector": ["memory", "iterator", "algorithm"],
                "string": ["memory", "iterator", "algorithm"],
                "memory": ["type_traits", "utility"],
                "optional": ["type_traits", "utility"],
                "variant": ["type_traits", "utility"],
                "ranges": ["iterator", "concepts", "functional"],     # New in C++20
                "concepts": ["type_traits"],                          # New in C++20
                "span": ["iterator", "type_traits"],                  # New in C++20
                "coroutine": ["type_traits"],                         # New in C++20
            }
        },
        {
            "name": "cpp20_to_cpp23",
            "commit1": "cpp20_release",
            "commit2": "cpp23_release",
            "before": {
                "algorithm": ["iterator", "functional", "concepts"],
                "ranges": ["iterator", "concepts", "functional"],
                "string": ["memory", "iterator", "algorithm"],
                "vector": ["memory", "iterator", "algorithm"],
                "expected": ["type_traits", "utility"],
            },
            "after": {
                "algorithm": ["iterator", "functional", "concepts"],
                "ranges": ["iterator", "concepts", "functional", "span"],  # Enhanced ranges
                "string": ["memory", "iterator", "algorithm", "string_view"],
                "vector": ["memory", "iterator", "algorithm"],
                "expected": ["type_traits", "utility"],
                "generator": ["coroutine", "ranges"],                 # New in C++23
                "mdspan": ["span", "type_traits"],                    # New in C++23
                "print": ["iostream", "format"],                     # New in C++23
            }
        }
    ]
    
    output_dir = Path("sample_analysis")
    output_dir.mkdir(exist_ok=True)
    
    comparator = DependencyComparator()
    
    for sample in samples:
        diff = comparator.compare_dependencies(
            sample["before"], 
            sample["after"], 
            sample["commit1"], 
            sample["commit2"]
        )
        
        # Save JSON diff
        json_file = output_dir / f"{sample['name']}_diff.json"
        with open(json_file, 'w') as f:
            json.dump(diff, f, indent=2)
        
        # Save human-readable report
        report_file = output_dir / f"{sample['name']}_report.txt"
        with open(report_file, 'w') as f:
            f.write(comparator.format_diff_report(diff))
        
        print(f"Created sample analysis: {sample['name']}")
        print(f"  JSON: {json_file}")
        print(f"  Report: {report_file}")
        print()


def main():
    """Run the demonstration."""
    
    print("Running Header Dependency Analysis Demonstration...")
    print()
    
    # Demo 1: Basic diff functionality
    demonstrate_diff_functionality()
    print()
    
    # Demo 2: Create sample evolution scenarios
    print("Creating sample C++ standard evolution scenarios...")
    print("-" * 50)
    create_sample_analysis_files()
    
    print("Demo completed! Check the generated files:")
    print("  - demo_output/demo_diff.json")
    print("  - sample_analysis/*.json")
    print("  - sample_analysis/*.txt")


if __name__ == "__main__":
    main()