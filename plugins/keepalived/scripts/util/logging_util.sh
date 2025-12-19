#!/bin/bash
# Logging helper shared by keepalived scripts.

LOG_UTIL_FILE=""
LOG_UTIL_NAME="keepalived"

logger_init() {
    LOG_UTIL_FILE="$1"
    LOG_UTIL_NAME="${2:-keepalived}"
    if [ -z "$LOG_UTIL_FILE" ]; then
        return
    fi
    local dir
    dir=$(dirname "$LOG_UTIL_FILE")
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
    fi
}

logger_log() {
    local message="$*"
    local now
    now=$(date +'%Y-%m-%d %H:%M:%S')

    if [ -n "$LOG_UTIL_FILE" ]; then
        echo "${now} [${LOG_UTIL_NAME}] $message" >> "$LOG_UTIL_FILE"
    else
        echo "${now} [${LOG_UTIL_NAME}] $message"
    fi
}
