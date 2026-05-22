"""
Integração com Google Sheets para registrar pagamentos.

Pré-requisitos:
1. Crie um projeto no Google Cloud Console
2. Ative a API Google Sheets e Google Drive
3. Crie uma conta de serviço e baixe o JSON de credenciais
4. Salve como credentials.json na raiz do projeto
5. Compartilhe a planilha com o e-mail da conta de serviço
6. Defina GOOGLE_SPREADSHEET_ID no config.py
"""

import config

try:
    import gspread
    from google.oauth2.service_account import Credentials
    SHEETS_DISPONIVEL = True
except ImportError:
    SHEETS_DISPONIVEL = False


def _get_worksheet():
    if not SHEETS_DISPONIVEL:
        return None
    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_file(
            config.GOOGLE_SHEETS_CREDENTIALS_FILE, scopes=scopes
        )
        client = gspread.authorize(creds)
        sheet = client.open_by_key(config.GOOGLE_SPREADSHEET_ID)
        # Usar a primeira aba, ou criar "Pagamentos"
        try:
            ws = sheet.worksheet("Pagamentos")
        except gspread.WorksheetNotFound:
            ws = sheet.add_worksheet(title="Pagamentos", rows=1000, cols=6)
            ws.append_row(["Nome do Cliente", "ID Discord", "Valor (R$)", "Produto", "Data", "ID Pagamento"])
        return ws
    except Exception as e:
        print(f"[Sheets] Erro ao conectar: {e}")
        return None


async def registrar_planilha(nome_cliente: str, discord_id: str, valor: float, item: str, data: str, pagamento_id: str = "-"):
    """Registra um pagamento aprovado na planilha Google Sheets."""
    if not SHEETS_DISPONIVEL:
        print("[Sheets] gspread não instalado, pulando registro na planilha.")
        return
    if not config.GOOGLE_SPREADSHEET_ID:
        return
    ws = _get_worksheet()
    if ws is None:
        return
    try:
        ws.append_row([nome_cliente, discord_id, f"R$ {valor:.2f}", item, data, pagamento_id])
        print(f"[Sheets] ✓ Registrado: {nome_cliente} — {item} — R$ {valor:.2f}")
    except Exception as e:
        print(f"[Sheets] Erro ao registrar: {e}")
