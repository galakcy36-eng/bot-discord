import discord
import os
import random
import asyncio
import re
from datetime import datetime, timedelta, timezone
from discord.ext import commands

# =========================
# 🔧 INTENTS
# =========================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="+", intents=intents)

# =========================
# 📊 DATA
# =========================
user_stats = {}
giveaways = {}
ticket_config = {}
ticket_claimed = {}

# =========================
# ⏱ TIME PARSER
# =========================
def parse_time(time_str: str):
    pattern = r"(\d+)([smhdwo])"
    matches = re.findall(pattern, time_str.lower())

    seconds = 0
    for value, unit in matches:
        value = int(value)

        if unit == "s":
            seconds += value
        elif unit == "m":
            seconds += value * 60
        elif unit == "h":
            seconds += value * 3600
        elif unit == "d":
            seconds += value * 86400
        elif unit == "w":
            seconds += value * 604800
        elif unit == "o":
            seconds += value * 2592000

    return seconds

# =========================
# 📡 READY
# =========================
@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")

# =========================
# 📩 STATS MESSAGE
# =========================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    uid = message.author.id
    user_stats.setdefault(uid, {"messages": 0, "voice": 0, "join": None})
    user_stats[uid]["messages"] += 1

    await bot.process_commands(message)

# =========================
# 🎙 STATS VOCAL
# =========================
@bot.event
async def on_voice_state_update(member, before, after):
    uid = member.id
    user_stats.setdefault(uid, {"messages": 0, "voice": 0, "join": None})

    if before.channel is None and after.channel is not None:
        user_stats[uid]["join"] = datetime.now()

    elif before.channel is not None and after.channel is None:
        join = user_stats[uid]["join"]
        if join:
            user_stats[uid]["voice"] += (datetime.now() - join).seconds
            user_stats[uid]["join"] = None

# =========================
# 📜 INFO
# =========================
@bot.command()
async def info(ctx):
    embed = discord.Embed(
        title="📜 Commandes du bot",
        description="Toutes les fonctionnalités disponibles 👇",
        color=0x2f3136
    )

    embed.add_field(
        name="🎁 Giveaway",
        value="+giveaway → système complet avec boutons + conditions",
        inline=False
    )

    embed.add_field(
        name="🎟 Tickets",
        value="+setupticket → panel tickets + roles + claim/close",
        inline=False
    )

    embed.add_field(
        name="🧹 Modération",
        value=(
            "+clear <nbr>\n"
            "+ban @user\n"
            "+unban <id>\n"
            "+mute @user <temps>\n"
            "+unmute @user"
        ),
        inline=False
    )

    embed.add_field(
        name="⚙️ Système",
        value="stats messages + vocal + temps avancé (1d 2h 5m)",
        inline=False
    )

    await ctx.send(embed=embed)

# =========================
# 🧹 CLEAR
# =========================
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    amount = max(1, min(amount, 100))
    deleted = await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"🧹 {len(deleted)-1} messages supprimés.")
    await asyncio.sleep(3)
    await msg.delete()

# =========================
# ⛔ BAN / UNBAN
# =========================
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member):
    await member.ban()
    await ctx.send(f"⛔ {member.mention} banni.")

@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int):
    user = await bot.fetch_user(user_id)
    await ctx.guild.unban(user)
    await ctx.send(f"🔓 {user} débanni.")

# =========================
# 🔇 MUTE / UNMUTE
# =========================
@bot.command()
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, time: str):
    seconds = parse_time(time)
    until = datetime.now(timezone.utc) + timedelta(seconds=seconds)
    await member.edit(timed_out_until=until)
    await ctx.send(f"🔇 {member.mention} mute {time}.")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member):
    await member.edit(timed_out_until=None)
    await ctx.send(f"🔊 {member.mention} unmute.")

# =========================
# 🎟 TICKETS PANEL
# =========================
class TicketSelect(discord.ui.Select):
    def __init__(self):

        options = [
            discord.SelectOption(label="Report", emoji="🚨"),
            discord.SelectOption(label="Donations", emoji="💰"),
            discord.SelectOption(label="Recrutement", emoji="🧑‍💼"),
            discord.SelectOption(label="Support", emoji="🛠"),
        ]

        super().__init__(
            placeholder="🎟 Choisis un type de ticket...",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):

        guild = interaction.guild
        user = interaction.user
        choice = self.values[0]

        existing = discord.utils.get(guild.text_channels, name=f"ticket-{user.name}".lower())
        if existing:
            return await interaction.response.send_message("❌ Tu as déjà un ticket.", ephemeral=True)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }

        # ajout staff selon config
        staff_role = ticket_config.get(guild.id, {}).get(choice)
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        channel = await guild.create_text_channel(
            name=f"ticket-{choice}-{user.name}".lower(),
            overwrites=overwrites
        )

        ticket_claimed[channel.id] = None

        await channel.send(
            f"🎟 Ticket {choice} ouvert\n"
            f"{user.mention}\n\n"
            f"Utilise les boutons 👇",
            view=TicketControlView()
        )

        await interaction.response.send_message(f"🎟 Ticket créé : {channel.mention}", ephemeral=True)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(TicketSelect())

# =========================
# 🎟 SETUP TICKETS (ROLES STAFF)
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
        return r.role_mentions

    ticket_config[ctx.guild.id] = {
        "Report": (await ask("🎭 rôle staff REPORT ?"))[0],
        "Donations": (await ask("🎭 rôle staff DONATIONS ?"))[0],
        "Recrutement": (await ask("🎭 rôle staff RECRUTEMENT ?"))[0],
        "Support": (await ask("🎭 rôle staff SUPPORT ?"))[0],
    }

    embed = discord.Embed(
        title="🎟 Support Tickets",
        description="Choisis une catégorie dans le menu 👇",
        color=0x2f3136
    )

    await ctx.send(embed=embed, view=TicketView())

# =========================
# 🔘 TICKET BUTTONS
# =========================
class TicketControlView(discord.ui.View):

    @discord.ui.button(label="🟢 Claim", style=discord.ButtonStyle.success)
    async def claim(self, interaction, button):

        guild = interaction.guild
        config = ticket_config.get(guild.id, {})
        allowed = list(config.values())

        if not any(r in interaction.user.roles for r in allowed):
            return await interaction.response.send_message("❌ Staff only.", ephemeral=True)

        if ticket_claimed.get(interaction.channel.id):
            return await interaction.response.send_message("❌ Déjà claim.", ephemeral=True)

        ticket_claimed[interaction.channel.id] = interaction.user.id
        await interaction.channel.send(f"🟢 Claim par {interaction.user.mention}")
        await interaction.response.send_message("✔ Claim OK", ephemeral=True)

    @discord.ui.button(label="❌ Close", style=discord.ButtonStyle.danger)
    async def close(self, interaction, button):

        guild = interaction.guild
        config = ticket_config.get(guild.id, {})
        allowed = list(config.values())

        if not any(r in interaction.user.roles for r in allowed):
            return await interaction.response.send_message("❌ Staff only.", ephemeral=True)

        await interaction.response.send_message("🔒 Fermeture...", ephemeral=True)
        await asyncio.sleep(3)
        await interaction.channel.delete()

# =========================
# 🚀 RUN
# =========================
bot.run(os.environ["TOKEN"])
