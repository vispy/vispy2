# Interactive project review

Use the review tour to inspect the semantic contracts and expected behavior across VisPy2, GSP,
Matplotlib, and Datoviz. It walks the whole project rather than limiting review to recent changes.
The tour reuses the existing `examples/manual_live_compare.py` cases where they fit and adds
focused review demos for newer behaviors.

Run it from the VisPy2 checkout on a machine with a GUI display. Install the optional Qt GUI
toolkit into the GSP development environment once:

```console
just review-setup
just review
```

The root GSP checkout also provides `just review` and forwards to this runner. Both entry points
use the GSP `.venv` Python by default. The setup recipe installs PySide6 into that environment.
When it is installed and `MPLBACKEND` is unset, the live Matplotlib child uses QtAgg. An explicit
`MPLBACKEND` value is preserved; headless mode selects Agg. When a sibling `../datoviz` checkout is available,
`GSP_DATOVIZ_SOURCE` defaults to it; an explicit environment value takes precedence. Backend
dependencies for both providers are needed for the complete tour. To review only the reference
backend, run `just review --backend matplotlib`.

The tour presents each contract, the expected behavior, and any explicit backend adaptation. It
opens paired Matplotlib and Datoviz windows in isolated child processes for cross-backend steps.
You can leave both open while inspecting them and writing notes in the terminal; enter a command
when ready. The commands are `run`, `pass`, `issue`, `note`, `repeat`, `skip`, `back`, `docs`, and
`quit`. A runnable step can be passed only after a successful run and after all child windows close
successfully. If a child process fails, the failure is recorded and that step cannot be passed.
Findings accept the severities `blocker`, `bug`, `doc`, `adaptation`, and `preference`.

The navigation step opts into experimental Datoviz View3D gestures for that exercise. Set
`GSP_DATOVIZ_ENABLE_EXPERIMENTAL_VIEW3D_NAV=0` to keep them disabled. This does not change the
adapter's default behavior outside the tour.

The default full plan reviews the whole project. A shorter `--plan smoke` samples seven selected
steps. `--list` prints the step catalog without preparing a graphics backend. `--step STEP_ID`
focuses that step even when it already has a saved verdict. `--resume [PATH]` resumes a prior
review, defaulting to the latest review when no path is supplied. If you omit `--plan` or
`--backend` while resuming, the saved values are restored. `--backend` accepts `both`,
`matplotlib`, or `datoviz`. `--headless` runs bounded automated checks and captures, but it is not
a human review and never records manual passes. Use `--output-dir PATH` to select the review
directory.

By default, JSON state, the Markdown report, and per-backend logs are saved outside the worktree
under `$XDG_STATE_HOME/gsp/reviews`, or `~/.local/state/gsp/reviews` when XDG state is unset.
The report links to captured images and backend logs alongside your observations.
Resume fingerprints are checked against the current inputs; changed inputs invalidate old passes
while keeping their history in the report.

See the [manual pre-release review workbook](manual-pre-release-review.md) for deeper API and
implementation questions. It remains usable as a standalone review, including its direct paired
window command. A full runnable tour requires a GUI host; `--list` and headless checks do not.
