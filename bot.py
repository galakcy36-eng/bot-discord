import discord
import os
import random
import asyncio
from discord.ext import commands

# 🔧 INTENTS (OBLIGATOIRE)
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="+", intents=intents)

# 📡 BOT READY
@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")

# ➕ ADD ROLE
@bot.command()
@commands.has_permissions(manage_roles=True)
async def addrole(ctx, member: discord.Member, role: discord.Role):
    await member.add_roles(role)
    await ctx.send(f"✔ {member.mention} a reçu le rôle {role.name}")

# ⛔ BAN
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f"⛔ {member} a été banni")

# 🔇 MUTE (timeout 10 min)
@bot.command()
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member):
    timeout = discord.utils.utcnow() + discord.timedelta(minutes=10)
    await member.edit(timed_out_until=timeout)
    await ctx.send(f"🔇 {member.mention} mute 10 minutes")

# 🎁 GIVEAWAY
@bot.command()
async def giveaway(ctx, duration: int, *, prize: str):

    embed = discord.Embed(
        title="🎁 GIVEAWAY",
        description=f"Prix : **{prize}**\nRéagis 🎉 pour participer !\nDurée : {duration} secondes",
        color=0x00ffcc
    )

    msg = await ctx.send(embed=embed)
    await msg.add_reaction("🎉")

    await asyncio.sleep(duration)

    new_msg = await ctx.channel.fetch_message(msg.id)
    users = await new_msg.reactions[0].users().flatten()

    users = [u for u in users if not u.bot]

    if len(users) == 0:
        await ctx.send("❌ Aucun participant.")
        return

    winner = random.choice(users)

    await ctx.send(f"🏆 Félicitations {winner.mention}, tu as gagné **{prize}** !")

# 🚀 LANCEMENT DU BOT
bot.run(os.environ["TOKEN"])
