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

bot = commands.Bot(command_prefix="+", intents=intents)

# =========================
# 📡 READY
# =========================
@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")

# =========================
# ➕ ADD ROLE
# =========================
@bot.command()
@commands.has_permissions(manage_roles=True)
async def addrole(ctx, member: discord.Member, role: discord.Role):
    await member.add_roles(role)
    await ctx.send(f"✔ {member.mention} a reçu {role.name}")

# =========================
# ⛔ TEMP BAN
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
    if amount > 100:
        amount = 100

    deleted = await ctx.channel.purge(limit=amount)
    await ctx.send(f"🧹 {len(deleted)} messages supprimés", delete_after=3)

# =========================
# 🚫 ANTI-SPAM
# =========================
user_messages = {}

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    uid = message.author.id
    now = datetime.now().timestamp()

    if uid not in user_messages:
        user_messages[uid] = []

    user_messages[uid].append(now)
    user_messages[uid] = [t for t in user_messages[uid] if now - t < 5]

    if len(user_messages[uid]) > 5:
        await message.channel.send(f"⚠️ {message.author.mention} stop spam")
        return

    await bot.process_commands(message)

# =========================
# 🎁 GIVEAWAY INTERACTIF
# =========================
@bot.command()
async def giveaway(ctx):

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    await ctx.send("🎁 Nom du giveaway ?")
    name = (await bot.wait_for("message", check=check)).content

    await ctx.send("📌 Informations ?")
    info = (await bot.wait_for("message", check=check)).content

    await ctx.send("⏳ Durée en secondes ?")
    duration = int((await bot.wait_for("message", check=check)).content)

    await ctx.send("🏆 Gain ?")
    prize = (await bot.wait_for("message", check=check)).content

    embed = discord.Embed(
        title=f"🎁 {name}",
        description=f"""
📌 Info : {info}
🏆 Gain : {prize}
⏳ Durée : {duration}s

Réagis 🎉 pour participer !
        """,
        color=0xffcc00
    )

    msg = await ctx.send(embed=embed)
    await msg.add_reaction("🎉")

    await ctx.send("✅ Giveaway lancé !")

    await asyncio.sleep(duration)

    new_msg = await ctx.channel.fetch_message(msg.id)
    users = [u async for u in new_msg.reactions[0].users()]
    users = [u for u in users if not u.bot]

    if not users:
        await ctx.send("❌ Aucun participant.")
        return

    winner = random.choice(users)

    await ctx.send(
        f"🎉 GIVEAWAY TERMINÉ !\n"
        f"🏆 Gagnant : {winner.mention}\n"
        f"🎁 Gain : {prize}"
    )

# =========================
# 🚀 RUN
# =========================
bot.run(os.environ["TOKEN"])
