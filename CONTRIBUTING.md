# Contributing

`tariochbctools` is a collection of importers, plugins and price fetchers for [Beancount](https://beancount.github.io/),
built on [beangulp](https://github.com/beancount/beangulp) and published to PyPI. User documentation is in `docs/`
(built with Sphinx, hosted on Read the Docs).

## Layout

| Path | Content |
|---|---|
| `src/tariochbctools/importers/<name>/importer.py` | one importer per bank or service |
| `src/tariochbctools/importers/general/` | shared code: MT940 importer, deduplication, price lookup, mail adapter |
| `src/tariochbctools/plugins/` | Beancount plugins and price fetchers |
| `tests/tariochbctools/` | tests, mirroring the layout of `src` |
| `docs/` | user documentation, `docs/api` is generated at build time and git-ignored |

Two kinds of importers exist:

- **Config file importers** (API based, e.g. ibkr, transferwise, truelayer, nordigen): `identify()` matches a file such as
  `ibkr.yaml`, which holds the credentials and options, `extract()` calls the API.
- **File importers** (statements, e.g. zkb, viseca, zak): constructed with a `filepattern` and the `account`, `extract()`
  parses the downloaded file.

Importers that can deduplicate set `cmp = ReferenceDuplicatesComparator()` and put the bank's reference into the `ref`
metadata of a transaction. Every importer is documented in `docs/importers.rst` (yaml config and the `CONFIG = [...]` snippet).

## Setup

```bash
uv sync --locked --dev
```

Python 3.11 to 3.14 are supported and tested. If a dependency has no wheel for the newest Python on your platform and
the build fails, use an older one: `uv sync --locked --dev --python 3.13`.

## Checks

CI runs the same commands, all of them have to pass:

```bash
uv run pre-commit run --all-files   # ruff, ruff format, mypy, uv-lock, zizmor, rst lint
uv run deptry src                   # imports vs declared dependencies
uv run pytest
uv run --group docs sphinx-build -W --keep-going -b html docs docs/_build   # documentation without warnings
uv build
```

Things that catch people out:

- `pre-commit run --all-files` only looks at files tracked by git. `git add` new files before running it, otherwise
  they are not checked (and CI then fails on them).
- mypy runs in the project environment (a local pre-commit hook calling `uv run mypy`), so it checks against the types of
  the installed packages. Stub packages (`types-*`) belong into the `dev` dependency group.
- deptry fails for an import that is only available transitively and for a declared dependency that is not used.
  Declare what you import in `pyproject.toml`, remove what you stop using.

## Code

- Type hints are required in `src` (mypy `disallow_untyped_defs`, tests are exempt).
- ruff selects `E4, E7, E9, F, B, I, S113, T20, UP` (see `pyproject.toml`), `ruff format` decides the formatting.
  `print` is only accepted in the small command line tools (`# noqa: T201`).
- Network access needs a timeout, otherwise a stalled server blocks an import forever. Pass `timeout=REQUEST_TIMEOUT` to
  `requests` (ruff `S113` checks it), the constants are in `importers/general/network.py`.
- Tests use synthetic data only: no real statements, account numbers or credentials, not even anonymized ones.
  Mock the network and libraries that need real documents (e.g. camelot), see `tests/tariochbctools/importers/`.
- `importers/ibkr/flexclient.py` adds the `period` option on top of ibflex 1.1. Once ibflex releases support for it,
  delete the module and call `client.download(..., period=period)` directly.

## Dependencies

- `uv.lock` is committed. Regenerate it with the uv version of the `uv-lock` pre-commit hook (`rev` in
  `.pre-commit-config.yaml`), a different uv version rewrites unrelated parts of the file:
  `uvx --from uv==<rev> uv lock`.
- Dependabot (`.github/dependabot.yml`) opens grouped PRs for minor and patch updates of Python packages weekly and for
  GitHub Actions monthly. Major updates come as separate PRs. New releases wait 7 days (cooldown), security updates do not.

## Git and pull requests

- Branch off `master`, named `feature/…`, `bugfix/…` or `chore/…` (snake_case after the prefix). The prefix labels the PR
  (`.github/pr-labeler.yml`), and the label decides the category in the release notes (the shared
  `release-drafter.yml` of [tarioch/.github](https://github.com/tarioch/.github)).
- Commit subjects are imperative and start with a capital letter ("Fix zak importer crash on statements with tables"),
  the body explains why.
- Changes go through pull requests into `master` and are merged with a merge commit (the only allowed merge method).
  Required checks: `Build`, `Lint` and `Test (Python 3.11)` to `Test (Python 3.14)`.

## CI and releases

`.github/workflows/build-publish.yml` runs `lint`, `test` (matrix), `build`, and on pushes to `master` and version tags
the publish jobs. Workflows use the least permissions they need, and every action is pinned to a commit SHA
(Dependabot keeps the pins current, zizmor fails for unpinned actions or broad permissions).

- Every push to `master` publishes a development version to TestPyPI.
- Release notes are drafted by release-drafter. Publishing the draft creates the tag `vX.Y.Z`, which publishes to PyPI.
- Publishing uses PyPI trusted publishing (OIDC) from the GitHub environments `testpypi` and `pypi`, there are no
  stored tokens.
- The version is derived from the git tags (uv-dynamic-versioning), so CI checks out the full history (`fetch-depth: 0`).
