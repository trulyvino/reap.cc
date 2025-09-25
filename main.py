import discord
from discord.ext import commands
import os
import json
import datetime
from dotenv import load_dotenv
load_dotenv()
import random
import string
import aiohttp
import subprocess
import asyncio
from discord import Webhook

TRUSTED_USERS = [1187555433116864673, 1237857990690738381, 1331737864706199623]  # Replace with actual user IDs

BUGREPORT_WEBHOOK = "https://discord.com/api/webhooks/1420557222240583762/lJuNVrrcL_iz1byAe0anDSmXxn-e_obEpaffwvYTESzDYMgp_5-xxWn9ISY8wHEJ9SoJ"  # Replace with your actual webhook URL

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=".", intents=intents)

WEBHOOK_URL = "https://discord.com/api/webhooks/1420511405211389972/LieXFd_I2U9e4JWhUZ_oe7Myu4V_IXXTaURozjrIPPX9qXHiE8LCI52NyZCQwscZkaW6"
EMBED_FOOTER = "reap.cc"

def has_bug_access(ctx):
    return (
        ctx.author.id == ctx.guild.owner_id or
        any(role.name in ["Admin [reap.cc]", "Co Owner [reap.cc]", "Owner [reap.cc]"] for role in ctx.author.roles)
    )

def has_case_access(ctx):
    return (
        ctx.author.id == ctx.guild.owner_id or
        any(role.name == "Admin [reap.cc]" for role in ctx.author.roles) or
        any(role.name == "Co Owner [reap.cc]" for role in ctx.author.roles)
    )

def is_trusted(ctx):
    guild_id = str(ctx.guild.id)
    owner_id = ctx.guild.owner_id
    co_owners = config.get(guild_id, {}).get("co_owners", [])
    admins = config.get(guild_id, {}).get("admins", [])
    return ctx.author.id == owner_id or ctx.author.id in co_owners or ctx.author.id in admins

def is_config_manager(ctx):
    guild_id = str(ctx.guild.id)
    owner_id = ctx.guild.owner_id
    co_owners = config.get(guild_id, {}).get("co_owners", [])
    return ctx.author.id == owner_id or ctx.author.id in co_owners

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
    async with aiohttp.ClientSession() as session:
        webhook = discord.Webhook.from_url(
            "https://discord.com/api/webhooks/1420511405211389972/LieXFd_I2U9e4JWhUZ_oe7Myu4V_IXXTaURozjrIPPX9qXHiE8LCI52NyZCQwscZkaW6",
            adapter=discord.AsyncWebhookAdapter(session)
        )
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

@bot.command(name="config")
async def config(ctx):
    if ctx.author.id != ctx.guild.owner_id and not discord.utils.get(ctx.author.roles, name="Co Owner [reap.cc]"):
        return await ctx.send("❌ Only the server owner or co-owner can run `.config`.")

    role_names = ["Admin [reap.cc]", "Co Owner [reap.cc]", "Whitelisted [reap.cc]"]
    created_roles = []

    for name in role_names:
        existing = discord.utils.get(ctx.guild.roles, name=name)
        if not existing:
            new_role = await ctx.guild.create_role(name=name, mentionable=True)
            created_roles.append(new_role.name)

    embed = discord.Embed(
        title="⚙️ reap.cc Configuration",
        description="Setup complete. Roles are ready.",
        color=discord.Color.blurple(),
        timestamp=datetime.datetime.utcnow()
    )
    embed.add_field(name="Admin Role", value="Admin [reap.cc]", inline=True)
    embed.add_field(name="Co-Owner Role", value="Co Owner [reap.cc]", inline=True)
    embed.add_field(name="Whitelisted Role", value="Whitelisted [reap.cc]", inline=True)

    if created_roles:
        embed.add_field(name="Created Roles", value="\n".join(created_roles), inline=False)

    embed.set_footer(text="reap.cc")

    await ctx.send(embed=embed)

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
    commands_list = [cmd for cmd in bot.commands if not cmd.hidden]
    pages = [commands_list[i:i+25] for i in range(0, len(commands_list), 25)]
    page_index = 0

    def build_embed(page):
        embed = discord.Embed(
            title="📜 Available Commands",
            description="Here’s a list of all active commands:",
            color=discord.Color.blurple()
        )
        for command in page:
            embed.add_field(
                name=f"• {ctx.prefix}{command.name}",
                value=command.help or "No description provided.",
                inline=False
            )
        embed.set_footer(text=f"Page {page_index + 1} of {len(pages)}")
        return embed

    view = discord.ui.View()

    async def update(interaction):
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

@bot.command(name="case")
async def case(ctx, *, details: str = None):
    if not has_case_access(ctx):
        return await ctx.send("❌ You’re not authorized to use this command.")

    if not details:
        return await ctx.send("⚠️ You must provide case details. Example: `.case User was spamming links`")

    embed = discord.Embed(
        title="📁 New Case Report",
        description=details,
        color=discord.Color.red(),
        timestamp=datetime.datetime.utcnow()
    )
    embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
    embed.set_footer(text="reap.cc case log")

    webhook_url = "https://discord.com/api/webhooks/1420511405211389972/LieXFd_I2U9e4JWhUZ_oe7Myu4V_IXXTaURozjrIPPX9qXHiE8LCI52NyZCQwscZkaW6"

    webhook = Webhook.from_url(webhook_url, adapter=RequestsWebhookAdapter())
    webhook.send(embed=embed, username="Case Logger")

    await ctx.send("✅ Case submitted and logged.")

@bot.command(name="cases")
async def cases(ctx, *, case_summary: str = None):
    if not has_case_access(ctx):
        return await ctx.send("❌ You’re not authorized to submit case logs.")

    if not case_summary:
        return await ctx.send("⚠️ You must provide a case summary. Example: `.cases User muted for spam`")

    embed = discord.Embed(
        title="📂 Case Log Entry",
        description=case_summary,
        color=discord.Color.red(),
        timestamp=datetime.datetime.utcnow()
    )
    embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
    embed.set_footer(text="reap.cc case log")

    webhook_url = "https://discord.com/api/webhooks/1420511405211389972/LieXFd_I2U9e4JWhUZ_oe7Myu4V_IXXTaURozjrIPPX9qXHiE8LCI52NyZCQwscZkaW6"

    async with aiohttp.ClientSession() as session:
        webhook = discord.Webhook.from_url(webhook_url, adapter=discord.AsyncWebhookAdapter(session))
        await webhook.send(embed=embed, username="Case Logger")

    await ctx.send("✅ Case log submitted.")

    @bot.event
    async def on_interaction(interaction):
        global page_index
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
    if ctx.author.id not in TRUSTED_USERS:
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

    if message.author.id in TRUSTED_USERS and hasattr(bot, "pending_status_type"):
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
    if ctx.author.id not in TRUSTED_USERS:
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

@bot.event
async def on_command_error(ctx, error):
    await ctx.send(f"⚠️ Command error: {error}")

@bot.command()
async def shutdown(ctx):
    if ctx.author.id not in TRUSTED_USERS:
        return await ctx.send("❌ You’re not authorized to shut down the bot.")

    class ConfirmShutdown(discord.ui.View):
        @discord.ui.button(label="Confirm Shutdown", style=discord.ButtonStyle.red)
        async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user.id != ctx.author.id:
                return await interaction.response.send_message("🚫 You didn’t initiate this shutdown.", ephemeral=True)

            await interaction.response.send_message("🛑 Bot is shutting down...", ephemeral=True)
            await bot.close()

        @discord.ui.button(label="Cancel", style=discord.ButtonStyle.gray)
        async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user.id != ctx.author.id:
                return await interaction.response.send_message("🚫 You didn’t initiate this shutdown.", ephemeral=True)

            await interaction.response.send_message("✅ Shutdown canceled.", ephemeral=True)

    embed = discord.Embed(
        title="⚠️ Shutdown Request",
        description="Click **Confirm Shutdown** to power off the bot.\nOnly the initiator can confirm.",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed, view=ConfirmShutdown())

@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")

@bot.command()
async def broadcastallowners(ctx, *, message: str):
    if ctx.author.id not in TRUSTED_USERS:
        return await ctx.send("❌ You’re not authorized to send broadcast messages.")

    embed = discord.Embed(
        title="📢 Broadcast Message",
        description=message,
        color=discord.Color.orange()
    )
    embed.set_footer(text=f"Sent by {ctx.author}", icon_url=ctx.author.display_avatar.url)

    success = 0
    for guild in bot.guilds:
        try:
            owner = guild.owner
            await owner.send(embed=embed)
            success += 1
        except:
            pass  # Owner might have DMs off

    await ctx.send(f"✅ Broadcast DM sent to `{success}` server owner(s).")

@bot.command()
async def purge(ctx, amount: int):
    if not ctx.author.guild_permissions.manage_messages:
        return await ctx.send("❌ You don’t have permission to purge messages.")

    if amount < 1 or amount > 100:
        return await ctx.send("⚠️ You can only purge between 1 and 100 messages.")

    deleted = await ctx.channel.purge(limit=amount + 1)

    embed = discord.Embed(
        title="🧹 Purge Complete",
        description=f"Deleted `{len(deleted) - 1}` messages from {ctx.channel.mention}.",
        color=discord.Color.red()
    )
    embed.set_footer(text=f"Purged by {ctx.author}", icon_url=ctx.author.display_avatar.url)

    confirmation = await ctx.send(embed=embed)
    await asyncio.sleep(4)
    await confirmation.delete()

    await send_webhook_embed(embed)

@bot.command()
async def globalban(ctx, user_id: int, *, reason: str = "No reason provided"):
    if ctx.author.id not in TRUSTED_USERS:
        return await ctx.send("❌ You’re not authorized to use global ban.")

    target_user = await bot.fetch_user(user_id)
    success = 0
    failed = []

    for guild in bot.guilds:
        try:
            await guild.ban(target_user, reason=f"[Global Ban] {reason}")
            success += 1
        except Exception as e:
            failed.append(guild.name)

    embed = discord.Embed(
        title="🚫 Global Ban Executed",
        description=f"User `{target_user}` (`{user_id}`) banned from `{success}` server(s).",
        color=discord.Color.red()
    )
    embed.add_field(name="Reason", value=reason, inline=False)
    if failed:
        embed.add_field(name="Failed Servers", value="\n".join(failed), inline=False)

    embed.set_footer(text=f"Triggered by {ctx.author}", icon_url=ctx.author.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="bugreport")
async def bugreport(ctx):
    if not has_bug_access(ctx):
        return await ctx.send("❌ You’re not authorized to submit bug reports.")

    await ctx.send("📝 Please describe the bug in one message:")

    def check_msg(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        bug_msg = await bot.wait_for("message", check=check_msg, timeout=60)
    except asyncio.TimeoutError:
        return await ctx.send("⏳ Bug report timed out.")

    await ctx.send("📷 Now upload a screenshot or image of the bug:")

    try:
        img_msg = await bot.wait_for("message", check=check_msg, timeout=60)
        image_url = img_msg.attachments[0].url if img_msg.attachments else None
    except asyncio.TimeoutError:
        return await ctx.send("⏳ Image upload timed out.")

    if not image_url:
        return await ctx.send("⚠️ No image detected. Bug report canceled.")

    embed = discord.Embed(
        title="🐞 Bug Report",
        description=bug_msg.content,
        color=discord.Color.orange(),
        timestamp=datetime.datetime.utcnow()
    )
    embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
    embed.set_image(url=image_url)
    embed.set_footer(text=f"Reported from {ctx.guild.name}")

    webhook_url = "https://discord.com/api/webhooks/1420557222240583762/lJuNVrrcL_iz1byAe0anDSmXxn-e_obEpaffwvYTESzDYMgp_5-xxWn9ISY8wHEJ9SoJ"

    async with aiohttp.ClientSession() as session:
        webhook = discord.Webhook.from_url(webhook_url, adapter=discord.AsyncWebhookAdapter(session))
        sent_msg = await webhook.send(embed=embed, username="Bug Reporter", wait=True)

    if isinstance(sent_msg, discord.Message):
        thread = await sent_msg.create_thread(
            name=f"Bug: {ctx.author.name}",
            auto_archive_duration=1440
        )
        await thread.send("🧵 Thread created for bug discussion.\nAnyone affected can reply here.")

@bot.event
async def on_guild_role_delete(role):
    guild_id = str(role.guild.id)
    trusted = config.get(guild_id, {}).get("trusted_roles", {})
    if not trusted:
        return

    for key, role_id in trusted.items():
        if role.id == role_id:
            owner = role.guild.owner
            await owner.send(f"⚠️ The `{key}` role (`{role.name}`) was deleted in `{role.guild.name}`. Trusted access may be broken.")
            del config[guild_id]["trusted_roles"][key]
            save_config(config)

@bot.event
async def on_member_update(before, after):
    guild_id = str(after.guild.id)
    trusted = config.get(guild_id, {}).get("trusted_roles", {})
    if not trusted:
        return

    added_roles = [r for r in after.roles if r not in before.roles]
    for role in added_roles:
        if role.id in trusted.values():
            if after.id != after.guild.owner_id:
                channel = after.guild.system_channel or after.guild.text_channels[0]
                await channel.send(f".setpunishment {after.mention}")

@bot.event
async def on_command(ctx):
    embed = discord.Embed(
        title="🧾 Command Executed",
        description=f"`{ctx.command}` was used by {ctx.author.mention}",
        color=discord.Color.dark_gray(),
        timestamp=datetime.datetime.utcnow()
    )
    embed.add_field(name="Executed By", value=str(ctx.author), inline=True)
    embed.add_field(name="Channel", value=str(ctx.channel), inline=True)
    embed.set_footer(text="reap.cc", icon_url=ctx.author.display_avatar.url)

    async with aiohttp.ClientSession() as session:
        webhook = discord.Webhook.from_url(
            "https://discord.com/api/webhooks/1420511405211389972/LieXFd_I2U9e4JWhUZ_oe7Myu4V_IXXTaURozjrIPPX9qXHiE8LCI52NyZCQwscZkaW6",  # Replace with your actual webhook URL
            adapter=discord.AsyncWebhookAdapter(session)
        )
        await webhook.send(embed=embed, username="reap.cc")

@bot.command(name="suggest")
async def suggest(ctx, *, suggestion: str):
    if not hasattr(bot, "suggestion_count"):
        bot.suggestion_count = {}

    guild_id = str(ctx.guild.id)
    bot.suggestion_count.setdefault(guild_id, 0)
    bot.suggestion_count[guild_id] += 1
    number = bot.suggestion_count[guild_id]

    embed = discord.Embed(
        title=f"💡 Suggestion #{number}",
        description=suggestion,
        color=discord.Color.blurple(),
        timestamp=datetime.datetime.utcnow()
    )
    embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
    embed.set_footer(text="reap.cc suggestions")

    # 🔁 Paste your webhook URL here
    webhook_url = "https://discord.com/api/webhooks/1420895162594496574/Pm-s1kp4YPQPsDMXVHUBPfvROrzYFwJ7D-qf8aiJyg3u_swOGpmA4AC6PFi8f9bkKdYC"

    async with aiohttp.ClientSession() as session:
        webhook = discord.Webhook.from_url(webhook_url, adapter=discord.AsyncWebhookAdapter(session))
        sent_msg = await webhook.send(embed=embed, username="reap.cc", wait=True)

    # Create a thread under the webhook message
    # This part only works if the webhook is tied to a real message in a Discord channel
    # So we need to fetch the message object from the webhook response
    # If you're using discord.py 2.x, you can do this:
    if isinstance(sent_msg, discord.Message):
        thread_name = f"💬 Suggestion #{number}"
        await sent_msg.create_thread(name=thread_name, auto_archive_duration=1440)


@bot.command(name="gitpush")
async def gitpush(ctx):
    if ctx.author.id not in TRUSTED_USERS:
        return await ctx.send("❌ You’re not authorized to push updates.")

    await ctx.send("📝 What should the commit message be?")

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        msg = await bot.wait_for("message", check=check, timeout=60)
        commit_message = msg.content
    except asyncio.TimeoutError:
        return await ctx.send("⏳ Timed out waiting for commit message.")

    try:
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        subprocess.run(["git", "push"], check=True)
        await ctx.send(f"✅ Git push complete with commit message: `{commit_message}`")
    except subprocess.CalledProcessError as e:
        await ctx.send(f"⚠️ Git error: `{e}`")


@bot.command(name="restart")
async def restart(ctx):
    if ctx.author.id not in TRUSTED_USERS:
        return await ctx.send("❌ You’re not authorized to restart the bot.")

    embed = discord.Embed(
        title="🔄 Restarting Bot",
        description="The bot is restarting now...",
        color=discord.Color.red(),
        timestamp=datetime.datetime.utcnow()
    )
    embed.set_footer(text="reap.cc")

    await ctx.send(embed=embed)
    await bot.close()  # Make sure your process manager auto-restarts the bot

@bot.event
async def on_command(ctx):
    print(f"Command used: {ctx.command} by {ctx.author}")
    # rest of your embed logic...

@bot.command()
async def channelnuke(ctx):
    if ctx.author.id not in has_case_access:
        await ctx.send("🚫 You don’t have permission to use this command.")
        return

    original = ctx.channel
    overwrites = original.overwrites
    name = original.name
    category = original.category

    try:
        await original.delete()
        new_channel = await ctx.guild.create_text_channel(name=name, overwrites=overwrites, category=category)
        await new_channel.send(f"✅ Channel `{name}` has been nuked and recreated.")
    except Exception as e:
        await ctx.send(f"❌ Failed to nuke channel: {e}")

@bot.command(name="setcoowner")
async def setcoowner(ctx, member: discord.Member):
    allowed_roles = ["Admin [reap.cc]", "Whitelisted [reap.cc]"]
    if ctx.author.id != ctx.guild.owner_id and not any(r.name in allowed_roles for r in ctx.author.roles):
        return await ctx.send("❌ Only admins or whitelisted users can assign the Co Owner role.")

    role = discord.utils.get(ctx.guild.roles, name="Co Owner [reap.cc]")
    if not role:
        return await ctx.send("⚠️ Co Owner role not found. Run `.config` to create it.")

    await member.add_roles(role)
    await ctx.send(f"✅ {member.mention} has been granted Co Owner access.")

@bot.event
async def on_member_update(before, after):
    guild = after.guild
    added_roles = [r for r in after.roles if r not in before.roles]
    sensitive_roles = ["Admin [reap.cc]", "Co Owner [reap.cc]", "Owner [reap.cc]", "Whitelisted [reap.cc]"]

    for role in added_roles:
        if role.name in sensitive_roles:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.member_role_update):
                executor = entry.user
                target = entry.target

                if executor == bot.user:
                    continue

                executor_roles = [r.name for r in executor.roles]
                is_admin = "Admin [reap.cc]" in executor_roles
                is_whitelisted = "Whitelisted [reap.cc]" in executor_roles
                is_owner = executor.id == guild.owner_id

                # Co Owner abuse
                if role.name == "Co Owner [reap.cc]" and not (is_admin or is_whitelisted or is_owner):
                    await target.remove_roles(role)
                    await guild.kick(executor, reason="Unauthorized Co Owner assignment")
                    return

                # Whitelist abuse
                if role.name == "Whitelisted [reap.cc]" and not is_admin and not is_owner:
                    await target.remove_roles(role)
                    await guild.kick(executor, reason="Unauthorized whitelist assignment")
                    return

                # Self-assignment abuse
                if executor == target and role.name in sensitive_roles:
                    await target.remove_roles(role)
                    await guild.kick(target, reason="Unauthorized self-assignment of sensitive role")
                    return

@bot.command(name="setwhitelist")
async def setwhitelist(ctx, member: discord.Member):
    if not is_admin(ctx):
        return await ctx.send("❌ Only admins can assign the Whitelisted role.")

    role = discord.utils.get(ctx.guild.roles, name="Whitelisted [reap.cc]")
    if not role:
        return await ctx.send("⚠️ Whitelisted role not found. Run `.config` to create it.")

    await member.add_roles(role)
    await ctx.send(f"✅ {member.mention} has been whitelisted.")

bot.run(TOKEN)