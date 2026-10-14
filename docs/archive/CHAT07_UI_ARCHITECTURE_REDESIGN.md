# CogniVault UI Architecture Redesign — Chat 07

## Purpose
Replace the patch-driven visual layer with a coherent, learner-first Streamlit application shell while preserving the existing learning services and evidence contracts.

## Product information architecture
- **Home**: one clear starting point, resume learning, one recommended next action, and a small set of shortcuts.
- **Courses**: human-readable course catalogue and course-specific resources.
- **Add materials**: ingestion/upload workflow (not presented as course creation).
- **AI Tutor**: ask questions, see grounded answers, citations, or a clear abstention.
- **Practice**: verified questions and feedback.
- **My Progress**: learner mastery and practice history, without presenting BKT posterior as course completion.
- **Recommendations**: prerequisite-aware next steps.
- **Evidence Explorer**: advanced provenance/debug view, separated from ordinary course browsing.
- **Evaluation**: technical benchmark interface, separated from student workflows.

## Layer boundaries
1. `app/ui/main.py` — app entry point and routing only.
2. `app/ui/shell.py` — navigation shell and common page chrome.
3. `app/ui/theme.py` — design tokens and responsive CSS only.
4. `app/ui/components.py` — reusable visual primitives.
5. `app/ui/views/*` — page composition and user interactions.
6. Existing domain services in `app/` — retrieval, grounding, verification, BKT, misconceptions, recommendations, persistence, and evaluation.

## UI principles
- Native Streamlit widgets first; no HTML wrapper may span independent Streamlit widgets.
- No untrusted user/source content interpolated into raw HTML.
- Use consistent spacing, typography, button hierarchy, cards, and responsive behavior.
- Use clear empty/loading/error states and explain the next action.
- No fabricated authentication, cloud sync, completion, mastery, or evaluation claims.
- Advanced technical evidence IDs and telemetry belong in expandable/advanced areas.
- The course catalogue shows courses and resources, not evidence chunks as if they were courses.
- Keep all existing route aliases and service injection compatible during migration.

## Migration sequence
- Pass A: define and implement the shell and visual tokens.
- Pass B: rebuild Home and Courses around learner tasks.
- Pass C: normalize Tutor, Practice, Progress, Recommendations, Evidence, and Evaluation layouts one page at a time.
- Pass D: run import/static checks, the existing test suite, and a browser walkthrough. Do not claim passing checks unless output is recorded.

## Acceptance gates
- No raw HTML leakage or headings wrapped one character at a time.
- Every primary navigation item routes to the intended view.
- The core workflow remains available: course/resource → tutor with citations/abstention → verified practice → learner state → next recommendation.
- No claims that tests, browser checks, or visual acceptance passed without evidence.
- Final UI acceptance remains pending until reviewed screenshots are approved by the product owner.


## Implementation checkpoint — 2026-10-11

### Implemented in source
- Shared shell and route dispatcher split into app/ui/shell.py and app/ui/main.py.
- Replaced the prior CSS bundle with a smaller responsive token-based theme.
- Rebuilt Home around first-run onboarding, resume learning, one recommendation, and compact quick actions.
- Rebuilt Courses around a selected course, its materials, original-file access, indexed-content exploration, assigning uploaded resources, unlinking from a course, and confirmed deletion of the indexed copy.
- Renamed key page introductions to learner-facing language.
- Routed multiline HTML fragments in Tutor, Practice, Progress, Recommendations, Materials, Evidence, and Evaluation through a dedenting helper; removed unnecessary spacer markup from several views.
- Updated README status and launch command so old test claims do not imply the new branch has been verified.

### Checks actually performed
- Retrieved changed files from GitHub and checked for common source-edit mistakes, including leftover malformed form-button syntax, stale vertical_alignment arguments, and direct unsafe_allow_html=True calls in the seven listed view modules.
- Confirmed GitHub branch chat06-ui-repair head and confirmed main remains at its earlier SHA; PR #1 remains open, draft, and unmerged.
- No Python test suite, Streamlit runtime, or real browser was available in this work session. GitHub reports no check runs for the current commit.

### Still required
- Run python -m compileall app and pytest -v --durations=10 in a local checkout.
- Start Streamlit and manually walk every navigation destination.
- Confirm add/remove/delete behavior with disposable test resources and confirm the original file remains on disk after deleting an indexed source.
- Inspect desktop and narrow-screen screenshots, then obtain explicit visual acceptance.
