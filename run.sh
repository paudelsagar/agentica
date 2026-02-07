#!/bin/bash

PID_FILE="server.pid"
LOG_FILE="server.log"
PORT=8000

start() {
    if [ -f "$PID_FILE" ]; then
        if ps -p $(cat "$PID_FILE") > /dev/null 2>&1; then
            echo "Server is already running (PID: $(cat "$PID_FILE"))"
            exit 1
        else
            echo "Found stale PID file. Removing..."
            rm "$PID_FILE"
        fi
    fi

    echo "Starting server..."
    if [ -d ".venv" ]; then
        source .venv/bin/activate
    fi
    # Run uvicorn in background
    nohup uvicorn server:app --port $PORT > "$LOG_FILE" 2>&1 &
    
    # Save PID
    echo $! > "$PID_FILE"
    echo "Server started (PID: $(cat "$PID_FILE"))"
    echo "Logs are being written to $LOG_FILE"
}

stop() {
    if [ ! -f "$PID_FILE" ]; then
        echo "Server is not running (no PID file found)"
        # Check if process exists anyway matching uvicorn
        if pgrep -f "uvicorn backend.server:app" > /dev/null; then
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
