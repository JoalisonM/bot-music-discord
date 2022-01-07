import discord
from discord.ext import commands

from music import bot_music

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

bot.add_cog(bot_music(bot))

token = ""
with open("token.txt") as file:
  token = file.read()

bot.run(token)