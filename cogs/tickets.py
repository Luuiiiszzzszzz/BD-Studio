import discord
from discord.ext import commands
from discord import app_commands
import random
import string
import datetime
import config
from utils.logger import log_ticket, log_comando
from utils.db import Database

db = Database()

def gerar_id_ticket():
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=6))

# ──────────────────────────────────────────────
#  MODAL: detalhes do ticket
# ──────────────────────────────────────────────
class ModalDetalhesTicket(discord.ui.Modal):
    def __init__(self, categoria: str):
        titulo = "Suporte - BD Studio" if categoria == "suporte" else "Compra - BD Studio"
        super().__init__(title=titulo)
        self.categoria = categoria

        self.assunto = discord.ui.TextInput(
            label="Assunto do Ticket",
            placeholder="Ex: Dúvida sobre pedido, problema com entrega...",
            max_length=100,
            required=True,
        )
        self.descricao = discord.ui.TextInput(
            label="Descreva em detalhes",
            placeholder="Explique o máximo de detalhes possível para agilizar o atendimento.",
            style=discord.TextStyle.paragraph,
            max_length=1000,
            required=True,
        )
        self.add_item(self.assunto)
        self.add_item(self.descricao)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        user = interaction.user
        ticket_id = gerar_id_ticket()
        categoria_nome = "Suporte" if self.categoria == "suporte" else "Compra"
        prefix = config.TICKET_PREFIX_SUPORTE if self.categoria == "suporte" else config.TICKET_PREFIX_COMPRA

        # Buscar categoria de tickets
        category = guild.get_channel(config.CATEGORY_TICKETS_ID)

        # Permissões do canal
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True
            ),
        }
        staff_role = guild.get_role(config.STAFF_ROLE_ID)
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True, manage_channels=True
            )

        canal = await guild.create_text_channel(
            name=f"{prefix}-{user.name}",
            category=category,
            overwrites=overwrites,
            reason=f"Ticket {ticket_id} aberto por {user}",
        )

        # Salvar no banco
        db.criar_ticket(ticket_id, user.id, canal.id, categoria_nome, str(self.assunto))

        # ── Embed do ticket ──
        embed = discord.Embed(color=config.COR_PRINCIPAL)
        embed.set_author(name="ATENDIMENTO BD STUDIO", icon_url=config.LOGO_URL)
        embed.description = (
            f"Olá {user.mention}, seja bem-vindo ao seu ticket.\n"
            "Aqui você poderá falar diretamente com a nossa equipe, a equipe já está "
            "ciente de sua abertura e irá esclarecer suas dúvidas o mais rápido possível.\n"
            "Basta aguardar e já será atendido."
        )
        embed.add_field(
            name="🗂️ Categoria do Atendimento:",
            value=f"{'🟡' if self.categoria == 'compra' else '🔴'} {categoria_nome}",
            inline=False,
        )
        embed.add_field(name="🎫 ID do Ticket:", value=f"`{ticket_id}`", inline=False)
        embed.add_field(name="📋 Assunto do Ticket:", value=f"`{str(self.assunto)}`", inline=False)
        embed.add_field(
            name="📝 Descrição:",
            value=str(self.descricao) or "Sem descrição.",
            inline=False,
        )
        embed.set_thumbnail(url=config.LOGO_URL)
        embed.timestamp = discord.utils.utcnow()

        view = ViewTicketAberto(ticket_id=ticket_id, canal_id=canal.id)
        await canal.send(
            content=f"{user.mention}" + (f" {staff_role.mention}" if staff_role else ""),
            embed=embed,
            view=view,
        )

        await log_ticket(
            guild=guild,
            acao="🟢 Ticket Aberto",
            user=user,
            ticket_id=ticket_id,
            canal=canal,
            categoria=categoria_nome,
            assunto=str(self.assunto),
            cor=config.COR_SUCESSO,
        )

        await interaction.followup.send(
            f"✅ Ticket criado com sucesso! {canal.mention}", ephemeral=True
        )


# ──────────────────────────────────────────────
#  SELECT: escolha de categoria
# ──────────────────────────────────────────────
class SelectCategoria(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Suporte",
                description="Ticket para suporte.",
                emoji="🎫",
                value="suporte",
            ),
            discord.SelectOption(
                label="Compras",
                description="Ticket para compras.",
                emoji="🛒",
                value="compra",
            ),
        ]
        super().__init__(
            placeholder="📋 Selecione a categoria de atendimento.",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        # Verificar se já tem ticket aberto
        ticket = db.buscar_ticket_aberto_por_usuario(interaction.user.id)
        if ticket:
            canal = interaction.guild.get_channel(ticket["canal_id"])
            if canal:
                await interaction.response.send_message(
                    f"❌ Você já possui um ticket aberto: {canal.mention}", ephemeral=True
                )
                return
        await interaction.response.send_modal(ModalDetalhesTicket(categoria=self.values[0]))


class ViewPainel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(SelectCategoria())


# ──────────────────────────────────────────────
#  VIEW: botões dentro do ticket
# ──────────────────────────────────────────────
class ViewTicketAberto(discord.ui.View):
    def __init__(self, ticket_id: str, canal_id: int):
        super().__init__(timeout=None)
        self.ticket_id = ticket_id
        self.canal_id = canal_id

    @discord.ui.button(label="Ticket Assumido", style=discord.ButtonStyle.success, emoji="✅", custom_id="btn_assumir")
    async def assumir(self, interaction: discord.Interaction, button: discord.ui.Button):
        staff_role = interaction.guild.get_role(config.STAFF_ROLE_ID)
        if staff_role not in interaction.user.roles:
            await interaction.response.send_message("❌ Apenas staff pode assumir tickets.", ephemeral=True)
            return

        db.assumir_ticket(self.ticket_id, interaction.user.id)
        embed = discord.Embed(
            description=f"✅ Ticket assumido por {interaction.user.mention}",
            color=config.COR_SUCESSO,
        )
        await interaction.response.send_message(embed=embed)
        await log_comando(interaction.guild, interaction.user, "Assumir Ticket", self.ticket_id)

    @discord.ui.button(label="Painel Admin", style=discord.ButtonStyle.primary, emoji="🔒", custom_id="btn_painel_admin")
    async def painel_admin(self, interaction: discord.Interaction, button: discord.ui.Button):
        staff_role = interaction.guild.get_role(config.STAFF_ROLE_ID)
        admin_role = interaction.guild.get_role(config.ADMIN_ROLE_ID)
        if staff_role not in interaction.user.roles and admin_role not in interaction.user.roles:
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
            return
        view = ViewPainelAdmin(ticket_id=self.ticket_id, canal_id=self.canal_id)
        embed = discord.Embed(title="🔒 Painel Admin", description="Selecione uma ação:", color=config.COR_INFO)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="Finalizar Ticket", style=discord.ButtonStyle.danger, emoji="✖️", custom_id="btn_finalizar")
    async def finalizar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await finalizar_ticket(interaction, self.ticket_id)


# ──────────────────────────────────────────────
#  VIEW: Painel Admin
# ──────────────────────────────────────────────
class ModalAdicionarMembro(discord.ui.Modal, title="Adicionar Membro"):
    user_id = discord.ui.TextInput(label="ID do usuário", placeholder="123456789012345678")

    def __init__(self, canal_id):
        super().__init__()
        self.canal_id = canal_id

    async def on_submit(self, interaction: discord.Interaction):
        try:
            membro = await interaction.guild.fetch_member(int(str(self.user_id)))
            canal = interaction.guild.get_channel(self.canal_id)
            await canal.set_permissions(membro, view_channel=True, send_messages=True, read_message_history=True)
            await interaction.response.send_message(f"✅ {membro.mention} adicionado ao ticket.", ephemeral=True)
            await canal.send(f"➕ {membro.mention} foi adicionado ao ticket por {interaction.user.mention}.")
            await log_comando(interaction.guild, interaction.user, "Adicionar Membro", str(self.canal_id), extra=str(membro))
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {e}", ephemeral=True)


class ModalRemoverMembro(discord.ui.Modal, title="Remover Membro"):
    user_id = discord.ui.TextInput(label="ID do usuário", placeholder="123456789012345678")

    def __init__(self, canal_id):
        super().__init__()
        self.canal_id = canal_id

    async def on_submit(self, interaction: discord.Interaction):
        try:
            membro = await interaction.guild.fetch_member(int(str(self.user_id)))
            canal = interaction.guild.get_channel(self.canal_id)
            await canal.set_permissions(membro, overwrite=None)
            await interaction.response.send_message(f"✅ {membro.mention} removido do ticket.", ephemeral=True)
            await canal.send(f"➖ {membro.mention} foi removido do ticket por {interaction.user.mention}.")
            await log_comando(interaction.guild, interaction.user, "Remover Membro", str(self.canal_id), extra=str(membro))
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {e}", ephemeral=True)


class ModalRenomearCanal(discord.ui.Modal, title="Renomear Canal"):
    novo_nome = discord.ui.TextInput(label="Novo nome do canal", placeholder="novo-nome")

    def __init__(self, canal_id):
        super().__init__()
        self.canal_id = canal_id

    async def on_submit(self, interaction: discord.Interaction):
        try:
            canal = interaction.guild.get_channel(self.canal_id)
            nome_antigo = canal.name
            await canal.edit(name=str(self.novo_nome))
            await interaction.response.send_message(f"✅ Canal renomeado para `{self.novo_nome}`.", ephemeral=True)
            await log_comando(interaction.guild, interaction.user, "Renomear Canal", str(self.canal_id), extra=f"{nome_antigo} → {self.novo_nome}")
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {e}", ephemeral=True)


class ModalNotificarMembro(discord.ui.Modal, title="Notificar Membro na DM"):
    user_id = discord.ui.TextInput(label="ID do usuário", placeholder="123456789012345678")
    mensagem = discord.ui.TextInput(
        label="Mensagem", style=discord.TextStyle.paragraph,
        placeholder="Digite a mensagem para enviar na DM do membro...", max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            membro = await interaction.guild.fetch_member(int(str(self.user_id)))
            embed = discord.Embed(
                title="📬 Mensagem do BD Studio",
                description=str(self.mensagem),
                color=config.COR_PRINCIPAL,
            )
            embed.set_footer(text=f"Enviado por {interaction.user} • BD Studio")
            embed.set_thumbnail(url=config.LOGO_URL)
            await membro.send(embed=embed)
            await interaction.response.send_message(f"✅ DM enviada para {membro.mention}.", ephemeral=True)
            await log_comando(interaction.guild, interaction.user, "Notificar DM", "-", extra=str(membro))
        except discord.Forbidden:
            await interaction.response.send_message("❌ Não foi possível enviar DM (usuário com DM fechada).", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {e}", ephemeral=True)


class ViewPainelAdmin(discord.ui.View):
    def __init__(self, ticket_id: str, canal_id: int):
        super().__init__(timeout=120)
        self.ticket_id = ticket_id
        self.canal_id = canal_id

    @discord.ui.button(label="Adicionar Membro", style=discord.ButtonStyle.success, emoji="➕", row=0)
    async def adicionar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalAdicionarMembro(self.canal_id))

    @discord.ui.button(label="Remover Membro", style=discord.ButtonStyle.danger, emoji="➖", row=0)
    async def remover(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalRemoverMembro(self.canal_id))

    @discord.ui.button(label="Renomear Canal", style=discord.ButtonStyle.secondary, emoji="✏️", row=0)
    async def renomear(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalRenomearCanal(self.canal_id))

    @discord.ui.button(label="Notificar na DM", style=discord.ButtonStyle.primary, emoji="📬", row=1)
    async def notificar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalNotificarMembro())

    @discord.ui.button(label="Finalizar Ticket", style=discord.ButtonStyle.danger, emoji="✖️", row=1)
    async def finalizar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await finalizar_ticket(interaction, self.ticket_id)


# ──────────────────────────────────────────────
#  HELPER: finalizar ticket
# ──────────────────────────────────────────────
async def finalizar_ticket(interaction: discord.Interaction, ticket_id: str):
    staff_role = interaction.guild.get_role(config.STAFF_ROLE_ID)
    admin_role = interaction.guild.get_role(config.ADMIN_ROLE_ID)
    is_staff = staff_role in interaction.user.roles or admin_role in interaction.user.roles

    ticket = db.buscar_ticket(ticket_id)
    if ticket:
        dono = interaction.guild.get_member(ticket["user_id"])
        if dono and not is_staff and interaction.user.id != dono.id:
            await interaction.response.send_message("❌ Sem permissão para finalizar este ticket.", ephemeral=True)
            return

    embed = discord.Embed(
        title="✖️ Ticket Finalizado",
        description=f"Ticket finalizado por {interaction.user.mention}.\nO canal será deletado em **5 segundos**.",
        color=config.COR_ERRO,
    )
    await interaction.response.send_message(embed=embed)

    # Notificar dono na DM
    if ticket:
        dono = interaction.guild.get_member(ticket["user_id"])
        if dono:
            try:
                dm_embed = discord.Embed(
                    title="🎫 Seu Ticket foi Finalizado",
                    description=(
                        f"**Servidor:** {interaction.guild.name}\n"
                        f"**ID do Ticket:** `{ticket_id}`\n"
                        f"**Finalizado por:** {interaction.user}\n\n"
                        "Obrigado por entrar em contato com o **BD Studio**! 💜"
                    ),
                    color=config.COR_PRINCIPAL,
                )
                dm_embed.set_thumbnail(url=config.LOGO_URL)
                dm_embed.timestamp = discord.utils.utcnow()
                await dono.send(embed=dm_embed)
            except discord.Forbidden:
                pass

    db.fechar_ticket(ticket_id)
    await log_ticket(
        guild=interaction.guild,
        acao="🔴 Ticket Finalizado",
        user=interaction.user,
        ticket_id=ticket_id,
        canal=interaction.channel,
        categoria=ticket["categoria"] if ticket else "?",
        assunto=ticket["assunto"] if ticket else "?",
        cor=config.COR_ERRO,
    )
    await log_comando(interaction.guild, interaction.user, "Finalizar Ticket", ticket_id)

    import asyncio
    await asyncio.sleep(5)
    try:
        await interaction.channel.delete(reason=f"Ticket {ticket_id} finalizado.")
    except Exception:
        pass


# ──────────────────────────────────────────────
#  COG
# ──────────────────────────────────────────────
class TicketCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="painel", description="Envia o painel de abertura de tickets.")
    @app_commands.default_permissions(manage_channels=True)
    async def painel(self, interaction: discord.Interaction):
        embed = discord.Embed(color=config.COR_PRINCIPAL)
        embed.set_author(name="ATENDIMENTO BD STUDIO", icon_url=config.LOGO_URL)
        embed.description = (
            "Seja bem-vindo ao sistema de atendimento **BD Studio**, use o menu abaixo para abrir um "
            "ticket e aguarde para ser atendido."
        )
        embed.add_field(
            name="\u200b",
            value=(
                "**Não abra um ticket sem necessidade.**\n"
                "**Não marque excessivamente a equipe.**\n"
                "**Agilize o atendimento fornecendo o máximo de informações possíveis.**"
            ),
            inline=False,
        )
        embed.set_thumbnail(url=config.LOGO_URL)
        view = ViewPainel()
        await interaction.response.send_message(embed=embed, view=view)
        await log_comando(interaction.guild, interaction.user, "/painel", "-")

    @app_commands.command(name="paineladmin", description="Painel de administração de tickets.")
    @app_commands.default_permissions(manage_channels=True)
    async def paineladmin(self, interaction: discord.Interaction):
        # Tenta detectar ticket_id pelo banco usando o canal atual
        ticket = db.buscar_ticket_por_canal(interaction.channel_id)
        if not ticket:
            await interaction.response.send_message(
                "❌ Este canal não é um ticket registrado. Use este comando dentro de um ticket.",
                ephemeral=True,
            )
            return

        view = ViewPainelAdmin(ticket_id=ticket["ticket_id"], canal_id=interaction.channel_id)
        embed = discord.Embed(
            title="🔒 Painel Admin — BD Studio",
            description="Selecione uma ação para gerenciar este ticket:",
            color=config.COR_INFO,
        )
        embed.add_field(name="🎫 Ticket ID", value=f"`{ticket['ticket_id']}`", inline=True)
        embed.add_field(name="🗂️ Categoria", value=ticket["categoria"], inline=True)
        embed.add_field(name="📋 Assunto", value=ticket["assunto"], inline=False)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        await log_comando(interaction.guild, interaction.user, "/paineladmin", ticket["ticket_id"])
