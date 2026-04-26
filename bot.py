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
# 📊 STOCKAGE SIMPLE (TEMP)
# =========================
user_stats = {}  # messages + vocal (base simplifiée)

# =========================
# 📡 READY
# =========================
@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")

# =========================
# 📊 TRACK MESSAGES + VOCAL (BASIC)
# =========================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    uid = message.author.id
    user_stats.setdefault(uid, {"messages": 0, "voice_time": 0, "voice_join": None})

    user_stats[uid]["messages"] += 1

    await bot.process_commands(message)

@bot.event
async def on_voice_state_update(member, before, after):
    uid = member.id
    user_stats.setdefault(uid, {"messages": 0, "voice_time": 0, "voice_join": None})

    # join vocal
    if before.channel is None and after.channel is not None:
        user_stats[uid]["voice_join"] = datetime.now()

    # leave vocal
    elif before.channel is not None and after.channel is None:
        join_time = user_stats[uid]["voice_join"]
        if join_time:
            duration = (datetime.now() - join_time).seconds
            user_stats[uid]["voice_time"] += duration
            user_stats[uid]["voice_join"] = None

# =========================
# ➕ ROLE
# =========================
@bot.command()
@commands.has_permissions(manage_roles=True)
async def addrole(ctx, member: discord.Member, role: discord.Role):
    await member.add_roles(role)
    await ctx.send(f"✔ {member.mention} a reçu {role.name}")

# =========================
# ⛔ BAN TEMP
# =========================
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, duration: int, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f"⛔ {member} banni {duration}s")

    await asyncio.sleep(duration)

    try:
        await ctx.guild.unban(discord.Object(id=member.id))
        await ctx.send(f"🔓 {member} débanni")
    except:
        pass

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
# 🔇 MUTE
# =========================
@bot.command()
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, duration: int):
    until = datetime.now(timezone.utc) + timedelta(seconds=duration)
    await member.edit(timed_out_until=until)
    await ctx.send(f"🔇 {member.mention} mute {duration}s")

# =========================
# 🔊 UNMUTE
# =========================
@bot.command()
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member):
    await member.edit(timed_out_until=None)
    await ctx.send(f"🔊 {member.mention} unmute")

# =========================
# 🧹 CLEAR
# =========================
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    amount = min(amount, 100)
    deleted = await ctx.channel.purge(limit=amount)
    await ctx.send(f"🧹 {len(deleted)} messages supprimés", delete_after=3)

# =========================
# 🚫 ANTI-SPAM
# =========================
spam = {}

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    uid = message.author.id
    now = datetime.now().timestamp()

    spam.setdefault(uid, [])
    spam[uid].append(now)

    spam[uid] = [t for t in spam[uid] if now - t < 5]

    if len(spam[uid]) > 5:
        await message.channel.send(f"⚠️ {message.author.mention} stop spam")
        return

    await bot.process_commands(message)

# =========================
# 🎁 GIVEAWAY PRO COMPLET
# =========================
@bot.command()
async def giveaway(ctx):

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    # 🎁 LOT
    q1 = await ctx.send("🎁 Quel est le lot ?")
    r1 = await bot.wait_for("message", check=check)
    prize = r1.content
    await q1.delete(); await r1.delete()

    # 👥 GAGNANTS
    q2 = await ctx.send("👥 Nombre de gagnants ?")
    r2 = await bot.wait_for("message", check=check)
    try:
        winners_count = int(r2.content)
    except:
        return await ctx.send("❌ Nombre invalide.")
    await q2.delete(); await r2.delete()

    # ⏳ DURÉE
    q3 = await ctx.send("⏳ Durée du giveaway (sec) ?")
    r3 = await bot.wait_for("message", check=check)
    try:
        duration = int(r3.content)
    except:
        return await ctx.send("❌ Durée invalide.")
    await q3.delete(); await r3.delete()

    # 💬 MSG REQUIS
    q4 = await ctx.send("💬 Messages requis ?")
    r4 = await bot.wait_for("message", check=check)
    msg_req = int(r4.content)
    await q4.delete(); await r4.delete()

    # 🎙 VOCAL REQUIS
    q5 = await ctx.send("🎙 Temps vocal requis (sec) ?")
    r5 = await bot.wait_for("message", check=check)
    vc_req = int(r5.content)
    await q5.delete(); await r5.delete()

    # 🎭 ROLE REQUIS
    q6 = await ctx.send("🎭 ID rôle requis (ou none)")
    r6 = await bot.wait_for("message", check=check)

    role_req = None
    if r6.content.lower() != "none":
        role_req = ctx.guild.get_role(int(r6.content))

    await q6.delete(); await r6.delete()

    # 🚫 BYPASS ROLES
    q7 = await ctx.send("🚫 IDs rôles bypass (ou none)")
    r7 = await bot.wait_for("message", check=check)

    bypass_roles = []
    if r7.content.lower() != "none":
        bypass_roles = [ctx.guild.get_role(int(r)) for r in r7.content.split()]

    await q7.delete(); await r7.delete()

    # ⏱ CLAIM TIME
    q8 = await ctx.send("⏱ Temps pour claim (sec)")
    r8 = await bot.wait_for("message", check=check)
    claim_time = int(r8.content)
    await q8.delete(); await r8.delete()

    # =========================
    # 🎉 EMBED GIVEAWAY
    # =========================
    end_time = datetime.now(timezone.utc) + timedelta(seconds=duration)

    embed = discord.Embed(
        title="🎁 GIVEAWAY",
        description=(
            f"🏆 **Lot :** {prize}\n"
            f"👑 **Hôte :** {ctx.author.mention}\n\n"
            f"📜 **Conditions :**\n"
            f"💬 Messages : {msg_req}\n"
            f"🎙 Vocal : {vc_req}s\n"
            f"🎭 Rôle : {role_req.name if role_req else 'Aucun'}\n\n"
            f"⏳ Fin : <t:{int(end_time.timestamp())}:R>"
        ),
        color=0x2f3136
    )

    msg = await ctx.send(embed=embed)
    await msg.add_reaction("🎉")

    await asyncio.sleep(duration)

    # =========================
    # 🎯 PARTICIPANTS
    # =========================
    new_msg = await ctx.channel.fetch_message(msg.id)
    reaction = new_msg.reactions[0]
    users = [u async for u in reaction.users()]
    users = [u for u in users if not u.bot]

    valid_users = []

    for u in users:
        member = ctx.guild.get_member(u.id)
        if not member:
            continue

        # 🚫 bypass
        if any(r in member.roles for r in bypass_roles):
            valid_users.append(u)
            continue

        # 🎭 role check
        if role_req and role_req not in member.roles:
            continue

        # 💬 stats check
        stats = user_stats.get(member.id, {})

        if stats.get("messages", 0) < msg_req:
            continue

        if stats.get("voice_time", 0) < vc_req:
            continue

        valid_users.append(u)

    if not valid_users:
        return await ctx.send("❌ Aucun participant valide.")

    winners = random.sample(valid_users, min(winners_count, len(valid_users)))
    winners_mentions = " ".join(w.mention for w in winners)

    embed.color = 0x00ff99
    embed.add_field(name="🏆 Gagnant(s)", value=winners_mentions, inline=False)

    await msg.edit(embed=embed)

    await ctx.send(f"🎉 Félicitations {winners_mentions} ! Vous avez {claim_time}s pour claim !")

# =========================
# 🚀 RUN
# =========================
bot.run(os.environ["TOKEN"])
