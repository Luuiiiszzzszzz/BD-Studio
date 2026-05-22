import discord
from discord.ext import commands
from discord import app_commands
import random
import string
import datetime
import config
from utils.logger import log_ticket, log_comando
from utils.transcript import gerar_transcript
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
        titulo = "✦ Suporte — BD Studio" if categoria == "suporte" else "✦ Compra — BD Studio"
        super().__init__(title=titulo)
        self.categoria = categoria

        self.assunto = discord.ui.TextInput(
            label="📌 Assunto do Ticket",
            placeholder="Ex: Dúvida sobre pedido, problema com entrega...",
            max_length=100,
            required=True,
        )
        self.descricao = discord.ui.TextInput(
            label="📝 Descreva em detalhes",
            placeholder="Quanto mais detalhes, mais rápido te atendemos!",
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
        emoji_cat = "🎫" if self.categoria == "suporte" else "🛒"
        cor_cat = 0x9B59B6 if self.categoria == "suporte" else 0xE91E8C

        category = guild.get_channel(config.CATEGORY_TICKETS_ID)

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

        db.criar_ticket(ticket_id, user.id, canal.id, categoria_nome, str(self.assunto))

        # ── Embed principal luxuoso ──
        embed = discord.Embed(color=cor_cat)
        embed.set_author(
            name="✦ ATENDIMENTO BD STUDIO ✦",
            icon_url=config.LOGO_URL
        )
        embed.description = (
            f"Olá {user.mention}, seja bem-vindo ao seu ticket! 👋\n"
            f"Nossa equipe já foi notificada e irá atendê-lo em breve.\n\u200b"
        )
        embed.add_field(
            name="🗂️ Categoria",
            value=f"{emoji_cat} **{categoria_nome}**",
            inline=True,
        )
        embed.add_field(
            name="🎫 ID do Ticket",
            value=f"`{ticket_id}`",
            inline=True,
        )
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        embed.add_field(
            name="📌 Assunto",
            value=f"> {str(self.assunto)}",
            inline=False,
        )
        embed.add_field(
            name="📝 Descrição",
            value=f"> {str(self.descricao)}",
            inline=False,
        )
        embed.add_field(
            name="\u200b",
            value="> ⏳ Aguarde — um membro da equipe irá assumir em breve.",
            inline=False,
        )
        embed.set_thumbnail(url=config.LOGO_URL)
        embed.set_footer(
            text=f"BD Studio • {datetime.datetime.now().strftime('%d/%m/%Y às %H:%M')}",
            icon_url=config.LOGO_URL
        )

        view = ViewTicketAberto(ticket_id=ticket_id, canal_id=canal.id)
        mentions = user.mention + (f" {staff_role.mention}" if staff_role else "")
        await canal.send(content=mentions, embed=embed, view=view)

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

        # Mensagem de confirmação com botão para ir ao ticket
        confirm_embed = discord.Embed(
            description=f"✅ Seu ticket foi aberto com sucesso!\n📂 {canal.mention}",
            color=config.COR_SUCESSO
        )
        view_link = discord.ui.View()
        view_link.add_item(discord.ui.Button(
            label="Ir para o Ticket",
            emoji="📂",
            style=discord.ButtonStyle.link,
            url=f"https://discord.com/channels/{guild.id}/{canal.id}"
        ))
        await interaction.followup.send(embed=confirm_embed, view=view_link, ephemeral=True)


# ──────────────────────────────────────────────
#  SELECT: escolha de categoria
# ──────────────────────────────────────────────
class SelectCategoria(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Suporte",
                description="Dúvidas, problemas e suporte técnico.",
                emoji="🎫",
                value="suporte",
            ),
            discord.SelectOption(
                label="Compras",
                description="Realizar pedidos e compras.",
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
        ticket = db.buscar_ticket_aberto_por_usuario(interaction.user.id)
        if ticket:
            canal = interaction.guild.get_channel(ticket["canal_id"])
            if canal:
                embed = discord.Embed(
                    description=f"⚠️ Você já possui um ticket aberto: {canal.mention}",
                    color=config.COR_AVISO
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
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
    def __init__(self, ticket_id: str, canal_id: int, assumido: bool = False):
        super().__init__(timeout=None)
        self.ticket_id = ticket_id
        self.canal_id = canal_id
        self.assumido = assumido
        # Aplicar estado inicial dos botões
        for item in self.children:
            if hasattr(item, "custom_id"):
                if item.custom_id == "btn_assumir" and assumido:
                    item.disabled = True
                    item.label = "Ticket Assumido"
                if item.custom_id == "btn_finalizar" and not assumido:
                    item.disabled = True

    @discord.ui.button(label="Assumir Ticket", style=discord.ButtonStyle.success, emoji="✅", custom_id="btn_assumir", row=0)
    async def assumir(self, interaction: discord.Interaction, button: discord.ui.Button):
        staff_role = interaction.guild.get_role(config.STAFF_ROLE_ID)
        admin_role = interaction.guild.get_role(config.ADMIN_ROLE_ID)
        if staff_role not in interaction.user.roles and admin_role not in interaction.user.roles:
            await interaction.response.send_message("❌ Apenas staff pode assumir tickets.", ephemeral=True)
            return

        db.assumir_ticket(self.ticket_id, interaction.user.id)

        # Desativar botão assumir e ativar finalizar
        button.disabled = True
        button.label = "Ticket Assumido"
        for item in self.children:
            if hasattr(item, "custom_id") and item.custom_id == "btn_finalizar":
                item.disabled = False

        embed = discord.Embed(color=config.COR_SUCESSO)
        embed.description = (
            f"### ✅ Ticket Assumido\n"
            f"> {interaction.user.mention} está cuidando deste ticket.\n"
            f"> Fique à vontade para conversar!"
        )
        embed.set_footer(text=f"BD Studio • {datetime.datetime.now().strftime('%d/%m/%Y às %H:%M')}")
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(embed=embed)
        await log_comando(interaction.guild, interaction.user, "Assumir Ticket", self.ticket_id)

    @discord.ui.button(label="Painel Admin", style=discord.ButtonStyle.primary, emoji="🔒", custom_id="btn_painel_admin", row=0)
    async def painel_admin(self, interaction: discord.Interaction, button: discord.ui.Button):
        staff_role = interaction.guild.get_role(config.STAFF_ROLE_ID)
        admin_role = interaction.guild.get_role(config.ADMIN_ROLE_ID)
        if staff_role not in interaction.user.roles and admin_role not in interaction.user.roles:
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
            return
        view = ViewPainelAdmin(ticket_id=self.ticket_id, canal_id=self.canal_id)
        embed = discord.Embed(
            title="🔒 Painel Administrativo",
            description=(
                "Selecione uma ação abaixo para gerenciar este ticket:\n\n"
                "➕ **Adicionar Membro** — Adiciona um usuário ao ticket\n"
                "➖ **Remover Membro** — Remove um usuário do ticket\n"
                "✏️ **Renomear Canal** — Altera o nome do canal\n"
                "📬 **Notificar na DM** — Envia mensagem privada\n"
                "✖️ **Finalizar** — Encerra e deleta o ticket"
            ),
            color=config.COR_INFO
        )
        embed.set_footer(text="BD Studio • Painel Admin", icon_url=config.LOGO_URL)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="Finalizar Ticket", style=discord.ButtonStyle.danger, emoji="✖️", custom_id="btn_finalizar", row=0, disabled=True)
    async def finalizar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await finalizar_ticket(interaction, self.ticket_id)


# ──────────────────────────────────────────────
#  MODAIS DO PAINEL ADMIN
# ──────────────────────────────────────────────
class ModalAdicionarMembro(discord.ui.Modal, title="➕ Adicionar Membro"):
    usuario = discord.ui.TextInput(
        label="ID ou nome do usuário",
        placeholder="Ex: 123456789012345678 ou joao_silva"
    )

    def __init__(self, canal_id):
        super().__init__()
        self.canal_id = canal_id

    async def on_submit(self, interaction: discord.Interaction):
        try:
            entrada = str(self.usuario).strip()
            membro = None

            # Tentar por ID primeiro
            if entrada.isdigit():
                try:
                    membro = await interaction.guild.fetch_member(int(entrada))
                except Exception:
                    pass

            # Tentar por nome/apelido se não achou por ID
            if not membro:
                entrada_lower = entrada.lower().lstrip("@")
                for m in interaction.guild.members:
                    if (m.name.lower() == entrada_lower or
                        m.display_name.lower() == entrada_lower or
                        str(m).lower() == entrada_lower):
                        membro = m
                        break

            if not membro:
                await interaction.response.send_message(
                    f"❌ Usuário `{entrada}` não encontrado no servidor.", ephemeral=True
                )
                return

            canal = interaction.guild.get_channel(self.canal_id)
            await canal.set_permissions(membro, view_channel=True, send_messages=True, read_message_history=True)
            embed = discord.Embed(
                description=f"➕ {membro.mention} foi adicionado ao ticket por {interaction.user.mention}.",
                color=config.COR_SUCESSO
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            await canal.send(embed=embed)
            await log_comando(interaction.guild, interaction.user, "Adicionar Membro", str(self.canal_id), extra=str(membro))
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {e}", ephemeral=True)


class ModalRemoverMembro(discord.ui.Modal, title="➖ Remover Membro"):
    usuario = discord.ui.TextInput(
        label="ID ou nome do usuário",
        placeholder="Ex: 123456789012345678 ou joao_silva"
    )

    def __init__(self, canal_id):
        super().__init__()
        self.canal_id = canal_id

    async def on_submit(self, interaction: discord.Interaction):
        try:
            entrada = str(self.usuario).strip()
            membro = None

            if entrada.isdigit():
                try:
                    membro = await interaction.guild.fetch_member(int(entrada))
                except Exception:
                    pass

            if not membro:
                entrada_lower = entrada.lower().lstrip("@")
                for m in interaction.guild.members:
                    if (m.name.lower() == entrada_lower or
                        m.display_name.lower() == entrada_lower or
                        str(m).lower() == entrada_lower):
                        membro = m
                        break

            if not membro:
                await interaction.response.send_message(
                    f"❌ Usuário `{entrada}` não encontrado no servidor.", ephemeral=True
                )
                return

            canal = interaction.guild.get_channel(self.canal_id)
            await canal.set_permissions(membro, overwrite=None)
            embed = discord.Embed(
                description=f"➖ {membro.mention} foi removido do ticket por {interaction.user.mention}.",
                color=config.COR_ERRO
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            await canal.send(embed=embed)
            await log_comando(interaction.guild, interaction.user, "Remover Membro", str(self.canal_id), extra=str(membro))
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {e}", ephemeral=True)


class ModalRenomearCanal(discord.ui.Modal, title="✏️ Renomear Canal"):
    novo_nome = discord.ui.TextInput(label="Novo nome do canal", placeholder="novo-nome-do-canal")

    def __init__(self, canal_id):
        super().__init__()
        self.canal_id = canal_id

    async def on_submit(self, interaction: discord.Interaction):
        try:
            canal = interaction.guild.get_channel(self.canal_id)
            nome_antigo = canal.name
            await canal.edit(name=str(self.novo_nome))
            embed = discord.Embed(
                description=f"✏️ Canal renomeado: `{nome_antigo}` → `{self.novo_nome}`",
                color=config.COR_INFO
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            await log_comando(interaction.guild, interaction.user, "Renomear Canal", str(self.canal_id), extra=f"{nome_antigo} → {self.novo_nome}")
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {e}", ephemeral=True)


class ModalNotificarMembro(discord.ui.Modal, title="📬 Notificar Dono do Ticket"):
    mensagem = discord.ui.TextInput(
        label="Mensagem para o cliente",
        style=discord.TextStyle.paragraph,
        default="Olá! Temos uma atualização sobre o seu ticket. Por favor, acesse o canal para mais informações.",
        max_length=1000
    )

    def __init__(self, ticket_id: str):
        super().__init__()
        self.ticket_id = ticket_id

    async def on_submit(self, interaction: discord.Interaction):
        try:
            ticket = db.buscar_ticket(self.ticket_id)
            if not ticket:
                await interaction.response.send_message("❌ Ticket não encontrado.", ephemeral=True)
                return
            membro = await interaction.guild.fetch_member(ticket["user_id"])
            canal = interaction.guild.get_channel(ticket["canal_id"])
            embed = discord.Embed(color=config.COR_PRINCIPAL)
            embed.set_author(name="📬 Notificação — BD Studio", icon_url=config.LOGO_URL)
            embed.description = (
                f"### Você tem uma nova mensagem!\n\n"
                f"**╔═ 💬 Mensagem:**\n"
                f"╚══ {str(self.mensagem)}\n\n"
                f"**╔═ 🎫 Ticket ID:** `{self.ticket_id}`\n"
                f"╚══ Acesse seu ticket no servidor para responder."
            )
            embed.set_thumbnail(url=config.LOGO_URL)
            embed.set_footer(text=f"Enviado por {interaction.user} • BD Studio")
            embed.timestamp = discord.utils.utcnow()
            view_link = discord.ui.View()
            if canal:
                view_link.add_item(discord.ui.Button(
                    label="Ir para o Ticket",
                    emoji="📂",
                    style=discord.ButtonStyle.link,
                    url=f"https://discord.com/channels/{interaction.guild.id}/{canal.id}"
                ))
            await membro.send(embed=embed, view=view_link)
            await interaction.response.send_message(f"✅ DM enviada para {membro.mention}.", ephemeral=True)
            await log_comando(interaction.guild, interaction.user, "Notificar DM", self.ticket_id, extra=str(membro))
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
        await interaction.response.send_modal(ModalNotificarMembro(self.ticket_id))

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

    embed = discord.Embed(color=config.COR_ERRO)
    embed.set_author(name="✦ ATENDIMENTO BD STUDIO ✦", icon_url=config.LOGO_URL)
    embed.description = (
        f"### ✖️ Ticket Encerrado\n"
        f"> Finalizado por {interaction.user.mention}\n"
        f"> Este canal será deletado em **5 segundos**."
    )
    embed.set_footer(text=f"BD Studio • {datetime.datetime.now().strftime('%d/%m/%Y às %H:%M')}")
    await interaction.response.send_message(embed=embed)

    if ticket:
        dono = interaction.guild.get_member(ticket["user_id"])
        if dono:
            try:
                dm_embed = discord.Embed(color=config.COR_PRINCIPAL)
                dm_embed.set_author(name="✦ BD STUDIO — Ticket Finalizado", icon_url=config.LOGO_URL)
                dm_embed.description = (
                    f"### Seu atendimento foi encerrado.\n\n"
                    f"**╔═ 🏠 Servidor:** {interaction.guild.name}\n"
                    f"**║  🎫 Ticket ID:** `{ticket_id}`\n"
                    f"**║  👤 Finalizado por:** {interaction.user}\n"
                    f"**╚═ 📅 Data:** {datetime.datetime.now().strftime('%d/%m/%Y às %H:%M')}\n\n"
                    f"*Obrigado por escolher o **BD Studio**! 💜*"
                )
                dm_embed.set_thumbnail(url=config.LOGO_URL)
                await dono.send(embed=dm_embed)
            except discord.Forbidden:
                pass

    db.fechar_ticket(ticket_id)

    # Gerar e enviar transcript
    try:
        caminho_html, url_pages = await gerar_transcript(
            interaction.channel,
            ticket or {"ticket_id": ticket_id, "categoria": "?", "assunto": "?"},
            interaction.guild
        )
        log_ch = interaction.guild.get_channel(config.LOG_TRANSCRIPTS_ID)
        if log_ch:
            t_embed = discord.Embed(
                title="📄 Transcript Gerado",
                color=config.COR_INFO,
            )
            t_embed.add_field(name="🎫 Ticket ID", value=f"`{ticket_id}`", inline=True)
            t_embed.add_field(name="🗂️ Categoria", value=ticket["categoria"] if ticket else "?", inline=True)
            t_embed.add_field(name="👤 Aberto por", value=f"<@{ticket['user_id']}>" if ticket else "?", inline=True)
            t_embed.add_field(name="🔒 Finalizado por", value=interaction.user.mention, inline=True)
            if url_pages:
                t_embed.add_field(name="🌐 Link", value=f"[Abrir Transcript]({url_pages})", inline=False)
            t_embed.set_footer(text="BD Studio • Transcripts", icon_url=config.LOGO_URL)
            t_embed.timestamp = discord.utils.utcnow()
            view_transcript = discord.ui.View()
            if url_pages:
                view_transcript.add_item(discord.ui.Button(
                    label="📄 Abrir Transcript",
                    url=url_pages,
                    style=discord.ButtonStyle.link
                ))
            arquivo_transcript = discord.File(caminho_html, filename=f"transcript-{ticket_id}.html")
            await log_ch.send(embed=t_embed, file=arquivo_transcript, view=view_transcript if url_pages else discord.ui.View())
        import os
        os.remove(caminho_html)
    except Exception as e:
        print(f"[Transcript] Erro: {e}")

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
        embed.set_author(name="✦ ATENDIMENTO BD STUDIO ✦", icon_url=config.LOGO_URL)
        embed.description = (
            "### 👋 Bem-vindo ao Atendimento BD Studio!\n"
            "> Selecione uma categoria no menu abaixo para abrir seu ticket.\n"
            "> Nossa equipe irá atendê-lo o mais rápido possível.\n\u200b"
        )
        embed.add_field(
            name="📌 Regras de Atendimento",
            value=(
                "> ❌ Não abra tickets sem necessidade\n"
                "> ❌ Não marque a equipe excessivamente\n"
                "> ✅ Forneça o máximo de detalhes possível"
            ),
            inline=False,
        )
        embed.add_field(name="\u200b", value="\u200b", inline=False)
        embed.set_thumbnail(url=config.LOGO_URL)
        embed.set_footer(text="BD Studio • Sistema de Atendimento", icon_url=config.LOGO_URL)
        embed.timestamp = discord.utils.utcnow()
        view = ViewPainel()
        await interaction.response.send_message(embed=embed, view=view)
        await log_comando(interaction.guild, interaction.user, "/painel", "-")

    @app_commands.command(name="paineladmin", description="Painel de administração de tickets.")
    @app_commands.default_permissions(manage_channels=True)
    async def paineladmin(self, interaction: discord.Interaction):
        ticket = db.buscar_ticket_por_canal(interaction.channel_id)
        if not ticket:
            await interaction.response.send_message(
                "❌ Este canal não é um ticket registrado.",
                ephemeral=True,
            )
            return

        view = ViewPainelAdmin(ticket_id=ticket["ticket_id"], canal_id=interaction.channel_id)
        embed = discord.Embed(color=config.COR_INFO)
        embed.set_author(name="🔒 Painel Administrativo — BD Studio", icon_url=config.LOGO_URL)
        embed.description = (
            "Selecione uma ação para gerenciar este ticket:\n\n"
            "➕ **Adicionar Membro** — Adiciona um usuário ao ticket\n"
            "➖ **Remover Membro** — Remove um usuário do ticket\n"
            "✏️ **Renomear Canal** — Altera o nome do canal\n"
            "📬 **Notificar na DM** — Envia mensagem privada\n"
            "✖️ **Finalizar** — Encerra e deleta o ticket"
        )
        embed.add_field(name="╔═ 🎫 Ticket ID", value=f"╚══ `{ticket['ticket_id']}`", inline=True)
        embed.add_field(name="╔═ 🗂️ Categoria", value=f"╚══ {ticket['categoria']}", inline=True)
        embed.add_field(name="╔═ 📌 Assunto", value=f"╚══ {ticket['assunto']}", inline=False)
        embed.set_footer(text="BD Studio • Painel Admin", icon_url=config.LOGO_URL)
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        await log_comando(interaction.guild, interaction.user, "/paineladmin", ticket["ticket_id"])
