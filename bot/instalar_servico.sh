#!/usr/bin/env bash
# Instala o bot como serviço do systemd: liga junto com a VM e reinicia sozinho se cair.
# Uso (na pasta do repositório):  bash bot/instalar_servico.sh
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
PY="$REPO/.venv/bin/python"

if [ ! -x "$PY" ]; then
  echo "Não achei $PY. Crie o ambiente antes:  python3 -m venv .venv && .venv/bin/pip install -r bot/requirements.txt"
  exit 1
fi
if [ ! -f "$REPO/bot/.env" ]; then
  echo "Não achei bot/.env. Crie com:  cp bot/.env.example bot/.env && nano bot/.env"
  exit 1
fi

sudo tee /etc/systemd/system/daeva-bot.service >/dev/null <<EOF
[Unit]
Description=Bot do Discord do Diario de Daeva
After=network-online.target
Wants=network-online.target

[Service]
User=$USER
WorkingDirectory=$REPO
ExecStart=$PY -m bot.daeva_bot
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now daeva-bot
sleep 3
sudo systemctl --no-pager status daeva-bot | head -n 5
echo
echo "Pronto. Para ver o que o bot está fazendo:  journalctl -u daeva-bot -f"
