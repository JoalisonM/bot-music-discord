import os
import re
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
  
  async def play_music(self):#toca a próxima música na fila
    if(len(self.music_queue) > 0):

      print("ENTREI")

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
  async def play(self, ctx, *args):#se conecta em um canal de voz e toca a música requisitada

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
  
  @commands.command(name="queue", help="Lista as músicas que estão na fila")
  async def queue(self, ctx):
    
    retval = ""
    for i in range(0, len(self.music_queue)):
      retval += f"{i+1} - " + self.music_queue[i][0]["title"] + "\n"
    
    if retval != "":
      await ctx.send(retval)
    else:
      await ctx.send("Não tem músicas na fila")
  
  @commands.command(name="skip", help="Pra pular aquela música que o caba tá abusado")
  async def skip(self, ctx):
    if self.voice != "" and self.voice:
      self.voice.stop()
      await self.play_music()

  @commands.command(name="leave", help="Disconnecting bot from voice channel")
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

  @commands.command(name="playlists", help="Lista todas as músicas da fila")
  async def playlists(self, ctx):
    try:

      playlists = self.db_client.query(
        q.paginate(
          q.match(
            q.index("findAllPlaylists")
          )
        )
      )

      playlists = playlists['data']
      ids = re.findall("\d+",str(playlists))

      saida = "```python\nLISTA DE PLAYLISTS\n"
      for i in range(len(playlists)):
        id = ids[i]
        playlist = self.db_client.query(
          q.get(
            q.ref(
              q.collection("playlists"), id
            )
          )
        )
        saida += str(playlist['data']['name']) + "\n"
      saida += "\n```"

      await ctx.send(saida)

    except:
      await ctx.send("Um erro ocorreu")


  @commands.command(name="addplaylist", help="Cria uma playlist de músicas")
  async def addplaylist(self, ctx, *name):
    try:

      if(len(name) > 1):
        await ctx.send("O nome da playlist não pode conter espaços")
        return

      name = name[0]

      playlist = self.db_client.query(
        q.paginate(
          q.match(
            q.index("findPlaylistByName"),
            name
          )
        )
      )

      playlist = playlist['data']

      if(len(playlist) > 0):
        await ctx.send("Playlist já existe, por favor crie uma nova")
      else:
        self.db_client.query(
          q.create(
            q.collection("playlists"),
            {"data": {"name": name}},
          )
        )
        await ctx.send("Playlist criada com sucesso!")

    except Exception:
      return False

  @commands.command(name="addto", help="Adiciona a música na playlist, ex: !add playlist música")
  async def add(self, ctx, *content):
    
    playlistName = content[0]

    list = []
    for i in range(1,len(content)):
      list.append(content[i])

    musicName = " ".join(list)

    musicData = { 
      "playlistName": playlistName,
      "name": musicName,
    }

    foundPlaylists = self.db_client.query(
      q.paginate(
        q.match(
          q.index("findPlaylistByName"),
          playlistName
        )
      )
    )

    foundPlaylists = foundPlaylists['data']

    if(len(foundPlaylists) > 0):
      self.db_client.query(
        q.create(
          q.collection("musics"),
          {"data": musicData}
        )
      )
      await ctx.send("Música adicionada à playlist %s"%(playlistName))
    else:
      await ctx.send("Playlist inexistente")

  @commands.command(name="playplaylist", help="Toca as músicas da playlist")
  async def playlist_musics(self, ctx, *name):
    
    try:

      voice_channel = ctx.author.voice.channel
      if voice_channel is None:
        await ctx.send("Conecte-se a um canal de voz!")

      playlistName = name[0]
      
      foundPlaylists = self.db_client.query(
        q.paginate(
          q.match(
            q.index("findPlaylistByName"),
            playlistName
          )
        )
      )

      foundPlaylists = foundPlaylists['data']

      if(len(foundPlaylists) == 0):
        await ctx.send("Playlist inexistente")
        return

      foundSongs = self.db_client.query(
        q.paginate(
          q.match(
            q.index("findMusicByPlaylistName"),
            playlistName
          )
        )
      )

      foundSongs = foundSongs['data']

      if(len(foundSongs) == 0):
        await ctx.send("Você ainda não adicionou nenhuma música a essa playlist")
        return

      ids = re.findall("\d+",str(foundSongs))
      songsNames = []
      for i in range(len(ids)):
        id = ids[i]
        music = self.db_client.query(
          q.get(
            q.ref(
              q.collection("musics"), id
            )
          )
        )
        songsNames.append(music['data']['name'])

      await ctx.send("Limpando fila de músicas...")
      self.music_queue.clear()
      for i in range(len(songsNames)):
        song = self.search_youtube(songsNames[i])
        self.music_queue.append([song, voice_channel, songsNames[i]])
        await ctx.send(f"{songsNames[i]} adicionada à fila...")


      await self.play_music()
      await ctx.send("Tocando playlist")

    except:
      return

  @commands.command(name="listplaylist", help="Lista as músicas da playlist")
  async def listplaylist(self, ctx, *name):
    
    try:

      playlistName = name[0]
      
      foundPlaylists = self.db_client.query(
        q.paginate(
          q.match(
            q.index("findPlaylistByName"),
            playlistName
          )
        )
      )

      foundPlaylists = foundPlaylists['data']

      if(len(foundPlaylists) == 0):
        await ctx.send("Playlist inexistente")
        return

      foundSongs = self.db_client.query(
        q.paginate(
          q.match(
            q.index("findMusicByPlaylistName"),
            playlistName
          )
        )
      )

      foundSongs = foundSongs['data']

      if(len(foundSongs) == 0):
        await ctx.send("Você ainda não adicionou nenhuma música a essa playlist")
        return

      ids = re.findall("\d+",str(foundSongs))
      songsNames = []
      for i in range(len(ids)):
        id = ids[i]
        music = self.db_client.query(
          q.get(
            q.ref(
              q.collection("musics"), id
            )
          )
        )
        songsNames.append(music['data']['name'])

      saida = "```python\n"
      for i in range(len(songsNames)):
        saida += f"[{i}] {songsNames[i]}.\n"
      saida += "```"

      await ctx.send(saida)

    except:
      await ctx.send("Um erro ocorreu")

  