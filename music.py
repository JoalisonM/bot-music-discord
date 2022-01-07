import discord
from discord.ext import commands
from youtube_dl import YoutubeDL

class bot_music(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

    self.is_playing = False

    self.music_queue = []
    self.YDL_OPTIONS = {"format": "bestaudio", "noplaylist": "True"}
    self.FFMPEG_OPTIONS = {"before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5", "options": "-vn"}
    self.voice = ""

  def search_youtube(self, music):
    with YoutubeDL(self.YDL_OPTIONS) as ydl:
      try:
        info = ydl.extract_info("ytsearch:%s" % music, download=False)["entries"][0]
      except Exception:
        return False
    
    return {"source": info["formats"][0]["url"], "title": info["title"]}

  def play_next(self):
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
      
      print(self.music_queue)

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
        self.music_queue.append([song, voice_channel])

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
  
  @commands.command(name="leave", help="Disconecta o bot do canal de voz")
  async def leave(self, ctx):
    await self.voice.disconnect()
