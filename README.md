# 🎨 BD Studio Bot — Documentação Completa

Bot completo para Discord do BD Studio com sistema de tickets, pagamentos Pix (Mercado Pago), portfólio e integração com Google Sheets.

---

## 📋 Funcionalidades

| Comando | Descrição | Permissão |
|---|---|---|
| `/painel` | Envia o painel de abertura de tickets | Manage Channels |
| `/paineladmin` | Painel admin dentro de um ticket aberto | Staff/Admin |
| `/gerarqrcode` | Gera QR Code Pix via Mercado Pago | Manage Guild |
| `/portfolio` | Envia apresentação do portfólio + link | Todos |
| `/listar @usuario` | Lista compras de um usuário | Manage Guild |

### 🎫 Sistema de Tickets
- Painel com seleção de categoria (Suporte / Compra)
- Modal para preencher assunto e descrição ao abrir
- Canal privado criado automaticamente com permissões
- Botões: **Ticket Assumido**, **Painel Admin**, **Finalizar Ticket**
- Notificação na DM ao finalizar
- Logs de abertura, fechamento e ações

### 💳 Pagamento Pix
- Geração de QR Code via API do Mercado Pago
- Confirmação automática (polling a cada 15s por 30 min)
- Notificação na DM do cliente ao confirmar
- Log no canal de pagamentos
- Registro automático no Google Sheets

### 🔒 Painel Admin (`/paineladmin`)
- ➕ Adicionar Membro ao ticket
- ➖ Remover Membro do ticket
- ✏️ Renomear Canal
- 📬 Notificar Membro na DM
- ✖️ Finalizar Ticket

---

## 🚀 Instalação

### 1. Pré-requisitos
- Python 3.10+
- Conta no [Discord Developer Portal](https://discord.com/developers/applications)
- Conta no [Mercado Pago Developers](https://www.mercadopago.com.br/developers)

### 2. Clone / Baixe os arquivos
Coloque todos os arquivos em uma pasta.

### 3. Instale as dependências
```bash
pip install -r requirements.txt
```

### 4. Configure o `.env`
Renomeie `.env.example` para `.env` e preencha:
```
DISCORD_TOKEN=seu_token_do_bot
GUILD_ID=id_do_seu_servidor
```

### 5. Configure o `config.py`
Abra `config.py` e preencha **todos** os IDs:

```python
GUILD_ID = 123456789          # ID do servidor
CATEGORY_TICKETS_ID = 123     # ID da categoria de tickets
LOG_CHANNEL_ID = 456          # Canal de logs de tickets
LOG_PAGAMENTOS_ID = 789       # Canal de logs de pagamentos
STAFF_ROLE_ID = 111           # Cargo da equipe/staff
ADMIN_ROLE_ID = 222           # Cargo de administrador

MERCADO_PAGO_ACCESS_TOKEN = "APP_USR-..." # Seu token MP

LOGO_URL = "https://link-da-sua-logo.png"
PORTFOLIO_URL = "https://seusite.com"
```

### 6. Configure permissões do bot no Discord
No Developer Portal, em **Bot > Privileged Gateway Intents**, ative:
- ✅ Server Members Intent
- ✅ Message Content Intent

Em **OAuth2 > URL Generator**, selecione os escopos:
- `bot`
- `applications.commands`

Permissões necessárias do bot:
- Manage Channels, Manage Roles
- View Channels, Send Messages, Embed Links
- Attach Files, Read Message History
- Use Slash Commands

### 7. Inicie o bot
```bash
python bot.py
```

---

## 📊 Google Sheets (opcional)

1. Acesse [Google Cloud Console](https://console.cloud.google.com)
2. Crie um projeto e ative as APIs: **Google Sheets** e **Google Drive**
3. Crie uma **Conta de Serviço** e baixe o JSON de credenciais
4. Renomeie o arquivo para `credentials.json` e coloque na raiz do projeto
5. Compartilhe sua planilha com o e-mail da conta de serviço
6. Copie o ID da planilha (da URL) e coloque em `config.py`:
   ```python
   GOOGLE_SPREADSHEET_ID = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms"
   ```

A planilha terá as colunas: **Nome do Cliente | ID Discord | Valor | Produto | Data | ID Pagamento**

---

## 🔑 Como obter o token do Mercado Pago

1. Acesse [developers.mercadopago.com](https://developers.mercadopago.com)
2. Faça login e vá em **Suas integrações > Criar aplicação**
3. Após criar, vá em **Credenciais de produção**
4. Copie o **Access Token** (começa com `APP_USR-`)
5. Cole em `config.py` no campo `MERCADO_PAGO_ACCESS_TOKEN`

> ⚠️ Use credenciais de **teste** durante desenvolvimento!

---

## 📁 Estrutura dos Arquivos

```
bdstudio_bot/
├── bot.py              # Arquivo principal
├── config.py           # Todas as configurações
├── requirements.txt    # Dependências
├── .env                # Tokens (não commitar!)
├── credentials.json    # Google Sheets (não commitar!)
├── data/
│   └── bdstudio.db     # Banco SQLite (criado automaticamente)
├── cogs/
│   ├── tickets.py      # Sistema completo de tickets
│   ├── admin.py        # Comando /listar
│   ├── pagamentos.py   # Pix + QR Code
│   └── portfolio.py    # Portfólio
└── utils/
    ├── db.py           # Banco de dados SQLite
    ├── logger.py       # Logs de tickets e comandos
    └── sheets.py       # Integração Google Sheets
```

---

## ❓ Suporte

Em caso de dúvidas, abra um ticket no servidor do BD Studio!
