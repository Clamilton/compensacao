#!/bin/bash
# Setup do X5 Tracker (veted.online) na VPS
# Rode como root na VPS:
#   bash /var/www/veted/repo/lol-tracker/setup-vps.sh

set -e

REPO_DIR="/var/www/veted/repo"
APP_DIR="$REPO_DIR/lol-tracker"
APP_PORT=3002
DOMAIN="veted.site"
REPO="https://github.com/Clamilton/compensacao.git"
BRANCH="claude/lol-score-tracker-MXLzA"
ADMIN_PASS='TnV&mnrRR#65'

# Credenciais Supabase (projeto veted)
DB_POOL="postgresql://postgres.rqrdddcegqtypcgtfmwv:TnV%26mnrRR%2312@aws-1-sa-east-1.pooler.supabase.com:6543/postgres?pgbouncer=true"
DB_DIRECT="postgresql://postgres:TnV%26mnrRR%2312@db.rqrdddcegqtypcgtfmwv.supabase.co:5432/postgres"

echo "============================================"
echo " X5 Tracker — Setup na VPS"
echo "============================================"

# ── 1. Node.js 20 ────────────────────────────────────────────────────────
echo ""
echo "▶ Verificando Node.js..."
if ! node --version 2>/dev/null | grep -q "^v2"; then
  echo "  Instalando Node.js 20..."
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y nodejs
fi
echo "  ✅ $(node --version)"

# ── 2. PM2 ───────────────────────────────────────────────────────────────
echo ""
echo "▶ Verificando PM2..."
if ! pm2 --version &>/dev/null; then
  npm install -g pm2
fi
echo "  ✅ PM2 ok"

# ── 3. Clonar / atualizar repositório ────────────────────────────────────
echo ""
echo "▶ Repositório..."
if [ -d "$REPO_DIR/.git" ]; then
  echo "  Atualizando..."
  git -C "$REPO_DIR" fetch origin
  git -C "$REPO_DIR" checkout "$BRANCH"
  git -C "$REPO_DIR" pull origin "$BRANCH"
else
  git clone --branch "$BRANCH" "$REPO" "$REPO_DIR"
fi
echo "  ✅ Repositório ok"

# ── 4. .env ───────────────────────────────────────────────────────────────
echo ""
echo "▶ Criando .env..."
cat > "$APP_DIR/.env" << ENVEOF
DATABASE_URL="$DB_POOL"
DATABASE_DIRECT_URL="$DB_DIRECT"
ADMIN_PASSWORD="$ADMIN_PASS"
PORT=$APP_PORT
HOSTNAME="0.0.0.0"
ENVEOF
echo "  ✅ .env criado"

# ── 5. Instalar dependências ──────────────────────────────────────────────
echo ""
echo "▶ Instalando dependências..."
cd "$APP_DIR"
npm ci
echo "  ✅ Dependências instaladas"

# ── 6. Build ──────────────────────────────────────────────────────────────
echo ""
echo "▶ Buildando aplicação..."
npm run build
cp -r .next/static .next/standalone/.next/static
cp -r public .next/standalone/public
echo "  ✅ Build concluído"

# ── 7. Migração do banco ──────────────────────────────────────────────────
echo ""
echo "▶ Rodando migrações no Supabase..."
npx prisma migrate deploy
echo "  ✅ Banco migrado"

# ── 8. PM2 ───────────────────────────────────────────────────────────────
echo ""
echo "▶ Iniciando app com PM2..."
cat > /var/www/veted/ecosystem.config.js << PMEOF
module.exports = {
  apps: [{
    name: 'veted',
    script: '$APP_DIR/.next/standalone/server.js',
    cwd:    '$APP_DIR',
    env: {
      NODE_ENV:            'production',
      PORT:                $APP_PORT,
      HOSTNAME:            '0.0.0.0',
      DATABASE_URL:        '$DB_POOL',
      ADMIN_PASSWORD:      '$ADMIN_PASS',
    },
  }],
};
PMEOF

pm2 delete veted 2>/dev/null || true
pm2 start /var/www/veted/ecosystem.config.js
pm2 save
pm2 startup systemd -u root --hp /root | tail -1 | bash
sleep 2
echo "  $(pm2 list | grep veted)"

# ── 9. Nginx ─────────────────────────────────────────────────────────────
echo ""
echo "▶ Configurando Nginx para $DOMAIN..."
cat > /etc/nginx/sites-available/veted << NGINXEOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;

    location / {
        proxy_pass         http://127.0.0.1:$APP_PORT;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade \$http_upgrade;
        proxy_set_header   Connection 'upgrade';
        proxy_set_header   Host \$host;
        proxy_set_header   X-Real-IP \$remote_addr;
        proxy_cache_bypass \$http_upgrade;
    }
}
NGINXEOF

ln -sf /etc/nginx/sites-available/veted /etc/nginx/sites-enabled/veted
nginx -t && systemctl reload nginx
echo "  ✅ Nginx configurado"

# ── 10. Verificar sistema-van ─────────────────────────────────────────────
echo ""
echo "▶ Verificando sistema-van..."
echo "  status: $(systemctl is-active sistema-van)"

# ── 11. SSL ───────────────────────────────────────────────────────────────
echo ""
echo "▶ Configurando SSL..."
if ! certbot --version &>/dev/null; then
  apt-get install -y certbot python3-certbot-nginx
fi
certbot --nginx -d "$DOMAIN" -d "www.$DOMAIN" \
  --non-interactive --agree-tos -m "admin@$DOMAIN" || \
  echo "  ⚠️  Certbot falhou — verifique se o DNS já aponta para este IP"

echo ""
echo "============================================"
echo " ✅  Deploy concluído!"
echo "    http://$DOMAIN  (https se certbot ok)"
echo "    Admin:       /$DOMAIN/admin  (senha: $ADMIN_PASS)"
echo "    Balanceador: /$DOMAIN/balancer"
echo "============================================"
