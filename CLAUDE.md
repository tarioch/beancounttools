# CLAUDE.md

@CONTRIBUTING.md

## Notes for Claude

- Open pull requests and stop there, the maintainer reviews and merges them. Do not merge unless explicitly asked.
- Run the checks from CONTRIBUTING.md before pushing, and `git add` new files first, `pre-commit --all-files` skips
  untracked files.
- Never put real financial data, credentials or personal details into the repository, commits, pull requests or issues.
  Tests, fixtures and examples are synthetic.
- Show that a test can fail: when fixing a bug, check that the new test fails without the fix.
- When dependencies change, regenerate `uv.lock` with the uv version of the pre-commit hook and check that the lock diff
  only contains what you intended.
- Keep pull request descriptions factual: the problem, the change, how it was verified (including what could not be
  verified before merging).
