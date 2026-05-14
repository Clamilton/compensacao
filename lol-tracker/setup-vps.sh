#!/bin/bash
# Setup do X5 Tracker (veted.online) na VPS
# Rode como root na VPS:
#   bash setup-vps.sh

set -e

REMOTE_DIR="/var/www/veted"
APP_PORT=3001
DOMAIN="veted.online"
REPO="https://github.com/Clamilton/compensacao.git"
BRANCH="claude/lol-score-tracker-MXLzA"
ADMIN_PASS="x5admin"   # mude se quiser

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
  pm2 startup systemd -u root --hp /root | tail -1 | bash
fi
echo "  ✅ PM2 $(pm2 --version)"

# ── 3. Clonar / atualizar repositório ────────────────────────────────────
echo ""
echo "▶ Clonando repositório..."
if [ -d "$REMOTE_DIR/.git" ]; then
  echo "  Atualizando repositório existente..."
  git -C "$REMOTE_DIR" fetch origin
  git -C "$REMOTE_DIR" checkout "$BRANCH"
  git -C "$REMOTE_DIR" pull origin "$BRANCH"
else
  git clone --branch "$BRANCH" "$REPO" "$REMOTE_DIR"
fi
echo "  ✅ Repositório em $REMOTE_DIR"

# ── 4. Entrar na pasta do app ─────────────────────────────────────────────
cd "$REMOTE_DIR/lol-tracker"

# ── 5. .env ───────────────────────────────────────────────────────────────
echo ""
echo "▶ Criando .env..."
mkdir -p "$REMOTE_DIR/data"
cat > .env << ENVEOF
DATABASE_URL="file:$REMOTE_DIR/data/prod.db"
ADMIN_PASSWORD="$ADMIN_PASS"
PORT=$APP_PORT
HOSTNAME="0.0.0.0"
ENVEOF
echo "  ✅ .env criado"

# ── 6. Instalar dependências ──────────────────────────────────────────────
echo ""
echo "▶ Instalando dependências..."
npm ci --production=false
echo "  ✅ Dependências instaladas"

# ── 7. Build ──────────────────────────────────────────────────────────────
echo ""
echo "▶ Buildando aplicação..."
npm run build
echo "  ✅ Build concluído"

# ── 8. Migração do banco ──────────────────────────────────────────────────
echo ""
echo "▶ Rodando migrações do banco..."
npx prisma migrate deploy
echo "  ✅ Banco migrado"

# ── 9. Copiar estáticos para standalone ──────────────────────────────────
echo ""
echo "▶ Ajustando build standalone..."
cp -r .next/static .next/standalone/.next/static
cp -r public .next/standalone/public
echo "  ✅ Estáticos copiados"

# ── 10. PM2 — iniciar / reiniciar ─────────────────────────────────────────
echo ""
echo "▶ Iniciando app com PM2..."
cat > ecosystem.config.js << PMEOF
module.exports = {
  apps: [{
    name: 'veted',
    script: '$REMOTE_DIR/lol-tracker/.next/standalone/server.js',
    cwd:    '$REMOTE_DIR/lol-tracker',
    env: {
      NODE_ENV: 'production',
      PORT: $APP_PORT,
      HOSTNAME: '0.0.0.0',
    },
  }],
};
PMEOF

pm2 delete veted 2>/dev/null || true
pm2 start ecosystem.config.js
pm2 save
sleep 2
echo "  $(pm2 list | grep veted || echo 'veted iniciado')"

# ── 11. Nginx ─────────────────────────────────────────────────────────────
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
nginx -t
systemctl reload nginx
echo "  ✅ Nginx configurado (sistema-van intacto)"

# ── 12. Verificar sistema-van ─────────────────────────────────────────────
echo ""
echo "▶ Verificando sistema-van (não deve ter sido afetado)..."
echo "  status: $(systemctl is-active sistema-van)"

# ── 13. SSL ───────────────────────────────────────────────────────────────
echo ""
echo "▶ Configurando SSL com Certbot..."
if ! certbot --version &>/dev/null; then
  apt-get install -y certbot python3-certbot-nginx
fi
certbot --nginx -d "$DOMAIN" -d "www.$DOMAIN" \
  --non-interactive --agree-tos -m "admin@$DOMAIN"

echo ""
echo "============================================"
echo " ✅  Deploy concluído!"
echo "    https://$DOMAIN"
echo "    https://$DOMAIN/admin  (senha: $ADMIN_PASS)"
echo "    https://$DOMAIN/balancer"
echo "============================================"
