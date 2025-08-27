# Header Dependency Analysis Tools

This directory contains tools for analyzing and comparing C++ Standard Library header inclusion dependencies across different commits.

## Overview

These tools help understand how the header inclusion graph has changed between different versions of the Microsoft STL implementation. This is valuable for:

- Understanding the evolution of header dependencies over time
- Identifying breaking changes in header inclusion patterns
- Analyzing the impact of refactoring on dependency graphs
- Providing context for automated agents analyzing STL changes

## Tools

### 1. `header_dependency_diff.py`

Analyzes and compares header dependency graphs between two specific commits.

#### Usage
```bash
python3 tools/header_dependency_diff.py <commit1> <commit2> [options]
```

#### Options
- `--repo REPO`: Repository path (default: current directory)
- `--output OUTPUT`: Output file for the diff report
- `--json`: Output in JSON format instead of human-readable text

#### Examples
```bash
# Compare two commits with human-readable output
python3 tools/header_dependency_diff.py abc123 def456

# Generate JSON output for programmatic use
python3 tools/header_dependency_diff.py abc123 def456 --json --output diff_report.json

# Analyze a different repository
python3 tools/header_dependency_diff.py abc123 def456 --repo /path/to/stl/repo
```

#### Output Format

The tool outputs a comprehensive report showing:
- Summary statistics (number of headers, headers with changed dependencies)
- Added headers (new headers introduced)
- Removed headers (headers that were removed)
- Changed dependencies (headers whose include relationships changed)

### 2. `batch_dependency_analysis.py`

Runs dependency analysis across multiple commit combinations to analyze evolution over time.

#### Usage
```bash
python3 tools/batch_dependency_analysis.py [options]
```

#### Options
- `--repo REPO`: Repository path (default: current directory)
- `--output-dir OUTPUT_DIR`: Output directory for reports (default: dependency_analysis)
- `--max-commits MAX_COMMITS`: Maximum number of commits to analyze (default: 10)
- `--all-pairs`: Compare all pairs of commits (default: sequential pairs only)

#### Examples
```bash
# Analyze the last 10 commits with sequential comparisons
python3 tools/batch_dependency_analysis.py

# Analyze all pairs of the last 5 commits
python3 tools/batch_dependency_analysis.py --max-commits 5 --all-pairs

# Custom output directory
python3 tools/batch_dependency_analysis.py --output-dir my_analysis
```

#### Output

The batch tool generates:
- Individual JSON diff reports for each comparison
- A summary JSON file with overview statistics
- Console output summarizing all comparisons

## How It Works

### Dependency Extraction

The tools analyze header dependencies by:

1. **Checking out target commits**: The script temporarily switches to each commit for analysis
2. **Reading header files**: Parses `#include` statements from STL headers
3. **Filtering STL headers**: Only includes headers that are part of the STL being analyzed
4. **Building dependency graph**: Creates a mapping of header -> [list of included headers]

### Comparison Algorithm

The comparison process:

1. **Extract dependencies** for both commits
2. **Identify structural changes**: 
   - Headers added or removed between commits
   - Headers whose dependency lists changed
3. **Calculate diffs**: 
   - Dependencies added to existing headers
   - Dependencies removed from existing headers
4. **Generate reports**: Format results in human-readable or JSON format

### Header Selection

The analysis focuses on headers listed in:
- `stl/inc/header-units.json`: Main list of STL headers
- Additional important headers: `version`, `yvals.h`, `yvals_core.h`

This ensures comprehensive coverage of the public STL interface.

## Implementation Notes

### Limitations

- **Simple parsing**: Currently uses regex-based parsing of `#include` statements rather than full C++ preprocessing
- **STL-specific**: Designed specifically for Microsoft's STL implementation
- **File-based analysis**: Analyzes source files directly rather than using compiler dependency scanning

### Future Enhancements

- Integration with MSVC's `/scanDependencies` for more accurate dependency extraction
- Support for conditional compilation (`#ifdef` blocks)
- Visualization of dependency graphs
- Performance optimization for large commit ranges
- Integration with CI/CD pipelines

## Sample Output

### Human-Readable Format
```
Header Dependency Diff Report
==================================================
From: abc123
To:   def456

Summary:
  Headers before: 158
  Headers after:  159
  Headers with changed dependencies: 3

Added Headers:
  + new_feature

Changed Dependencies:
  algorithm:
    + includes ranges
  vector:
    - includes memory_resource
    + includes allocator_traits
```

### JSON Format
```json
{
  "commit1": "abc123",
  "commit2": "def456",
  "added_headers": ["new_feature"],
  "removed_headers": [],
  "changed_dependencies": {
    "algorithm": {
      "added": ["ranges"],
      "removed": []
    },
    "vector": {
      "added": ["allocator_traits"],
      "removed": ["memory_resource"]
    }
  },
  "summary": {
    "total_headers_before": 158,
    "total_headers_after": 159,
    "headers_with_changed_deps": 3
  }
}
```

## Requirements

- Python 3.6+
- Git repository with STL source code
- Standard Python libraries (no external dependencies)

## License

Copyright (c) Microsoft Corporation.
SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception