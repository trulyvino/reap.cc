import discord
from discord.ext import commands
import os
import json
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=",", intents=intents)

WEBHOOK_URL = "https://discord.com/api/webhooks/1420511405211389972/LieXFd_I2U9e4JWhUZ_oe7Myu4V_IXXTaURozjrIPPX9qXHiE8LCI52NyZCQwscZkaW6"
EMBED_FOOTER = "reap.cc"

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
    webhook = discord.SyncWebhook.from_url(WEBHOOK_URL)
    embed.set_footer(text=EMBED_FOOTER)
    await webhook.send(embed=embed, username="reap.cc")

@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}")

@bot.command()
@commands.has_permissions(administrator=True)
async def config(ctx):
    config_data = load_config()
    guild_id = str(ctx.guild.id)

    if guild_id not in config_data:
        config_data[guild_id] = {
            "co_owners": [],
            "whitelist": [],
            "log_channel": None
        }
        save_config(config_data)

    class ConfigView(discord.ui.View):
        @discord.ui.button(label="➕ Add Co-Owner", style=discord.ButtonStyle.primary)
        async def add_coowner(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message("Mention the user to set as Co-Owner:", ephemeral=True)

            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel

            msg = await bot.wait_for("message", check=check, timeout=30)
            user_id = msg.mentions[0].id if msg.mentions else None

            if user_id:
                config_data[guild_id]["co_owners"].append(user_id)
                save_config(config_data)
                await ctx.send(f"✅ `{msg.mentions[0]}` added as Co-Owner.")
            else:
                await ctx.send("❌ No user mentioned.")

        @discord.ui.button(label="➕ Add Whitelist", style=discord.ButtonStyle.success)
        async def add_whitelist(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message("Mention the user to whitelist:", ephemeral=True)

            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel

            msg = await bot.wait_for("message", check=check, timeout=30)
            user_id = msg.mentions[0].id if msg.mentions else None

            if user_id:
                config_data[guild_id]["whitelist"].append(user_id)
                save_config(config_data)
                await ctx.send(f"✅ `{msg.mentions[0]}` added to whitelist.")
            else:
                await ctx.send("❌ No user mentioned.")

        @discord.ui.button(label="📍 Set Log Channel", style=discord.ButtonStyle.secondary)
        async def set_log_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
            config_data[guild_id]["log_channel"] = ctx.channel.id
            save_config(config_data)
            await interaction.response.send_message(f"✅ Log channel set to `{ctx.channel.name}`.", ephemeral=True)

        @discord.ui.button(label="🧾 View Config", style=discord.ButtonStyle.gray)
        async def view_config(self, interaction: discord.Interaction, button: discord.ui.Button):
            co_owners = config_data[guild_id]["co_owners"]
            whitelist = config_data[guild_id]["whitelist"]
            log_channel = config_data[guild_id]["log_channel"]

            embed = discord.Embed(
                title="⚙️ Server Configuration",
                color=discord.Color.blurple()
            )
            embed.add_field(name="Co-Owners", value="\n".join([f"<@{uid}>" for uid in co_owners]) or "None", inline=False)
            embed.add_field(name="Whitelisted Users", value="\n".join([f"<@{uid}>" for uid in whitelist]) or "None", inline=False)
            embed.add_field(name="Log Channel", value=f"<#{log_channel}>" if log_channel else "Not set", inline=False)
            embed.set_footer(text="reap.cc")

            await interaction.response.send_message(embed=embed, ephemeral=True)

    view = ConfigView()
    await ctx.send("🔧 Configuration Panel", view=view)

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
@commands.has_permissions(administrator=True)
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
@commands.has_permissions(administrator=True)
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
@commands.has_permissions(administrator=True)
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

    webhook = discord.SyncWebhook.from_url(WEBHOOK_URL)
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

    webhook = discord.SyncWebhook.from_url(WEBHOOK_URL)
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

    webhook = discord.SyncWebhook.from_url(WEBHOOK_URL)
    await webhook.send(embed=embed, username="reap.cc")

@bot.command()
@commands.is_owner()
async def servers(ctx):
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
        title="📜 Vino Command List",
        description="Here are all available commands:",
        color=discord.Color.orange()
    )

    for command in bot.commands:
        if command.hidden:
            continue  # Skip hidden commands
        embed.add_field(
            name=f",{command.name}",
            value=command.help or "No description provided.",
            inline=False
        )

    embed.set_footer(text=EMBED_FOOTER)
    await ctx.send(embed=embed)

@bot.command()
async def help(ctx):
    try:
        await ctx.author.send(
            "👋 Need support with our bot or server?\n\nPlease join our support server and create a ticket:\n🔗 https://discord.gg/j6bXmjtfSU"
        )
        await ctx.send("📬 Help info sent to your DMs.")
    except discord.Forbidden:
        await ctx.send("❌ I couldn’t DM you. Please make sure your DMs are open.")



bot.run(TOKEN)
