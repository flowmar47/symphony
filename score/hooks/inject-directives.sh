#!/usr/bin/env bash
# ENFORCES: the always-on blocks (Prime Directives, Integrity Rules, Recency Verification).
# MAPS TO: CLAUDE.md master — plugin-native replacement for the @import line; toggles with the plugin.
# TEST: CLAUDE_PLUGIN_ROOT=<repo> bash inject-directives.sh  (expect the master CLAUDE.md on stdout)
#
# SessionStart hook (plugin form): print the collection's master CLAUDE.md to stdout, which
# Claude Code injects as session context (verified behavior). This is how the directives load
# when running as a plugin — no user-CLAUDE.md edit needed, and disabling the plugin disables
# them cleanly. Fail-safe: missing file → exit 0 silently.
set -uo pipefail

master="${CLAUDE_PLUGIN_ROOT:-}/CLAUDE.md"
[ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -r "$master" ] || exit 0

echo "=== symphony score directives (plugin) ==="
cat "$master"
echo "=== end symphony score directives ==="
exit 0
