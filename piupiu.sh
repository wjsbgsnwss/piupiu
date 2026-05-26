#!/usr/bin/env bash
# PiuPiu process manager — usage: ./piupiu.sh {start|stop|restart|status|log}

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/.piupiu/piupiu.pid"
LOG_FILE="$SCRIPT_DIR/.piupiu/piupiu.log"

_is_running() {
    [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null
}

cmd_start() {
    if _is_running; then
        echo "PiuPiu is already running (PID $(cat "$PID_FILE"))"
        return 1
    fi
    mkdir -p "$SCRIPT_DIR/.piupiu"
    echo "Starting PiuPiu..."
    nohup bash -c "cd '$SCRIPT_DIR' && exec python3 -m piupiu" >> "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    sleep 1
    if _is_running; then
        echo "PiuPiu started (PID $(cat "$PID_FILE"))  log: $LOG_FILE"
    else
        echo "PiuPiu failed to start — check the log:"
        tail -20 "$LOG_FILE"
        return 1
    fi
}

cmd_stop() {
    if ! _is_running; then
        echo "PiuPiu is not running"
        return 1
    fi
    local pid
    pid=$(cat "$PID_FILE")
    echo "Stopping PiuPiu (PID $pid)..."
    kill "$pid"
    local i=0
    while kill -0 "$pid" 2>/dev/null; do
        sleep 0.5
        i=$(( i + 1 ))
        if [ $i -ge 10 ]; then
            echo "Process did not exit — sending SIGKILL"
            kill -9 "$pid" 2>/dev/null || true
            break
        fi
    done
    rm -f "$PID_FILE"
    echo "PiuPiu stopped"
}

cmd_restart() {
    if _is_running; then
        cmd_stop
    fi
    cmd_start
}

cmd_status() {
    if _is_running; then
        echo "PiuPiu is running (PID $(cat "$PID_FILE"))"
    else
        echo "PiuPiu is not running"
    fi
}

cmd_log() {
    if [ ! -f "$LOG_FILE" ]; then
        echo "No log file found at $LOG_FILE"
        return 1
    fi
    tail -f "$LOG_FILE"
}

case "${1:-}" in
    start)   cmd_start   ;;
    stop)    cmd_stop    ;;
    restart) cmd_restart ;;
    status)  cmd_status  ;;
    log)     cmd_log     ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|log}"
        exit 1
        ;;
esac
