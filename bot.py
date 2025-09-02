import os
import discord
from discord.ext import commands, tasks
from discord import app_commands
from dotenv import load_dotenv
import asyncio
import aiohttp
import json

# -------------------- CONFIG --------------------
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Prefijo y intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="-", intents=intents)

# Configuración (logs)
CONFIG_FILE = "config.json"
if not os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "w") as f:
        json.dump({}, f)

def load_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

# -------------------- EVENTOS --------------------
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"{bot.user} está activo!")
    keep_alive.start()

# -------------------- KEEP ALIVE --------------------
@tasks.loop(minutes=5)
async def keep_alive():
    print("Manteniendo vivo el bot...")

# -------------------- LOGS --------------------
async def send_log(guild: discord.Guild, message: str):
    config = load_config()
    if str(guild.id) in config and "log_channel" in config[str(guild.id)]:
        channel_id = config[str(guild.id)]["log_channel"]
        channel = guild.get_channel(channel_id)
        if channel:
            await channel.send(f"📋 {message}")

@bot.tree.command(name="set-logs", description="Configura el canal de logs")
@app_commands.checks.has_permissions(administrator=True)
async def set_logs(interaction: discord.Interaction, canal: discord.TextChannel):
    config = load_config()
    if str(interaction.guild.id) not in config:
        config[str(interaction.guild.id)] = {}
    config[str(interaction.guild.id)]["log_channel"] = canal.id
    save_config(config)
    await interaction.response.send_message(f"✅ Canal de logs configurado en {canal.mention}", ephemeral=True)

# -------------------- MODERACIÓN --------------------
@bot.tree.command(name="ban", description="Banea a un miembro")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, miembro: discord.Member, razon: str = "No especificada"):
    await miembro.ban(reason=razon)
    await interaction.response.send_message(f"🚫 {miembro} baneado. Razón: {razon}")
    await send_log(interaction.guild, f"{miembro} fue baneado por {interaction.user}. Razón: {razon}")

@bot.tree.command(name="kick", description="Expulsa a un miembro")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, miembro: discord.Member, razon: str = "No especificada"):
    await miembro.kick(reason=razon)
    await interaction.response.send_message(f"👢 {miembro} expulsado. Razón: {razon}")
    await send_log(interaction.guild, f"{miembro} fue expulsado por {interaction.user}. Razón: {razon}")

@bot.tree.command(name="timeout", description="Aplica timeout a un miembro")
@app_commands.checks.has_permissions(moderate_members=True)
async def timeout(interaction: discord.Interaction, miembro: discord.Member, minutos: int, razon: str = "No especificada"):
    duracion = discord.utils.utcnow() + discord.timedelta(minutes=minutos)
    await miembro.timeout(until=duracion, reason=razon)
    await interaction.response.send_message(f"⏳ {miembro} en timeout por {minutos} minutos. Razón: {razon}")
    await send_log(interaction.guild, f"{miembro} recibió timeout por {minutos}m. Razón: {razon}")

# -------------------- HELP --------------------
@bot.tree.command(name="help", description="Muestra el menú de ayuda del bot")
async def slash_help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📘 Menú de Ayuda - Bot Wheeling Racing",
        description="Lista de comandos y funciones disponibles:",
        color=0xf1c40f
    )
    embed.add_field(name="⚙️ Moderación", value="`/ban`, `/kick`, `/timeout`", inline=False)
    embed.add_field(name="👥 Roles", value="`/autoroles` - Auto roles con reacciones", inline=False)
    embed.add_field(name="🏁 GP", value="`/gp` (calendario/clasificación), `/curiosidades`", inline=False)
    embed.add_field(name="🎮 Diversión", value="`/trivial` - Pregunta aleatoria de F1", inline=False)
    embed.add_field(name="📝 Utilidades", value="`/ocr` (texto de imágenes), `/stats` (estadísticas servidor)", inline=False)
    embed.set_footer(text="Bot de Fórmula 1 - Wheeling Racing 🚀")
    await interaction.response.send_message(embed=embed)

# -------------------- AUTOROLES --------------------
@bot.tree.command(name="autoroles", description="Crea un embed con auto roles")
@app_commands.checks.has_permissions(manage_roles=True)
async def autoroles(interaction: discord.Interaction):
    embed = discord.Embed(
        title="👥 Auto Roles",
        description="Reacciona para obtener o quitar un rol",
        color=discord.Color.blue()
    )
    embed.add_field(name="🏎️ Piloto", value="Reacciona con 🏎️", inline=False)
    embed.add_field(name="🛠️ Staff", value="Reacciona con 🛠️", inline=False)

    msg = await interaction.channel.send(embed=embed)
    await msg.add_reaction("🏎️")
    await msg.add_reaction("🛠️")

    await interaction.response.send_message("✅ Auto roles configurados.", ephemeral=True)

@bot.event
async def on_raw_reaction_add(payload):
    if payload.member.bot:
        return
    guild = bot.get_guild(payload.guild_id)
    role = None
    if payload.emoji.name == "🏎️":
        role = discord.utils.get(guild.roles, name="Piloto")
    elif payload.emoji.name == "🛠️":
        role = discord.utils.get(guild.roles, name="Staff")
    if role:
        await payload.member.add_roles(role)

@bot.event
async def on_raw_reaction_remove(payload):
    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    if not member:
        return
    role = None
    if payload.emoji.name == "🏎️":
        role = discord.utils.get(guild.roles, name="Piloto")
    elif payload.emoji.name == "🛠️":
        role = discord.utils.get(guild.roles, name="Staff")
    if role:
        await member.remove_roles(role)

# -------------------- ESTADÍSTICAS --------------------
@bot.tree.command(name="stats", description="Muestra estadísticas del servidor")
async def stats(interaction: discord.Interaction):
    guild = interaction.guild
    embed = discord.Embed(title="📊 Estadísticas del Servidor", color=discord.Color.green())
    embed.add_field(name="👥 Miembros", value=str(guild.member_count), inline=True)
    embed.add_field(name="💬 Canales de texto", value=str(len(guild.text_channels)), inline=True)
    embed.add_field(name="🔊 Canales de voz", value=str(len(guild.voice_channels)), inline=True)
    embed.add_field(name="🎭 Roles", value=str(len(guild.roles)), inline=True)
    await interaction.response.send_message(embed=embed)

# -------------------- ARRANQUE --------------------
bot.run(DISCORD_TOKEN)

