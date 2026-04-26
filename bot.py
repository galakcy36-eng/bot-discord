import discord
import os
import random
import asyncio
from datetime import datetime, timedelta, timezone
from discord.ext import commands

# 🔧 INTENTS OBLIGATOIRES
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="+", intents=intents)

# 📡 READY
@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")

# ➕ ADD ROLE
@bot.command()
@commands.has_permissions(manage_roles=True)
async def addrole(ctx, member: discord.Member, role: discord.Role):
    await member.add_roles(role)
    await ctx.send(f"✔ {member.mention} a reçu le rôle {role.name}")

# ⛔ TEMP BAN
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, duration: int, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f"⛔ {member} banni pour {duration} secondes")

    await asyncio.sleep(duration)

    try:
        await ctx.guild.unban(discord.Object(id=member.id))
        await ctx.send(f"🔓 {member} a été débanni")
    except:
        pass

# 🔇 TEMP MUTE
@bot.command()
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, duration: int):
    until = datetime.now(timezone.utc) + timedelta(seconds=duration)
    await member.edit(timed_out_until=until)

    await ctx.send(f"🔇 {member.mention} mute {duration} secondes")

# 🎁 GIVEAWAY PRO
@bot.command()
async def giveaway(ctx, duration: int, *, prize: str):

    embed = discord.Embed(
        title="🎁 GIVEAWAY",
        description=(
            f"🏆 **Prix : {prize}**\n"
            f"⏳ **Durée : {duration} secondes**\n\n"
            "Réagis 🎉 pour participer !"
        ),
        color=0xffcc00
    )

    msg = await ctx.send(embed=embed)
    await msg.add_reaction("🎉")

    await asyncio.sleep(duration)

    new_msg = await ctx.channel.fetch_message(msg.id)
    users = [u async for u in new_msg.reactions[0].users()]
    users = [u for u in users if not u.bot]

    if not users:
        await ctx.send("❌ Aucun participant.")
        return

    winner = random.choice(users)

    await ctx.send(
        f"🎉 Félicitations {winner.mention} !\n"
        f"🏆 Tu as gagné **{prize}** !"
    )

# 🚀 RUN BOT
bot.run(os.environ["TOKEN"])
bot.run(os.environ["TOKEN"])
