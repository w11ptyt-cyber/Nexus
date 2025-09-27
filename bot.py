import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="+", intents=intents)

banned_words = ["badword1", "badword2"]

bot.remove_command("help")  # Remove default help to override it


class CustomHelp(commands.HelpCommand):
    def get_command_signature(self, command):
        return f"{self.context.clean_prefix}{command.qualified_name} {command.signature}"

    async def send_bot_help(self, mapping):
        embed = discord.Embed(
            title="📘 Bot Commands Help",
            description="Use `+help <command>` for more info on a command.",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow(),
        )
        for cog, commands_list in mapping.items():
            filtered = await self.filter_commands(commands_list, sort=True)
            if filtered:
                name = getattr(cog, "qualified_name", "General")
                value = "\n".join(
                    f"`{self.get_command_signature(c)}` - {c.help or 'No description'}"
                    for c in filtered
                )
                embed.add_field(name=name, value=value, inline=False)
        embed.set_footer(
            text=f"Requested by {self.context.author}", icon_url=self.context.author.avatar.url if self.context.author.avatar else None
        )
        channel = self.get_destination()
        await channel.send(embed=embed)

    async def send_command_help(self, command):
        embed = discord.Embed(
            title=self.get_command_signature(command),
            description=command.help or "No description provided.",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow(),
        )
        if aliases := command.aliases:
            embed.add_field(name="Aliases", value=", ".join(aliases), inline=False)
        embed.set_footer(
            text=f"Requested by {self.context.author}", icon_url=self.context.author.avatar.url if self.context.author.avatar else None
        )
        channel = self.get_destination()
        await channel.send(embed=embed)

    async def send_error_message(self, error):
        channel = self.get_destination()
        await channel.send(error)


bot.help_command = CustomHelp()


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    for word in banned_words:
        if word in message.content.lower():
            await message.delete()
            await message.channel.send(f"{message.author.mention}, that word is not allowed!")
            return

    await bot.process_commands(message)


@bot.command(help="Kick a member from the server.")
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    try:
        await member.kick(reason=reason)
        await ctx.send(
            embed=discord.Embed(
                description=f"✅ Kicked {member.mention}\nReason: {reason or 'No reason provided'}",
                color=discord.Color.blue(),
            )
        )
    except discord.Forbidden:
        await ctx.send("I do not have permission to kick this user.")
    except discord.HTTPException:
        await ctx.send("Failed to kick the user.")


@bot.command(help="Ban a member from the server.")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    try:
        await member.ban(reason=reason)
        await ctx.send(
            embed=discord.Embed(
                description=f"✅ Banned {member.mention}\nReason: {reason or 'No reason provided'}",
                color=discord.Color.blue(),
            )
        )
    except discord.Forbidden:
        await ctx.send("I do not have permission to ban this user.")
    except discord.HTTPException:
        await ctx.send("Failed to ban the user.")


@bot.command(help="Mute a member by adding Muted role.")
@commands.has_permissions(mute_members=True)
async def mute(ctx, member: discord.Member):
    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not mute_role:
        mute_role = await ctx.guild.create_role(name="Muted")
        for channel in ctx.guild.channels:
            await channel.set_permissions(
                mute_role, speak=False, send_messages=False, add_reactions=False
            )
    await member.add_roles(mute_role)
    await ctx.send(
        embed=discord.Embed(
            description=f"🔇 Muted {member.mention}", color=discord.Color.blue()
        )
    )


@bot.command(help="Unmute a muted member.")
@commands.has_permissions(mute_members=True)
async def unmute(ctx, member: discord.Member):
    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if mute_role in member.roles:
        await member.remove_roles(mute_role)
        await ctx.send(
            embed=discord.Embed(
                description=f"🔈 Unmuted {member.mention}", color=discord.Color.blue()
            )
        )
    else:
        await ctx.send(f"{member.mention} is not muted.")


@bot.command(help="Lock a channel to prevent members from sending messages.")
@commands.has_permissions(manage_channels=True)
async def lock(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    overwrite = channel.overwrites_for(ctx.guild.default_role)
    overwrite.send_messages = False
    await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
    await ctx.send(
        embed=discord.Embed(
            description=f"🔒 Locked {channel.mention}", color=discord.Color.blue()
        )
    )


@bot.command(help="Unlock a channel to allow members to send messages.")
@commands.has_permissions(manage_channels=True)
async def unlock(ctx, channel: discord.TextChannel = None):
    channel = channel or ctx.channel
    overwrite = channel.overwrites_for(ctx.guild.default_role)
    overwrite.send_messages = True
    await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
    await ctx.send(
        embed=discord.Embed(
            description=f"🔓 Unlocked {channel.mention}", color=discord.Color.blue()
        )
    )


@bot.command(help="Delete and recreate the current channel (Nuke command).")
@commands.has_permissions(administrator=True)
async def renew(ctx):
    channel = ctx.channel
    new_channel = await channel.clone(reason="Channel nuked by renew command")
    await channel.delete()
    await new_channel.send(
        embed=discord.Embed(
            description="Channel has been nuked and renewed!",
            color=discord.Color.blue(),
        )
    )


@bot.command(help="Show the bot's latency.")
async def ping(ctx):
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Latency: {round(bot.latency * 1000)}ms",
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow(),
    )
    embed.set_footer(
        text=f"Requested by {ctx.author}",
        icon_url=ctx.author.avatar.url if ctx.author.avatar else None,
    )
    await ctx.send(embed=embed)


@bot.command(help="Make the bot say something.")
async def say(ctx, *, message=None):
    if not message:
        await ctx.send("Please provide a message to say.")
        return
    await ctx.message.delete()
    await ctx.send(embed=discord.Embed(description=message, color=discord.Color.blue()))


@bot.command(help="Show a user's avatar.")
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(
        title=f"{member.display_name}'s Avatar",
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow(),
    )
    embed.set_image(url=member.avatar.url)
    embed.set_footer(
        text=f"Requested by {ctx.author}",
        icon_url=ctx.author.avatar.url if ctx.author.avatar else None,
    )
    await ctx.send(embed=embed)


@bot.command(help="Show detailed information about the server.")
async def serverinfo(ctx):
    guild = ctx.guild
    embed = discord.Embed(
        title=f"🌐 {guild.name} Server Info",
        description="Detailed server information.",
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow(),
    )
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    embed.add_field(name="Server ID", value=guild.id, inline=True)
    embed.add_field(name="Owner", value=guild.owner.mention if guild.owner else "Unknown", inline=True)
    embed.add_field(name="Created On", value=guild.created_at.strftime("%b %d, %Y"), inline=True)
    embed.add_field(name="Members", value=guild.member_count, inline=True)
    embed.add_field(
        name="Channels",
        value=f"{len(guild.text_channels)} Text | {len(guild.voice_channels)} Voice",
        inline=True,
    )
    embed.set_footer(
        text=f"Requested by {ctx.author}",
        icon_url=ctx.author.avatar.url if ctx.author.avatar else None,
    )
    await ctx.send(embed=embed)


@bot.command(help="Delete a number of messages in the channel.")
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 5):
    deleted = await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"{len(deleted)-1} messages deleted!")
    await msg.delete(delay=3)


@bot.command(help="Display information about the bot.")
async def botinfo(ctx):
    embed = discord.Embed(
        title="🤖 Bot Info",
        description="A powerful moderation bot with beautiful blue-themed embeds.",
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow(),
    )
    embed.add_field(name="Library", value="discord.py")
    embed.add_field(name="Prefix", value=bot.command_prefix)
    embed.set_footer(
        text=f"Requested by {ctx.author}",
        icon_url=ctx.author.avatar.url if ctx.author.avatar else None,
    )
    await ctx.send(embed=embed)


@bot.command(help="Display server rules.")
@commands.has_permissions(manage_guild=True)
async def rules(ctx):
    embed = discord.Embed(
        title="📜 Server Rules", color=discord.Color.blue(), timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="Rule 1", value="Be respectful to everyone.", inline=False)
    embed.add_field(name="Rule 2", value="No spamming or flooding the chat.", inline=False)
    embed.add_field(name="Rule 3", value="No offensive language.", inline=False)
    embed.add_field(name="Rule 4", value="Follow Discord Terms of Service.", inline=False)
    embed.set_footer(
        text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None
    )
    await ctx.send(embed=embed)


bot.run("MTQyMTQwNTM3MTY1MzgyMDQzNw.GGFoE9.SQBH8tGzsQnexwmoqP2Ip-iwO0-Z82oPdlngHI")
