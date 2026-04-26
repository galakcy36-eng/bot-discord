import discord
import os
import random
import asyncio
import re
from datetime import datetime, timedelta, timezone
from discord.ext import commands

# =========================
# INTENTS
# =========================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="+", intents=intents)

# =========================
# DATA
# =========================
ticket_config = {}
ticket_claimed = {}
spam_cache = {}

# =========================
# TIME PARSER
# =========================
def parse_time(time_str: str):
    pattern = r"(\d+)([smhdwo])"
    matches = re.findall(pattern, time_str.lower())

    seconds = 0
    for value, unit in matches:
        value = int(value)
        if unit == "s": seconds += value
        elif unit == "m": seconds += value * 60
        elif unit == "h": seconds += value * 3600
        elif unit == "d": seconds += value * 86400
        elif unit == "w": seconds += value * 604800
        elif unit == "o": seconds += value * 2592000

    return seconds

# =========================
# READY
# =========================
@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")

# =========================
# ANTI-SPAM
# =========================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    uid = message.author.id
    now = datetime.now().timestamp()

    spam_cache.setdefault(uid, [])
    spam_cache[uid].append(now)
    spam_cache[uid] = [t for t in spam_cache[uid] if now - t < 5]

    if len(spam_cache[uid]) > 5:
        await message.channel.send(f"⚠️ {message.author.mention} merci de ralentir vos messages.")
        return

    await bot.process_commands(message)

# =========================
# INFO (VERSION PLUS DÉTAILLÉE)
# =========================
@bot.command()
async def info(ctx):

    embed = discord.Embed(
        title="📜 Commandes du serveur",
        description=(
            "Bienvenue sur le système de commandes du serveur.\n\n"
            "Voici l’ensemble des fonctionnalités disponibles 👇"
        ),
        color=0x2f3136
    )

    embed.add_field(
        name="🎁 Giveaway",
        value="`+giveaway` → lancer un giveaway interactif",
        inline=False
    )

    embed.add_field(
        name="🎟 Tickets",
        value="`+setupticket` → créer le système de support complet",
        inline=False
    )

    embed.add_field(
        name="🧹 Modération",
        value="`+clear` `+ban` `+unban` `+mute` `+unmute`",
        inline=False
    )

    embed.add_field(
        name="⚙️ Système",
        value="• Anti-spam actif\n• Système de temps avancé (1d 2h 5m)\n• Stats utilisateurs (messages/vocal)",
        inline=False
    )

    await ctx.send(embed=embed)

# =========================
# MODERATION
# =========================
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    amount = max(1, min(amount, 100))
    await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send("🧹 Messages supprimés")
    await asyncio.sleep(2)
    await msg.delete()

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member):
    await member.ban()
    await ctx.send(f"⛔ {member.mention} a été banni.")

@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int):
    user = await bot.fetch_user(user_id)
    await ctx.guild.unban(user)
    await ctx.send(f"🔓 {user} a été débanni.")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, time: str):
    seconds = parse_time(time)
    await member.edit(timed_out_until=datetime.now(timezone.utc) + timedelta(seconds=seconds))
    await ctx.send(f"🔇 {member.mention} mute {time}")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member):
    await member.edit(timed_out_until=None)
    await ctx.send(f"🔊 {member.mention} unmute")

# =========================
# GIVEAWAY
# =========================
@bot.command()
async def giveaway(ctx):
    await ctx.send("🎁 Giveaway lancé ! Réagissez avec 🎉")

    msg = await ctx.send("🎉 GIVEAWAY 🎉")
    await msg.add_reaction("🎉")

    await asyncio.sleep(15)

    new = await ctx.channel.fetch_message(msg.id)
    users = [u async for u in new.reactions[0].users() if not u.bot]

    if not users:
        return await ctx.send("❌ Aucun gagnant")

    winner = random.choice(users)
    await ctx.send(f"🏆 Gagnant : {winner.mention}")

# =========================
# SETUP TICKETS
# =========================
@bot.command()
@commands.has_permissions(administrator=True)
async def setupticket(ctx):

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    async def ask(msg):
        q = await ctx.send(msg)
        r = await bot.wait_for("message", check=check)
        await q.delete()
        await r.delete()
        return r.role_mentions[0]

    ticket_config[ctx.guild.id] = {
        "Report": await ask("🎭 rôle staff REPORT ?"),
        "Donations": await ask("🎭 rôle staff DONATIONS ?"),
        "Recrutement": await ask("🎭 rôle staff RECRUTEMENT ?"),
        "Support": await ask("🎭 rôle staff SUPPORT ?"),
    }

    embed = discord.Embed(
        title="🎟 Centre de Support",
        description=(
            "Bienvenue dans le système de support du serveur.\n\n"
            "Merci de sélectionner une catégorie correspondant à votre demande.\n\n"
            "🚨 Report → signaler un joueur ou problème\n"
            "💰 Donations → faire un don au serveur\n"
            "🧑‍💼 Recrutement → rejoindre le staff\n"
            "🛠 Support → aide générale\n\n"
            "⚠️ Merci de ne pas ouvrir de tickets inutiles."
        ),
        color=0x2f3136
    )

    await ctx.send(embed=embed, view=TicketView())

# =========================
# TICKET PANEL (AMÉLIORÉ)
# =========================
class TicketSelect(discord.ui.Select):
    def __init__(self):

        options = [
            discord.SelectOption(label="Report", emoji="🚨", description="Signaler un problème"),
            discord.SelectOption(label="Donations", emoji="💰", description="Soutenir le serveur"),
            discord.SelectOption(label="Recrutement", emoji="🧑‍💼", description="Rejoindre l’équipe"),
            discord.SelectOption(label="Support", emoji="🛠", description="Aide générale"),
        ]

        super().__init__(
            placeholder="🎟 Sélectionnez une catégorie de support afin de créer un ticket adapté à votre demande...",
            options=options
        )

    async def callback(self, interaction):

        guild = interaction.guild
        user = interaction.user
        choice = self.values[0]

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }

        role = ticket_config.get(guild.id, {}).get(choice)
        if role:
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        channel = await guild.create_text_channel(
            name=f"ticket-{choice}-{user.name}".lower(),
            overwrites=overwrites
        )

        ticket_claimed[channel.id] = None

        await channel.send(
            "🎟 **Votre ticket a bien été créé**\n\n"
            "📢 Un staff vous répondra dans les plus brefs délais.\n"
            "Merci de patienter 🙏",
            view=TicketControl()
        )

        await interaction.response.send_message(f"🎟 Ticket créé : {channel.mention}", ephemeral=True)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(TicketSelect())

# =========================
# CLAIM / CLOSE
# =========================
class TicketControl(discord.ui.View):

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.success)
    async def claim(self, interaction, button):

        role_ids = ticket_config.get(interaction.guild.id, {}).values()

        if not any(r in interaction.user.roles for r in role_ids):
            return await interaction.response.send_message("❌ Staff only", ephemeral=True)

        ticket_claimed[interaction.channel.id] = interaction.user.id

        await interaction.channel.edit(name=f"claim-{interaction.user.name}")

        await interaction.channel.send(f"🟢 Claim par {interaction.user.mention}")
        await interaction.response.send_message("✔ Claim OK", ephemeral=True)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger)
    async def close(self, interaction, button):

        role_ids = ticket_config.get(interaction.guild.id, {}).values()

        if not any(r in interaction.user.roles for r in role_ids):
            return await interaction.response.send_message("❌ Staff only", ephemeral=True)

        await interaction.response.send_message("Fermeture...", ephemeral=True)
        await asyncio.sleep(2)
        await interaction.channel.delete()

# =========================
# RUN
# =========================
bot.run(os.environ["TOKEN"])
