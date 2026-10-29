# Semgrep rule fixtures

`positive/` contains code that must produce findings:
- Python `os.system(...)` — command injection
- Python `pickle.loads(...)` — unsafe deserialization
- JavaScript `execSync(...)` — shell command

`negative/` contains the argv-list equivalents and must produce no findings. The test suite copies
these into a temporary repository and runs the repository's Semgrep configuration, so a rule without
a demonstrated positive and negative does not stay in the kit.
