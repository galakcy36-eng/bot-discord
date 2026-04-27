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
        title="📜 Centre d'informations du bot",
        description=(
            "Bienvenue dans le panneau d'aide du bot.\n\n"
            "Vous trouverez ici l'ensemble des commandes disponibles ainsi que leur utilisation.\n"
            "Merci de respecter les règles du serveur lors de l'utilisation de ces commandes.\n\n"
            "━━━━━━━━━━━━━━━━━━"
        ),
        color=0x2f3136
    )

    embed.add_field(
        name="🎁 Giveaway",
        value=(
            "`+giveaway`\n"
            "→ Lance un giveaway interactif.\n"
            "Le bot vous posera plusieurs questions (lot, gagnants, durée).\n"
            "Les membres participent avec 🎉 et un tirage est effectué automatiquement."
        ),
        inline=False
    )

    embed.add_field(
        name="🎟 Système de tickets",
        value=(
            "`+setupticket`\n"
            "→ Configure un panneau de support.\n\n"
            "Catégories disponibles :\n"
            "• 🚨 Report → signaler un problème\n"
            "• 💰 Donations → soutenir le serveur\n"
            "• 🧑‍💼 Recrutement → rejoindre le staff\n"
            "• 🛠 Support → aide générale\n\n"
            "Un membre du staff prendra en charge le ticket."
        ),
        inline=False
    )

    embed.add_field(
        name="🧹 Modération",
        value=(
            "`+clear <nombre>` → supprimer des messages\n"
            "`+ban @user` → bannir\n"
            "`+unban <id>` → débannir\n"
            "`+mute @user <temps>` → mute\n"
            "`+unmute @user` → unmute"
        ),
        inline=False
    )

    embed.add_field(
        name="⏱ Temps supporté",
        value=(
            "`10s` `5m` `2h` `1d` `1w` `1o`\n"
            "Combinaisons possibles : `1h30m`, `2d5h`"
        ),
        inline=False
    )

    embed.add_field(
        name="🛡 Systèmes automatiques",
        value=(
            "• Anti-spam\n"
            "• Gestion tickets\n"
            "• Tirage giveaway automatique\n"
            "• Interface interactive"
        ),
        inline=False
    )

    embed.set_footer(text=f"Demandé par {ctx.author}", icon_url=ctx.author.avatar)

    await ctx.send(embed=embed)
    
# =========================
# GIVEAWAY
# =========================
@bot.command()
async def giveaway(ctx):

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    # QUESTIONS
    q1 = await ctx.send("🎁 Quel est le lot ?")
    r1 = await bot.wait_for("message", check=check)
    prize = r1.content
    await q1.delete(); await r1.delete()

    q2 = await ctx.send("👥 Combien de gagnants ?")
    r2 = await bot.wait_for("message", check=check)
    winners_count = int(r2.content)
    await q2.delete(); await r2.delete()

    q3 = await ctx.send("⏳ Durée ? (ex: 1h, 30m)")
    r3 = await bot.wait_for("message", check=check)
    duration = parse_time(r3.content)
    await q3.delete(); await r3.delete()

    q4 = await ctx.send("💬 Nombre de messages requis pour participer ? (0 = aucun)")
    r4 = await bot.wait_for("message", check=check)
    msg_required = int(r4.content)
    await q4.delete(); await r4.delete()

    q5 = await ctx.send("🎤 Temps en vocal requis ? (ex: 10m, 1h, 0 = aucun)")
    r5 = await bot.wait_for("message", check=check)
    vocal_required = parse_time(r5.content) if r5.content != "0" else 0
    await q5.delete(); await r5.delete()

    q6 = await ctx.send("🎭 Rôle requis pour participer ? (ping ou 'aucun')")
    r6 = await bot.wait_for("message", check=check)
    role_required = r6.role_mentions[0] if r6.role_mentions else None
    await q6.delete(); await r6.delete()

    q7 = await ctx.send("🛡 Rôle bypass (ignore toutes les conditions) ? (ping ou 'aucun')")
    r7 = await bot.wait_for("message", check=check)
    bypass_role = r7.role_mentions[0] if r7.role_mentions else None
    await q7.delete(); await r7.delete()

    # NOUVELLE QUESTION (JUSTE AFFICHAGE)
    q8 = await ctx.send("⏱ Temps pour claim le giveaway ? (ex: 30s, 1m, 0 = aucun)")
    r8 = await bot.wait_for("message", check=check)
    claim_time_display = r8.content
    await q8.delete(); await r8.delete()

    end_time = datetime.now(timezone.utc) + timedelta(seconds=duration)

    # CONDITIONS
    conditions = ""
    conditions += f"• 💬 Messages : {msg_required}\n" if msg_required > 0 else ""
    conditions += f"• 🎤 Vocal : {vocal_required}s\n" if vocal_required > 0 else ""
    conditions += f"• 🎭 Rôle requis : {role_required.mention}\n" if role_required else ""
    conditions += f"• 🛡 Bypass : {bypass_role.mention}\n" if bypass_role else ""

    if conditions == "":
        conditions = "Aucune condition"

    embed = discord.Embed(
        title="🎁 Giveaway",
        description=(
            f"🏆 **Lot :** {prize}\n"
            f"👥 **Gagnants :** {winners_count}\n"
            f"👑 **Hôte :** {ctx.author.mention}\n"
            f"⏱ **Fin :** <t:{int(end_time.timestamp())}:R>\n"
            f"⏱ **Temps pour claim :** {claim_time_display}\n\n"

            f"📋 **Conditions :**\n{conditions}\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"

            f"🎉 Réagissez avec 🎉 pour participer !"
        ),
        color=0x2f3136
    )

    msg = await ctx.send(embed=embed)
    await msg.add_reaction("🎉")

    # FIN
    await asyncio.sleep(duration)

    new_msg = await ctx.channel.fetch_message(msg.id)
    users = [u async for u in new_msg.reactions[0].users() if not u.bot]

    if not users:
        return await ctx.send("❌ Aucun participant.")

    winners = random.sample(users, min(winners_count, len(users)))
    mentions = " ".join([w.mention for w in winners])

    embed.color = 0x00ff99
    embed.add_field(name="🏆 Gagnant(s)", value=mentions, inline=False)

    await msg.edit(embed=embed)
    await ctx.send(f"🎉 Félicitations {mentions} !")
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
    await member.edit(
        timed_out_until=datetime.now(timezone.utc) + timedelta(seconds=seconds)
    )
    await ctx.send(f"🔇 {member.mention} mute pendant {time}")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member):
    await member.edit(timed_out_until=None)
    await ctx.send(f"🔊 {member.mention} unmute")
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
