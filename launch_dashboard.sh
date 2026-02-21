#!/bin/bash
# Launch the dashboard with a local web server

cd "/Users/allman/Library/CloudStorage/Dropbox/Dropbox Mike/Judging Bias"

echo "========================================"
echo "  Starting Dashboard Server"
echo "========================================"
echo ""
echo "Opening browser to: http://localhost:8000/dashboard.html"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start Python HTTP server and open browser
python3 -m http.server 8000 &
SERVER_PID=$!

# Wait a moment for server to start
sleep 1

# Open browser
open "http://localhost:8000/dashboard.html"

# Wait for user to press Ctrl+C
wait $SERVER_PID
