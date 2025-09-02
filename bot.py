import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv
import aiohttp
from aiohttp import web
from PIL import Image
import io
import pytesseract
import asyncio

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.reactions = True
bot = commands.Bot(command_prefix="-", intents=intents)

# Simple webserver para Render
async def handle(request):
    return web.Response(text="Wheeling Racing Bot activo!")

async def run_webserver():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()

async def main():
    asyncio.create_task(run_webserver())  # Webserver en background
    await bot.start(DISCORD_TOKEN)               # Bot de Discord

asyncio.run(main())

# Desactivar help por defecto
bot = commands.Bot(command_prefix="-", intents=intents, help_command=None)

# -------------------- EVENTOS --------------------
@bot.event
async def on_ready():
    print(f"{bot.user} está activo!")
    try:
        synced = await bot.tree.sync()
        print(f"Slash commands sincronizados ({len(synced)})")
    except Exception as e:
        print(e)

# -------------------- MODERACIÓN --------------------
@bot.tree.command(name="ban", description="Banea a un miembro (staff)")
@app_commands.checks.has_permissions(ban_members=True)
async def slash_ban(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    await member.ban(reason=reason)
    await interaction.response.send_message(f"{member} ha sido baneado. Razón: {reason}", ephemeral=True)
    logs_channel = discord.utils.get(interaction.guild.text_channels, name="logs-moderacion")
    if logs_channel:
        await logs_channel.send(f"✅ {interaction.user} baneó a {member}. Razón: {reason}")

@bot.tree.command(name="kick", description="Expulsa a un miembro (staff)")
@app_commands.checks.has_permissions(kick_members=True)
async def slash_kick(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    await member.kick(reason=reason)
    await interaction.response.send_message(f"{member} ha sido expulsado. Razón: {reason}", ephemeral=True)
    logs_channel = discord.utils.get(interaction.guild.text_channels, name="logs-moderacion")
    if logs_channel:
        await logs_channel.send(f"⚠️ {interaction.user} expulsó a {member}. Razón: {reason}")

@bot.tree.command(name="timeout", description="Pone en timeout a un miembro (staff)")
@app_commands.checks.has_permissions(moderate_members=True)
async def slash_timeout(interaction: discord.Interaction, member: discord.Member, duration: int):
    await member.timeout(discord.Duration(seconds=duration))
    await interaction.response.send_message(f"{member} ha sido puesto en timeout por {duration} segundos.", ephemeral=True)
    logs_channel = discord.utils.get(interaction.guild.text_channels, name="logs-moderacion")
    if logs_channel:
        await logs_channel.send(f"⏱️ {interaction.user} puso en timeout a {member} por {duration} segundos.")

# -------------------- GP INFO --------------------
@bot.tree.command(name="gp", description="Muestra calendario o clasificación del GP")
async def slash_gp(interaction: discord.Interaction, tipo: str = "imagen"):
    if tipo.lower() == "texto":
        await interaction.response.send_message("Aquí iría el calendario o clasificación en texto.")
    else:
        await interaction.response.send_message("Sube aquí la imagen de calendario o clasificación.")

# -------------------- TRIVIAL --------------------
@bot.tree.command(name="trivial", description="Pregunta de trivial sobre F1")
async def slash_trivial(interaction: discord.Interaction):
    await interaction.response.send_message("Pregunta de Trivial sobre F1: ...")

# -------------------- CURIOSIDADES --------------------
@bot.tree.command(name="curiosidades", description="Muestra 5 curiosidades del GP")
async def slash_curiosidades(interaction: discord.Interaction):
    curiosidades = [
        "Curiosidad 1 del GP",
        "Curiosidad 2 del GP",
        "Curiosidad 3 del GP",
        "Curiosidad 4 del GP",
        "Curiosidad 5 del GP"
    ]
    embed = discord.Embed(
        title="Curiosidades del GP",
        description="\n".join(curiosidades),
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed)

# -------------------- AUTOROLES --------------------
@bot.tree.command(name="autoroles", description="Crea un embed de autoroles (staff)")
async def slash_autoroles(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message("No tienes permisos para esto.", ephemeral=True)
        return
    embed = discord.Embed(
        title="Asignación de Roles",
        description="Reacciona para obtener tu rol:\n🏎️ Piloto\n🛠️ Mecánico\n🎤 Fan",
        color=discord.Color.red()
    )
    msg = await interaction.channel.send(embed=embed)
    roles = {"🏎️": "Piloto", "🛠️": "Mecánico", "🎤": "Fan"}
    for emoji in roles:
        await msg.add_reaction(emoji)
    await interaction.response.send_message("Embed de autoroles creado.", ephemeral=True)

# -------------------- ESTADÍSTICAS --------------------
@bot.tree.command(name="stats", description="Muestra estadísticas del servidor")
async def slash_stats(interaction: discord.Interaction):
    guild = interaction.guild
    embed = discord.Embed(title=f"Estadísticas de {guild.name}", color=discord.Color.green())
    embed.add_field(name="Miembros totales", value=str(guild.member_count))
    embed.add_field(name="Canales de texto", value=str(len(guild.text_channels)))
    embed.add_field(name="Canales de voz", value=str(len(guild.voice_channels)))
    await interaction.response.send_message(embed=embed)

# -------------------- CONFIGURACIÓN DE LOGS --------------------
@bot.tree.command(name="set_channel_logs", description="Establece el canal de logs para moderación (staff)")
async def slash_set_logs(interaction: discord.Interaction, canal: discord.TextChannel):
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message("No tienes permisos para esto.", ephemeral=True)
        return
    # Guardar canal en memoria o DB según tu implementación
    global LOGS_CHANNEL_ID
    LOGS_CHANNEL_ID = canal.id
    await interaction.response.send_message(f"Canal de logs configurado: {canal.mention}", ephemeral=True)

# -------------------- OCR --------------------
@bot.command()
async def ocr(ctx):
    if ctx.message.attachments:
        image_url = ctx.message.attachments[0].url
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as resp:
                data = await resp.read()
                img = Image.open(io.BytesIO(data))
                texto = pytesseract.image_to_string(img)
                await ctx.send(f"Texto extraído:\n{texto}")
    else:
        await ctx.send("Adjunta una imagen para extraer el texto.")

@app_commands.command(name="ocr", description="Extrae texto de una imagen")
async def slash_ocr(interaction: discord.Interaction):
    if interaction.channel.last_message.attachments:
        image_url = interaction.channel.last_message.attachments[0].url
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as resp:
                data = await resp.read()
                img = Image.open(io.BytesIO(data))
                texto = pytesseract.image_to_string(img)
                await interaction.response.send_message(f"Texto extraído:\n{texto}")
    else:
        await interaction.response.send_message("Adjunta una imagen para extraer el texto.")
bot.tree.add_command(slash_ocr)

# -------------------- HELP EMBED --------------------
@bot.command()
async def help(ctx):
    embed = discord.Embed(title="Wheeling Racing Help", color=0xf1c40f)
    embed.add_field(name="-ban / /ban", value="Banea a un miembro", inline=False)
    embed.add_field(name="-kick / /kick", value="Expulsa a un miembro", inline=False)
    embed.add_field(name="-timeout / /timeout", value="Pone un miembro en timeout", inline=False)
    embed.add_field(name="-autoroles / /autoroles", value="Crea autoroles con reacciones", inline=False)
    embed.add_field(name="-gp / /gp", value="Muestra calendario o clasificación", inline=False)
    embed.add_field(name="-trivial / /trivial", value="Pregunta de trivial F1", inline=False)
    embed.add_field(name="-curiosidades / /curiosidades", value="5 curiosidades de cada GP", inline=False)
    embed.add_field(name="-stats / /stats", value="Muestra estadísticas del servidor", inline=False)
    embed.add_field(name="-ocr / /ocr", value="Extrae texto de una imagen", inline=False)
    await ctx.send(embed=embed)

# -------------------- KEEP ALIVE (impulsos) --------------------
@tasks.loop(minutes=5)
async def keep_alive():
    print("Impulso enviado para mantener vivo el bot")

@bot.event
async def on_ready():
    print(f"{bot.user} está activo!")
    try:
        synced = await bot.tree.sync()
        print(f"Slash commands sincronizados ({len(synced)})")
    except Exception as e:
        print(e)
    # Arranca el keep_alive aquí dentro del loop activo
    if not keep_alive.is_running():
        keep_alive.start()


# -------------------- RUN --------------------
bot.run(DISCORD_TOKEN)
