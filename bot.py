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
# 📊 STATS SIMPLES
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
# 🚫 ON_MESSAGE UNIQUE
# =========================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    uid = message.author.id
    now = datetime.now().timestamp()

    # anti spam
    spam_tracker.setdefault(uid, [])
    spam_tracker[uid].append(now)
    spam_tracker[uid] = [t for t in spam_tracker[uid] if now - t < 5]

    if len(spam_tracker[uid]) > 5:
        await message.channel.send(f"⚠️ {message.author.mention} stop spam")
        return

    # stats messages
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
# 🎁 GIVEAWAY PRO FINAL
# =========================
@bot.command()
async def giveaway(ctx):

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        # 🎁 LOT
        await ctx.send("🎁 Quel est le lot ?")
        r1 = await bot.wait_for("message", timeout=60, check=check)
        prize = r1.content

        # 👥 WINNERS
        await ctx.send("👥 Nombre de gagnants ?")
        r2 = await bot.wait_for("message", timeout=60, check=check)

        if not r2.content.isdigit():
            return await ctx.send("❌ Nombre invalide.")
        winners_count = int(r2.content)

        # ⏳ DURÉE GIVEAWAY
        await ctx.send("⏳ Durée du giveaway (secondes) ?")
        r3 = await bot.wait_for("message", timeout=60, check=check)

        if not r3.content.isdigit():
            return await ctx.send("❌ Durée invalide.")
        duration = int(r3.content)

        # 💬 MESSAGES REQUIS
        await ctx.send("💬 Nombre de messages requis ? (0 si aucun)")
        r4 = await bot.wait_for("message", timeout=60, check=check)
        msg_req = int(r4.content)

        # 🎙 VOCAL REQUIS
        await ctx.send("🎙 Temps vocal requis (secondes) ? (0 si aucun)")
        r5 = await bot.wait_for("message", timeout=60, check=check)
        vc_req = int(r5.content)

        # 🎭 ROLE REQUIS (PING)
        await ctx.send("🎭 Ping le rôle requis (ou 'none')")
        r6 = await bot.wait_for("message", timeout=60, check=check)

        role_req = None
        if r6.content.lower() != "none":
            if len(r6.role_mentions) == 0:
                return await ctx.send("❌ Tu dois mentionner un rôle.")
            role_req = r6.role_mentions[0]

        # 🚫 BYPASS ROLES (PING)
        await ctx.send("🚫 Ping les rôles bypass (ou 'none')")
        r7 = await bot.wait_for("message", timeout=60, check=check)

        bypass_roles = []
        if r7.content.lower() != "none":
            bypass_roles = r7.role_mentions

        # ⏱ CLAIM TIME
        await ctx.send("⏱ Temps pour claim (secondes) ?")
        r8 = await bot.wait_for("message", timeout=60, check=check)
        claim_time = int(r8.content)

    except asyncio.TimeoutError:
        return await ctx.send("⏱️ Temps écoulé, giveaway annulé.")

    # =========================
    # 🎉 EMBED
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
            f"🎭 Rôle : {role_req.mention if role_req else 'Aucun'}\n\n"
            f"⏳ Fin : <t:{int(end_time.timestamp())}:R>"
        ),
        color=0x2f3136
    )

    msg = await ctx.send(embed=embed)
    await msg.add_reaction("🎉")

    # =========================
    # ⏳ WAIT END
    # =========================
    await asyncio.sleep(duration)

    new_msg = await ctx.channel.fetch_message(msg.id)

    if not new_msg.reactions:
        return await ctx.send("❌ Aucun participant.")

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

        # 💬 messages + 🎙 vocal
        stats = user_stats.get(member.id, {"messages": 0, "voice": 0})

        if stats["messages"] < msg_req:
            continue

        if stats["voice"] < vc_req:
            continue

        valid_users.append(u)

    if not valid_users:
        return await ctx.send("❌ Aucun participant valide.")

    winners = random.sample(valid_users, min(winners_count, len(valid_users)))
    winners_mentions = " ".join(w.mention for w in winners)

    embed.color = 0x00ff99
    embed.add_field(name="🏆 Gagnant(s)", value=winners_mentions, inline=False)

    await msg.edit(embed=embed)

    await ctx.send(f"🎉 Félicitations {winners_mentions} ! Vous avez {claim_time}s pour claim.")

# =========================
# 🚀 RUN
# =========================
bot.run(os.environ["TOKEN"])
