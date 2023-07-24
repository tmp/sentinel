# pylint: disable=line-too-long, missing-module-docstring, missing-function-docstring, missing-class-docstring, broad-exception-caught

# sentinel
# dead-simple Discord bot for managing locked-down server environments

# first-party imports
import sqlite3
from threading import Lock

# third-party imports
import discord
from discord import app_commands
from discord.ext import commands

# local imports
from bot_config import bot_token

# bot configuration
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

# the actual bot object
bot = commands.Bot(command_prefix="!", intents=intents)

# used for converting discord snowflakes to epoch time
DISCORD_EPOCH = 1420070400000

# connect to SQLite database (or create it if it doesn't exist)
conn = sqlite3.connect('sentinel.sqlite3')
c = conn.cursor()
lock = Lock()

# create table for servers if it doesn't exist
c.execute('''
    CREATE TABLE IF NOT EXISTS servers (
        guild_id INTEGER PRIMARY KEY,
        admin_role_id INTEGER,
        verified_role_id INTEGER,
        alert_channel_id INTEGER
    )
''')

# create table to store admin user ids if it doesn't exist
c.execute('''
    CREATE TABLE IF NOT EXISTS admin_users (
        user_id INTEGER PRIMARY KEY
    )
''')

# checks to see if a user is a bot admin
def is_admin(user_id: int):
    return user_id in admin_user_ids

# returns guild information from the database
def get_guild_info(guild_id: int):
    with lock:
        c.execute("SELECT * FROM servers WHERE guild_id = ?", (guild_id,))
        data = c.fetchone()
    return data

# get list of all admin user ids
def get_admin_user_ids():
    with lock:
        c.execute("SELECT user_id FROM admin_users")
        admin_users = c.fetchall()
    return [user_id for (user_id,) in admin_users]

# convert discord snowflake to unix epoch time
def snowflake_to_epoch(snowflake, epoch=DISCORD_EPOCH):
    milliseconds = snowflake >> 22
    return int((milliseconds + epoch) / 1000)

# list of all bot administrators
admin_user_ids = get_admin_user_ids()

# this runs when the bot loads
@bot.event
async def on_ready():
    print("sentinel is up and running.")
    # game activity
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="new member joins"))
    try:
        # sync all commands
        synced_tree = await bot.tree.sync()
        print(f"synced {len(synced_tree)} commands.")
    except Exception as exc:
        print(f"exception: {exc}")

# ping pong
@bot.tree.command(name="ping")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("pong!")

# register a server with the bot (watch member joins on this server)
@bot.tree.command(name="register_server", description="register a server with the bot's database")
# parameters for this command
@app_commands.describe(
    guild_id="id of the server you want to register",
    admin_role_id="admin role id",
    verified_role_id="verified role id",
    alert_channel_id="alert channel id"
)
async def register_server(interaction: discord.Interaction, guild_id: str, admin_role_id: str, verified_role_id: str, alert_channel_id: str):
    # permission check
    if not is_admin(interaction.user.id):
        await interaction.response.send_message(content="you don't have permission to run this command.", ephemeral=True)
        return

    # attempt to add server to database
    with lock:
        try:
            c.execute("INSERT INTO servers VALUES (?,?,?,?)", (guild_id, admin_role_id, verified_role_id, alert_channel_id))
        except sqlite3.IntegrityError:
            await interaction.response.send_message(content=f"the server `{guild_id}` is already registered!")
        conn.commit()

    await interaction.response.send_message(content=f"server `{guild_id}` registered successfully.")

# UI view for the buttons when a user joins
class JoinResponseButtons(discord.ui.View):
    # initialize class
    def __init__(self, user_id: int, guild_info):
        super().__init__()
        self.user_id = user_id
        self.guild_info = guild_info

    # yes button
    @discord.ui.button(label="yes, give them access to the server", style=discord.ButtonStyle.success)
    async def yes_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # check if the user has the admin role
        if self.guild_info[1] not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message(content="you don't have permission to use this button.", ephemeral=True)
            return

        # fetch guild and member info
        guild = interaction.guild
        member = guild.get_member(self.user_id)

        # if the user is a part of the guild
        if member:
            # get the verified role object
            verified_role = discord.utils.get(guild.roles, id=self.guild_info[2])
            if verified_role:
                # add the role to the user
                await member.add_roles(verified_role)
                await interaction.response.send_message("user verified!")
        else:
            await interaction.response.send_message("failed to verify user!")

    # no button
    @discord.ui.button(label="no, ban them!", style=discord.ButtonStyle.danger)
    async def no_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # check if the user has the admin role
        if self.guild_info[1] not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message(content="you don't have permission to use this button.", ephemeral=True)
            return

        # fetch guild and member info
        guild = interaction.guild
        member = guild.get_member(self.user_id)

        # if the user is a part of the guild
        if member:
            # ban the user
            await member.ban(reason="[sentinel] not verified")
            await interaction.response.send_message("user banned!")
        else:
            await interaction.response.send_message("failed to ban user!")

# runs whenever a member joins to a guild the bot is in
@bot.event
async def on_member_join(member):
    # fetch guild info from database
    guild_info = get_guild_info(member.guild.id)

    # if nothing is found in the database, we're not tracking the guild
    # so we can just ignore this
    if not guild_info:
        return

    # save all the important info from guild_info into their own variables
    _, admin_role_id, _, alert_channel_id = guild_info
    # get the admin role object
    admin_role = discord.utils.get(member.guild.roles, id=admin_role_id)
    # get the channel object for the alert channel
    channel = bot.get_channel(alert_channel_id)

    # if we couldn't get this info, we must ignore this join event
    if not admin_role or not channel:
        return

    # prepare embed
    embed = discord.Embed(title=f"`{member.name}` just joined, are they meant to be here?", color=0xff0000)
    embed.set_thumbnail(url=member.avatar)
    embed.add_field(name="user details", value=f"name: {member.name}\nid: {member.id}\ncreation date: <t:{snowflake_to_epoch(member.id)}>", inline=False)

    # prepare view
    view = JoinResponseButtons(member.id, guild_info)

    # send the embed + view into admin channel
    await channel.send(content=admin_role.mention, embed=embed, view=view)

bot.run(bot_token)
