docs_host := env("VISPY2_DOCS_HOST", "")
docs_port := env("VISPY2_DOCS_PORT", "8295")

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
