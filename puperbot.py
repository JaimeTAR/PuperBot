import discord
from discord.ext import commands

import yt_dlp as youtube_dl
from youtube_search import YoutubeSearch as search
from spotipy.oauth2 import SpotifyClientCredentials
from lyricsgenius import Genius
import spotipy
from dotenv import load_dotenv

from datetime import timedelta
import json
import logging
import asyncio
import random
import os

#####################################################################################
############################ Load .env variables ####################################
#####################################################################################

load_dotenv()

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
IPV4 = os.getenv("IPV4")
BOT_TOKEN = os.getenv("BOT_TOKEN")
GENIUS_TOKEN = os.getenv("GENIUS_TOKEN")

genius = Genius(GENIUS_TOKEN)

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
    "cookiefile": "cookies.txt"
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
################################ SPOTIFY CREDENTIALS ################################
#####################################################################################

client_credentials_mgmt = SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
)

sp = spotipy.Spotify(client_credentials_manager=client_credentials_mgmt)

#####################################################################################
###################################### Bot setup ####################################
#####################################################################################

logger = logging.getLogger("discord")
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
handler.setFormatter(
    logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s")
)
logger.addHandler(handler)

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="puper ", intents=intents, help_command=None)

lock = asyncio.Lock()


# Apply the lock to all commands
@bot.before_invoke
async def before_any_command(ctx):
    await lock.acquire()


@bot.after_invoke
async def after_any_command(ctx):
    lock.release()


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")


#####################################################################################
########################### Bot helper functions ####################################
#####################################################################################


@bot.check
async def user_in_vc(ctx):
    """Global middleware to check if the user is in a voice channel before executing any command."""
    # if ctx.command.name in ["join", "leave"]:  # Exclude certain commands if needed
    #     return True  # Allow commands that don't need the user in a VC

    if ctx.author.voice and ctx.author.voice.channel:
        return True

    await ctx.send("You must be in a voice channel.")
    return False


async def ensure_bot_in_vc(ctx):
    """Middleware to make the bot join the user's voice channel if it's not already in one."""
    if ctx.voice_client is None:
        await ctx.author.voice.channel.connect()
    elif ctx.voice_client.channel != ctx.author.voice.channel:
        await ctx.voice_client.move_to(ctx.author.voice.channel)


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
            query = f"{track_name} - {first_artist}"
            queries.append(query)
    random.shuffle(queries)
    return queries


async def getSpotifyTrackQuery(url):
    url = str(url)
    track_ID = url.split("/")[-1].split("?")[0]
    result = sp.track(track_ID)
    first_artist = result["artists"][0]["name"]
    track_name = result["name"]

    query = f"{track_name} - {first_artist}"

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
            queueList.insert(0, query)
        else:
            queueList.append(query)
    if not urgent:
        await ctx.send(f"Se añadió a la cola: {arg}")


async def play(ctx, arg):
    await ctx.send(f"Buscando: {arg}")

    async with ctx.typing():
        if await isYoutubeUrl(arg):
            player = await YTDLSource.from_url(arg, loop=bot.loop)
        else:
            player = await YTDLSource.from_query(arg, loop=bot.loop)

        vc = ctx.voice_client

        vc.play(
            player,
            after=lambda e: bot.loop.create_task(play_next(ctx)),
        )

    await ctx.send(f"Now playing: {player.title}")


async def play_next(ctx):
    if queueList:  # Check if there are any songs in the queue
        arg = queueList.pop(0)
        await play(ctx, arg)
    else:
        vc = ctx.voice_client
        await vc.disconnect()  # Disconnect if queue is empty


#####################################################################################
################################## Bot Variables ####################################
#####################################################################################

queueList = []

playlistLinks = {
    0: "https://open.spotify.com/playlist/4NxWGWQOETCFRbGCKCJDww",  # Corridos
    1: "https://open.spotify.com/playlist/4qgYbmarI1Gnyz5HHAGoEa",  # Banda
    2: "https://open.spotify.com/playlist/61zazA5kwYP31Le1dczS7a",  # Alternativo
    3: "https://open.spotify.com/playlist/2hpv0UHaRKv4hlKXprmC2g",  # Trapgertino
    4: "https://open.spotify.com/playlist/5Y84YXLPRKpwkZhtJl6lVH",  # Jaime
    5: "https://open.spotify.com/playlist/5NVrLVDdnvYHo8eOWllRrJ",  # Las sabrosas
}

playlists = [
    "Corridos",
    "Banda",
    "Alternativo",
    "Trapgertino",
    "Jaime",
    "Las Sabrosas",
]

bot_commands = {
    "pon <url | search>": "Adds the song to the queue.",
    "ya <url | search>": "Places the song next in the queue.",
    "plists": "Displays a menu to select and play a playlist.",
    "plists <playlist number>": "Plays the selected playlist.",
    "queue": "Shows the first elements of the queue",
    "queue <page number>": "Shows the queue in the specified page",
    "lyrics <song name>": "Shows the lyrics of the specified song",
    "skip": "Skips the current song.",
    "shuffle": "Shuffles the queue.",
    "pause": "Pauses the current song.",
    "resume": "Resumes the current song.",
    "stop": "Stops the bot.",
    "salte": "Times out Puper for 10 seconds.",
    "help": "Displays this help message.",
}


class PlaylistsMenu(discord.ui.View):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx

    @discord.ui.select(
        placeholder="Choose a playlist",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(label=f"{i + 1}. {playlist}", value=str(i))
            for i, playlist in enumerate(playlists)
        ],
    )
    async def select_callback(self, select, interaction):
        self.disable_all_items()
        await interaction.message.edit(view=self)

        index = int(select.values[0])
        url = playlistLinks[index]

        await interaction.response.send_message(f"Playing {playlists[index]} playlist")
        await self.ctx.invoke(pon, arg=url)


#####################################################################################
################################## Bot Commands #####################################
#####################################################################################


@bot.command()
async def pon(ctx, *, arg):

    await ensure_bot_in_vc(ctx)

    await addToQueue(ctx, arg, False)

    vc = ctx.voice_client
    if not vc.is_playing() and not vc.is_paused():
        await play_next(ctx)


@bot.command()
async def ya(ctx, *, arg):

    await ensure_bot_in_vc(ctx)
    await addToQueue(ctx, arg, True)
    await ctx.send(f"{arg} is next in the queue.")

    vc = ctx.voice_client
    if not vc.is_playing() and not vc.is_paused():
        await play_next(ctx)


@bot.command()
async def shuffle(ctx):

    if queueList:
        random.shuffle(queueList)
        await ctx.send("Queue shuffled.")
    else:
        await ctx.send("Queue is empty.")


@bot.command()
async def skip(ctx):

    vc = ctx.voice_client
    if vc and vc.is_playing():
        vc.stop()
        await ctx.send("Skipped the song.")
    else:
        await ctx.send("No song is currently playing.")


@bot.command()
async def plists(ctx, arg=0):

    if arg == 0:
        await ctx.send(view=PlaylistsMenu(ctx))
    elif 1 <= arg <= len(playlists):
        url = playlistLinks[arg - 1]
        await ctx.send(f"Playing {playlists[arg - 1]} playlist")
        await ctx.invoke(pon, arg=url)
    else:
        await ctx.send(
            "Playlist doesnt exist, to see all playlists, type 'puper plists'"
        )


@bot.command()
async def queue(ctx, page: int = 1):

    if not queueList:
        await ctx.send("Queue is empty")
        return

    items_per_page = 10
    total_items = len(queueList)
    total_pages = (
        total_items + items_per_page - 1
    ) // items_per_page  # Calculate total pages

    # Ensure the page is within valid range
    if page < 1 or page > total_pages:
        await ctx.send(
            f"Invalid page number. Please choose a page between 1 and {total_pages}."
        )
        return

    start_index = (page - 1) * items_per_page
    end_index = start_index + items_per_page

    output = ""

    # Add page information (current page / total pages)
    output += f"\nPage {page} of {total_pages} \n"
    for index, item in enumerate(
        queueList[start_index:end_index], start=start_index + 1
    ):
        output += f"{index}. {item}\n"

    # Indicate more pages if necessary
    if end_index < total_items:
        output += "[...]"

    await ctx.send(output)


@bot.command()
async def lyrics(ctx, *, args):

    await ctx.send(f"Looking for lyrics for {args}...")

    async with ctx.typing():
        # Search for the song
        data = genius.search(args, per_page=5, page=1)
        song = data["hits"][0]["result"]["url"]

        # Get the lyrics
        lyrics = genius.lyrics(song_url=song)

        # Split the lyrics into chunks of 2000 characters
        chunk_size = 1800
        chunks = [lyrics[i : i + chunk_size] for i in range(0, len(lyrics), chunk_size)]

        # Send each chunk
        for chunk in chunks:
            await ctx.send(chunk)


@bot.command()
async def pause(ctx):

    vc = ctx.voice_client
    if vc:
        if vc.is_playing():
            vc.pause()
            await ctx.send("Paused the song.")
        else:
            await ctx.send("Already paused.")
    else:
        await ctx.send("I'm not in a voice channel")


@bot.command()
async def resume(ctx):

    vc = ctx.voice_client
    if vc:
        if vc.is_paused():
            vc.resume()
            await ctx.send("Resuming the song.")
        else:
            await ctx.send("Already playing.")
    else:
        await ctx.send("I'm not in a voice channel")


@bot.command()
async def stop(ctx):

    queueList.clear()
    vc = ctx.voice_client
    if vc and vc.is_playing():
        await vc.disconnect()
        await ctx.send("Bye!")
    else:
        await ctx.send("I'm not in a voice channel")


@bot.command()
async def salte(ctx):

    member_id = 434017185615052800
    member = ctx.guild.get_member(member_id)
    vc = ctx.voice_client

    if member:
        if member.voice:
            await ya(ctx, arg="Himno Nacional Mexicano (Version Escolar)")

            if vc and vc.is_playing():
                await skip(ctx)

            await asyncio.sleep(4)

            await member.timeout(timedelta(seconds=10), reason="A pensar")

            await ctx.send(f"Gracias Dios")

            await asyncio.sleep(25)
            await skip(ctx)
        else:
            await ctx.send(f"No está, menos mal")
    else:
        await ctx.send(f"No está en el servidor, menos mal")


@bot.command()
async def help(ctx):
    """Displays all available bot commands and their descriptions."""
    help_message = "**Available command list:**\n"
    for cmd, desc in bot_commands.items():
        help_message += f"**`puper {cmd}`** - {desc}\n"

    await ctx.send(help_message)


#############################################################################


bot.run(BOT_TOKEN)  # Run the bot with your token.
