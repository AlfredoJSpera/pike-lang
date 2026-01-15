# pike

This project uses [uv](https://github.com/astral-sh/uv) for Python environment management and running commands.

## Running the Compiler

To run the Pike compiler, use:

```bash
uv run src/main.py
```

You can pass a `.pike` source file as an argument:

```bash
uv run src/main.py -f path/to/file.pike
```

## Running Tests

To execute the test suite with pytest:

```bash
uv run pytest tests/testfile.py
```