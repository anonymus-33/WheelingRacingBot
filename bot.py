import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
from dotenv import load_dotenv
import aiohttp
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
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f"{member} ha sido baneado. Razón: {reason}")
    logs = discord.utils.get(ctx.guild.text_channels, name="logs-moderacion")
    if logs:
        await logs.send(f"✅ {ctx.author} baneó a {member}. Razón: {reason}")

@app_commands.command(name="ban", description="Banea a un miembro (staff)")
@app_commands.checks.has_permissions(ban_members=True)
async def slash_ban(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    await member.ban(reason=reason)
    await interaction.response.send_message(f"{member} ha sido baneado. Razón: {reason}")
    logs = discord.utils.get(interaction.guild.text_channels, name="logs-moderacion")
    if logs:
        await logs.send(f"✅ {interaction.user} baneó a {member}. Razón: {reason}")
bot.tree.add_command(slash_ban)

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    await member.kick(reason=reason)
    await ctx.send(f"{member} ha sido expulsado. Razón: {reason}")
    logs = discord.utils.get(ctx.guild.text_channels, name="logs-moderacion")
    if logs:
        await logs.send(f"⚠️ {ctx.author} expulsó a {member}. Razón: {reason}")

@app_commands.command(name="kick", description="Expulsa a un miembro (staff)")
@app_commands.checks.has_permissions(kick_members=True)
async def slash_kick(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    await member.kick(reason=reason)
    await interaction.response.send_message(f"{member} ha sido expulsado. Razón: {reason}")
    logs = discord.utils.get(interaction.guild.text_channels, name="logs-moderacion")
    if logs:
        await logs.send(f"⚠️ {interaction.user} expulsó a {member}. Razón: {reason}")
bot.tree.add_command(slash_kick)

@bot.command()
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, duration: int):
    await member.timeout(discord.Duration(seconds=duration))
    await ctx.send(f"{member} ha sido puesto en timeout por {duration} segundos.")
    logs = discord.utils.get(ctx.guild.text_channels, name="logs-moderacion")
    if logs:
        await logs.send(f"⏱️ {ctx.author} puso en timeout a {member} por {duration} segundos.")

@app_commands.command(name="timeout", description="Pone a un miembro en timeout (staff)")
@app_commands.checks.has_permissions(moderate_members=True)
async def slash_timeout(interaction: discord.Interaction, member: discord.Member, duration: int):
    await member.timeout(discord.Duration(seconds=duration))
    await interaction.response.send_message(f"{member} ha sido puesto en timeout por {duration} segundos.")
    logs = discord.utils.get(interaction.guild.text_channels, name="logs-moderacion")
    if logs:
        await logs.send(f"⏱️ {interaction.user} puso en timeout a {member} por {duration} segundos.")
bot.tree.add_command(slash_timeout)

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
    roles = {"🏎️": "Piloto", "🛠️": "Mecánico", "🎤": "Fan"}
    for emoji in roles:
        await msg.add_reaction(emoji)

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot: return
    roles = {"🏎️": "Piloto", "🛠️": "Mecánico", "🎤": "Fan"}
    if str(reaction.emoji) in roles:
        role = discord.utils.get(user.guild.roles, name=roles[str(reaction.emoji)])
        if role:
            await user.add_roles(role)

@bot.event
async def on_reaction_remove(reaction, user):
    if user.bot: return
    roles = {"🏎️": "Piloto", "🛠️": "Mecánico", "🎤": "Fan"}
    if str(reaction.emoji) in roles:
        role = discord.utils.get(user.guild.roles, name=roles[str(reaction.emoji)])
        if role:
            await user.remove_roles(role)

# -------------------- GP INFO --------------------
@bot.command()
async def gp(ctx, tipo="imagen"):
    if tipo.lower() == "texto":
        await ctx.send("Aquí iría el calendario o clasificación en texto.")
    else:
        await ctx.send("Sube aquí la imagen de calendario o clasificación.")

@app_commands.command(name="gp", description="Muestra calendario o clasificación")
async def slash_gp(interaction: discord.Interaction, tipo: str = "imagen"):
    if tipo.lower() == "texto":
        await interaction.response.send_message("Aquí iría el calendario o clasificación en texto.")
    else:
        await interaction.response.send_message("Sube aquí la imagen de calendario o clasificación.")
bot.tree.add_command(slash_gp)

@bot.command()
async def trivial(ctx):
    await ctx.send("Pregunta de Trivial sobre F1: ...")

@app_commands.command(name="trivial", description="Pregunta de Trivial sobre F1")
async def slash_trivial(interaction: discord.Interaction):
    await interaction.response.send_message("Pregunta de Trivial sobre F1: ...")
bot.tree.add_command(slash_trivial)

@bot.command()
async def curiosidades(ctx):
    curiosidades = [f"Curiosidad {i}" for i in range(1,6)]
    embed = discord.Embed(title="Curiosidades del GP", description="\n".join(curiosidades), color=discord.Color.blue())
    await ctx.send(embed=embed)

@app_commands.command(name="curiosidades", description="5 curiosidades de cada GP")
async def slash_curiosidades(interaction: discord.Interaction):
    curiosidades = [f"Curiosidad {i}" for i in range(1,6)]
    embed = discord.Embed(title="Curiosidades del GP", description="\n".join(curiosidades), color=discord.Color.blue())
    await interaction.response.send_message(embed=embed)
bot.tree.add_command(slash_curiosidades)

# -------------------- ESTADÍSTICAS --------------------
@bot.command()
async def stats(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"Estadísticas de {guild.name}", color=discord.Color.green())
    embed.add_field(name="Miembros totales", value=str(guild.member_count))
    embed.add_field(name="Canales de texto", value=str(len(guild.text_channels)))
    embed.add_field(name="Canales de voz", value=str(len(guild.voice_channels)))
    await ctx.send(embed=embed)

@app_commands.command(name="stats", description="Estadísticas del servidor")
async def slash_stats(interaction: discord.Interaction):
    guild = interaction.guild
    embed = discord.Embed(title=f"Estadísticas de {guild.name}", color=discord.Color.green())
    embed.add_field(name="Miembros totales", value=str(guild.member_count))
    embed.add_field(name="Canales de texto", value=str(len(guild.text_channels)))
    embed.add_field(name="Canales de voz", value=str(len(guild.voice_channels)))
    await interaction.response.send_message(embed=embed)
bot.tree.add_command(slash_stats)

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
