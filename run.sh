#!/bin/bash

# Get the absolute path to the project root
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Ensure centralized directories exist at project root
mkdir -p "$ROOT_DIR/.pids" "$ROOT_DIR/logs"

PID_FILE="$ROOT_DIR/.pids/server.pid"
LOG_FILE="$ROOT_DIR/logs/server.log"
PORT=8000

TOOLBOX_PID_FILE="$ROOT_DIR/.pids/toolbox.pid"
TOOLBOX_LOG_FILE="$ROOT_DIR/logs/toolbox.log"
TOOLBOX_PORT=5005


start_toolbox() {
    if [ -f "$TOOLBOX_PID_FILE" ] && ps -p $(cat "$TOOLBOX_PID_FILE") > /dev/null 2>&1; then
        echo "Toolbox is already running (PID: $(cat "$TOOLBOX_PID_FILE"))"
        return
    fi

    echo "Starting Toolbox server on port $TOOLBOX_PORT..."
    # Load SQLITE_DATABASE from .env if it exists
    if [ -f "$ROOT_DIR/agentica/.env" ]; then
        # Export env variables correctly
        set -a
        source "$ROOT_DIR/agentica/.env"
        set +a
    fi
    export SQLITE_DATABASE=${SQLITE_DATABASE:-"data/chinook.db"}

    cd "$ROOT_DIR/agentica"
    nohup npx -y @toolbox-sdk/server --prebuilt sqlite --port $TOOLBOX_PORT > "$TOOLBOX_LOG_FILE" 2>&1 &
    echo $! > "$TOOLBOX_PID_FILE"
    cd "$ROOT_DIR"

    echo "Toolbox started (PID: $(cat "$TOOLBOX_PID_FILE"))"
}

stop_toolbox() {
    if [ -f "$TOOLBOX_PID_FILE" ]; then
        PID=$(cat "$TOOLBOX_PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            echo "Stopping Toolbox server (PID: $PID)..."
            kill $PID
            rm "$TOOLBOX_PID_FILE"
            echo "Toolbox stopped"
        else
            rm "$TOOLBOX_PID_FILE"
        fi
    fi
}

start() {
    start_toolbox
    if [ -f "$PID_FILE" ] && ps -p $(cat "$PID_FILE") > /dev/null 2>&1; then
        echo "Server is already running (PID: $(cat "$PID_FILE"))"
        exit 1
    fi

    echo "Starting server..."
    if [ -d "$ROOT_DIR/.venv" ]; then
        source "$ROOT_DIR/.venv/bin/activate"
    fi
    
    cd "$ROOT_DIR/agentica"
    export PYTHONPATH="$ROOT_DIR/agentica:$PYTHONPATH"
    nohup uvicorn server:app --host 0.0.0.0 --port $PORT --log-level info > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    cd "$ROOT_DIR"
    
    echo "Server started (PID: $(cat "$PID_FILE"))"
    echo "Logs are being written to $LOG_FILE"
}

stop() {
    stop_toolbox
    if [ ! -f "$PID_FILE" ]; then

        echo "Server is not running (no PID file found)"
        # Check if process exists anyway matching uvicorn
        if pgrep -f "uvicorn server:app" > /dev/null; then
             echo "Warning: PID file missing but uvicorn process found. Manual cleanup required."
        fi
        return
    fi

    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        echo "Stopping server (PID: $PID)..."
        kill $PID
        # Wait for process to exit
        sleep 1
        if ps -p $PID > /dev/null 2>&1; then
             echo "Force killing..."
             kill -9 $PID
        fi
        rm "$PID_FILE"
        echo "Server stopped"
    else
        echo "Server process $PID not found. Removing stale PID file."
        rm "$PID_FILE"
    fi
}

status() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            echo "Server is running (PID: $PID)"
        else
            echo "Server is stopped (stale PID file found)"
        fi
    else
        # Fallback check
        if pgrep -f "uvicorn server:app" > /dev/null; then
            echo "Server is running (PID: $(pgrep -f "uvicorn server:app")) - but no PID file found"
        else
            echo "Server is stopped"
        fi
    fi
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        sleep 1
        start
        ;;
    status)
        status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
