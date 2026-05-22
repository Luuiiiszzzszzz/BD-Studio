import discord
import datetime
import os

async def gerar_transcript(canal: discord.TextChannel, ticket: dict, guild: discord.Guild) -> str:
    """Gera um arquivo HTML de transcript no estilo Discord e retorna o caminho."""

    mensagens = []
    async for msg in canal.history(limit=500, oldest_first=True):
        mensagens.append(msg)

    # Info do ticket
    ticket_id = ticket.get("ticket_id", "?")
    categoria = ticket.get("categoria", "?")
    assunto = ticket.get("assunto", "?")
    user_id = ticket.get("user_id")
    staff_id = ticket.get("staff_id")

    dono = guild.get_member(user_id) if user_id else None
    staff = guild.get_member(staff_id) if staff_id else None

    dono_nome = str(dono) if dono else f"ID: {user_id}"
    dono_avatar = str(dono.display_avatar.url) if dono else "https://cdn.discordapp.com/embed/avatars/0.png"
    staff_nome = f"@{staff.display_name}" if staff else "Não assumido"

    data_criacao = datetime.datetime.now().strftime("%d/%m/%Y %I:%M %p")

    # Gerar HTML das mensagens
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

        # Conteúdo
        conteudo = ""
        if msg.content:
            conteudo += f'<div class="msg-text">{discord.utils.escape_mentions(msg.content)}</div>'

        for embed in msg.embeds:
            cor = f"#{embed.colour.value:06x}" if embed.colour else "#E91E8C"
            embed_html = f'<div class="embed" style="border-left-color:{cor}">'
            if embed.author and embed.author.name:
                icon = f'<img src="{embed.author.icon_url}" class="embed-author-icon">' if embed.author.icon_url else ''
                embed_html += f'<div class="embed-author">{icon}{embed.author.name}</div>'
            if embed.title:
                embed_html += f'<div class="embed-title">{embed.title}</div>'
            if embed.description:
                desc = embed.description.replace('\n', '<br>').replace('`', '')
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

        # Agrupar mensagens do mesmo autor
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
        body {{
            background: #313338;
            color: #dcddde;
            font-family: 'gg sans', 'Noto Sans', Whitney, 'Helvetica Neue', Helvetica, Roboto, Arial, sans-serif;
            font-size: 16px;
            line-height: 1.375rem;
        }}

        /* HEADER */
        .header {{
            background: #2b2d31;
            padding: 20px 30px;
            display: flex;
            align-items: center;
            gap: 20px;
            border-bottom: 2px solid #1e1f22;
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        .header-logo {{
            width: 80px;
            height: 80px;
            border-radius: 50%;
            object-fit: cover;
        }}
        .header-info h1 {{
            color: #ffffff;
            font-size: 22px;
            font-weight: 700;
        }}
        .header-info .channel-name {{
            color: #b5bac1;
            font-size: 14px;
            margin-top: 2px;
        }}
        .header-info .channel-desc {{
            color: #b5bac1;
            font-size: 13px;
            margin-top: 4px;
        }}

        /* TICKET INFO CARD */
        .ticket-card {{
            background: #2b2d31;
            border-left: 4px solid #E91E8C;
            margin: 20px 30px;
            padding: 16px 20px;
            border-radius: 4px;
        }}
        .ticket-card .card-title {{
            color: #ffffff;
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 10px;
        }}
        .ticket-card .info-row {{
            font-size: 14px;
            color: #b5bac1;
            margin: 4px 0;
        }}
        .ticket-card .info-row span {{
            color: #dcddde;
            font-weight: 500;
        }}
        .ticket-card .mention {{
            color: #7289da;
            background: rgba(114,137,218,0.1);
            padding: 0 3px;
            border-radius: 3px;
        }}
        .ticket-card .status-open {{
            color: #3ba55c;
            font-weight: 600;
        }}
        .ticket-card .ticket-id-row {{
            margin-top: 10px;
            font-size: 12px;
            color: #72767d;
        }}
        .btn-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 14px;
        }}
        .btn {{
            padding: 6px 16px;
            border-radius: 4px;
            font-size: 14px;
            font-weight: 500;
            color: white;
            border: none;
            cursor: default;
        }}
        .btn-red {{ background: #ed4245; }}
        .btn-blue {{ background: #5865f2; }}
        .btn-gray {{ background: #4e5058; }}

        /* DIVIDER */
        .start-divider {{
            padding: 10px 30px 4px;
            color: #72767d;
            font-size: 13px;
        }}

        /* MESSAGES */
        .messages {{
            padding: 10px 30px 40px;
        }}
        .message {{
            display: flex;
            gap: 16px;
            padding: 4px 0;
            margin-top: 16px;
        }}
        .message:hover, .msg-continuation:hover {{
            background: rgba(4,4,5,0.07);
            border-radius: 4px;
        }}
        .avatar {{
            width: 40px;
            height: 40px;
            border-radius: 50%;
            flex-shrink: 0;
            margin-top: 2px;
            object-fit: cover;
        }}
        .msg-body {{ flex: 1; min-width: 0; }}
        .msg-header {{
            display: flex;
            align-items: baseline;
            gap: 8px;
            margin-bottom: 2px;
        }}
        .username {{
            color: #ffffff;
            font-weight: 600;
            font-size: 15px;
        }}
        .badge {{
            background: #5865f2;
            color: white;
            font-size: 10px;
            padding: 1px 5px;
            border-radius: 3px;
            font-weight: 700;
            text-transform: uppercase;
        }}
        .timestamp {{
            color: #72767d;
            font-size: 12px;
        }}
        .msg-text {{
            color: #dcddde;
            font-size: 15px;
            white-space: pre-wrap;
            word-break: break-word;
        }}
        .msg-continuation {{
            padding: 1px 0 1px 56px;
        }}

        /* EMBEDS */
        .embed {{
            border-left: 4px solid #E91E8C;
            background: #2b2d31;
            border-radius: 4px;
            padding: 12px 16px;
            margin-top: 6px;
            max-width: 520px;
            position: relative;
        }}
        .embed-author {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
            font-weight: 600;
            color: #dcddde;
            margin-bottom: 6px;
        }}
        .embed-author-icon {{
            width: 20px; height: 20px; border-radius: 50%;
        }}
        .embed-title {{
            color: #ffffff;
            font-weight: 700;
            font-size: 15px;
            margin-bottom: 6px;
        }}
        .embed-desc {{
            color: #dcddde;
            font-size: 14px;
            margin-bottom: 8px;
            line-height: 1.4;
        }}
        .embed-field {{ margin: 6px 0; }}
        .embed-field-name {{
            color: #ffffff;
            font-weight: 600;
            font-size: 13px;
        }}
        .embed-field-value {{
            color: #dcddde;
            font-size: 13px;
        }}
        .embed-thumb {{
            position: absolute;
            top: 12px; right: 12px;
            width: 60px; height: 60px;
            border-radius: 4px;
            object-fit: cover;
        }}
        .embed-footer {{
            color: #72767d;
            font-size: 12px;
            margin-top: 8px;
            border-top: 1px solid #3f4147;
            padding-top: 6px;
        }}

        /* ATTACHMENTS */
        .attachment-img {{
            max-width: 400px;
            max-height: 300px;
            border-radius: 4px;
            margin-top: 6px;
            display: block;
        }}
        .attachment-file {{
            color: #7289da;
            font-size: 14px;
            display: block;
            margin-top: 4px;
        }}

        /* FOOTER */
        .footer {{
            text-align: center;
            padding: 20px;
            color: #72767d;
            font-size: 13px;
            border-top: 1px solid #1e1f22;
        }}
    </style>
</head>
<body>

<!-- HEADER -->
<div class="header">
    <img src="https://cdn.discordapp.com/attachments/1492452836494282783/1492453026135543958/logobdstudiopsdgif.gif"
         class="header-logo"
         onerror="this.style.display='none'">
    <div class="header-info">
        <h1>BD Studio</h1>
        <div class="channel-name"># ⚙️ {canal.name}</div>
        <div class="channel-desc">This is the start of # ⚙️ {canal.name} channel.</div>
    </div>
</div>

<!-- TICKET INFO -->
<div class="ticket-card">
    <div class="card-title">{categoria}</div>
    <div class="info-row">Aberto por: <span class="mention">@{dono_nome}</span></div>
    <div class="info-row">Motivo: <span>{assunto}</span></div>
    <div class="info-row">Status: <span class="status-open">Fechado</span></div>
    <div class="info-row">Assumido por: <span class="mention">{staff_nome}</span></div>
    <div class="ticket-id-row">ID do Ticket: {ticket_id} • {data_criacao}</div>
    <div class="btn-row">
        <span class="btn btn-red">Fechar Ticket</span>
        <span class="btn btn-blue">Assumir Ticket</span>
        <span class="btn btn-gray">Painel Admin</span>
    </div>
</div>

<div class="start-divider">— Início do transcript —</div>

<!-- MESSAGES -->
<div class="messages">
    {msgs_html}
</div>

<!-- FOOTER -->
<div class="footer">
    BD Studio • Transcript gerado em {data_criacao} • Total de {len(mensagens)} mensagens
</div>

</body>
</html>'''

    # Salvar arquivo
    os.makedirs("transcripts", exist_ok=True)
    caminho = f"transcripts/transcript-{ticket_id}.html"
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(html)

    return caminho
