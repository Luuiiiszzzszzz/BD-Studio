import discord
from discord.ext import commands
from discord import app_commands
import config
from utils.logger import log_comando


class PortfolioCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="portfolio", description="Apresenta o portfólio do BD Studio.")
    async def portfolio(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎨 BD Studio — Portfólio",
            description=config.PORTFOLIO_DESCRICAO,
            color=config.COR_PRINCIPAL,
        )
        embed.set_thumbnail(url=config.LOGO_URL)
        embed.timestamp = discord.utils.utcnow()
        embed.set_footer(text="BD Studio • Criações de Alto Nível")

        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label="🌐 Ver Portfólio Completo",
                url=config.PORTFOLIO_URL,
                style=discord.ButtonStyle.link,
            )
        )
        view.add_item(
            discord.ui.Button(
                label="🎫 Abrir Ticket",
                style=discord.ButtonStyle.primary,
                custom_id="btn_abrir_ticket_portfolio",
                emoji="📩",
            )
        )

        await interaction.response.send_message(embed=embed, view=view)
        await log_comando(interaction.guild, interaction.user, "/portfolio", "-")

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.component:
            if interaction.data.get("custom_id") == "btn_abrir_ticket_portfolio":
                from cogs.tickets import SelectCategoria, ViewPainel
                embed = discord.Embed(
                    title="🎫 Abrir Ticket",
                    description="Selecione a categoria de atendimento abaixo:",
                    color=config.COR_PRINCIPAL,
                )
                view = ViewPainel()
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
