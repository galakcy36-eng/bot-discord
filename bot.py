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
# 📊 STOCKAGE SIMPLE
# =========================
user_stats = {}       # messages + vocal
giveaways = {}        # giveaways actifs

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

    # join vocal
    if before.channel is None and after.channel is not None:
        user_stats[uid]["join"] = datetime.now()

    # leave vocal
    elif before.channel is not None and after.channel is None:
        join = user_stats[uid]["join"]
        if join:
            user_stats[uid]["voice"] += (datetime.now() - join).seconds
            user_stats[uid]["join"] = None

# =========================
# 🎁 VIEW GIVEAWAY
# =========================
class GiveawayView(discord.ui.View):
    def __init__(self, msg_id):
        super().__init__(timeout=None)
        self.msg_id = msg_id

    @discord.ui.button(label="Participer", style=discord.ButtonStyle.success)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):

        data = giveaways.get(self.msg_id)
        if not data:
            return await interaction.response.send_message("❌ Giveaway introuvable.", ephemeral=True)

        member = interaction.user
        missing = []

        # 🚫 BYPASS
        if any(r in member.roles for r in data["bypass"]):
            data["participants"].add(member.id)
            return await interaction.response.send_message("✔ Bypass détecté, participation acceptée.", ephemeral=True)

        # 🎭 ROLE
        if data["role_req"] and data["role_req"] not in member.roles:
            missing.append(f"🎭 Rôle requis : {data['role_req'].mention}")

        stats = user_stats.get(member.id, {"messages": 0, "voice": 0})

        # 💬 MESSAGES
        if stats["messages"] < data["msg_req"]:
            missing.append(f"💬 Messages requis : {data['msg_req']}")

        # 🎙 VOCAL
        if stats["voice"] < data["vc_req"]:
            missing.append(f"🎙 Vocal requis : {data['vc_req']}s")

        if missing:
            return await interaction.response.send_message(
                "❌ Tu n'as pas les conditions requises :\n" + "\n".join(missing),
                ephemeral=True
            )

        data["participants"].add(member.id)
        await interaction.response.send_message("🎉 Tu participes au giveaway !", ephemeral=True)

    @discord.ui.button(label="Quitter", style=discord.ButtonStyle.danger)
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):

        data = giveaways.get(self.msg_id)
        if not data:
            return await interaction.response.send_message("❌ Giveaway introuvable.", ephemeral=True)

        data["participants"].discard(interaction.user.id)
        await interaction.response.send_message("👋 Tu as quitté le giveaway.", ephemeral=True)

# =========================
# 🎁 GIVEAWAY COMMAND
# =========================
@bot.command()
async def giveaway(ctx):

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        # 🎁 LOT
        await ctx.send("🎁 Quel est le lot ?")
        prize = (await bot.wait_for("message", timeout=60, check=check)).content

        # 👥 WINNERS
        await ctx.send("👥 Nombre de gagnants ?")
        winners = int((await bot.wait_for("message", timeout=60, check=check)).content)

        # ⏳ DURATION
        await ctx.send("⏳ Durée (secondes) ?")
        duration = int((await bot.wait_for("message", timeout=60, check=check)).content)

        # 💬 MSG REQUIS
        await ctx.send("💬 Messages requis ?")
        msg_req = int((await bot.wait_for("message", timeout=60, check=check)).content)

        # 🎙 VOCAL REQUIS
        await ctx.send("🎙 Vocal requis (secondes) ?")
        vc_req = int((await bot.wait_for("message", timeout=60, check=check)).content)

        # 🎭 ROLE REQUIS (PING)
        await ctx.send("🎭 Ping le rôle requis (ou none)")
        r = await bot.wait_for("message", timeout=60, check=check)
        role_req = r.role_mentions[0] if r.role_mentions else None

        # 🚫 BYPASS ROLES
        await ctx.send("🚫 Ping les rôles bypass (ou none)")
        r2 = await bot.wait_for("message", timeout=60, check=check)
        bypass = r2.role_mentions if r2.role_mentions else []

        # 🖼 IMAGE
        await ctx.send("🖼 URL image (thumbnail)")
        image_url = (await bot.wait_for("message", timeout=60, check=check)).content

    except asyncio.TimeoutError:
        return await ctx.send("⏱️ Temps écoulé, giveaway annulé.")

    # =========================
    # 🎉 EMBED
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

    embed.set_thumbnail(url=image_url)

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
        "prize": prize
    }

    # =========================
    # ⏳ FIN
    # =========================
    await asyncio.sleep(duration)

    data = giveaways.get(msg.id)
    if not data:
        return

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
