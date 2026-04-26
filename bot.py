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
    await ctx.send(f"✔ {member.mention} a reçu le rôle {role.name}")

# =========================
# ⛔ TEMP BAN
# =========================
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, duration: int, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f"⛔ {member} banni pour {duration}s")

    await asyncio.sleep(duration)

    try:
        await ctx.guild.unban(discord.Object(id=member.id))
        await ctx.send(f"🔓 {member} débanni")
    except:
        pass

# =========================
# 🔇 TEMP MUTE
# =========================
@bot.command()
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, duration: int):
    until = datetime.now(timezone.utc) + timedelta(seconds=duration)
    await member.edit(timed_out_until=until)

    await ctx.send(f"🔇 {member.mention} mute {duration}s")

# =========================
# 🧹 CLEAR MESSAGES
# =========================
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    if amount > 100:
        amount = 100

    deleted = await ctx.channel.purge(limit=amount)
    await ctx.send(f"🧹 {len(deleted)} messages supprimés", delete_after=3)

# =========================
# 🚨 ANTI-SPAM SIMPLE
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
        await message.channel.send(f"⚠️ {message.author.mention} anti-spam activé")
        return

    await bot.process_commands(message)

# =========================
# 🎁 GIVEAWAY MODAL
# =========================
class GiveawayModal(discord.ui.Modal, title="Créer un Giveaway"):

    name = discord.ui.TextInput(label="Nom du giveaway")
    info = discord.ui.TextInput(label="Informations")
    duration = discord.ui.TextInput(label="Durée (secondes)")
    prize = discord.ui.TextInput(label="Gain")

    async def on_submit(self, interaction: discord.Interaction):

        embed = discord.Embed(
            title=f"🎁 {self.name.value}",
            description=f"""
📌 Info : {self.info.value}
🏆 Gain : {self.prize.value}
⏳ Durée : {self.duration.value}s

Réagis 🎉 pour participer !
            """,
            color=0xffcc00
        )

        msg = await interaction.channel.send(embed=embed)
        await msg.add_reaction("🎉")

        await interaction.response.send_message("🎁 Giveaway lancé !", ephemeral=True)

        await asyncio.sleep(int(self.duration.value))

        new_msg = await interaction.channel.fetch_message(msg.id)
        users = [u async for u in new_msg.reactions[0].users()]
        users = [u for u in users if not u.bot]

        if not users:
            await interaction.channel.send("❌ Aucun participant.")
            return

        winner = random.choice(users)

        await interaction.channel.send(
            f"🎉 GIVEAWAY TERMINÉ !\n"
            f"🏆 Gagnant : {winner.mention}\n"
            f"🎁 Gain : {self.prize.value}"
        )

# =========================
# 🎁 GIVEAWAY COMMAND
# =========================
@bot.command()
async def giveaway(ctx):
    await ctx.send_modal(GiveawayModal())

# =========================
# 🚀 RUN BOT
# =========================
bot.run(os.environ["TOKEN"])
