#!/bin/bash
# Kiro command execution wrapper
# Handles: output capture, ANSI stripping, size limiting
# Usage: ./.kiro_exec.sh your_command arg1 arg2 ...

set -o pipefail  # Ensure we catch pipe failures

# Find workspace root (where this script lives)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ALWAYS write to workspace root, regardless of where command is run from
OUTPUT_FILE="$SCRIPT_DIR/.kiro_command_output.txt"
TEMP_FILE="$SCRIPT_DIR/.kiro_command_output.tmp"
MAX_LINES=100  # Limit output to prevent token waste

# Validate command exists
if [ $# -eq 0 ]; then
    echo "Error: No command provided" > "$OUTPUT_FILE"
    echo "Usage: ./.kiro_exec.sh command [args...]" >> "$OUTPUT_FILE"
    exit 1
fi

# Execute command and capture output to temp file
# We do NOT pipe through sed here to preserve the real exit code
"$@" > "$TEMP_FILE" 2>&1
EXIT_CODE=$?

# Now strip ANSI codes (comprehensive regex) and write to a clean temp file
# Handles: colors, cursor movement, clear codes, OSC sequences
sed 's/\x1b\[[0-9;]*[a-zA-Z]//g; s/\x1b].*\x07//g; s/\x1b].*\x1b\\//g' "$TEMP_FILE" > "$TEMP_FILE.clean"
mv "$TEMP_FILE.clean" "$TEMP_FILE"

# Count total lines (handles files without trailing newline)
TOTAL_LINES=$(grep -c ^ "$TEMP_FILE" 2>/dev/null || echo 0)

# Write to output file with truncation if needed
if [ "$TOTAL_LINES" -gt "$MAX_LINES" ]; then
    # Take last MAX_LINES and add truncation notice
    {
        echo "[OUTPUT TRUNCATED: Showing last $MAX_LINES of $TOTAL_LINES lines]"
        echo ""
        tail -n "$MAX_LINES" "$TEMP_FILE"
    } > "$OUTPUT_FILE"
else
    # Copy entire output
    cp "$TEMP_FILE" "$OUTPUT_FILE"
fi

# Clean up
rm -f "$TEMP_FILE"

# Exit with original command's exit code
exit $EXIT_CODE
