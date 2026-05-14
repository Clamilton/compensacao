#!/usr/bin/env python3
"""
Deploy do X5 Tracker (veted.online) na VPS.
Rode este script na sua máquina local após fazer 'npm run build' no lol-tracker/.

Dependência: pip install paramiko
"""

import paramiko
import os
import sys
import time
from pathlib import Path

# ── Configuração ────────────────────────────────────────────────────────────
VPS_IP       = '187.77.49.158'
VPS_USER     = 'root'
VPS_PASSWORD = 'TnV&mnrRR#65'
REMOTE_DIR   = '/var/www/veted'
APP_PORT     = 3001          # porta interna do Next.js (nginx faz proxy)
DOMAIN       = 'veted.online'
ADMIN_PASS   = 'x5admin'     # senha do painel admin — MUDE SE QUISER
# ────────────────────────────────────────────────────────────────────────────

BUILD_DIR = Path(__file__).parent / '.next' / 'standalone'
STATIC_DIR = Path(__file__).parent / '.next' / 'static'
PUBLIC_DIR = Path(__file__).parent / 'public'
PRISMA_DIR = Path(__file__).parent / 'prisma'

if not BUILD_DIR.exists():
    print('❌  Pasta .next/standalone não encontrada.')
    print('   Rode antes:  cd lol-tracker && npm run build')
    sys.exit(1)


def run(ssh, cmd, check=True):
    print(f'  $ {cmd}')
    _, out, err = ssh.exec_command(cmd)
    stdout = out.read().decode().strip()
    stderr = err.read().decode().strip()
    if stdout:
        print(f'    {stdout}')
    if stderr and check:
        print(f'    [err] {stderr}')
    return stdout


def sftp_put_dir(sftp, ssh, local_dir: Path, remote_dir: str):
    """Envia recursivamente um diretório inteiro via SFTP."""
    for item in sorted(local_dir.rglob('*')):
        if item.is_file():
            rel = item.relative_to(local_dir)
            remote_path = f"{remote_dir}/{str(rel).replace(os.sep, '/')}"
            remote_parent = remote_path.rsplit('/', 1)[0]
            run(ssh, f'mkdir -p {remote_parent}', check=False)
            sftp.put(str(item), remote_path)


print('🔌  Conectando na VPS...')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VPS_IP, username=VPS_USER, password=VPS_PASSWORD, timeout=30)
sftp = ssh.open_sftp()
print('✅  Conectado!\n')

# ── 1. Instalar Node.js 20 (se ausente) ──────────────────────────────────
print('📦  Verificando Node.js...')
node_ver = run(ssh, 'node --version 2>/dev/null || echo missing')
if 'missing' in node_ver or not node_ver.startswith('v2'):
    print('   Instalando Node.js 20 via NodeSource...')
    run(ssh, 'curl -fsSL https://deb.nodesource.com/setup_20.x | bash -')
    run(ssh, 'apt-get install -y nodejs')
    print('   ✅  Node.js instalado:', run(ssh, 'node --version'))
else:
    print('   ✅  Node.js já ok:', node_ver)

# ── 2. Instalar PM2 (se ausente) ─────────────────────────────────────────
print('\n📦  Verificando PM2...')
pm2_ver = run(ssh, 'pm2 --version 2>/dev/null || echo missing')
if 'missing' in pm2_ver:
    run(ssh, 'npm install -g pm2')
    run(ssh, 'pm2 startup systemd -u root --hp /root | tail -1 | bash')
    print('   ✅  PM2 instalado')
else:
    print('   ✅  PM2 já ok:', pm2_ver)

# ── 3. Criar diretório na VPS ─────────────────────────────────────────────
print(f'\n📁  Criando {REMOTE_DIR}...')
run(ssh, f'mkdir -p {REMOTE_DIR}/data')

# ── 4. Enviar arquivos do build standalone ────────────────────────────────
print('\n📤  Enviando build standalone...')
print('   Limpando versão anterior...')
run(ssh, f'rm -rf {REMOTE_DIR}/.next {REMOTE_DIR}/server.js {REMOTE_DIR}/package.json {REMOTE_DIR}/node_modules')

print('   Enviando .next/standalone → {REMOTE_DIR}...')
sftp_put_dir(sftp, ssh, BUILD_DIR, REMOTE_DIR)

print('   Enviando .next/static → {REMOTE_DIR}/.next/static...')
run(ssh, f'mkdir -p {REMOTE_DIR}/.next/static')
sftp_put_dir(sftp, ssh, STATIC_DIR, f'{REMOTE_DIR}/.next/static')

print('   Enviando public/...')
run(ssh, f'mkdir -p {REMOTE_DIR}/public')
sftp_put_dir(sftp, ssh, PUBLIC_DIR, f'{REMOTE_DIR}/public')

print('   Enviando prisma/...')
run(ssh, f'mkdir -p {REMOTE_DIR}/prisma')
sftp_put_dir(sftp, ssh, PRISMA_DIR, f'{REMOTE_DIR}/prisma')

# ── 5. Criar .env na VPS ─────────────────────────────────────────────────
print('\n⚙️   Criando .env...')
env_content = f"""DATABASE_URL="file:{REMOTE_DIR}/data/prod.db"
ADMIN_PASSWORD="{ADMIN_PASS}"
PORT={APP_PORT}
HOSTNAME="0.0.0.0"
"""
sftp.open(f'{REMOTE_DIR}/.env', 'w').write(env_content)

# ── 6. Instalar prisma cli e rodar migração ───────────────────────────────
print('\n🗄️   Rodando migrações do banco...')
# Copiar prisma.config.ts e package.json para o standalone reconhecer
pftp = sftp.open(f'{REMOTE_DIR}/prisma.config.ts', 'w')
pftp.write(f"""import "dotenv/config";
import {{ defineConfig }} from "prisma/config";
export default defineConfig({{
  schema: "prisma/schema.prisma",
  migrations: {{ path: "prisma/migrations" }},
  datasource: {{ url: process.env["DATABASE_URL"] }},
}});
""")
pftp.close()

run(ssh, f'cd {REMOTE_DIR} && npm install prisma dotenv @prisma/adapter-better-sqlite3 better-sqlite3 2>&1 | tail -3')
run(ssh, f'cd {REMOTE_DIR} && npx prisma migrate deploy 2>&1')
print('   ✅  Banco migrado')

# ── 7. Configurar e (re)iniciar PM2 ──────────────────────────────────────
print('\n🚀  Configurando PM2...')
ecosystem = f"""module.exports = {{
  apps: [{{
    name: 'veted',
    script: '{REMOTE_DIR}/server.js',
    cwd: '{REMOTE_DIR}',
    env: {{
      NODE_ENV: 'production',
      PORT: {APP_PORT},
      HOSTNAME: '0.0.0.0',
    }},
  }}],
}};
"""
sftp.open(f'{REMOTE_DIR}/ecosystem.config.js', 'w').write(ecosystem)

run(ssh, f'pm2 delete veted 2>/dev/null || true')
run(ssh, f'pm2 start {REMOTE_DIR}/ecosystem.config.js')
run(ssh, 'pm2 save')
time.sleep(3)
status = run(ssh, 'pm2 list | grep veted')
print('   PM2 status:', status)

# ── 8. Configurar Nginx ───────────────────────────────────────────────────
print('\n🌐  Configurando Nginx para veted.online...')
nginx_conf = f"""server {{
    listen 80;
    server_name {DOMAIN} www.{DOMAIN};

    location / {{
        proxy_pass         http://127.0.0.1:{APP_PORT};
        proxy_http_version 1.1;
        proxy_set_header   Upgrade $http_upgrade;
        proxy_set_header   Connection 'upgrade';
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_cache_bypass $http_upgrade;
    }}
}}
"""
sftp.open('/etc/nginx/sites-available/veted', 'w').write(nginx_conf)
run(ssh, 'ln -sf /etc/nginx/sites-available/veted /etc/nginx/sites-enabled/veted')
run(ssh, 'nginx -t')
run(ssh, 'systemctl reload nginx')
print('   ✅  Nginx configurado')

# ── 9. Verificar que sistema-van ainda está ok ────────────────────────────
print('\n🔍  Verificando sistema-van (não deve ter sido afetado)...')
van_status = run(ssh, 'systemctl is-active sistema-van')
print('   sistema-van status:', van_status)

# ── 10. SSL com Certbot ──────────────────────────────────────────────────
print('\n🔒  Configurando SSL (certbot)...')
certbot_check = run(ssh, 'certbot --version 2>/dev/null || echo missing')
if 'missing' in certbot_check:
    run(ssh, 'apt-get install -y certbot python3-certbot-nginx')

ssl_result = run(ssh, f'certbot --nginx -d {DOMAIN} -d www.{DOMAIN} --non-interactive --agree-tos -m admin@{DOMAIN} 2>&1')
print('   Certbot:', ssl_result[:200])

sftp.close()
ssh.close()

print('\n' + '='*50)
print(f'✅  Deploy concluído!')
print(f'   Site: https://{DOMAIN}')
print(f'   Admin: https://{DOMAIN}/admin  (senha: {ADMIN_PASS})')
print(f'   Balanceador: https://{DOMAIN}/balancer')
print('='*50)
