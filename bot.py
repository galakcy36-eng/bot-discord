import discord
import os
import random
import asyncio
import re
from datetime import datetime, timedelta, timezone
from discord.ext import commands

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
giveaways = {}

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
# INFO
# =========================
@bot.command()
async def info(ctx):
    embed = discord.Embed(title="📜 Commandes du bot", color=0x2f3136)

    embed.add_field(name="🎁 Giveaway", value="`+giveaway` → créer un giveaway\n`+gwclaim` → réclamer un gain", inline=False)
    embed.add_field(name="🎟 Tickets", value="`+setupticket` → panneau support", inline=False)
    embed.add_field(name="🧹 Modération", value="`+clear` `+ban` `+unban` `+mute` `+unmute`", inline=False)

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

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    q1 = await ctx.send("🎁 Lot ?")
    r1 = await bot.wait_for("message", check=check)
    prize = r1.content
    await q1.delete(); await r1.delete()

    q2 = await ctx.send("👥 Nombre de gagnants ?")
    r2 = await bot.wait_for("message", check=check)
    winners_count = int(r2.content)
    await q2.delete(); await r2.delete()

    q3 = await ctx.send("⏳ Durée ? (1h, 30m...)")
    r3 = await bot.wait_for("message", check=check)
    duration = parse_time(r3.content)
    await q3.delete(); await r3.delete()

    end_time = datetime.now(timezone.utc) + timedelta(seconds=duration)

    embed = discord.Embed(
        title="🎁 Giveaway",
        description=f"{prize}\nFin <t:{int(end_time.timestamp())}:R>\n🎉 Réagissez pour participer",
        color=0x2f3136
    )

    msg = await ctx.send(embed=embed)
    await msg.add_reaction("🎉")

    await asyncio.sleep(duration)

    new_msg = await ctx.channel.fetch_message(msg.id)
    users = [u async for u in new_msg.reactions[0].users() if not u.bot]

    if not users:
        return await ctx.send("❌ Aucun participant.")

    winners = random.sample(users, min(winners_count, len(users)))
    mentions = " ".join([w.mention for w in winners])

    claim_time = 30

    giveaways[msg.id] = {
        "winners": winners,
        "claimed": False,
        "users": users,
        "winners_count": winners_count
    }

    await ctx.send(f"🎉 Gagnants : {mentions}\n⏱ {claim_time}s pour `+gwclaim`")

    await asyncio.sleep(claim_time)

    if not giveaways[msg.id]["claimed"]:
        new_winners = random.sample(users, min(winners_count, len(users)))
        new_mentions = " ".join([w.mention for w in new_winners])

        await ctx.send(f"🔁 Nouveau tirage : {new_mentions}")

# =========================
# CLAIM
# =========================
@bot.command()
async def gwclaim(ctx):

    for data in giveaways.values():
        if ctx.author in data["winners"]:

            if data["claimed"]:
                return await ctx.send("❌ Déjà réclamé.")

            data["claimed"] = True
            return await ctx.send(f"✅ {ctx.author.mention} a réclamé son gain !")

    await ctx.send("❌ Tu n'es pas gagnant.")
