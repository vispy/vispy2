docs_host := env("VISPY2_DOCS_HOST", "")
docs_port := env("VISPY2_DOCS_PORT", "8295")
review_python := env("VISPY2_REVIEW_PYTHON", "../gsp/.venv/bin/python")

# Walk the full project, open isolated live windows, and save feedback after every step.
[positional-arguments]
review *args:
    @"{{review_python}}" tools/review.py "$@"

# Install the optional GUI toolkit into the development environment used by review.
review-setup:
    @uv pip install --python "{{review_python}}" 'PySide6>=6.8,<7'

# Inputs for the cross-backend qualification. The four project wheel
# paths can be overridden individually when a candidate has a non-default
# version or filename; an exact Datoviz runtime wheel may also be supplied.
qualification_python := env("VISPY2_QUALIFICATION_PYTHON", "python")
qualification_output := env("VISPY2_QUALIFICATION_OUTPUT", "../qualification/vispy2")
qualification_wheel_dir := env("VISPY2_QUALIFICATION_WHEEL_DIR", "../wheels")
qualification_gsp_source := env("VISPY2_QUALIFICATION_GSP_SOURCE", "../gsp")
qualification_vispy2_source := env("VISPY2_QUALIFICATION_VISPY2_SOURCE", ".")
qualification_datoviz_source := env("VISPY2_QUALIFICATION_DATOVIZ_SOURCE", "")
qualification_datoviz_source_revision := env("VISPY2_DATOVIZ_SOURCE_REVISION", "")
qualification_datoviz_runtime_wheel := env("VISPY2_DATOVIZ_RUNTIME_WHEEL", "")
qualification_pre_rc3 := env("VISPY2_PRE_RC3_RUNTIME", "0")
qualification_runtime_source_revision := env("VISPY2_DATOVIZ_RUNTIME_SOURCE_REVISION", "")
qualification_allow_dirty := env("VISPY2_QUALIFICATION_ALLOW_DIRTY", "0")
qualification_gsp_core_wheel := env("VISPY2_GSP_CORE_WHEEL", qualification_wheel_dir + "/gsp_core-0.2.0a1-py3-none-any.whl")
qualification_gsp_matplotlib_wheel := env("VISPY2_GSP_MATPLOTLIB_WHEEL", qualification_wheel_dir + "/gsp_matplotlib-0.2.0a1-py3-none-any.whl")
qualification_gsp_datoviz_wheel := env("VISPY2_GSP_DATOVIZ_WHEEL", qualification_wheel_dir + "/gsp_datoviz-0.2.0a1-py3-none-any.whl")
qualification_vispy2_wheel := env("VISPY2_WHEEL", qualification_wheel_dir + "/vispy2-0.2.0a1-py3-none-any.whl")

lint:
    @uvx --from 'ruff==0.16.1' ruff check src tests examples tools
    @uvx --from 'ruff==0.16.1' ruff format --check src tests examples tools

format:
    @uvx --from 'ruff==0.16.1' ruff check --fix src tests examples tools
    @uvx --from 'ruff==0.16.1' ruff format src tests examples tools

pre-commit-check: lint
    @git diff --check
    @git diff --cached --check

# Run the existing validator against four explicit project wheels and, when
# supplied, one exact Datoviz runtime wheel. Source-checkout mode remains useful
# during development.
exact-wheel-qualification:
    #!/usr/bin/env bash
    set -euo pipefail
    env_args=()
    runtime_args=()
    if [[ -n "{{qualification_datoviz_runtime_wheel}}" ]]; then
        runtime_args+=(--datoviz-runtime-wheel "{{qualification_datoviz_runtime_wheel}}")
        env_args+=("GSP_DATOVIZ_SOURCE=none")
    elif [[ -n "{{qualification_datoviz_source}}" ]]; then
        runtime_args+=(--datoviz-source "{{qualification_datoviz_source}}")
        env_args+=("GSP_DATOVIZ_SOURCE={{qualification_datoviz_source}}")
    fi
    if [[ -n "{{qualification_datoviz_source_revision}}" ]]; then
        runtime_args+=(--datoviz-source-revision "{{qualification_datoviz_source_revision}}")
    fi
    if [[ "{{qualification_pre_rc3}}" == "1" ]]; then
        runtime_args+=(--pre-rc3-runtime --datoviz-runtime-source-revision "{{qualification_runtime_source_revision}}")
    fi
    if [[ "{{qualification_allow_dirty}}" == "1" ]]; then
        runtime_args+=(--allow-dirty-project-sources)
    fi
    env "${env_args[@]}" "{{qualification_python}}" examples/validate_gallery.py \
        --python "{{qualification_python}}" \
        --output-dir "{{qualification_output}}" \
        --gsp-source "{{qualification_gsp_source}}" \
        --vispy2-source "{{qualification_vispy2_source}}" \
        --gsp-core-wheel "{{qualification_gsp_core_wheel}}" \
        --gsp-matplotlib-wheel "{{qualification_gsp_matplotlib_wheel}}" \
        --gsp-datoviz-wheel "{{qualification_gsp_datoviz_wheel}}" \
        --vispy2-wheel "{{qualification_vispy2_wheel}}" \
        "${runtime_args[@]}"

docs-build-check:
    @uv run --no-project --with 'mkdocs-material==9.7.7' mkdocs build --strict

serve:
    #!/usr/bin/env bash
    set -euo pipefail
    host="{{docs_host}}"
    tailnet_host=""
    if command -v tailscale >/dev/null 2>&1; then
        tailnet_ip=$(tailscale ip -4 2>/dev/null || true)
        if [ -z "$host" ]; then
            host="$tailnet_ip"
        fi
        if [ -n "$tailnet_ip" ] && [ "$host" = "$tailnet_ip" ]; then
            tailnet_host=$(tailscale status --json | python3 -c 'import json, sys; print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))')
        fi
    fi
    host="${host:-127.0.0.1}"
    display_host="${tailnet_host:-$host}"
    echo "VisPy2 documentation: http://${display_host}:{{docs_port}}/"
    uv run --no-project --with 'mkdocs-material==9.7.7' mkdocs serve -a "${host}:{{docs_port}}"

docs-serve:
    @just serve
