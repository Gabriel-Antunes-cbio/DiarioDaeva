# Bot do Discord: timer do Gartua para o grupo

O bot guarda quando o **Eternal Gartua** (e os outros bosses de campo) vai nascer e divide essa informação com todo mundo:

- No Discord, alguém usa `/gartua` quando o boss cai, ou `/gartua falta:3h20` com a contagem do mapa do jogo.
- O bot avisa no canal **5 minutos antes do respawn**, e pode marcar um cargo como `@Bosses`.
- O app de cada amigo busca os horários do bot a cada 30 segundos. O **Morreu agora** e o **Quanto falta…** do app também vão para o bot e aparece no canal.

O bot **não sabe sozinho** que o boss morreu: alguém do grupo precisa marcar. Ele não lê nada do jogo.

## Comandos

| Comando | O que faz |
|---|---|
| `/gartua` | Registra que o Eternal Gartua (lado Elyos) morreu agora: nasce em 12 h |
| `/gartua falta:3h20` | Registra quanto falta para ele nascer, copiando a contagem do mapa do jogo (Exploração → Field Boss) |
| `/morreu boss:<boss> [falta]` | O mesmo para Immortal Gartua, Lagta, Dartan, Kashapa e Danar |
| `/timers` | Mostra todos os respawns registrados |
| `/limpar boss:<boss>` | Apaga um registro errado |
| `/velsta` | Mostra a arte da Velsta no canal |

O tempo aceita `3h20`, `3h 20m`, `3:20`, `2h`, `45m` ou só os minutos (`90`). Informar quanto falta é o jeito mais preciso, porque usa a contagem do próprio jogo.

Os horários aparecem no fuso de cada pessoa, porque o bot usa as marcações de tempo do próprio Discord.

---

## Parte 1: criar o bot no Discord (10 min)

1. Abra o **[Discord Developer Portal](https://discord.com/developers/applications)** → **New Application** → nome: `Diário de Daeva`.
2. No menu **Bot**:
   - Clique em **Reset Token** e copie o token. Esse é o `DISCORD_TOKEN`. **Não mostre para ninguém**; se vazar, é só gerar outro aqui.
   - Nenhuma das opções de *Privileged Gateway Intents* é necessária.
3. No menu **OAuth2 → URL Generator**:
   - Scopes: marque **bot** e **applications.commands**.
   - Bot Permissions: marque **View Channels** e **Send Messages**.
   - Copie a URL gerada no fim da página, abra no navegador e adicione o bot ao seu servidor.
4. Pegue os IDs no Discord. Primeiro ative **Configurações de usuário → Avançado → Modo desenvolvedor**. Depois:
   - Botão direito no **servidor** → **Copiar ID do servidor** → `GUILD_ID`
   - Botão direito no **canal** dos avisos → **Copiar ID do canal** → `CHANNEL_ID`
   - **Quem é avisado:** escolha uma opção no `.env`. Com `ALERT_MENTION=everyone` (todos) ou `ALERT_MENTION=here` (só quem está online), dê ao cargo do bot a permissão **Mencionar @everyone, @here e todos os cargos** no canal dos avisos. Se nem isso nem o `ROLE_ID` estiver preenchido, o aviso aparece no canal sem notificar ninguém.
   - Ou, para marcar só quem quiser: em **Configurações do servidor → Cargos**, crie um cargo `Bosses`, ative **Permitir que qualquer um @mencione este cargo** e copie o ID → `ROLE_ID`. Quem quiser ser avisado pega o cargo.

## Parte 2: VM na Oracle (20 min)

### Criar a VM

1. No console da Oracle: **Compute → Instances → Create instance**.
2. **Image**: Canonical **Ubuntu 24.04**. **Shape**: **VM.Standard.E2.1.Micro** (marcado como *Always Free*).
3. Em **Add SSH keys**, escolha **Generate a key pair** e **baixe a chave privada**. Sem ela você não entra na VM.
4. Crie e anote o **Public IP address**.

### Liberar a porta da API (8080)

A Oracle bloqueia portas em dois lugares, e os dois precisam ser liberados:

1. **No console**: na página da instância, clique na **Subnet** → **Security Lists** → a lista padrão → **Add Ingress Rules**:
   - Source CIDR: `0.0.0.0/0`
   - IP Protocol: TCP
   - Destination Port Range: `8080`
2. **Dentro da VM**, depois de entrar pelo SSH (próximo passo):
   ```bash
   sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8080 -j ACCEPT
   sudo netfilter-persistent save
   ```

### Entrar na VM

No Windows, abra o **Terminal** na pasta onde salvou a chave:

```bash
ssh -i nome-da-chave.key ubuntu@SEU_IP
```

Se reclamar das permissões da chave, mova o arquivo para `C:\Users\<você>\.ssh\`.

### Instalar o bot

```bash
sudo apt update && sudo apt install -y python3-venv git
git clone https://github.com/Gabriel-Antunes-cbio/DiarioDaeva.git ~/DiarioDaeva
cd ~/DiarioDaeva
python3 -m venv .venv
.venv/bin/pip install -r bot/requirements.txt
cp bot/.env.example bot/.env
python3 -c "import secrets; print(secrets.token_urlsafe(24))"   # gera a chave do grupo
nano bot/.env
```

No `nano`, preencha `DISCORD_TOKEN`, `GUILD_ID`, `CHANNEL_ID`, `ROLE_ID` (opcional) e `GROUP_KEY` (a chave gerada acima). Salve com **Ctrl+O**, **Enter**, **Ctrl+X**.

### Testar

```bash
.venv/bin/python -m bot.daeva_bot
```

Deve aparecer `Conectado como Diário de Daeva#...` e `API do app ouvindo na porta 8080`. No Discord, teste `/timers`. Depois pare com **Ctrl+C**.

### Deixar ligado para sempre

```bash
sudo cp bot/daeva-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now daeva-bot
sudo systemctl status daeva-bot          # deve mostrar "active (running)"
```

Com isso, o bot volta sozinho se cair ou se a VM reiniciar. Para ver o que ele está fazendo: `journalctl -u daeva-bot -f`.

### Atualizar o bot depois

```bash
cd ~/DiarioDaeva && git pull && sudo systemctl restart daeva-bot
```

## Parte 3: ligar o app dos amigos

Mande para cada amigo, **por mensagem privada** e não no canal aberto:

- o endereço: `http://SEU_IP:8080`
- a chave do grupo (`GROUP_KEY`)

No app: **Ajustes → Grupo (bot do Discord)**, cole os dois, escreva o nome que vai aparecer nas marcações e clique em **Testar conexão**. Na aba **Bosses**, a linha verde "Sincronizado com o bot do grupo" confirma que está funcionando.

---

## Segurança e cuidados

| Ponto | Detalhe |
|---|---|
| Token do Discord | Fica só no `bot/.env` da VM, que **não vai para o GitHub**. Se vazar: Developer Portal → Bot → Reset Token. |
| Chave do grupo | Só quem tem a chave lê e marca horários. Para trocar, mude o `GROUP_KEY`, reinicie o bot e passe a nova chave aos amigos. |
| Conexão sem HTTPS | A chave e os horários trafegam sem criptografia. Para horários de boss isso é aceitável, mas **não use como chave uma senha que você usa em outro lugar**. |
| Backup | Os registros ficam em `~/DiarioDaeva/bot/dados/mortes.json`. |
| VM ociosa | No plano só gratuito, a Oracle pode recolher VMs com pouco uso. Fazer upgrade para Pay As You Go, com um alerta de orçamento, evita isso sem custo dentro dos limites gratuitos. |
