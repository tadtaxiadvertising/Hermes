#!/bin/bash
# ============================================================
# VPS Setup Script - Hermes + Syncthing + Honcho Memory Server
# Ejecuta en el VPS via SSH: curl -fsSL <url> | bash
# O copia y pega en terminal SSH
# ============================================================

set -e

echo "=== Hermes VPS Setup (with Honcho Server) ==="

# --- Configuración ---
HONCHO_API_KEY="${HONCHO_API_KEY:-hch-v3-1kjj7gyr465yswnyrwtjntx2ptbvebf90ty0otepc1h1q7tmpmuky3y44s69idhv}"
WORKSPACE="tad-dooh-platform"
HERMES_HOME="${HERMES_HOME:-/data/hermes}"

# --- 1. Instalar dependencias del sistema ---
echo "[1/8] Instalando dependencias del sistema..."
apt-get update -qq
apt-get install -y -qq \
    curl \
    git \
    nodejs \
    npm \
    python3 \
    python3-pip \
    python3-venv \
    syncthing \
    docker.io \
    docker-compose \
    2>/dev/null | tail -5

# --- 2. Instalar uv (para uvx MCP servers) ---
echo "[2/8] Instalando uv..."
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# --- 3. Desplegar Honcho Server con Docker Compose ---
echo "[3/8] Desplegando Honcho Server (PostgreSQL + Redis + Honcho)..."
mkdir -p /opt/honcho
cat > /opt/honcho/docker-compose.yml << 'HONCHO_EOF'
version: '3.8'

services:
  honcho:
    image: ghcr.io/plastic-labs/honcho:latest
    ports:
      - "8000:8000"
    environment:
      - HONCHO_API_KEY=hch-v3-1kjj7gyr465yswnyrwtjntx2ptbvebf90ty0otepc1h1q7tmpmuky3y44s69idhv
      - HONCHO_DATABASE_URL=postgresql://postgres:postgres@db:5432/honcho
      - HONCHO_REDIS_URL=redis://redis:6379/0
      - HONCHO_LOG_LEVEL=INFO
    volumes:
      - honcho-data:/data
    depends_on:
      - db
      - redis
    restart: unless-stopped

  db:
    image: postgres:16-alpine
    environment:
      - POSTGRES_DB=honcho
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    volumes:
      - postgres-data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data
    restart: unless-stopped

volumes:
  honcho-data:
  postgres-data:
  redis-data:
HONCHO_EOF

cd /opt/honcho
docker-compose up -d

# Wait for Honcho to be ready
echo "Esperando a que Honcho esté listo..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
        echo "Honcho listo!"
        break
    fi
    sleep 2
done

# --- 4. Instalar Hermes Agent ---
echo "[4/8] Instalando Hermes Agent..."
pip install --no-cache-dir hermes-agent[mcp] honcho-ai

# --- 5. Configurar directorio Hermes ---
echo "[5/8] Configurando Hermes en $HERMES_HOME..."
mkdir -p "$HERMES_HOME"
export HERMES_HOME

# --- 6. Crear y configurar perfil ---
echo "[6/8] Creando perfil 'tad-shared'..."
hermes profile create tad-shared
hermes profile use tad-shared

# --- 7. Configurar memoria Honcho ---
echo "[7/8] Configurando memoria Honcho (apuntando a Honcho local)..."
hermes memory setup honcho --non-interactive \
    --url http://localhost:8000/ \
    --apikey "$HONCHO_API_KEY" \
    --workspace "$WORKSPACE"

# --- 8. Configurar cron solo en VPS ---
echo "[8/8] Habilitando cron jobs en VPS..."
hermes config set cron.enabled true

# --- 9. Configurar Syncthing como servicio ---
echo "Configurando Syncthing servicio..."
mkdir -p /var/syncthing
cat > /etc/systemd/user/syncthing.service << 'EOF'
[Unit]
Description=Syncthing - Open Source Continuous File Synchronization
Documentation=man:syncthing(1)
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/syncthing serve --no-browser --home=/var/syncthing --gui-address=0.0.0.0:8384
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now syncthing.service

# --- 10. Obtener Device ID y API Key de Syncthing ---
sleep 3
SYNCTHING_DEVICE_ID=$(syncthing --home=/var/syncthing device-id 2>/dev/null || echo "WAITING")
SYNCTHING_API_KEY=$(grep -oP '(?<=<apikey>)[^<]+' /var/syncthing/config.xml 2>/dev/null || echo "WAITING")

echo ""
echo "=== SETUP COMPLETADO ==="
echo ""
echo "Honcho Server: http://localhost:8000 (interno) / https://TU_DOMINIO_HONCHO (público)"
echo "HONCHO_API_KEY: $HONCHO_API_KEY"
echo ""
echo "Syncthing Device ID (para agregar en Windows):"
echo "  $SYNCTHING_DEVICE_ID"
echo ""
echo "Syncthing API Key (para configurar folder share via API):"
echo "  $SYNCTHING_API_KEY"
echo ""
echo "Syncthing UI: http://TU_VPS_IP:8384"
echo ""
echo "Próximos pasos en Windows Syncthing UI (http://localhost:8384):"
echo "  1. Add Remote Device → Device ID: $SYNCTHING_DEVICE_ID"
echo "  2. Share folder 'hermes-tad-shared' con este device"
echo "  3. En VPS Syncthing UI: aceptar share entrante, path: /data/hermes/profiles/tad-shared/"
echo ""
echo "En Windows (HERMES_HOME debe apuntar a tad-shared):"
echo "  set HERMES_HOME=C:\\Users\\Arismendy\\AppData\\Local\\hermes\\profiles\\tad-shared"
echo "  set HERMES_HONCHO_HOST=hermes_tad-shared"
echo "  hermes memory status"
echo "  hermes chat -q 'Test memoria compartida desde Windows'"