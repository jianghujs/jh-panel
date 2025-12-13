#!/usr/bin/env sh
STATE="$1"
PREV_STATE="$2"
TYPE="$3"

BASE_DIR="{$SERVER_PATH}//keepalived"
LOG_DIR="${BASE_DIR}/logs"
LOG_FILE="${LOG_DIR}/events.log"

mkdir -p "$LOG_DIR"

MSG="$(date +'%Y-%m-%d %H:%M:%S') [keepalived] VRRP ${TYPE}: ${PREV_STATE} -> ${STATE}"
printf '%s\n' "$MSG" >> "$LOG_FILE"

