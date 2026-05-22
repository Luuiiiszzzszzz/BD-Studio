import discord
from discord.ext import commands
from discord import app_commands
import mercadopago
import qrcode
import io
import datetime
import asyncio
import config
from utils.db import Database
from utils.logger import log_pagamento, log_comando
from utils.sheets import registrar_planilha

db = Database()

def criar_sdk():
    return mercadopago.SDK(config.MERCADO_PAGO_ACCESS_TOKEN)

class ModalGerarPix(discord.ui.Modal, title="Gerar Pagamento Pix"):
    valor = discord.ui.TextInput(
        label="Valor (R$)",
        placeholder="Ex: 50.00",
        max_length=10,
    )
    item = discord.ui.TextInput(
        label="Produto / Serviço",
        placeholder="Ex: Logo + Banner",
        max_length=100,
    )
    descricao = discord.ui.TextInput(
        label="Descrição (opcional)",
        placeholder="Detalhes adicionais...",
        required=False,
        style=discord.TextStyle.paragraph,
        max_length=300,
    )
    cliente_id = discord.ui.TextInput(
        label="ID Discord do cliente (opcional)",
        placeholder="123456789012345678",
        required=False,
        max_length=20,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            valor_float = float(str(self.valor).replace(",", "."))
        except ValueError:
            await interaction.followup.send("❌ Valor inválido. Use o formato: `50.00`", ephemeral=True)
            return

        item_nome = str(self.item)
        descricao_txt = str(self.descricao) or item_nome
        cliente_discord_id = str(self.cliente_id).strip() if str(self.cliente_id).strip() else None

        sdk = criar_sdk()
        payment_data = {
            "transaction_amount": valor_float,
            "description": f"BD Studio - {item_nome}",
            "payment_method_id": "pix",
            "payer": {
                "email": "cliente@bdstudio.com",
            },
            "external_reference": f"discord_{interaction.user.id}_{int(datetime.datetime.now().timestamp())}",
            "notification_url": "",  # Seu webhook URL aqui (opcional)
        }

        result = sdk.payment().create(payment_data)
        payment = result["response"]

        if result["status"] not in [200, 201]:
            await interaction.followup.send(
                f"❌ Erro ao criar pagamento: `{payment.get('message', 'Erro desconhecido')}`",
                ephemeral=True,
            )
            return

        pix_copia_cola = payment["point_of_interaction"]["transaction_data"]["qr_code"]
        qr_base64 = payment["point_of_interaction"]["transaction_data"]["qr_code_base64"]
        payment_id = str(payment["id"])
        expiracao = payment.get("date_of_expiration", "30 minutos")

        # Gerar imagem QR Code
        qr_img = qrcode.make(pix_copia_cola)
        buf = io.BytesIO()
        qr_img.save(buf, format="PNG")
        buf.seek(0)
        arquivo_qr = discord.File(buf, filename="pix_qrcode.png")

        embed = discord.Embed(
            title="💳 Pagamento Pix — BD Studio",
            color=config.COR_PRINCIPAL,
        )
        embed.add_field(name="🛒 Produto/Serviço", value=item_nome, inline=False)
        embed.add_field(name="💰 Valor", value=f"**R$ {valor_float:.2f}**", inline=True)
        embed.add_field(name="🆔 ID Pagamento", value=f"`{payment_id}`", inline=True)
        embed.add_field(
            name="📋 Pix Copia e Cola",
            value=f"```{pix_copia_cola[:500]}```",
            inline=False,
        )
        embed.set_image(url="attachment://pix_qrcode.png")
        embed.set_footer(text=f"Pagamento gerado por {interaction.user} • BD Studio")
        embed.timestamp = discord.utils.utcnow()
        embed.add_field(
            name="⏰ Validade",
            value=f"Este QR Code expira em ~30 minutos.",
            inline=False,
        )

        await interaction.followup.send(embed=embed, file=arquivo_qr, ephemeral=False)

        # Salvar pendente no banco para verificação
        db.criar_pagamento_pendente(
            pagamento_id=payment_id,
            criador_id=interaction.user.id,
            cliente_id=int(cliente_discord_id) if cliente_discord_id and cliente_discord_id.isdigit() else None,
            item=item_nome,
            valor=valor_float,
        )

        await log_comando(interaction.guild, interaction.user, "/gerarqrcode", payment_id, extra=f"R$ {valor_float:.2f} - {item_nome}")

        # Aguardar confirmação de pagamento (polling simples por 30 min)
        asyncio.create_task(
            aguardar_pagamento(
                bot=interaction.client,
                guild=interaction.guild,
                gerador=interaction.user,
                cliente_discord_id=cliente_discord_id,
                payment_id=payment_id,
                item=item_nome,
                valor=valor_float,
            )
        )


async def aguardar_pagamento(bot, guild, gerador, cliente_discord_id, payment_id, item, valor):
    """Polling para confirmar pagamento a cada 15s por até 30 min."""
    sdk = criar_sdk()
    tentativas = 120  # 120 x 15s = 30 min
    for _ in range(tentativas):
        await asyncio.sleep(15)
        result = sdk.payment().get(payment_id)
        status = result["response"].get("status", "")
        if status == "approved":
            # Registrar no banco
            cliente_id = None
            if cliente_discord_id and str(cliente_discord_id).isdigit():
                cliente_id = int(cliente_discord_id)
            db.confirmar_pagamento(payment_id, cliente_id, item, valor)

            # Registrar na planilha
            try:
                await registrar_planilha(
                    nome_cliente=str(gerador),
                    discord_id=str(gerador.id),
                    valor=valor,
                    item=item,
                    data=datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                )
            except Exception:
                pass

            # Log de pagamento
            await log_pagamento(
                guild=guild,
                gerador=gerador,
                cliente_id=cliente_id,
                payment_id=payment_id,
                item=item,
                valor=valor,
            )

            # Notificar cliente na DM se tiver ID
            if cliente_id:
                try:
                    cliente = await bot.fetch_user(cliente_id)
                    embed_dm = discord.Embed(
                        title="✅ Pagamento Confirmado!",
                        description=(
                            f"Seu pagamento foi confirmado com sucesso!\n\n"
                            f"**Produto:** {item}\n"
                            f"**Valor:** R$ {valor:.2f}\n"
                            f"**ID:** `{payment_id}`\n\n"
                            "Obrigado por comprar com o **BD Studio**! 💜"
                        ),
                        color=config.COR_SUCESSO,
                    )
                    embed_dm.set_thumbnail(url=config.LOGO_URL)
                    embed_dm.timestamp = discord.utils.utcnow()
                    await cliente.send(embed=embed_dm)
                except Exception:
                    pass
            break
        elif status in ["rejected", "cancelled", "refunded"]:
            break


class PagamentoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="gerarqrcode", description="Gera um QR Code Pix para pagamento.")
    @app_commands.default_permissions(manage_guild=True)
    async def gerarqrcode(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ModalGerarPix())
