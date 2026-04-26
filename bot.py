import discord
import os
import random
import asyncio
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
# 🧹 CLEAR
# =========================
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):

    if amount <= 0:
        return await ctx.send("❌ Nombre invalide.")

    if amount > 100:
        amount = 100

    try:
        deleted = await ctx.channel.purge(limit=amount + 1)
        msg = await ctx.send(f"🧹 {len(deleted)-1} messages supprimés")
        await asyncio.sleep(3)
        await msg.delete()

    except discord.Forbidden:
        await ctx.send("❌ Permissions manquantes (Gérer les messages).")

# =========================
# ⛔ BAN
# =========================
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f"⛔ {member} banni. Raison : {reason or 'Aucune'}")

# =========================
# 🔓 UNBAN
# =========================
@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int):
    user = await bot.fetch_user(user_id)
    await ctx.guild.unban(user)
    await ctx.send(f"🔓 {user} débanni")

# =========================
# 🔇 MUTE (TIMEOUT)
# =========================
@bot.command()
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, seconds: int):
    until = datetime.now(timezone.utc) + timedelta(seconds=seconds)
    await member.edit(timed_out_until=until)
    await ctx.send(f"🔇 {member} mute {seconds}s")

# =========================
# 🔊 UNMUTE
# =========================
@bot.command()
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member):
    await member.edit(timed_out_until=None)
    await ctx.send(f"🔊 {member} unmute")

# =========================
# 🎁 GIVEAWAY VIEW
# =========================
class GiveawayView(discord.ui.View):
    def __init__(self, msg_id):
        super().__init__(timeout=None)
        self.msg_id = msg_id

    # 🎉 PARTICIPER
    @discord.ui.button(label="Participer", style=discord.ButtonStyle.success)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):

        data = giveaways.get(self.msg_id)
        if not data:
            return await interaction.response.send_message("❌ Giveaway introuvable.", ephemeral=True)

        if data["ended"]:
            return await interaction.response.send_message("⛔ Giveaway terminé.", ephemeral=True)

        member = interaction.user
        missing = []

        # 🚫 BYPASS
        if any(r in member.roles for r in data["bypass"]):
            data["participants"].add(member.id)
            return await interaction.response.send_message("✔ Bypass accepté.", ephemeral=True)

        stats = user_stats.get(member.id, {"messages": 0, "voice": 0})

        if data["role_req"] and data["role_req"] not in member.roles:
            missing.append(f"🎭 Rôle requis : {data['role_req'].mention}")

        if stats["messages"] < data["msg_req"]:
            missing.append(f"💬 Messages requis : {data['msg_req']}")

        if stats["voice"] < data["vc_req"]:
            missing.append(f"🎙 Vocal requis : {data['vc_req']}s")

        if missing:
            return await interaction.response.send_message(
                "❌ Conditions manquantes :\n" + "\n".join(missing),
                ephemeral=True
            )

        data["participants"].add(member.id)
        await interaction.response.send_message("🎉 Tu participes !", ephemeral=True)

    # ❌ QUITTER
    @discord.ui.button(label="Quitter", style=discord.ButtonStyle.danger)
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):

        data = giveaways.get(self.msg_id)
        if not data:
            return await interaction.response.send_message("❌ Giveaway introuvable.", ephemeral=True)

        if data["ended"]:
            return await interaction.response.send_message("⛔ Giveaway terminé.", ephemeral=True)

        uid = interaction.user.id

        if uid not in data["participants"]:
            return await interaction.response.send_message("❌ Tu ne participes pas.", ephemeral=True)

        data["participants"].discard(uid)
        await interaction.response.send_message("👋 Tu as quitté.", ephemeral=True)

# =========================
# 🎁 GIVEAWAY
# =========================
@bot.command()
async def giveaway(ctx):

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        await ctx.send("🎁 Lot ?")
        prize = (await bot.wait_for("message", timeout=60, check=check)).content

        await ctx.send("👥 Gagnants ?")
        winners = int((await bot.wait_for("message", timeout=60, check=check)).content)

        await ctx.send("⏳ Durée ?")
        duration = int((await bot.wait_for("message", timeout=60, check=check)).content)

        await ctx.send("💬 Messages requis ?")
        msg_req = int((await bot.wait_for("message", timeout=60, check=check)).content)

        await ctx.send("🎙 Vocal requis ?")
        vc_req = int((await bot.wait_for("message", timeout=60, check=check)).content)

        await ctx.send("🎭 Rôle requis (ping ou none)")
        r = await bot.wait_for("message", timeout=60, check=check)
        role_req = r.role_mentions[0] if r.role_mentions else None

        await ctx.send("🚫 Rôles bypass (ping ou none)")
        r2 = await bot.wait_for("message", timeout=60, check=check)
        bypass = r2.role_mentions if r2.role_mentions else []

    except asyncio.TimeoutError:
        return await ctx.send("⏱️ Giveaway annulé.")

    # =========================
    # EMBED
    # =========================
    end = datetime.now(timezone.utc) + timedelta(seconds=duration)

    embed = discord.Embed(
        title="🎁 GIVEAWAY",
        description=(
            f"🏆 **Lot :** {prize}\n"
            f"👑 **Hôte :** {ctx.author.mention}\n\n"
            f"💬 Messages : {msg_req}\n"
            f"🎙 Vocal : {vc_req}s\n"
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

    # =========================
    # FIN GIVEAWAY
    # =========================
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

    embed.color = 0x00ff99
    embed.add_field(name="🏆 Gagnant(s)", value=mentions, inline=False)

    await msg.edit(embed=embed)
    await ctx.send(f"🎉 Félicitations {mentions} !")

# =========================
# 🚀 RUN
# =========================
bot.run(os.environ["TOKEN"])
