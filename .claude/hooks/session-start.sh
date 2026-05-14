#!/bin/bash
set -euo pipefail

# Only run in Claude Code on the web
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
BACKEND_LOG="$PROJECT_DIR/backend.log"
FRONTEND_LOG="$PROJECT_DIR/frontend.log"

echo "🚀 Starting development servers..."

# Kill any existing processes on ports 8000 and 3000
echo "🔍 Checking for existing processes on ports 8000 and 3000..."
pkill -f "uvicorn.*8000" || true
pkill -f "next dev" || true
sleep 1

# Setup backend Python environment
echo "📦 Setting up backend Python environment..."
cd "$PROJECT_DIR/backend"

# Ensure pip is up to date
python3 -m pip install --upgrade pip setuptools wheel > /dev/null 2>&1 || true

# Install backend dependencies with verbose error reporting
echo "📦 Installing backend dependencies (this may take a moment)..."
if python3 -m pip install -e . 2>&1 | tee "$BACKEND_LOG.install"; then
  echo "✅ Backend dependencies installed"
else
  echo "⚠️  Backend installation had issues (attempting to continue)"
  cat "$BACKEND_LOG.install" >> "$BACKEND_LOG"
fi

# Start backend server
echo "🔧 Starting backend (FastAPI on port 8000)..."
nohup python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!
echo "✅ Backend started (PID: $BACKEND_PID)"

# Wait for backend to be ready
sleep 4

# Setup frontend
echo "📦 Setting up frontend..."
cd "$PROJECT_DIR/frontend"

# Install frontend dependencies
echo "📦 Installing frontend dependencies..."
npm install > /dev/null 2>&1 || {
  echo "⚠️  Frontend npm install had issues (attempting to continue)"
  npm install 2>&1 | tail -10 >> "$FRONTEND_LOG"
}

# Start frontend server
echo "🎨 Starting frontend (Next.js on port 3000)..."
nohup npm run dev > "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!
echo "✅ Frontend started (PID: $FRONTEND_PID)"

# Save PIDs for potential cleanup
echo "$BACKEND_PID" > "$PROJECT_DIR/.claude/backend.pid"
echo "$FRONTEND_PID" > "$PROJECT_DIR/.claude/frontend.pid"

# Wait a bit for servers to fully start
sleep 6

# Verify servers are running
echo ""
echo "📋 Server status:"
if kill -0 $BACKEND_PID 2>/dev/null; then
  echo "✅ Backend is running (PID: $BACKEND_PID)"
else
  echo "❌ Backend failed to start"
  echo "   Log: $BACKEND_LOG"
  if [ -f "$BACKEND_LOG" ]; then
    echo "   Last 10 lines:"
    tail -10 "$BACKEND_LOG" | sed 's/^/   /'
  fi
fi

if kill -0 $FRONTEND_PID 2>/dev/null; then
  echo "✅ Frontend is running (PID: $FRONTEND_PID)"
else
  echo "❌ Frontend failed to start"
  echo "   Log: $FRONTEND_LOG"
  if [ -f "$FRONTEND_LOG" ]; then
    echo "   Last 10 lines:"
    tail -10 "$FRONTEND_LOG" | sed 's/^/   /'
  fi
fi

echo ""
echo "🎉 Development servers initialization complete!"
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:3000"
echo ""

