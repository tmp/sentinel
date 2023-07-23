# sentinel
a dead-simple Discord bot for managing locked-down server environments

### why?
i initially made this bot for a specific server i'm in where we need to manage a locked-down environment. we needed a simple bot to manually approve new joins to the server before they were able to see any channels. the code is posted here because i noticed i haven't posted many of my projects and i've decided to begin doing so.

### how to run
1. `git clone https://github.com/tmp/sentinel`
2. `pip install discord`
3. edit `bot_config.py` with the bot token
4. `python3 sentinel.py`

### configure the bot
1. invite the bot to a server
2. register the server using `/register_server guild_id admin_role_id verified_role_id alert_channel_id`
3. that's it. when a new member joins the server you'll need to manually approve them through sentinel before they're able to see anything else.
