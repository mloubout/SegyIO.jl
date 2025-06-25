# pysegy

[![CI](https://github.com/mloubout/pysegy/actions/workflows/main.yml/badge.svg)](https://github.com/mloubout/pysegy/actions/workflows/main.yml)
[![Docs](https://github.com/mloubout/pysegy/actions/workflows/docs.yml/badge.svg)](https://mloubout.github.io/pysegy)
[![codecov](https://codecov.io/gh/mloubout/pysegy/branch/master/graph/badge.svg)](https://codecov.io/gh/mloubout/pysegy)

`pysegy` is a minimal Python library for reading and writing SEGY Rev 1 files. The package focuses on simplicity and provides helpers to parse headers and traces from local files.

## Installation

Install the project in editable mode from the repository root:

```bash
python -m pip install -e .
```

## Testing

Run the unit tests with `pytest`:

```bash
pytest -vs
```

The tests run automatically on GitHub Actions with coverage reports uploaded to Codecov.
