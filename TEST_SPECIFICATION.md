# Test Specification — Release Candidate

## Reported baseline
Chat 04/05 reports state 102 tests passed in 39.30 seconds and AppTest 8/8 navigation targets. This docs update did not rerun the suite.

## Regression groups
- Ingestion/source manifest and provenance.
- Stable evidence IDs, retrieval traces and citation resolution.
- Supported tutor query and unsupported abstention.
- Fail-closed citation/provider errors.
- Assessment selection, answer validation and BKT state update.
- Persistence across expected reruns/restarts where claimed.
- Recommendation rationale and prerequisite gate.
- Evaluation formulas, denominators and displayed values.
- Dashboard normal-zoom layout, no raw HTML leakage, no one-character wrapping, working routes, global tutor submission, continue/history actions, empty states and narrow viewport behavior.

## Command
Run on the actual implementation branch and configured environment, not assumed runnable from scaffold-only main:
```powershell
& .\.venv\Scripts\python.exe -m pytest -v --durations=10
```

If unavailable, report the exact blocker. Never claim tests passed without output.

## Browser disclosure
Prior Playwright attempt failed downloading its driver. AppTest does not replace browser acceptance. Label each check as AppTest, real-browser, or pending.
