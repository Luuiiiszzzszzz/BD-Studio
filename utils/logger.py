import discord
import config
from utils.db import Database

db = Database()


async def log_ticket(guild, acao, user, ticket_id, canal, categoria, assunto, cor):
    log_ch = guild.get_channel(config.LOG_CHANNEL_ID)
    if not log_ch:
        return
    embed = discord.Embed(title=f"📋 Log de Ticket — {acao}", color=cor)
    embed.add_field(name="👤 Usuário", value=f"{user.mention}\n`{user.id}`", inline=True)
    embed.add_field(name="🎫 Ticket ID", value=f"`{ticket_id}`", inline=True)
    embed.add_field(name="📁 Canal", value=canal.mention if canal else "Deletado", inline=True)
    embed.add_field(name="🗂️ Categoria", value=categoria, inline=True)
    embed.add_field(name="📋 Assunto", value=assunto, inline=True)
    embed.set_footer(text=f"BD Studio Logs")
    embed.timestamp = discord.utils.utcnow()
    try:
        await log_ch.send(embed=embed)
    except Exception:
        pass


async def log_comando(guild, user, comando, referencia=None, extra=None):
    """Loga uso de comando tanto no canal quanto no banco."""
    db.salvar_log_comando(
        user_id=user.id,
        username=str(user),
        comando=comando,
        referencia=referencia,
        extra=extra,
    )
    log_ch = guild.get_channel(config.LOG_CHANNEL_ID)
    if not log_ch:
        return
    embed = discord.Embed(
        title="⌨️ Log de Comando",
        color=config.COR_INFO,
    )
    embed.add_field(name="👤 Usuário", value=f"{user.mention}\n`{user.id}`", inline=True)
    embed.add_field(name="📟 Comando", value=f"`{comando}`", inline=True)
    if referencia:
        embed.add_field(name="🔗 Referência", value=f"`{referencia}`", inline=True)
    if extra:
        embed.add_field(name="ℹ️ Detalhe", value=extra, inline=False)
    embed.set_footer(text="BD Studio • Log de Ações")
    embed.timestamp = discord.utils.utcnow()
    try:
        await log_ch.send(embed=embed)
    except Exception:
        pass


async def log_pagamento(guild, gerador, cliente_id, payment_id, item, valor):
    log_ch = guild.get_channel(config.LOG_PAGAMENTOS_ID)
    if not log_ch:
        return
    cliente_str = f"<@{cliente_id}>\n`{cliente_id}`" if cliente_id else "Não informado"
    embed = discord.Embed(
        title="💰 Log de Pagamento — Aprovado",
        color=config.COR_SUCESSO,
    )
    embed.add_field(name="🧑 Gerado por", value=f"{gerador.mention}\n`{gerador.id}`", inline=True)
    embed.add_field(name="👤 Cliente", value=cliente_str, inline=True)
    embed.add_field(name="💳 ID Pagamento", value=f"`{payment_id}`", inline=False)
    embed.add_field(name="🛒 Produto", value=item, inline=True)
    embed.add_field(name="💰 Valor", value=f"**R$ {valor:.2f}**", inline=True)
    embed.set_footer(text="BD Studio • Log de Pagamentos")
    embed.timestamp = discord.utils.utcnow()
    try:
        await log_ch.send(embed=embed)
    except Exception:
        pass
