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
# 📜 INFO (inchangé comme avant)
# =========================
@bot.command()
async def info(ctx):
    embed = discord.Embed(
        title="📜 Commandes du bot",
        description="Voici toutes les commandes disponibles 👇",
        color=0x2f3136
    )

    embed.add_field(
        name="🎁 Giveaway",
        value="`+giveaway` → créer un giveaway interactif complet",
        inline=False
    )

    embed.add_field(
        name="🎟 Tickets",
        value="`+setupticket` → panel tickets (menu déroulant)",
        inline=False
    )

    embed.add_field(
        name="🧹 Modération",
        value=(
            "`+clear <nombre>`\n"
            "`+ban @user`\n"
            "`+unban <id>`\n"
            "`+mute @user <temps>`\n"
            "`+unmute @user`"
        ),
        inline=False
    )

    embed.add_field(
        name="⚙️ Système",
        value="stats messages + vocal + système temps (1d 2h 5m)",
        inline=False
    )

    await ctx.send(embed=embed)

# =========================
# 🎟 SETUP TICKETS
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
        return r.role_mentions[0] if r.role_mentions else None

    ticket_config[ctx.guild.id] = {
        "Report": await ask("🎭 rôle staff REPORT ?"),
        "Donations": await ask("🎭 rôle staff DONATIONS ?"),
        "Recrutement": await ask("🎭 rôle staff RECRUTEMENT ?"),
        "Support": await ask("🎭 rôle staff SUPPORT ?"),
    }

    embed = discord.Embed(
        title="🎟 Support Tickets",
        description=(
            "📌 Choisis une catégorie :\n\n"
            "🚨 Report → signaler un problème\n"
            "💰 Donations → faire un don\n"
            "🧑‍💼 Recrutement → rejoindre staff\n"
            "🛠 Support → aide générale\n\n"
            "📢 Un staff vous répondra rapidement."
        ),
        color=0x2f3136
    )

    await ctx.send(embed=embed, view=TicketView())

# =========================
# 🎟 PANEL
# =========================
class TicketSelect(discord.ui.Select):
    def __init__(self):

        options = [
            discord.SelectOption(label="Report", emoji="🚨"),
            discord.SelectOption(label="Donations", emoji="💰"),
            discord.SelectOption(label="Recrutement", emoji="🧑‍💼"),
            discord.SelectOption(label="Support", emoji="🛠"),
        ]

        super().__init__(placeholder="🎟 Choisis un ticket...", options=options)

    async def callback(self, interaction: discord.Interaction):

        guild = interaction.guild
        user = interaction.user
        choice = self.values[0]

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }

        staff_role = ticket_config.get(guild.id, {}).get(choice)
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        channel = await guild.create_text_channel(
            name=f"ticket-{choice}-{user.name}".lower(),
            overwrites=overwrites
        )

        ticket_claimed[channel.id] = None

        await channel.send(
            f"🎟 Ticket {choice} ouvert\n\n"
            f"👤 {user.mention}\n\n"
            f"📢 Un staff vous répondra dans les plus brefs délais."
            ,
            view=TicketControlView()
        )

        await interaction.response.send_message(f"🎟 Ticket créé : {channel.mention}", ephemeral=True)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(TicketSelect())

# =========================
# 🔘 CLAIM + CLOSE (MODIF CLAIM ICI)
# =========================
class TicketControlView(discord.ui.View):

    @discord.ui.button(label="🟢 Claim", style=discord.ButtonStyle.success)
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):

        guild = interaction.guild
        config = ticket_config.get(guild.id, {})
        allowed = list(config.values())

        if not any(role in interaction.user.roles for role in allowed):
            return await interaction.response.send_message("❌ Staff only.", ephemeral=True)

        if ticket_claimed.get(interaction.channel.id):
            return await interaction.response.send_message("❌ Déjà claim.", ephemeral=True)

        ticket_claimed[interaction.channel.id] = interaction.user.id

        # ✅ RENOMMAGE DEMANDÉ
        new_name = f"claim-{interaction.user.name}".lower()
        await interaction.channel.edit(name=new_name)

        await interaction.channel.send(f"🟢 Ticket claim par {interaction.user.mention}")
        await interaction.response.send_message("✔ Ticket claim.", ephemeral=True)

    @discord.ui.button(label="❌ Close", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):

        guild = interaction.guild
        config = ticket_config.get(guild.id, {})
        allowed = list(config.values())

        if not any(role in interaction.user.roles for role in allowed):
            return await interaction.response.send_message("❌ Staff only.", ephemeral=True)

        await interaction.response.send_message("🔒 Fermeture...", ephemeral=True)
        await asyncio.sleep(2)
        await interaction.channel.delete()

# =========================
# 🚀 RUN
# =========================
bot.run(os.environ["TOKEN"])
