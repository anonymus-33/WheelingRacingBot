import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
from dotenv import load_dotenv
import aiohttp
from aiohttp import web
import asyncio
from PIL import Image
import pytesseract
import io

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.reactions = True

bot = commands.Bot(command_prefix="-", intents=intents, help_command=None)

# -------------------- VARIABLES --------------------
log_channel_id = None
roles_emoji = {"🏎️": "Piloto", "🛠️": "Mecánico", "🎤": "Fan"}

# Ejemplo GP info y curiosidades
gp_texto = "Calendario/Clasificación en texto."
curiosidades_gp = [
    "Curiosidad 1 del GP",
    "Curiosidad 2 del GP",
    "Curiosidad 3 del GP",
    "Curiosidad 4 del GP",
    "Curiosidad 5 del GP"
]

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
    if log_channel_id:
        channel = bot.get_channel(log_channel_id)
        if channel:
            await channel.send(f"✅ {ctx.author} baneó a {member}. Razón: {reason}")

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    await member.kick(reason=reason)
    await ctx.send(f"{member} ha sido expulsado. Razón: {reason}")
    if log_channel_id:
        channel = bot.get_channel(log_channel_id)
        if channel:
            await channel.send(f"⚠️ {ctx.author} expulsó a {member}. Razón: {reason}")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, duration: int):
    await member.timeout(discord.Duration(seconds=duration))
    await ctx.send(f"{member} ha sido puesto en timeout por {duration} segundos.")
    if log_channel_id:
        channel = bot.get_channel(log_channel_id)
        if channel:
            await channel.send(f"⏱️ {ctx.author} puso en timeout a {member} por {duration} segundos.")

# -------------------- SLASH COMMANDS --------------------
@bot.tree.command(name="ban", description="Banea a un miembro (staff)")
@app_commands.checks.has_permissions(ban_members=True)
async def slash_ban(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    await member.ban(reason=reason)
    await interaction.response.send_message(f"{member} ha sido baneado. Razón: {reason}")
    if log_channel_id:
        channel = bot.get_channel(log_channel_id)
        if channel:
            await channel.send(f"✅ {interaction.user} baneó a {member}. Razón: {reason}")

@bot.tree.command(name="kick", description="Expulsa a un miembro (staff)")
@app_commands.checks.has_permissions(kick_members=True)
async def slash_kick(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    await member.kick(reason=reason)
    await interaction.response.send_message(f"{member} ha sido expulsado. Razón: {reason}")
    if log_channel_id:
        channel = bot.get_channel(log_channel_id)
        if channel:
            await channel.send(f"⚠️ {interaction.user} expulsó a {member}. Razón: {reason}")

@bot.tree.command(name="timeout", description="Pone a un miembro en timeout (staff)")
@app_commands.checks.has_permissions(moderate_members=True)
async def slash_timeout(interaction: discord.Interaction, member: discord.Member, duration: int):
    await member.timeout(discord.Duration(seconds=duration))
    await interaction.response.send_message(f"{member} ha sido puesto en timeout por {duration} segundos.")
    if log_channel_id:
        channel = bot.get_channel(log_channel_id)
        if channel:
            await channel.send(f"⏱️ {interaction.user} puso en timeout a {member} por {duration} segundos")

@bot.tree.command(name="set-channel-logs", description="Configura el canal donde se guardan los logs de moderación")
@app_commands.checks.has_permissions(administrator=True)
async def set_channel_logs(interaction: discord.Interaction, channel: discord.TextChannel):
    global log_channel_id
    log_channel_id = channel.id
    await interaction.response.send_message(f"Canal de logs establecido: {channel.mention}", ephemeral=True)

# -------------------- AUTOROLES --------------------
@bot.command()
@commands.has_permissions(manage_roles=True)
async def autoroles(ctx):
    embed = discord.Embed(
        title="Asignación de Roles",
        description="Reacciona para obtener tu rol:",
        color=discord.Color.red()
    )
    for emoji, role_name in roles_emoji.items():
        embed.add_field(name=role_name, value=emoji, inline=True)
    msg = await ctx.send(embed=embed)
    for emoji in roles_emoji:
        await msg.add_reaction(emoji)

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    role_name = roles_emoji.get(str(reaction.emoji))
    if role_name:
        role = discord.utils.get(user.guild.roles, name=role_name)
        if role:
            await user.add_roles(role)

@bot.event
async def on_reaction_remove(reaction, user):
    if user.bot:
        return
    role_name = roles_emoji.get(str(reaction.emoji))
    if role_name:
        role = discord.utils.get(user.guild.roles, name=role_name)
        if role:
            await user.remove_roles(role)

# -------------------- HELP --------------------
@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="Wheeling Racing - Comandos",
        description="Aquí están las funciones disponibles:",
        color=0xf1c40f
    )
    embed.add_field(name="-ban", value="Banea a un miembro (staff).", inline=False)
    embed.add_field(name="-kick", value="Expulsa a un miembro (staff).", inline=False)
    embed.add_field(name="-timeout", value="Pone a un miembro en timeout (staff).", inline=False)
    embed.add_field(name="-autoroles", value="Crea el embed para autoroles con reacciones.", inline=False)
    embed.add_field(name="/set-channel-logs", value="Configura el canal donde se guardan los logs de moderación.", inline=False)
    embed.add_field(name="-gp", value="Muestra GP en texto o imagen.", inline=False)
    embed.add_field(name="-trivial", value="Pregunta de Trivial F1.", inline=False)
    embed.add_field(name="-curiosidades", value="Curiosidades del GP.", inline=False)
    embed.add_field(name="-help", value="Muestra este mensaje.", inline=False)
    await ctx.send(embed=embed)

# -------------------- GP INFO --------------------
@bot.command()
async def gp(ctx, tipo="imagen"):
    if tipo.lower() == "texto":
        await ctx.send(gp_texto)
    else:
        await ctx.send("Sube la imagen correspondiente del GP.")

@bot.command()
async def trivial(ctx):
    await ctx.send("Pregunta de Trivial sobre F1: ¿... ?")

@bot.command()
async def curiosidades(ctx):
    embed = discord.Embed(title="Curiosidades del GP", description="\n".join(curiosidades_gp), color=discord.Color.blue())
    await ctx.send(embed=embed)

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

# -------------------- KEEP ALIVE --------------------
@tasks.loop(minutes=4)
async def keep_alive():
    print("Impulso keep alive enviado...")

@bot.event
async def on_ready():
    print(f"{bot.user} está activo!")
    try:
        synced = await bot.tree.sync()
        print(f"Slash commands sincronizados ({len(synced)})")
    except Exception as e:
        print(e)
    # Aquí arrancamos el loop de keep_alive correctamente
    if not keep_alive.is_running():
        keep_alive.start()


# -------------------- HTTP RENDER --------------------
async def handle(request):
    return web.Response(text="Bot Wheeling Racing activo")

app = web.Application()
app.router.add_get("/", handle)

async def start_web():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()

asyncio.get_event_loop().create_task(start_web())

# -------------------- RUN BOT --------------------
bot.run(TOKEN)
