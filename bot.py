import discord
import os

intents = discord.Intents.default()
intents.message_content = True  # 👈 OBLIGATOIRE

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print("Bot connecté !")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content == "!ping":
        await message.channel.send("pong 🏓")

client.run(os.environ['TOKEN'])
