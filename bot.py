import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
from dotenv import load_dotenv
import aiohttp
import pytesseract
from PIL import Image
import io

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)

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
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f"{member} ha sido baneado. Razón: {reason}")
    logs = discord.utils.get(ctx.guild.text_channels, name="logs-moderacion")
    if logs:
        await logs.send(f"✅ {ctx.author} baneó a {member}. Razón: {reason}")

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    await member.kick(reason=reason)
    await ctx.send(f"{member} ha sido expulsado. Razón: {reason}")
    logs = discord.utils.get(ctx.guild.text_channels, name="logs-moderacion")
    if logs:
        await logs.send(f"⚠️ {ctx.author} expulsó a {member}. Razón: {reason}")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, duration: int):
    await member.timeout(discord.Duration(seconds=duration))
    await ctx.send(f"{member} ha sido puesto en timeout por {duration} segundos.")
    logs = discord.utils.get(ctx.guild.text_channels, name="logs-moderacion")
    if logs:
        await logs.send(f"⏱️ {ctx.author} puso en timeout a {member} por {duration} segundos.")

# Slash commands de moderación
@app_commands.command(name="ban", description="Banea a un miembro (staff)")
@app_commands.checks.has_permissions(ban_members=True)
async def slash_ban(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    await member.ban(reason=reason)
    await interaction.response.send_message(f"{member} ha sido baneado. Razón: {reason}")
    logs = discord.utils.get(interaction.guild.text_channels, name="logs-moderacion")
    if logs:
        await logs.send(f"✅ {interaction.user} baneó a {member}. Razón: {reason}")

bot.tree.add_command(slash_ban)

# -------------------- AUTOROLES --------------------
@bot.command()
@commands.has_permissions(manage_roles=True)
async def autoroles(ctx):
    embed = discord.Embed(
        title="Asignación de Roles",
        description="Reacciona para obtener tu rol:\n🏎️ Piloto\n🛠️ Mecánico\n🎤 Fan",
        color=discord.Color.red()
    )
    msg = await ctx.send(embed=embed)
    roles = {
        "🏎️": "Piloto",
        "🛠️": "Mecánico",
        "🎤": "Fan"
    }
    for emoji in roles:
        await msg.add_reaction(emoji)

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    roles = {
        "🏎️": "Piloto",
        "🛠️": "Mecánico",
        "🎤": "Fan"
    }
    if str(reaction.emoji) in roles:
        role = discord.utils.get(user.guild.roles, name=roles[str(reaction.emoji)])
        if role:
            await user.add_roles(role)

@bot.event
async def on_reaction_remove(reaction, user):
    if user.bot:
        return
    roles = {
        "🏎️": "Piloto",
        "🛠️": "Mecánico",
        "🎤": "Fan"
    }
    if str(reaction.emoji) in roles:
        role = discord.utils.get(user.guild.roles, name=roles[str(reaction.emoji)])
        if role:
            await user.remove_roles(role)

# -------------------- GP INFO --------------------
@bot.command()
async def gp(ctx, tipo="imagen"):
    """Muestra calendario o clasificación"""
    if tipo.lower() == "texto":
        await ctx.send("Aquí iría el calendario o clasificación en texto.")
    else:
        await ctx.send("Sube aquí la imagen de calendario o clasificación.")

@bot.command()
async def trivial(ctx):
    await ctx.send("Pregunta de Trivial sobre F1: ...")

@bot.command()
async def curiosidades(ctx):
    curiosidades = [
        "Curiosidad 1 del GP",
        "Curiosidad 2 del GP",
        "Curiosidad 3 del GP",
        "Curiosidad 4 del GP",
        "Curiosidad 5 del GP"
    ]
    embed = discord.Embed(title="Curiosidades del GP", description="\n".join(curiosidades), color=discord.Color.blue())
    await ctx.send(embed=embed)

# OCR de imagen a texto
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

# -------------------- NOTICIAS F1 --------------------
news_channels = []

@tasks.loop(minutes=5)
async def f1_news():
    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.name == "noticias-f1":
                news_channels.append(channel)

    async with aiohttp.ClientSession() as session:
        url = "https://www.formula1.com/en/latest.html"  # ejemplo
        async with session.get(url) as resp:
            html = await resp.text()
            # Esto sería scraping simple de titulares
            # Para hacerlo más profesional se puede usar una API real
            headlines = ["Titular 1 de F1", "Titular 2 de F1"]  
            for channel in news_channels:
                for h in headlines:
                    await channel.send(f"📰 {h}")

@bot.event
async def on_ready():
    print(f"{bot.user} está activo!")
    try:
        synced = await bot.tree.sync()
        print(f"Slash commands sincronizados ({len(synced)})")
    except Exception as e:
        print(e)

    # Iniciar la tarea de noticias después de que el bot esté listo
    f1_news.start()


# -------------------- ESTADÍSTICAS DEL SERVIDOR --------------------
@bot.command()
async def stats(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"Estadísticas de {guild.name}", color=discord.Color.green())
    embed.add_field(name="Miembros totales", value=str(guild.member_count))
    embed.add_field(name="Canales de texto", value=str(len(guild.text_channels)))
    embed.add_field(name="Canales de voz", value=str(len(guild.voice_channels)))
    await ctx.send(embed=embed)

bot.run(DISCORD_TOKEN)
