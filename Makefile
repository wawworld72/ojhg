.PHONY: dev backend frontend install-deps

dev: install-deps
	@echo "🚀 Starting development servers..."
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:3000"
	@echo ""
	@echo "Starting backend in background..."
	@cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > ../backend.log 2>&1 &
	@sleep 2
	@echo "✅ Backend started"
	@echo "Starting frontend..."
	@cd frontend && npm run dev

backend:
	@cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	@cd frontend && npm run dev

install-deps:
	@echo "Installing backend dependencies..."
	@cd backend && python3 -m pip install -e . > /dev/null
	@echo "Installing frontend dependencies..."
	@cd frontend && npm install > /dev/null
	@echo "✅ All dependencies installed"
