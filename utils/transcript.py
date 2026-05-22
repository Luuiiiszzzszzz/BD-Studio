import discord
import datetime
import os
import base64
import aiohttp

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")
GITHUB_PAGES_URL = f"https://{GITHUB_REPO.split('/')[0].lower()}.github.io/{GITHUB_REPO.split('/')[1]}" if GITHUB_REPO else ""

async def upload_para_github(ticket_id: str, html: str) -> str:
    """Faz upload do HTML para o GitHub e retorna a URL do GitHub Pages."""
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return ""

    caminho = f"transcripts/transcript-{ticket_id}.html"
    url_api = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{caminho}"
    conteudo_b64 = base64.b64encode(html.encode("utf-8")).decode("utf-8")

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    payload = {
        "message": f"transcript: {ticket_id}",
        "content": conteudo_b64,
    }

    async with aiohttp.ClientSession() as session:
        async with session.put(url_api, json=payload, headers=headers) as resp:
            if resp.status in [200, 201]:
                return f"{GITHUB_PAGES_URL}/transcripts/transcript-{ticket_id}.html"
            else:
                text = await resp.text()
                print(f"[Transcript] Erro GitHub API: {resp.status} — {text}")
                return ""


async def gerar_transcript(canal: discord.TextChannel, ticket: dict, guild: discord.Guild):
    """Gera transcript HTML, faz upload no GitHub Pages e retorna (caminho_local, url_pages)."""

    mensagens = []
    async for msg in canal.history(limit=500, oldest_first=True):
        mensagens.append(msg)

    ticket_id = ticket.get("ticket_id", "?")
    categoria = ticket.get("categoria", "?")
    assunto = ticket.get("assunto", "?")
    user_id = ticket.get("user_id")
    staff_id = ticket.get("staff_id")

    dono = guild.get_member(user_id) if user_id else None
    staff = guild.get_member(staff_id) if staff_id else None

    dono_nome = str(dono) if dono else f"ID: {user_id}"
    staff_nome = f"@{staff.display_name}" if staff else "Não assumido"
    data_criacao = datetime.datetime.now().strftime("%d/%m/%Y %I:%M %p")

    msgs_html = ""
    ultimo_autor = None
    ultimo_tempo = None

    for msg in mensagens:
        if not msg.content and not msg.embeds and not msg.attachments:
            continue

        autor = msg.author
        avatar_url = str(autor.display_avatar.url)
        nome = autor.display_name
        is_bot = autor.bot
        tempo = msg.created_at.strftime("%d/%m/%Y %I:%M %p")
        badge = '<span class="badge">BOT</span>' if is_bot else ''

        conteudo = ""
        if msg.content:
            texto = msg.content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            conteudo += f'<div class="msg-text">{texto}</div>'

        for embed in msg.embeds:
            cor = f"#{embed.colour.value:06x}" if embed.colour else "#E91E8C"
            embed_html = f'<div class="embed" style="border-left-color:{cor}">'
            if embed.author and embed.author.name:
                icon = f'<img src="{embed.author.icon_url}" class="embed-author-icon">' if embed.author.icon_url else ''
                embed_html += f'<div class="embed-author">{icon}{embed.author.name}</div>'
            if embed.title:
                embed_html += f'<div class="embed-title">{embed.title}</div>'
            if embed.description:
                desc = embed.description.replace('\n', '<br>')
                embed_html += f'<div class="embed-desc">{desc}</div>'
            for field in embed.fields:
                embed_html += f'<div class="embed-field"><div class="embed-field-name">{field.name}</div><div class="embed-field-value">{field.value}</div></div>'
            if embed.thumbnail and embed.thumbnail.url:
                embed_html += f'<img src="{embed.thumbnail.url}" class="embed-thumb">'
            if embed.footer and embed.footer.text:
                embed_html += f'<div class="embed-footer">{embed.footer.text}</div>'
            embed_html += '</div>'
            conteudo += embed_html

        for att in msg.attachments:
            if any(att.filename.lower().endswith(ext) for ext in ['.png','.jpg','.jpeg','.gif','.webp']):
                conteudo += f'<img src="{att.url}" class="attachment-img">'
            else:
                conteudo += f'<a href="{att.url}" class="attachment-file">📎 {att.filename}</a>'

        mesmo_autor = (ultimo_autor == autor.id and ultimo_tempo and
                       (msg.created_at - ultimo_tempo).seconds < 420)

        if mesmo_autor:
            msgs_html += f'<div class="msg-continuation">{conteudo}</div>'
        else:
            msgs_html += f'''
            <div class="message">
                <img src="{avatar_url}" class="avatar" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
                <div class="msg-body">
                    <div class="msg-header">
                        <span class="username">{nome}</span>{badge}
                        <span class="timestamp">{tempo}</span>
                    </div>
                    {conteudo}
                </div>
            </div>'''

        ultimo_autor = autor.id
        ultimo_tempo = msg.created_at

    html = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Transcript • {canal.name}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ background: #313338; color: #dcddde; font-family: 'gg sans', 'Noto Sans', Whitney, 'Helvetica Neue', Helvetica, Roboto, Arial, sans-serif; font-size: 16px; line-height: 1.375rem; }}
        .header {{ background: #2b2d31; padding: 20px 30px; display: flex; align-items: center; gap: 20px; border-bottom: 2px solid #1e1f22; position: sticky; top: 0; z-index: 10; }}
        .header-logo {{ width: 80px; height: 80px; border-radius: 50%; object-fit: cover; }}
        .header-info h1 {{ color: #ffffff; font-size: 22px; font-weight: 700; }}
        .header-info .channel-name {{ color: #b5bac1; font-size: 14px; margin-top: 2px; }}
        .header-info .channel-desc {{ color: #b5bac1; font-size: 13px; margin-top: 4px; }}
        .ticket-card {{ background: #2b2d31; border-left: 4px solid #E91E8C; margin: 20px 30px; padding: 16px 20px; border-radius: 4px; }}
        .ticket-card .card-title {{ color: #ffffff; font-size: 16px; font-weight: 600; margin-bottom: 10px; }}
        .ticket-card .info-row {{ font-size: 14px; color: #b5bac1; margin: 4px 0; }}
        .ticket-card .info-row span {{ color: #dcddde; font-weight: 500; }}
        .ticket-card .mention {{ color: #7289da; background: rgba(114,137,218,0.1); padding: 0 3px; border-radius: 3px; }}
        .ticket-card .status-closed {{ color: #ed4245; font-weight: 600; }}
        .ticket-card .ticket-id-row {{ margin-top: 10px; font-size: 12px; color: #72767d; }}
        .btn-row {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }}
        .btn {{ padding: 6px 16px; border-radius: 4px; font-size: 14px; font-weight: 500; color: white; border: none; cursor: default; }}
        .btn-red {{ background: #ed4245; }}
        .btn-blue {{ background: #5865f2; }}
        .btn-gray {{ background: #4e5058; }}
        .start-divider {{ padding: 10px 30px 4px; color: #72767d; font-size: 13px; }}
        .messages {{ padding: 10px 30px 40px; }}
        .message {{ display: flex; gap: 16px; padding: 4px 0; margin-top: 16px; }}
        .message:hover, .msg-continuation:hover {{ background: rgba(4,4,5,0.07); border-radius: 4px; }}
        .avatar {{ width: 40px; height: 40px; border-radius: 50%; flex-shrink: 0; margin-top: 2px; object-fit: cover; }}
        .msg-body {{ flex: 1; min-width: 0; }}
        .msg-header {{ display: flex; align-items: baseline; gap: 8px; margin-bottom: 2px; }}
        .username {{ color: #ffffff; font-weight: 600; font-size: 15px; }}
        .badge {{ background: #5865f2; color: white; font-size: 10px; padding: 1px 5px; border-radius: 3px; font-weight: 700; text-transform: uppercase; }}
        .timestamp {{ color: #72767d; font-size: 12px; }}
        .msg-text {{ color: #dcddde; font-size: 15px; white-space: pre-wrap; word-break: break-word; }}
        .msg-continuation {{ padding: 1px 0 1px 56px; }}
        .embed {{ border-left: 4px solid #E91E8C; background: #2b2d31; border-radius: 4px; padding: 12px 16px; margin-top: 6px; max-width: 520px; position: relative; }}
        .embed-author {{ display: flex; align-items: center; gap: 8px; font-size: 13px; font-weight: 600; color: #dcddde; margin-bottom: 6px; }}
        .embed-author-icon {{ width: 20px; height: 20px; border-radius: 50%; }}
        .embed-title {{ color: #ffffff; font-weight: 700; font-size: 15px; margin-bottom: 6px; }}
        .embed-desc {{ color: #dcddde; font-size: 14px; margin-bottom: 8px; line-height: 1.4; }}
        .embed-field {{ margin: 6px 0; }}
        .embed-field-name {{ color: #ffffff; font-weight: 600; font-size: 13px; }}
        .embed-field-value {{ color: #dcddde; font-size: 13px; }}
        .embed-thumb {{ position: absolute; top: 12px; right: 12px; width: 60px; height: 60px; border-radius: 4px; object-fit: cover; }}
        .embed-footer {{ color: #72767d; font-size: 12px; margin-top: 8px; border-top: 1px solid #3f4147; padding-top: 6px; }}
        .attachment-img {{ max-width: 400px; max-height: 300px; border-radius: 4px; margin-top: 6px; display: block; }}
        .attachment-file {{ color: #7289da; font-size: 14px; display: block; margin-top: 4px; }}
        .footer {{ text-align: center; padding: 20px; color: #72767d; font-size: 13px; border-top: 1px solid #1e1f22; }}
    </style>
</head>
<body>
<div class="header">
    <img src="https://cdn.discordapp.com/attachments/1492452836494282783/1492453026135543958/logobdstudiopsdgif.gif" class="header-logo" onerror="this.style.display='none'">
    <div class="header-info">
        <h1>BD Studio</h1>
        <div class="channel-name"># ⚙️ {canal.name}</div>
        <div class="channel-desc">This is the start of # ⚙️ {canal.name} channel.</div>
    </div>
</div>
<div class="ticket-card">
    <div class="card-title">{categoria}</div>
    <div class="info-row">Aberto por: <span class="mention">@{dono_nome}</span></div>
    <div class="info-row">Motivo: <span>{assunto}</span></div>
    <div class="info-row">Status: <span class="status-closed">Fechado</span></div>
    <div class="info-row">Assumido por: <span class="mention">{staff_nome}</span></div>
    <div class="ticket-id-row">ID do Ticket: {ticket_id} • {data_criacao}</div>
    <div class="btn-row">
        <span class="btn btn-red">Fechar Ticket</span>
        <span class="btn btn-blue">Assumir Ticket</span>
        <span class="btn btn-gray">Painel Admin</span>
    </div>
</div>
<div class="start-divider">— Início do transcript —</div>
<div class="messages">{msgs_html}</div>
<div class="footer">BD Studio • Transcript gerado em {data_criacao} • Total de {len(mensagens)} mensagens</div>
</body>
</html>'''

    # Salvar localmente
    os.makedirs("transcripts", exist_ok=True)
    caminho = f"transcripts/transcript-{ticket_id}.html"
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(html)

    # Upload para GitHub Pages
    url_pages = await upload_para_github(ticket_id, html)

    return caminho, url_pages
