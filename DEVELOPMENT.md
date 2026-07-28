# Developing VisPy2

VisPy2 is a typed producer of semantic GSP scenes. Keep backend selection, capability probing,
native resources, displays, and event loops in caller-owned GSP sessions. Production code must
not import `gsp_matplotlib`, `gsp_datoviz`, or another concrete adapter.

## Local environment

Python 3.13 is required. With sibling VisPy2 and GSP checkouts:

```console
python -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install \
  "mypy>=1.15,<3" \
  "pytest>=8,<10" \
  "ruff>=0.11,<1" \
  "build>=1,<2"
.venv/bin/python -m pip install \
  -e ../gsp/packages/gsp-core \
  -e .
```

Install an adapter only for adapter-dependent examples and tests:

```console
.venv/bin/python -m pip install -e ../gsp/packages/gsp-matplotlib
```

Datoviz development also requires its compatible binding environment and explicit local source
selector. See [installation](docs/installation.md).

## Required checks

Run the producer gates from the repository root:

```console
.venv/bin/python -m pytest -q
.venv/bin/python -m mypy src --strict --show-error-codes
.venv/bin/python -m ruff check src tests examples
.venv/bin/python examples/validate_docs.py .
```

The full test suite expects the Matplotlib adapter. Producer-only qualification is a separate
installed-wheel gate, not an editable-install test shortcut.

Build the producer wheel with:

```console
.venv/bin/python -m build --wheel
```

For cross-backend release evidence, follow the exact-wheel procedure in
[the gallery guide](docs/gallery.md). Do not substitute editable installs or old PNGs.

## Change guidelines

- Preserve typed semantic behavior and immutable `Figure.to_scene()` snapshots.
- Keep one-shot Matplotlib conveniences delegated to ephemeral GSP sessions.
- Require a caller-owned session for interactive or non-blocking execution.
- Add ordinary and versioned capability checks for every strict backend path.
- Fail closed when an adapter cannot prove a requested semantic contract.
- Test producer behavior without importing a concrete adapter.
- Record exact source provenance when migrating code or behavior.
- Preserve historical evidence; append later disposition instead of rewriting what an earlier run
  observed.

When adding a public producer method, update the tests, [user guide](docs/user-guide.md),
[API reference](docs/api-reference.md), and [capability matrix](docs/capability-matrix.md) in the
same change where applicable.

## Documentation checks

`examples/validate_docs.py` compiles every Python fence in repository README and `docs` Markdown
files and verifies local link targets. Use `python`, `console`, or `text` fence labels so the
validator can classify examples. Commands that require a backend should say which provider,
runtime, and capability assumptions apply.

## Repository operations

Do not add remotes, push, tag, publish, or import legacy Git history without owner approval.
Keep generated environments and build output outside commits. Checked-in gallery artifacts are
qualification evidence and must be replaced only by the transactional exact-wheel harness.
