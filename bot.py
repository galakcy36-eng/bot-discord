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
# 📩 MESSAGE TRACKING
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
# 🎙 VOCAL TRACKING
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
# 📜 INFO (AMÉLIORÉ)
# =========================
@bot.command()
async def info(ctx):
    embed = discord.Embed(
        title="📜 Commandes du bot",
        description="Voici toutes les fonctionnalités disponibles 👇",
        color=0x2f3136
    )

    embed.add_field(
        name="🎁 Giveaway",
        value=(
            "`+giveaway` → Créer un giveaway interactif\n"
            "• Participation / Quitter\n"
            "• Conditions : messages, vocal, rôle\n"
            "• Tirage automatique des gagnants"
        ),
        inline=False
    )

    embed.add_field(
        name="🧹 Modération",
        value=(
            "`+clear <nombre>` → Supprimer des messages\n"
            "`+ban @user [raison]` → Bannir un membre\n"
            "`+unban <id>` → Débannir un utilisateur\n"
            "`+mute @user <temps>` → Timeout (1h, 1d...)\n"
            "`+unmute @user` → Retirer le mute"
        ),
        inline=False
    )

    embed.add_field(
        name="⚙️ Système",
        value=(
            "• Tracking messages & vocal automatique\n"
            "• Système de conditions giveaway\n"
            "• Temps flexible (1s, 1m, 1h, 1d, 1mo)\n"
            "• Interface boutons interactive"
        ),
        inline=False
    )

    embed.set_footer(text="Bot Discord - Giveaway & Modération")

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
# ⛔ BAN
# =========================
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f"⛔ {member.mention} a été banni.")

# =========================
# 🔓 UNBAN
# =========================
@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int):
    user = await bot.fetch_user(user_id)
    await ctx.guild.unban(user)
    await ctx.send(f"🔓 {user} débanni.")

# =========================
# 🔇 MUTE
# =========================
@bot.command()
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, time: str):
    seconds = parse_time(time)
    until = datetime.now(timezone.utc) + timedelta(seconds=seconds)

    await member.edit(timed_out_until=until)
    await ctx.send(f"🔇 {member.mention} mute pendant {time}.")

# =========================
# 🔊 UNMUTE
# =========================
@bot.command()
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member):
    await member.edit(timed_out_until=None)
    await ctx.send(f"🔊 {member.mention} unmute.")

# =========================
# 🎁 GIVEAWAY VIEW
# =========================
class GiveawayView(discord.ui.View):
    def __init__(self, msg_id):
        super().__init__(timeout=None)
        self.msg_id = msg_id

    @discord.ui.button(label="🎉 Participer", style=discord.ButtonStyle.success)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):

        data = giveaways.get(self.msg_id)
        if not data or data["ended"]:
            return await interaction.response.send_message("⛔ Giveaway terminé.", ephemeral=True)

        member = interaction.user
        stats = user_stats.get(member.id, {"messages": 0, "voice": 0})

        missing = []

        if data["role_req"] and data["role_req"] not in member.roles:
            missing.append(f"🎭 rôle requis : {data['role_req'].mention}")

        if stats["messages"] < data["msg_req"]:
            missing.append(f"💬 messages requis : {data['msg_req']}")

        if stats["voice"] < data["vc_req"]:
            missing.append(f"🎙 vocal requis : {data['vc_req']}")

        if missing:
            return await interaction.response.send_message(
                "❌ Conditions non remplies :\n" + "\n".join(missing),
                ephemeral=True
            )

        data["participants"].add(member.id)

        await interaction.response.send_message(
            "🎉 Tu viens de rejoindre le giveaway ! Bonne chance 🍀",
            ephemeral=True
        )

    @discord.ui.button(label="❌ Quitter", style=discord.ButtonStyle.danger)
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):

        data = giveaways.get(self.msg_id)
        if not data or data["ended"]:
            return await interaction.response.send_message("⛔ Giveaway terminé.", ephemeral=True)

        uid = interaction.user.id

        if uid not in data["participants"]:
            return await interaction.response.send_message(
                "❌ Tu n’es pas inscrit au giveaway.",
                ephemeral=True
            )

        data["participants"].remove(uid)

        await interaction.response.send_message(
            "👋 Tu as quitté le giveaway… la chance t’attend peut-être ailleurs.",
            ephemeral=True
        )

# =========================
# 🎁 GIVEAWAY
# =========================
@bot.command()
async def giveaway(ctx):

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    await ctx.send("🎁 Lot ?")
    prize = (await bot.wait_for("message", check=check)).content

    await ctx.send("👥 Nombre de gagnants ?")
    winners = int((await bot.wait_for("message", check=check)).content)

    await ctx.send("⏱ Durée (ex: 1d 2h 10m) ?")
    duration = parse_time((await bot.wait_for("message", check=check)).content)

    await ctx.send("💬 Messages requis ?")
    msg_req = int((await bot.wait_for("message", check=check)).content)

    await ctx.send("🎙 Vocal requis ?")
    vc_req = int((await bot.wait_for("message", check=check)).content)

    await ctx.send("🎭 Rôle requis (ping ou none)")
    r = await bot.wait_for("message", check=check)
    role_req = r.role_mentions[0] if r.role_mentions else None

    await ctx.send("🚫 Rôles bypass (ping ou none)")
    r2 = await bot.wait_for("message", check=check)
    bypass = r2.role_mentions if r2.role_mentions else []

    end = datetime.now(timezone.utc) + timedelta(seconds=duration)

    embed = discord.Embed(
        title="🎁 GIVEAWAY EN COURS",
        description=(
            f"🏆 **Lot :** {prize}\n"
            f"👑 **Hôte :** {ctx.author.mention}\n\n"
            f"📜 **Conditions :**\n"
            f"💬 Messages : {msg_req}\n"
            f"🎙 Vocal : {vc_req}\n"
            f"🎭 Rôle : {role_req.mention if role_req else 'Aucun'}\n\n"
            f"⏳ Fin : <t:{int(end.timestamp())}:R>"
        ),
        color=0x2f3136
    )

    msg = await ctx.send(embed=embed)
    view = GiveawayView(msg.id)
    await msg.edit(view=view)

    giveaways[msg.id] = {
        "participants": set(),
        "msg_req": msg_req,
        "vc_req": vc_req,
        "role_req": role_req,
        "bypass": bypass,
        "winners": winners,
        "prize": prize,
        "ended": False
    }

    await asyncio.sleep(duration)

    data = giveaways.get(msg.id)
    if not data:
        return

    data["ended"] = True

    participants = list(data["participants"])

    if not participants:
        return await ctx.send("❌ Aucun participant.")

    winners_list = random.sample(participants, min(winners, len(participants)))
    mentions = " ".join(f"<@{i}>" for i in winners_list)

    await ctx.send(
        f"🎉 **GIVEAWAY TERMINÉ !**\n"
        f"🏆 Gagnant(s) : {mentions}\n"
        f"🎁 Lot : {prize}"
    )

# =========================
# 🚀 RUN
# =========================
bot.run(os.environ["TOKEN"])
