import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.dm_messages = True

class BDStudioBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        from cogs.tickets import TicketCog, ViewPainel, ViewTicketAberto
        from cogs.admin import AdminCog
        from cogs.pagamentos import PagamentoCog
        from cogs.portfolio import PortfolioCog

        await self.add_cog(TicketCog(self))
        await self.add_cog(AdminCog(self))
        await self.add_cog(PagamentoCog(self))
        await self.add_cog(PortfolioCog(self))

        # Registrar views persistentes para funcionar após restart
        self.add_view(ViewPainel())
        self.add_view(ViewTicketAberto(ticket_id="persistent", canal_id=0))

        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        synced = await self.tree.sync(guild=guild)
        print(f"[✓] {len(synced)} comandos sincronizados na guild.")

    async def on_ready(self):
        print(f"[✓] Bot online como {self.user} ({self.user.id})")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="BD Studio | Tickets"
            )
        )

bot = BDStudioBot()

if __name__ == "__main__":
    bot.run(TOKEN)
