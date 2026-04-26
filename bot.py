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
# INFO (RESTO ORIGINAL)
# =========================
@bot.command()
async def info(ctx):
    embed = discord.Embed(
        title="📜 Commandes du bot",
        description="Voici toutes les commandes disponibles 👇",
        color=0x2f3136
    )

    embed.add_field(name="🎁 Giveaway", value="`+giveaway`", inline=False)
    embed.add_field(name="🎟 Tickets", value="`+setupticket`", inline=False)
    embed.add_field(
        name="🧹 Modération",
        value="`+clear` `+ban` `+unban` `+mute` `+unmute`",
        inline=False
    )

    await ctx.send(embed=embed)

# =========================
# CLEAR
# =========================
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    amount = max(1, min(amount, 100))
    await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send("🧹 Messages supprimés")
    await asyncio.sleep(2)
    await msg.delete()

# =========================
# BAN / UNBAN
# =========================
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member):
    await member.ban()
    await ctx.send(f"⛔ {member} banni")

@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int):
    user = await bot.fetch_user(user_id)
    await ctx.guild.unban(user)
    await ctx.send(f"🔓 {user} débanni")

# =========================
# MUTE / UNMUTE
# =========================
@bot.command()
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, time: str):
    seconds = parse_time(time)
    await member.edit(timed_out_until=datetime.now(timezone.utc) + timedelta(seconds=seconds))
    await ctx.send(f"🔇 {member} mute")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member):
    await member.edit(timed_out_until=None)
    await ctx.send(f"🔊 {member} unmute")

# =========================
# GIVEAWAY SIMPLE FIX
# =========================
@bot.command()
async def giveaway(ctx):
    await ctx.send("🎁 Giveaway lancé ! Réagis 🎉")

    msg = await ctx.send("🎉 GIVEAWAY 🎉")
    await msg.add_reaction("🎉")

    await asyncio.sleep(10)

    new = await ctx.channel.fetch_message(msg.id)
    users = [u async for u in new.reactions[0].users() if not u.bot]

    if not users:
        return await ctx.send("❌ Aucun gagnant")

    winner = random.choice(users)
    await ctx.send(f"🏆 Gagnant : {winner.mention}")

# =========================
# TICKETS SETUP
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
        "Report": await ask("🎭 REPORT role ?"),
        "Donations": await ask("🎭 DONATIONS role ?"),
        "Recrutement": await ask("🎭 RECRUTEMENT role ?"),
        "Support": await ask("🎭 SUPPORT role ?"),
    }

    embed = discord.Embed(
        title="🎟 Tickets",
        description="Choisis une catégorie",
        color=0x2f3136
    )

    await ctx.send(embed=embed, view=TicketView())

# =========================
# TICKET PANEL
# =========================
class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Report", emoji="🚨"),
            discord.SelectOption(label="Donations", emoji="💰"),
            discord.SelectOption(label="Recrutement", emoji="🧑‍💼"),
            discord.SelectOption(label="Support", emoji="🛠"),
        ]
        super().__init__(placeholder="Choisis un ticket", options=options)

    async def callback(self, interaction):

        guild = interaction.guild
        user = interaction.user
        choice = self.values[0]

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True),
            guild.me: discord.PermissionOverwrite(view_channel=True),
        }

        role = ticket_config.get(guild.id, {}).get(choice)
        if role:
            overwrites[role] = discord.PermissionOverwrite(view_channel=True)

        channel = await guild.create_text_channel(
            name=f"ticket-{choice}-{user.name}".lower(),
            overwrites=overwrites
        )

        ticket_claimed[channel.id] = None

        await channel.send(
            "📢 Un staff vous répondra bientôt.",
            view=TicketControl()
        )

        await interaction.response.send_message(f"Ticket créé {channel.mention}", ephemeral=True)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(TicketSelect())

# =========================
# CLAIM / CLOSE STAFF ONLY
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
