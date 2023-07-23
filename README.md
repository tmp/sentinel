# sentinel
a dead-simple Discord bot for managing locked-down server environments

### why?
i initially made this bot for a specific server i'm in where we need to manage a locked-down environment. we needed a simple bot to manually approve new joins to the server before they were able to see any channels. the code is posted here because i noticed i haven't posted many of my projects and i've decided to begin doing so.

### how to run
1. make a bot account
2. enable `members` and `message_content` intents
3. `git clone https://github.com/tmp/sentinel`
4. `pip install discord`
5. edit `bot_config.py` with the bot token
6. `touch sentinel.sqlite3`
7. add your user ID to the admin_users table (can use [DB Browser for SQLite](https://sqlitebrowser.org/))
8. `python3 sentinel.py`

### configure the bot
1. invite the bot to a server
2. register the server using `/register_server guild_id admin_role_id verified_role_id alert_channel_id` either in direct messages or inside a channel the bot can see + use slash commands in
3. that's it. when a new member joins the server you'll need to manually approve them through sentinel before they're able to see anything else.
