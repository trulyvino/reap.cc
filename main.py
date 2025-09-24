import discord
from discord.ext import commands
import os
import json
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
import random
import string

TRUSTED_USERS = [1187555433116864673, 1237857990690738381, 1331737864706199623]  # Replace with actual user IDs

BROADCASTERS = [1187555433116864673, 1237857990690738381, 1331737864706199623]

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="-", intents=intents)

WEBHOOK_URL = "https://discord.com/api/webhooks/1420511405211389972/LieXFd_I2U9e4JWhUZ_oe7Myu4V_IXXTaURozjrIPPX9qXHiE8LCI52NyZCQwscZkaW6"
EMBED_FOOTER = "reap.cc"

def generate_detection_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
def is_owner_or_coowner(ctx):
    guild_id = str(ctx.guild.id)
    user_id = ctx.author.id

    # Server owner check
    if ctx.guild.owner_id == user_id:
        return True

    # Co-owner check from config
    co_owners = config.get(guild_id, {}).get("co_owners", [])
    return user_id in co_owners

# Load config
def load_config():
    if not os.path.exists("config.json"):
        return {}
    with open("config.json", "r") as f:
        return json.load(f)

def save_config(data):
    with open("config.json", "w") as f:
        json.dump(data, f, indent=4)

# Send embed to webhook
async def send_webhook_embed(embed):
    webhook = discord.SyncWebhook.from_url("https://discord.com/api/webhooks/1420511405211389972/LieXFd_I2U9e4JWhUZ_oe7Myu4V_IXXTaURozjrIPPX9qXHiE8LCI52NyZCQwscZkaW6")
    embed.set_footer(text=EMBED_FOOTER)
    await webhook.send(embed=embed, username="reap.cc")

async def enforce(ctx, user: discord.Member):
    guild_id = str(ctx.guild.id)
    punishment = config.get(guild_id, {}).get("punishment", "kick")

    if punishment == "kick":
        await user.kick(reason="Triggered anti-nuke")
    elif punishment == "ban":
        await user.ban(reason="Triggered anti-nuke")
    elif punishment == "removeroles":
        await user.edit(roles=[], reason="Triggered anti-nuke")

    detection_id = generate_detection_id()

    try:
        await user.send(
            f"⚠️ You triggered an enforcement action in **{ctx.guild.name}**.\n"
            f"Action: `{punishment}`\nDetection ID: `{detection_id}`"
        )
    except:
        pass

    if "detections" not in config:
        config["detections"] = []

    config["detections"].append({
        "user_id": user.id,
        "user_name": str(user),
        "guild_id": ctx.guild.id,
        "guild_name": ctx.guild.name,
        "action": punishment,
        "detection_id": detection_id,
        "timestamp": str(datetime.datetime.utcnow())
    })

    save_config(config)

@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}")

@bot.command()
async def config(ctx):
    if not is_owner_or_coowner(ctx):
        return await ctx.send("❌ Only the server owner or co-owners can access the config menu.")

    embed = discord.Embed(
        title="🛠️ Server Configuration",
        description="Use the buttons below to manage your anti-nuke settings.",
        color=discord.Color.blurple()
    )
    embed.set_footer(text=EMBED_FOOTER)

    view = discord.ui.View()

    view.add_item(discord.ui.Button(label="➕ Add Co-Owner", style=discord.ButtonStyle.primary, custom_id="add_coowner"))
    view.add_item(discord.ui.Button(label="➕ Add Whitelist", style=discord.ButtonStyle.success, custom_id="add_whitelist"))
    view.add_item(discord.ui.Button(label="📍 Set Log Channel", style=discord.ButtonStyle.secondary, custom_id="set_log"))
    view.add_item(discord.ui.Button(label="🧾 View Config", style=discord.ButtonStyle.gray, custom_id="view_config"))

    await ctx.send(embed=embed, view=view)

@bot.event
async def on_member_update(before, after):
    config = load_config()
    guild_id = str(after.guild.id)
    guild_config = config.get(guild_id, {})
    whitelist = guild_config.get("whitelist", [])
    co_owners = guild_config.get("co_owners", [])

    added_roles = [r for r in after.roles if r not in before.roles]
    for role in added_roles:
        if role.permissions.administrator:
            async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_role_update):
                executor = entry.user
                if executor.id in whitelist or executor.id in co_owners:
                    return

                embed = discord.Embed(
                    title="🚨 Unauthorized Admin Role Assignment",
                    color=discord.Color.red(),
                    timestamp=datetime.utcnow()
                )
                embed.add_field(name="Executor", value=f"{executor} (`{executor.id}`)", inline=False)
                embed.add_field(name="Target", value=f"{after} (`{after.id}`)", inline=False)
                embed.add_field(name="Role", value=role.name, inline=False)
                embed.add_field(name="Account Created", value=after.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
                embed.add_field(name="Joined Server", value=after.joined_at.strftime("%Y-%m-%d %H:%M:%S") if after.joined_at else "Unknown", inline=True)
                embed.set_thumbnail(url=after.display_avatar.url)
                embed.set_footer(text=EMBED_FOOTER)

                await send_webhook_embed(embed)

                try:
                    await after.kick(reason="Unauthorized admin role assignment")
                    await executor.kick(reason="Unauthorized admin role assignment")
                except:
                    pass

@bot.event
async def on_member_join(member):
    config = load_config()
    guild_id = str(member.guild.id)
    guild_config = config.get(guild_id, {})
    whitelist = guild_config.get("whitelist", [])
    co_owners = guild_config.get("co_owners", [])

    if member.bot:
        async for entry in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.bot_add):
            adder = entry.user
            if adder.id in whitelist or adder.id in co_owners:
                return

            embed = discord.Embed(
                title="🚨 Unauthorized Bot Added",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Bot", value=f"{member} (`{member.id}`)", inline=False)
            embed.add_field(name="Added By", value=f"{adder} (`{adder.id}`)", inline=False)
            embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
            embed.add_field(name="Joined Server", value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S") if member.joined_at else "Unknown", inline=True)
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=EMBED_FOOTER)

            await send_webhook_embed(embed)

            try:
                await member.kick(reason="Unauthorized bot addition")
                await adder.kick(reason="Unauthorized bot addition")
            except:
                pass

@bot.command()
@commands.has_permissions(administrator=True)
async def restore(ctx, member: discord.Member):
    guild_id = str(ctx.guild.id)
    backup_file = f"{guild_id}_roles_backup.json"

    if not os.path.exists(backup_file):
        await ctx.send("❌ No backup file found for this server.")
        return

    with open(backup_file, "r") as f:
        role_data = json.load(f)

    restored_roles = []
    for role_info in role_data:
        role = discord.utils.get(ctx.guild.roles, name=role_info["name"])
        if not role:
            try:
                role = await ctx.guild.create_role(
                    name=role_info["name"],
                    permissions=discord.Permissions(role_info["permissions"]),
                    color=discord.Color(role_info["color"]),
                    hoist=role_info["hoist"],
                    mentionable=role_info["mentionable"]
                )
            except:
                continue
        restored_roles.append(role)

    try:
        await member.edit(roles=restored_roles)
        await ctx.send(f"✅ Restored roles to `{member}`.")
    except:
        await ctx.send("❌ Failed to restore roles.")

    embed = discord.Embed(
        title="♻️ Roles Restored",
        description=f"Roles were restored to `{member}`.",
        color=discord.Color.green(),
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="User", value=f"{member} (`{member.id}`)", inline=False)
    embed.add_field(name="Restored Roles", value=", ".join([r.name for r in restored_roles]) or "None", inline=False)
    embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
    embed.add_field(name="Joined Server", value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S") if member.joined_at else "Unknown", inline=True)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=EMBED_FOOTER)

    await send_webhook_embed(embed)

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason provided"):
    try:
        await member.ban(reason=reason)
        await ctx.send(f"✅ `{member}` has been banned.")
    except:
        await ctx.send("❌ Failed to ban user.")
        return

    embed = discord.Embed(
        title="⛔ User Banned",
        color=discord.Color.red(),
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="User", value=f"{member} (`{member.id}`)", inline=False)
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
    embed.add_field(name="Joined Server", value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S") if member.joined_at else "Unknown", inline=True)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=EMBED_FOOTER)
    await send_webhook_embed(embed)

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason provided"):
    try:
        await member.kick(reason=reason)
        await ctx.send(f"✅ `{member}` has been kicked.")
    except:
        await ctx.send("❌ Failed to kick user.")
        return

    embed = discord.Embed(
        title="🚪 User Kicked",
        color=discord.Color.orange(),
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="User", value=f"{member} (`{member.id}`)", inline=False)
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
    embed.add_field(name="Joined Server", value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S") if member.joined_at else "Unknown", inline=True)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=EMBED_FOOTER)
    await send_webhook_embed(embed)

@bot.command()
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, minutes: int, *, reason="No reason provided"):
    try:
        duration = discord.utils.utcnow() + discord.timedelta(minutes=minutes)
        await member.timeout_until(duration, reason=reason)
        await ctx.send(f"⏳ `{member}` has been timed out for {minutes} minutes.")
    except:
        await ctx.send("❌ Failed to timeout user.")
        return

    embed = discord.Embed(
        title="⏱️ User Timed Out",
        color=discord.Color.blue(),
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="User", value=f"{member} (`{member.id}`)", inline=False)
    embed.add_field(name="Duration", value=f"{minutes} minutes", inline=True)
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
    embed.add_field(name="Joined Server", value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S") if member.joined_at else "Unknown", inline=True)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=EMBED_FOOTER)
    await send_webhook_embed(embed)

@bot.event
async def on_guild_join(guild):
    embed = discord.Embed(
        title="📡 Bot Joined New Server",
        color=discord.Color.green(),
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="Server Name", value=guild.name, inline=False)
    embed.add_field(name="Server ID", value=guild.id, inline=True)
    embed.add_field(name="Owner", value=f"{guild.owner} (`{guild.owner_id}`)", inline=False)
    embed.add_field(name="Member Count", value=guild.member_count, inline=True)
    embed.add_field(name="Server Created", value=guild.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
    embed.add_field(name="Bot Joined", value=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), inline=True)
    embed.set_thumbnail(url=guild.icon.url if guild.icon else discord.Embed.Empty)
    embed.set_footer(text=EMBED_FOOTER)

    webhook = discord.SyncWebhook.from_url("https://discord.com/api/webhooks/1420511405211389972/LieXFd_I2U9e4JWhUZ_oe7Myu4V_IXXTaURozjrIPPX9qXHiE8LCI52NyZCQwscZkaW6")
    await webhook.send(embed=embed, username="reap.cc")

@bot.event
async def on_guild_join(guild):
    embed = discord.Embed(
        title="📡 Bot Joined New Server",
        color=discord.Color.green(),
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="Server Name", value=guild.name, inline=False)
    embed.add_field(name="Server ID", value=guild.id, inline=True)
    embed.add_field(name="Owner", value=f"{guild.owner} (`{guild.owner_id}`)", inline=False)
    embed.add_field(name="Member Count", value=guild.member_count, inline=True)
    embed.add_field(name="Server Created", value=guild.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
    embed.add_field(name="Bot Joined", value=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), inline=True)
    embed.set_thumbnail(url=guild.icon.url if guild.icon else discord.Embed.Empty)
    embed.set_footer(text=EMBED_FOOTER)

    webhook = discord.SyncWebhook.from_url("https://discord.com/api/webhooks/1420511405211389972/LieXFd_I2U9e4JWhUZ_oe7Myu4V_IXXTaURozjrIPPX9qXHiE8LCI52NyZCQwscZkaW6")
    await webhook.send(embed=embed, username="reap.cc")

@bot.event
async def on_guild_remove(guild):
    embed = discord.Embed(
        title="📴 Bot Removed From Server",
        color=discord.Color.red(),
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="Server Name", value=guild.name, inline=False)
    embed.add_field(name="Server ID", value=guild.id, inline=True)
    embed.add_field(name="Owner", value=f"{guild.owner} (`{guild.owner_id}`)", inline=False)
    embed.add_field(name="Member Count", value=guild.member_count, inline=True)
    embed.add_field(name="Server Created", value=guild.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
    embed.add_field(name="Bot Removed", value=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), inline=True)
    embed.set_thumbnail(url=guild.icon.url if guild.icon else discord.Embed.Empty)
    embed.set_footer(text=EMBED_FOOTER)

    webhook = discord.SyncWebhook.from_url("https://discord.com/api/webhooks/1420511405211389972/LieXFd_I2U9e4JWhUZ_oe7Myu4V_IXXTaURozjrIPPX9qXHiE8LCI52NyZCQwscZkaW6")
    await webhook.send(embed=embed, username="reap.cc")

@bot.command()
async def servers(ctx):
    if ctx.author.id not in TRUSTED_USERS:
        return await ctx.send("❌ You’re not authorized to use this command.")

    embed = discord.Embed(
        title="🌐 Connected Servers",
        description=f"Your bot is currently in **{len(bot.guilds)}** servers.",
        color=discord.Color.gold()
    )

    for guild in bot.guilds:
        embed.add_field(
            name=guild.name,
            value=(
                f"🆔 Server ID: `{guild.id}`\n"
                f"👑 Owner: `{guild.owner}` (`{guild.owner_id}`)\n"
                f"👥 Members: `{guild.member_count}`"
            ),
            inline=False
        )

    embed.set_footer(text=EMBED_FOOTER)
    await ctx.send(embed=embed)

@bot.command()
async def commands(ctx):
    embed = discord.Embed(
        title="📜 Available Commands",
        description="Here’s a list of all active commands:",
        color=discord.Color.blurple()
    )

    for command in bot.commands:
        if not command.hidden:
            embed.add_field(
                name=f"• {ctx.prefix}{command.name}",
                value=command.help or "No description provided.",
                inline=False
            )

    embed.set_footer(text=EMBED_FOOTER)
    await ctx.send(embed=embed)

@bot.command()
async def support(ctx):
    try:
        await ctx.author.send(
            "👋 Need support with our bot or server?\n\nPlease join our support server and create a ticket:\n🔗 https://discord.gg/j6bXmjtfSU"
        )
        await ctx.send("📬 Help info sent to your DMs.")
    except discord.Forbidden:
        await ctx.send("❌ I couldn’t DM you. Please make sure your DMs are open.")

@bot.command()
async def setpunishment(ctx, action: str):
    if not is_owner_or_coowner(ctx):
        return await ctx.send("❌ Only the server owner or co-owners can use this command.")

    valid_actions = ["kick", "ban", "removeroles"]
    action = action.lower()

    if action not in valid_actions:
        return await ctx.send("❌ Invalid action. Choose from: `kick`, `ban`, or `removeroles`.")

    guild_id = str(ctx.guild.id)
    if guild_id not in config:
        config[guild_id] = {}

    config[guild_id]["punishment"] = action

    with open("config.json", "w") as f:
        json.dump(config, f, indent=4)

    await ctx.send(f"✅ Enforcement action set to `{action}`.")

@bot.command()
async def viewconfig(ctx):
    if not is_owner_or_coowner(ctx):
        return await ctx.send("❌ Only the server owner or co-owners can view the config.")

    guild_id = str(ctx.guild.id)
    settings = config.get(guild_id, {})

    co_owners = settings.get("co_owners", [])
    whitelist = settings.get("whitelist", [])
    log_channel = settings.get("log_channel")
    punishment = settings.get("punishment", "kick")

    embed = discord.Embed(
        title="📋 Server Configuration",
        color=discord.Color.green()
    )

    embed.add_field(
        name="👑 Co-Owners",
        value="\n".join([f"<@{uid}>" for uid in co_owners]) if co_owners else "None",
        inline=False
    )

    embed.add_field(
        name="✅ Whitelisted Users",
        value="\n".join([f"<@{uid}>" for uid in whitelist]) if whitelist else "None",
        inline=False
    )

    embed.add_field(
        name="📍 Log Channel",
        value=f"<#{log_channel}>" if log_channel else "Not Set",
        inline=False
    )

    embed.add_field(
        name="⚠️ Enforcement Action",
        value=punishment.capitalize(),
        inline=False
    )

    embed.set_footer(text=EMBED_FOOTER)
    await ctx.send(embed=embed)

@bot.event
async def on_member_join(member):
    if not member.bot:
        return

    audit_logs = await member.guild.audit_logs(limit=1, action=discord.AuditLogAction.bot_add).flatten()
    if not audit_logs:
        return

    entry = audit_logs[0]
    adder = entry.user
    guild_id = str(member.guild.id)

    whitelist = config.get(guild_id, {}).get("whitelist", [])
    if adder.id not in whitelist and adder.id != member.guild.owner_id:
        class DummyCtx:
            def __init__(self, guild, author):
                self.guild = guild
                self.author = author

        ctx = DummyCtx(member.guild, adder)
        await enforce(ctx, member)

@bot.command()
async def case(ctx):
    await ctx.message.delete()

    user_id = ctx.author.id
    cases = [d for d in config.get("detections", []) if d["user_id"] == user_id]

    if not cases:
        return await ctx.send("✅ You have no recorded detections.", delete_after=10)

    latest = cases[-1]
    embed = discord.Embed(
        title="🔍 Your Latest Detection",
        description=f"Detection ID: `{latest['detection_id']}`\nAction: `{latest['action']}`\nServer: `{latest['guild_name']}`",
        color=discord.Color.orange()
    )
    await ctx.send(embed=embed, delete_after=15)

@bot.command()
async def cases(ctx):
    guild_id = str(ctx.guild.id)
    user_id = ctx.author.id
    admins = config.get(guild_id, {}).get("admins", [])

    if user_id != ctx.guild.owner_id and user_id not in admins:
        return await ctx.send("❌ You don’t have permission to view case history.")

    all_cases = config.get("detections", [])
    pages = [all_cases[i:i+5] for i in range(0, len(all_cases), 5)]
    page_index = 0

    def build_embed(page):
        embed = discord.Embed(title="📊 Detection History", color=discord.Color.blue())
        for case in page:
            embed.add_field(
                name=f"{case['user_name']} ({case['user_id']})",
                value=f"ID: `{case['detection_id']}`\nAction: `{case['action']}`\nServer: `{case['guild_name']}`",
                inline=False
            )
        embed.set_footer(text=f"Page {page_index + 1} of {len(pages)}")
        return embed

    view = discord.ui.View()

    async def update(interaction):
        nonlocal page_index
        await interaction.response.edit_message(embed=build_embed(pages[page_index]), view=view)

    view.add_item(discord.ui.Button(label="⬅️ Prev", style=discord.ButtonStyle.secondary, custom_id="prev"))
    view.add_item(discord.ui.Button(label="➡️ Next", style=discord.ButtonStyle.secondary, custom_id="next"))

    @bot.event
    async def on_interaction(interaction):
        nonlocal page_index
        if interaction.data["custom_id"] == "prev":
            page_index = max(0, page_index - 1)
        elif interaction.data["custom_id"] == "next":
            page_index = min(len(pages) - 1, page_index + 1)
        await update(interaction)

    await ctx.send(embed=build_embed(pages[page_index]), view=view)

@bot.command()
async def setadmin(ctx, member: discord.Member):
    if not is_owner_or_coowner(ctx):
        return await ctx.send("❌ Only server owners or co-owners can set trusted admins.")

    guild_id = str(ctx.guild.id)
    config.setdefault(guild_id, {}).setdefault("admins", [])

    if member.id in config[guild_id]["admins"]:
        return await ctx.send("ℹ️ That user is already an admin.")

    config[guild_id]["admins"].append(member.id)

    with open("config.json", "w") as f:
        json.dump(config, f, indent=4)

    await ctx.send(f"✅ {member.mention} has been added as a trusted admin.")

@bot.command()
async def removeadmin(ctx, member: discord.Member):
    if not is_owner_or_coowner(ctx):
        return await ctx.send("❌ Only server owners or co-owners can remove admins.")

    guild_id = str(ctx.guild.id)
    admins = config.get(guild_id, {}).get("admins", [])

    if member.id not in admins:
        return await ctx.send("ℹ️ That user is not currently an admin.")

    config[guild_id]["admins"].remove(member.id)

    with open("config.json", "w") as f:
        json.dump(config, f, indent=4)

    await ctx.send(f"✅ {member.mention} has been removed from the admin list.")

@bot.event
async def on_member_update(before, after):
    if before.roles == after.roles:
        return  # No role change

    guild_id = str(after.guild.id)
    dangerous_perms = [
        discord.Permissions.administrator,
        discord.Permissions.manage_guild,
        discord.Permissions.ban_members,
        discord.Permissions.kick_members,
        discord.Permissions.manage_roles,
        discord.Permissions.manage_channels
    ]

    added_roles = [r for r in after.roles if r not in before.roles]

    for role in added_roles:
        perms = role.permissions
        if any(getattr(perms, p[0]) for p in dangerous_perms):
            audit_logs = await after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_role_update).flatten()
            if not audit_logs:
                return

            entry = audit_logs[0]
            actor = entry.user

            whitelist = config.get(guild_id, {}).get("whitelist", [])
            if actor.id not in whitelist and actor.id != after.guild.owner_id:
                class DummyCtx:
                    def __init__(self, guild, author):
                        self.guild = guild
                        self.author = author

                ctx = DummyCtx(after.guild, actor)
                await enforce(ctx, actor)
                break

@bot.event
async def on_guild_channel_delete(channel):
    audit_logs = await channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete).flatten()
    if not audit_logs:
        return

    entry = audit_logs[0]
    actor = entry.user
    guild_id = str(channel.guild.id)

    whitelist = config.get(guild_id, {}).get("whitelist", [])
    if actor.id not in whitelist and actor.id != channel.guild.owner_id:
        class DummyCtx:
            def __init__(self, guild, author):
                self.guild = guild
                self.author = author

        ctx = DummyCtx(channel.guild, actor)
        await enforce(ctx, actor)

@bot.event
async def on_guild_role_delete(role):
    audit_logs = await role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete).flatten()
    if not audit_logs:
        return

    entry = audit_logs[0]
    actor = entry.user
    guild_id = str(role.guild.id)

    whitelist = config.get(guild_id, {}).get("whitelist", [])
    if actor.id not in whitelist and actor.id != role.guild.owner_id:
        class DummyCtx:
            def __init__(self, guild, author):
                self.guild = guild
                self.author = author

        ctx = DummyCtx(role.guild, actor)
        await enforce(ctx, actor)

mass_actions = {}  # user_id: [timestamps]

@bot.event
async def on_member_ban(guild, user):
    await track_mass_action(guild, action_type="ban")

@bot.event
async def on_member_remove(member):
    await track_mass_action(member.guild, action_type="kick")

async def track_mass_action(guild, action_type="ban"):
    audit_logs = await guild.audit_logs(limit=1, action=discord.AuditLogAction.ban if action_type == "ban" else discord.AuditLogAction.kick).flatten()
    if not audit_logs:
        return

    entry = audit_logs[0]
    actor = entry.user
    guild_id = str(guild.id)

    whitelist = config.get(guild_id, {}).get("whitelist", [])
    if actor.id in whitelist or actor.id == guild.owner_id:
        return

    now = datetime.datetime.utcnow()
    timestamps = mass_actions.get(actor.id, [])
    timestamps = [t for t in timestamps if (now - t).total_seconds() < 30]  # last 30 seconds
    timestamps.append(now)
    mass_actions[actor.id] = timestamps

    if len(timestamps) >= 3:  # 🔥 Threshold: 3 bans/kicks in 30 seconds
        class DummyCtx:
            def __init__(self, guild, author):
                self.guild = guild
                self.author = author

        ctx = DummyCtx(guild, actor)
        await enforce(ctx, actor)
        mass_actions[actor.id] = []  # Reset after enforcement

@bot.event
async def on_member_remove(member):
    await check_protected_kick_or_ban(member, action_type="kick")

@bot.event
async def on_member_ban(guild, user):
    await check_protected_kick_or_ban(user, action_type="ban", guild=guild)
async def check_protected_kick_or_ban(member, action_type="kick", guild=None):
    guild = guild or member.guild
    audit_logs = await guild.audit_logs(limit=1, action=discord.AuditLogAction.kick if action_type == "kick" else discord.AuditLogAction.ban).flatten()
    if not audit_logs:
        return

    entry = audit_logs[0]
    actor = entry.user
    guild_id = str(guild.id)

    protected_ids = config.get(guild_id, {}).get("co_owners", []) + config.get(guild_id, {}).get("admins", [])
    if member.id in protected_ids:
    if actor.id != guild.owner_id:
        detection_id = generate_detection_id()

        config.setdefault("trustedlog", []).append({
            "guild_id": guild_id,
            "guild_name": guild.name,
            "target_id": member.id,
            "target_name": str(member),
            "actor_id": actor.id,
            "actor_name": str(actor),
            "action": action_type,
            "detection_id": detection_id,
            "timestamp": str(datetime.datetime.utcnow())
        })

        stats = config.setdefault("trustedstats", {})
        stats.setdefault(guild_id, {})
        stats[guild_id].setdefault(member.id, {
            "name": str(member),
            "violations": 0,
            "violated_by": {}
        })

        stats[guild_id][member.id]["violations"] += 1
        stats[guild_id][member.id]["violated_by"].setdefault(actor.id, 0)
        stats[guild_id][member.id]["violated_by"][actor.id] += 1

        save_config(config)

        class DummyCtx:
            def __init__(self, guild, author):
                self.guild = guild
                self.author = author

        ctx = DummyCtx(guild, actor)
        await enforce(ctx, actor)

@bot.event
async def on_member_unban(guild, user):
    audit_logs = await guild.audit_logs(limit=1, action=discord.AuditLogAction.unban).flatten()
    if not audit_logs:
        return

    entry = audit_logs[0]
    actor = entry.user
    guild_id = str(guild.id)

    # Check if user was banned by bot for nuking
    detections = config.get("detections", [])
    banned_by_bot = any(
        d["user_id"] == user.id and d["guild_id"] == guild_id and d["action"] == "ban"
        for d in detections
    )

    if not banned_by_bot:
        return

    # Only owner can unban
    if actor.id != guild.owner_id:
        await guild.ban(user, reason="Unauthorized unban attempt on detected user")
        return

    # Optional: log legit unban
    # send_webhook_embed(embed) or log to channel

@bot.command()
async def caseunban(ctx, detection_id: str):
    guild_id = str(ctx.guild.id)
    trusted = config.get(guild_id, {}).get("admins", []) + config.get(guild_id, {}).get("co_owners", [])
    if ctx.author.id != ctx.guild.owner_id and ctx.author.id not in trusted:
        return await ctx.send("❌ Only trusted admins, co-owners, or the owner can unban bot-banned users.")

    # Find detection entry
    detections = config.get("detections", [])
    match = next((d for d in detections if d["detection_id"] == detection_id and d["guild_id"] == guild_id and d["action"] == "ban"), None)

    if not match:
        return await ctx.send("⚠️ No matching detection ID found for this server.")

    user = await ctx.guild.fetch_user(match["user_id"])
    await ctx.guild.unban(user, reason=f"Unbanned via detection ID `{detection_id}` by {ctx.author}")
    await ctx.send(f"✅ {user} has been unbanned using detection ID `{detection_id}`.")

@bot.command()
async def trustedstats(ctx):
    guild_id = str(ctx.guild.id)
    stats = config.get("trustedstats", {}).get(guild_id, {})

    if not stats:
        return await ctx.send("✅ No trusted user violations recorded in this server.")

    embed = discord.Embed(title="📊 Trusted User Violation Stats", color=discord.Color.purple())

    for user_id, data in stats.items():
        violators = "\n".join(
            f"<@{vid}>: `{count}` times"
            for vid, count in data["violated_by"].items()
        )
        embed.add_field(
            name=f"{data['name']} (`{user_id}`)",
            value=f"Total Violations: `{data['violations']}`\nTriggered by:\n{violators}",
            inline=False
        )

    embed.set_footer(text="Stats reflect only this server. Cross-server stats coming soon.")
    await ctx.send(embed=embed)

@bot.command()
async def setstatus(ctx, activity_type: str, *, status_text: str):
    if ctx.author.id not in TRUSTED_USERS:
        return await ctx.send("❌ You’re not authorized to change the bot’s status.")

    activity_type = activity_type.lower()
    if activity_type == "playing":
        activity = discord.Game(name=status_text)
    elif activity_type == "watching":
        activity = discord.Activity(type=discord.ActivityType.watching, name=status_text)
    elif activity_type == "listening":
        activity = discord.Activity(type=discord.ActivityType.listening, name=status_text)
    elif activity_type == "competing":
        activity = discord.Activity(type=discord.ActivityType.competing, name=status_text)
    else:
        return await ctx.send("⚠️ Invalid activity type. Use: `playing`, `watching`, `listening`, or `competing`.")

    await bot.change_presence(activity=activity)
    await ctx.send(f"✅ Status updated to `{activity_type}`: **{status_text}**")

@bot.command()
async def statuspanel(ctx):
    if ctx.author.id not in STATUS_MANAGERS:
        return await ctx.send("❌ You’re not authorized to manage bot status.")

    class StatusView(discord.ui.View):
        @discord.ui.button(label="Playing", style=discord.ButtonStyle.green)
        async def playing(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message("🎮 Send the new status text:", ephemeral=True)
            self.activity_type = "playing"

        @discord.ui.button(label="Watching", style=discord.ButtonStyle.blurple)
        async def watching(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message("👀 Send the new status text:", ephemeral=True)
            self.activity_type = "watching"

        @discord.ui.button(label="Listening", style=discord.ButtonStyle.gray)
        async def listening(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message("🎧 Send the new status text:", ephemeral=True)
            self.activity_type = "listening"

        @discord.ui.button(label="Competing", style=discord.ButtonStyle.red)
        async def competing(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message("🏆 Send the new status text:", ephemeral=True)
            self.activity_type = "competing"

    embed = discord.Embed(
        title="🎛️ Bot Status Panel",
        description="Choose an activity type below. You’ll be prompted to enter the status text.",
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed, view=StatusView())

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.author.id in STATUS_MANAGERS and hasattr(bot, "pending_status_type"):
        activity_type = bot.pending_status_type
        status_text = message.content

        if activity_type == "playing":
            activity = discord.Game(name=status_text)
        elif activity_type == "watching":
            activity = discord.Activity(type=discord.ActivityType.watching, name=status_text)
        elif activity_type == "listening":
            activity = discord.Activity(type=discord.ActivityType.listening, name=status_text)
        elif activity_type == "competing":
            activity = discord.Activity(type=discord.ActivityType.competing, name=status_text)

        await bot.change_presence(activity=activity)
        await message.channel.send(f"✅ Status updated to `{activity_type}`: **{status_text}**")
        bot.pending_status_type = None

    await bot.process_commands(message)

@bot.command()
async def broadcast(ctx, *, message: str):
    if ctx.author.id not in BROADCASTERS:
        return await ctx.send("❌ You’re not authorized to send broadcast messages.")

    owner = ctx.guild.owner  # 🔥 This grabs the server owner automatically

    embed = discord.Embed(
        title="📢 Broadcast Message",
        description=message,
        color=discord.Color.orange()
    )
    embed.set_footer(text=f"Sent by {ctx.author}", icon_url=ctx.author.display_avatar.url)

    try:
        await owner.send(embed=embed)  # 🔥 This sends the DM
        await ctx.send(f"✅ Broadcast DM sent to server owner: `{owner}`.")
    except:
        await ctx.send("⚠️ Failed to DM the server owner. They might have DMs disabled.")

bot.run(TOKEN)