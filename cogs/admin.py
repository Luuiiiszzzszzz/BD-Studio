import discord
from discord.ext import commands
from discord import app_commands
import config
from utils.db import Database
from utils.logger import log_comando

db = Database()

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="listar", description="Lista todos os produtos comprados por um usuário.")
    @app_commands.describe(usuario="ID ou menção do usuário")
    @app_commands.default_permissions(manage_guild=True)
    async def listar(self, interaction: discord.Interaction, usuario: discord.Member):
        compras = db.listar_compras(usuario.id)

        embed = discord.Embed(
            title=f"🛒 Histórico de Compras — {usuario.display_name}",
            color=config.COR_PRINCIPAL,
        )
        embed.set_thumbnail(url=usuario.display_avatar.url)
        embed.add_field(name="👤 Usuário", value=f"{usuario.mention}\n`{usuario.id}`", inline=True)
        embed.add_field(name="📦 Total de Compras", value=str(len(compras)), inline=True)

        if not compras:
            embed.description = "❌ Nenhuma compra encontrada para este usuário."
        else:
            total_gasto = sum(c["valor"] for c in compras)
            embed.add_field(name="💰 Total Gasto", value=f"R$ {total_gasto:.2f}", inline=True)
            embed.description = ""
            for i, c in enumerate(compras, 1):
                embed.add_field(
                    name=f"#{i} — {c['item']}",
                    value=(
                        f"💰 Valor: **R$ {c['valor']:.2f}**\n"
                        f"📅 Data: `{c['data']}`\n"
                        f"🆔 ID Pagamento: `{c['pagamento_id']}`"
                    ),
                    inline=False,
                )

        embed.set_footer(text="BD Studio • Sistema de Compras")
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.send_message(embed=embed)
        await log_comando(interaction.guild, interaction.user, "/listar", str(usuario.id))
