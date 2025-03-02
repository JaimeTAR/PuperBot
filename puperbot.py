import asyncio
import discord
from discord.ext import commands
import yt_dlp as youtube_dl
from youtube_search import YoutubeSearch as search
import json
import logging
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import random
from datetime import timedelta
from dotenv import load_dotenv
import os

#####################################################################################
############################ Load .env variables ####################################
#####################################################################################

load_dotenv()

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
IPV4 = os.getenv("IPV4")
BOT_TOKEN = os.getenv("BOT_TOKEN")

#####################################################################################
################################ BOT DETAILS ########################################
#####################################################################################

description = """Discord Music Bot"""

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="puper ", description=description, intents=intents)

handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")

#####################################################################################
################################ SPOTIFY CREDENTIALS ################################
#####################################################################################

client_credentials_mgmt = SpotifyClientCredentials(
    client_id = SPOTIFY_CLIENT_ID,
    client_secret = SPOTIFY_CLIENT_SECRET,
)

sp = spotipy.Spotify(client_credentials_manager=client_credentials_mgmt)

#####################################################################################
################################ YOUTUBE SETUP ######################################
#####################################################################################

youtube_dl.utils.bug_reports_message = lambda: ""

ytdl_format_options = {
    "format": "bestaudio/best",
    "outtmpl": "./Songs/%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "source_address": IPV4,  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    "options": "-vn",
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get("title")
        self.url = data.get("url")

    @classmethod
    async def from_url(cls, url, *, loop=None):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, lambda: ytdl.extract_info(url, download=True)
        )

        if "entries" in data:
            # take first item from a playlist
            data = data["entries"][0]

        filename = ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

    @classmethod
    async def from_query(cls, query, *, loop=None):
        query = str(query)

        query = query

        results = search(query, max_results=1).to_json()

        resultsJson = json.loads(results)

        selected_result = None

        selected_result = resultsJson["videos"][0]

        url = "youtube.com/watch?v=" + selected_result["id"]
        print(url)
        print("-----------------------------------")

        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, lambda: ytdl.extract_info(url, download=True)
        )

        if "entries" in data:
            data = data["entries"][0]

        filename = ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


#####################################################################################
################################ BOT EVENTS #########################################
#####################################################################################


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")


#####################################################################################
################################ BOT COMMANDS #######################################
#####################################################################################

queue = []
playlists = [
    {"Corridos": "https://open.spotify.com/playlist/4NxWGWQOETCFRbGCKCJDww"},
    {"Banda": "https://open.spotify.com/playlist/4qgYbmarI1Gnyz5HHAGoEa"},
    {"Alternativo": "https://open.spotify.com/playlist/61zazA5kwYP31Le1dczS7a"},
    {"Trapgertino": "https://open.spotify.com/playlist/2hpv0UHaRKv4hlKXprmC2g"},
    {"Jaime": "https://open.spotify.com/playlist/5Y84YXLPRKpwkZhtJl6lVH"},
    {"Las Sabrosas": "https://open.spotify.com/playlist/5NVrLVDdnvYHo8eOWllRrJ"},
    {
        "Cumbias de Microbusero": "https://open.spotify.com/playlist/0EfZGNw0JHvoCkNfnMDYAU"
    },
]


@bot.command()
async def pon(ctx, *, arg):
    if ctx.voice_client is None:
        await join(ctx)
    vc = ctx.voice_client

    await addToQueue(ctx, arg, False)

    # Start playing if nothing is currently playing
    if not vc.is_playing():
        await play_next(ctx, vc)


@bot.command()
async def shuffle(ctx):
    random.shuffle(queue)
    await ctx.send("Queue shuffleada alv")


@bot.command()
async def ya(ctx, *, arg):
    if ctx.voice_client is None:
        await ctx.invoke(pon, arg=arg)
    else:
        await addToQueue(ctx, arg, True)

    await ctx.send(f"Se puso {arg} en la que sigue")


@bot.command()
async def skip(ctx):
    if ctx.voice_client.is_playing():
        ctx.voice_client.stop()  # Stop the current song, triggering `play_next`
        await ctx.send("Skipped the song!")
    else:
        await ctx.send("No song is currently playing.")


@bot.command()
async def plists(ctx, *, arg=0):
    if arg != 0:
        name, url = list(playlists[arg - 1].items())[0]
        await ctx.send(f"Poniendo playlist de {name}")
        await ctx.invoke(pon, arg=url)
    else:
        output_text = ""
        for i, playlist in enumerate(playlists):
            name, url = list(playlist.items())[0]
            output_text += f"{i + 1}. {name}\n"
        await ctx.send(output_text)


@bot.command()
async def salte(ctx):
    member_id = 434017185615052800
    member = ctx.guild.get_member(member_id)
    vc = ctx.voice_client

    if member:
        if member.voice:
            if vc:
                if vc.is_playing():
                    await ya(ctx, arg="Himno Nacional Mexicano")
                    await skip(ctx)
                else:
                    await ctx.invoke(pon, arg="Himno Nacional Mexicano")
            else:
                await ctx.invoke(pon, arg="Himno Nacional Mexicano")

            await asyncio.sleep(7)

            await member.timeout(timedelta(seconds=10), reason="A pensar")

            await ctx.send(f"Gracias Dios")

            await asyncio.sleep(30)
            await skip(ctx)
        else:
            await ctx.send(f"No está, menos mal")


#####################################################################################
################################ BOT FUNCTIONS ######################################
#####################################################################################


async def join(ctx):
    channel = ctx.message.author.voice.channel

    await channel.connect()


async def isUrl(query):
    query = str(query)
    return query.startswith("http")


async def isYoutubeUrl(query):
    query = str(query)
    return query.startswith("https://youtube.com/") or query.startswith(
        "https://youtu.be/"
    )


async def isSpotifyUrl(query):
    query = str(query)
    return query.startswith("https://open.spotify.com/")


async def isSpotifyPlaylist(url):
    url = str(url)
    return await isSpotifyUrl(url) and url.find("playlist") != -1


async def isSpotifyTrack(url):
    url = str(url)
    return await isSpotifyUrl(url) and url.find("track") != -1


async def getSpotifyPlaylistQueries(url):
    url = str(url)
    playlist_ID = url.split("/")[-1].split("?")[0]
    results = sp.playlist_tracks(playlist_ID)
    tracks = results["items"]
    queries = []
    while results["next"]:
        results = sp.next(results)
        tracks.extend(results["items"])

    for item in tracks:
        track_info = item.get("track")  # Check if 'track' exists in item
        if track_info:  # Only proceed if 'track' is not None
            track_name = track_info.get("name", "Unknown Track")
            first_artist = track_info.get("artists", [{}])[0].get(
                "name", "Unknown Artist"
            )
            query = f"{first_artist} - {track_name}"
            queries.append(query)
    random.shuffle(queries)
    return queries


async def getSpotifyTrackQuery(url):
    url = str(url)
    track_ID = url.split("/")[-1].split("?")[0]
    result = sp.track(track_ID)
    artist_name = result["artists"][0]["name"]
    song_name = result["name"]

    query = artist_name + " " + song_name

    return query


async def addToQueue(ctx, arg, urgent):
    queries = []
    async with ctx.typing():
        if await isSpotifyPlaylist(arg):
            queries = await getSpotifyPlaylistQueries(arg)
        elif await isSpotifyTrack(arg):
            queries.append(await getSpotifyTrackQuery(arg))
        else:
            queries.append(arg)
    for query in queries:
        if urgent:
            queue.insert(0, query)
        else:
            queue.append(query)
    if not urgent:
        await ctx.send(f"Se añadió a la cola: {arg}")


async def play(ctx, arg, vc):
    await ctx.send(f"Buscando: {arg}")
    async with ctx.typing():
        if await isYoutubeUrl(arg):
            player = await YTDLSource.from_url(arg, loop=bot.loop)
        else:
            player = await YTDLSource.from_query(arg, loop=bot.loop)

        vc.play(
            player,
            after=lambda e: bot.loop.create_task(play_next(ctx, vc)),
            bitrate=240,
            signal_type="music",
        )

    await ctx.send(f"Now playing: {player.title}")


async def play_next(ctx, vc):
    if queue:  # Check if there are any songs in the queue
        arg = queue.pop(0)
        await play(ctx, arg, vc)
    else:
        await vc.disconnect()  # Disconnect if queue is empty


#####################################################################################
################################ BOT RUN ############################################
#####################################################################################

bot.run(
    BOT_TOKEN,
    log_handler=handler,
    log_level=logging.DEBUG,
)
