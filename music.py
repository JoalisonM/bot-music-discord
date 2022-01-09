import os
import discord
from dotenv import load_dotenv
from discord.ext import commands
from youtube_dl import YoutubeDL

from faunadb import query as q
from faunadb.objects import Ref
from faunadb.client import FaunaClient

load_dotenv()

class bot_music(commands.Cog):

  def __init__(self, bot):
    self.bot = bot
    self.is_playing = False
    self.music_queue = []
    self.YDL_OPTIONS = {"format": "bestaudio", "noplaylist": "True"}
    self.FFMPEG_OPTIONS = {"before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5", "options": "-vn"}
    self.voice = ""
    self.db_client = FaunaClient(secret=os.getenv("FAUNADB_KEY"))

  # Search musics on Youtube
  def search_youtube(self, music):#Retorna a URL da música, ou False se algum erro ocorrer
    with YoutubeDL(self.YDL_OPTIONS) as ydl:
      try:
        info = ydl.extract_info("ytsearch:%s" % music, download=False)["entries"][0]
      except Exception:
        return False
    
    return {"source": info["formats"][0]["url"], "title": info["title"]}

  def play_next(self):#Olha a fila de músicas e toca a primeira música da fila
    if(len(self.music_queue) > 0):
      self.is_playing = True
      m_url = self.music_queue[0][0]["source"]
      self.music_queue.pop(0)
      self.voice.play(discord.FFmpegPCMAudio(m_url, **self.FFMPEG_OPTIONS), after=lambda e: self.play_next())
    else:
      self.is_playing = False
  
  async def play_music(self):
    if(len(self.music_queue) > 0):

      self.is_playing = True
      m_url = self.music_queue[0][0]["source"]

      if(self.voice == "" or not self.voice.is_connected() or self.voice == None):
        self.voice = await self.music_queue[0][1].connect()
      else:
        await self.voice.move_to(self.music_queue[0][1])

      self.music_queue.pop(0)
      self.voice.play(discord.FFmpegPCMAudio(m_url, **self.FFMPEG_OPTIONS), after=lambda e: self.play_next())
   
    else:
   
      self.is_playing = False
  
  @commands.command(name="play", help="Toca o som dj")
  async def play(self, ctx, *args):

    query = " ".join(args)

    voice_channel = ctx.author.voice.channel
    if voice_channel is None:
      await ctx.send("Conecte a um canal de voz!")
    else:
      song = self.search_youtube(query)
      if type(song) == type(True):
        await ctx.send("Não foi possível baixar a música")
      else:
        await ctx.send("Música adicionada a fila")
        self.music_queue.append([song, voice_channel, query])

        if self.is_playing == False:
          await self.play_music()
  
  @commands.command(name="skip", help="Pra pular aquela música que o caba tá abusado")
  async def skip(self, ctx):
    if self.voice != "" and self.voice:
      self.voice.stop()

      await self.play_music()
  
  @commands.command(name="leave", help="Disconnecting bot from VC")
  async def leave(self, ctx):
    if(self.voice == "" or not self.voice.is_connected() or self.voice == None):
      return
    else:
      await self.voice.disconnect()

  @commands.command(name="queue", help="Lista todas as músicas da fila")
  async def queue(self, ctx):
    saida = "```python\nLISTA DE MÚSICAS\n"
    for i in range(len(self.music_queue)):
      saida += f"[{i}] {self.music_queue[i][2]}.\n"
    saida += "```"
    await ctx.send(saida)

  @commands.command(name="addplaylist", help="Cria uma playlist de músicas")
  async def addplaylist(self, ctx, name):
    try:

      self.db_client.query(
        q.if_(
          q.not_(
            q.exists(
              q.match(
                q.index("playlist_by_name"),
                q.casefold(name)
              )
            )
          ),
          q.create(
            q.collection("playlists"),
            {"data": {"name": name}},
          ),
          q.get(
            q.match(
              q.index("playlist_by_name"),
              q.casefold(name)
            )
          )
        )
      )

      playlist = self.db_client.query(
        q.get(
          q.match(
            q.index("playlist_by_name"),
            q.casefold(name)
          )
        )
      )

      if(playlist):
        await ctx.send("Playlist já existe, por favor crie uma nova")
      else:
        await ctx.send("Playlist criada com sucesso!")
  
    except Exception:
      return False
  
  @commands.command(name="add", help="Adiciona a música na playlist")
  async def add(self, ctx, playlistName, music):
    playlistId = self.db_client.query(
      q.select(
        "ref",
        q.get(
          q.match(
            q.index("playlist_by_name"),
            q.casefold(playlistName)
          )
        ) 
      )
    )

    musicData = { 
      "playlistId": playlistId,
      "name": music,
    }
    
    self.db_client.query(
      q.create(
        q.collection("musics"),
        {"data": musicData}
      )
    )

    playlistDataName = self.db_client.query(
      q.select(
        "data",
        q.get(
          q.match(
            q.index("playlist_by_name"),
            q.casefold(playlistName)
          )
        ) 
      )
    )

    await ctx.send("Música adicionada à playlist %s"%(playlistDataName["name"]))