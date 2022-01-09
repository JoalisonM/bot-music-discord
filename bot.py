import os
import discord
from dotenv import load_dotenv
from discord.ext import commands

from music import bot_music

load_dotenv()

tokenDiscord = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

bot.add_cog(bot_music(bot))

bot.run(tokenDiscord)