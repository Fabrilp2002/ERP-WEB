#!/bin/bash
# ═════════════════════════════════════════════════════════════════════════════
# Setup Script — ERP Universal v4.0
# ═════════════════════════════════════════════════════════════════════════════
# Uso: bash tools/scripts/setup.sh

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║ ERP Universal — Setup                                                  ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"

# Detectar OS
OS="$(uname)"
if [[ "$OS" == "MINGW64_NT"* ]]; then
  OS="Windows"
elif [[ "$OS" == "Darwin" ]]; then
  OS="macOS"
else
  OS="Linux"
fi

echo "Detected OS: $OS"

# 1. Backend setup
echo ""
echo "→ Setting up Backend..."
cd backend

if [ ! -f ".env" ]; then
  echo "  Creating .env from .env.example..."
  cp ../.env.example .env
  echo "  ⚠️  Please edit backend/.env with your DATABASE_URL"
fi

echo "  Installing Python dependencies..."
pip install -r requirements.txt

cd ..

# 2. Frontend setup
echo ""
echo "→ Setting up Frontend..."
cd frontend

echo "  Installing Node.js dependencies..."
npm install

if [ ! -f ".env.local" ]; then
  echo "  Creating .env.local..."
  cat > .env.local << EOF
NEXT_PUBLIC_API_URL=http://localhost:8000
EOF
fi

cd ..

# 3. Database setup (if PostgreSQL is running)
echo ""
echo "→ Database Setup (Optional)"
echo "  To initialize the database, run:"
echo "  psql -U postgres -f db/esquema_bd.sql"

# 4. Verification
echo ""
echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║ Setup Complete! Next steps:                                            ║"
echo "╠════════════════════════════════════════════════════════════════════════╣"
echo "║                                                                        ║"
echo "║ 1. Edit backend/.env with your database credentials                   ║"
echo "║ 2. Initialize database: psql -U postgres -f db/esquema_bd.sql        ║"
echo "║                                                                        ║"
echo "║ 3. Start Backend:  cd backend && uvicorn main:app --reload            ║"
echo "║    → Swagger UI: http://localhost:8000/docs                           ║"
echo "║                                                                        ║"
echo "║ 4. Start Frontend: cd frontend && npm run dev                          ║"
echo "║    → App: http://localhost:3000                                        ║"
echo "║                                                                        ║"
echo "║ 5. (Optional) Start Electron:  cd frontend && npm run electron        ║"
echo "║                                                                        ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
