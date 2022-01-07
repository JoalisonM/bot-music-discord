import discord
from discord.ext import commands

from music import bot_music

bot = commands.Bot(command_prefix="!")

bot.add_cog(bot_music(bot))

token = ""
with open("token.txt") as file:
  token = file.read()

bot.run(token)