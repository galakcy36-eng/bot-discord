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
# 📊 STATS (messages + vocal simple)
# =========================
user_stats = {}
spam_tracker = {}

# =========================
# 📡 READY
# =========================
@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")

# =========================
# 🚫 ON_MESSAGE UNIQUE (IMPORTANT)
# =========================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    uid = message.author.id
    now = datetime.now().timestamp()

    # -------------------------
    # 🚫 ANTI SPAM
    # -------------------------
    spam_tracker.setdefault(uid, [])
    spam_tracker[uid].append(now)
    spam_tracker[uid] = [t for t in spam_tracker[uid] if now - t < 5]

    if len(spam_tracker[uid]) > 5:
        await message.channel.send(f"⚠️ {message.author.mention} stop spam")
        return

    # -------------------------
    # 📊 STATS MESSAGES
    # -------------------------
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
            duration = (datetime.now() - join).seconds
            user_stats[uid]["voice"] += duration
            user_stats[uid]["join"] = None

# =========================
# ➕ ADD ROLE
# =========================
@bot.command()
@commands.has_permissions(manage_roles=True)
async def addrole(ctx, member: discord.Member, role: discord.Role):
    await member.add_roles(role)
    await ctx.send(f"✔ {member.mention} a reçu {role.name}")

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
# 🎁 GIVEAWAY STABLE PRO
# =========================
@bot.command()
async def giveaway(ctx):

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        # 🎁 LOT
        await ctx.send("🎁 Quel est le lot ?")
        r1 = await bot.wait_for("message", check=check)
        prize = r1.content

        # 👥 WINNERS
        await ctx.send("👥 Nombre de gagnants ?")
        r2 = await bot.wait_for("message", check=check)

        try:
            winners_count = int(r2.content)
        except:
            return await ctx.send("❌ Nombre invalide.")

        # ⏳ DURATION
        await ctx.send("⏳ Durée (secondes) ?")
        r3 = await bot.wait_for("message", check=check)

        try:
            duration = int(r3.content)
        except:
            return await ctx.send("❌ Durée invalide.")

    except asyncio.TimeoutError:
        return await ctx.send("⏱️ Temps écoulé.")

    end_time = datetime.now(timezone.utc) + timedelta(seconds=duration)

    embed = discord.Embed(
        title="🎁 GIVEAWAY",
        description=(
            f"🏆 **Lot :** {prize}\n"
            f"👑 **Hôte :** {ctx.author.mention}\n"
            f"👥 **Gagnants :** {winners_count}\n"
            f"⏳ **Fin :** <t:{int(end_time.timestamp())}:R>\n\n"
            f"🎉 Réagis pour participer !"
        ),
        color=0x2f3136
    )

    msg = await ctx.send(embed=embed)
    await msg.add_reaction("🎉")

    await asyncio.sleep(duration)

    # =========================
    # 🔍 PARTICIPANTS SAFE
    # =========================
    new_msg = await ctx.channel.fetch_message(msg.id)

    if not new_msg.reactions:
        return await ctx.send("❌ Aucun participant.")

    reaction = new_msg.reactions[0]
    users = [u async for u in reaction.users()]
    users = [u for u in users if not u.bot]

    if not users:
        return await ctx.send("❌ Aucun participant valide.")

    winners = random.sample(users, min(winners_count, len(users)))
    winners_mentions = " ".join(w.mention for w in winners)

    embed.color = 0x00ff99
    embed.add_field(name="🏆 Gagnant(s)", value=winners_mentions, inline=False)

    await msg.edit(embed=embed)

    await ctx.send(f"🎉 Félicitations {winners_mentions} !")

# =========================
# 🚀 RUN BOT
# =========================
bot.run(os.environ["TOKEN"])
