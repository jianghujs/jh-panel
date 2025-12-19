#!/bin/bash
# Logging helper shared by keepalived scripts.

LOG_UTIL_FILE=""
LOG_UTIL_NAME="keepalived"
LOG_UTIL_MAX_LINES=0

logger_init() {
    LOG_UTIL_FILE="$1"
    LOG_UTIL_NAME="${2:-keepalived}"
    LOG_UTIL_MAX_LINES="${3:-0}"
    if [ -z "$LOG_UTIL_FILE" ]; then
        return
    fi
    local dir
    dir=$(dirname "$LOG_UTIL_FILE")
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
    fi
}

logger_trim() {
    if [ -z "$LOG_UTIL_FILE" ] || [ "$LOG_UTIL_MAX_LINES" -le 0 ]; then
        return
    fi

    if [ ! -f "$LOG_UTIL_FILE" ]; then
        return
    fi

    local line_count
    line_count=$(wc -l < "$LOG_UTIL_FILE" 2>/dev/null || echo 0)
    if [ "$line_count" -le "$LOG_UTIL_MAX_LINES" ]; then
        return
    fi

    local tmp
    tmp=$(mktemp "/tmp/logger.XXXXXX") || return
    tail -n "$LOG_UTIL_MAX_LINES" "$LOG_UTIL_FILE" > "$tmp" && mv "$tmp" "$LOG_UTIL_FILE"
    rm -f "$tmp"
}

logger_log() {
    local message="$*"
    local now
    now=$(date +'%Y-%m-%d %H:%M:%S')

    if [ -n "$LOG_UTIL_FILE" ]; then
        echo "${now} [${LOG_UTIL_NAME}] $message" >> "$LOG_UTIL_FILE"
        logger_trim
    else
        echo "${now} [${LOG_UTIL_NAME}] $message"
    fi
}
