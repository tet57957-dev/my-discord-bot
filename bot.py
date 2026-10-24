import discord
from discord.ext import commands
import asyncio
from collections import defaultdict
import time
import os

TOKEN = os.getenv("DISCORD_TOKEN")
from flask import Flask
from threading import Thread
app = Flask(__name__)
@app.route("/")
def home():
    return "Bot is alive!"
def run_web():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
Thread(target=run_web, daemon=True).start()
LOG_CHANNEL_NAME = "・°・Ban"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

spam_data = defaultdict(list)
join_times = []

def is_exempt(guild, user):
    if user.id == guild.owner_id: return True
    if user.guild_permissions.administrator: return True
    bot_mem = guild.get_member(bot.user.id)
    if bot_mem and user.top_role >= bot_mem.top_role: return True
    return False

async def send_log(guild, text):
    ch = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
    if ch: await ch.send(text)

@bot.event
async def on_ready():
    print(f"บอทออนไลน์แล้ว: {bot.user} - V5 โหดสุดครบจบ")

@bot.event
async def on_member_join(member):
    if member.bot and member.id != bot.user.id:
        try: await member.kick(reason="กันบอทแปลกปลอม")
        except: pass
        return
    join_times.append(time.time())
    join_times[:] = [t for t in join_times if time.time() - t < 60]
    if len(join_times) > 10:
        for ch in member.guild.text_channels:
            await ch.set_permissions(member.guild.default_role, send_messages=False)
            await ch.send("🚨 Raid! ล็อคเซิร์ฟแล้ว พิมพ์ !unlock")
            break

@bot.event
async def on_guild_update(before, after):
    if before.name != after.name or before.icon != after.icon:
        async for entry in after.audit_logs(limit=1, action=discord.AuditLogAction.guild_update):
            culprit = entry.user
            if culprit.id == bot.user.id or is_exempt(after, culprit): return
            try:
                await after.edit(name=before.name, icon=before.icon)
                await after.ban(culprit, reason="เปลี่ยนชื่อ/รูปเซิร์ฟมั่ว")
                await send_log(after, f"🚨 แบน {culprit} เหตุผล: แอบเปลี่ยนชื่อ/รูปเซิร์ฟ")
            except: pass
            break

@bot.event
async def on_guild_role_create(role):
    async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_create):
        culprit = entry.user
        if culprit.id == bot.user.id or is_exempt(role.guild, culprit): return
        try:
            await role.delete(reason="สร้างยศมั่ว")
            await role.guild.ban(culprit, reason="สร้างยศมั่ว")
            await send_log(role.guild, f"🚨 แบน {culprit} เหตุผล: สร้างยศ {role.name} มั่ว")
        except: pass

@bot.event
async def on_guild_role_delete(role):
    async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
        culprit = entry.user
        if culprit.id == bot.user.id or is_exempt(role.guild, culprit): return
        try:
            await role.guild.ban(culprit, reason="ลบยศมั่ว")
            await send_log(role.guild, f"🚨 แบน {culprit} เหตุผล: ลบยศ {role.name}")
        except: pass

@bot.event
async def on_member_update(before, after):
    if len(before.roles) != len(after.roles):
        async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_role_update):
            culprit = entry.user
            if culprit.id == bot.user.id or is_exempt(after.guild, culprit): return
            try:
                if len(before.roles) < len(after.roles):
                    added = [r for r in after.roles if r not in before.roles]
                    await after.remove_roles(*added)
                await after.guild.ban(culprit, reason="ใส่ยศมั่ว")
                await send_log(after.guild, f"🔨 แบน {culprit} เหตุผล: ใส่ยศมั่วให้ {after}")
            except: pass
            break

@bot.event
async def on_guild_channel_create(channel):
    async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_create):
        culprit = entry.user
        if culprit.id == bot.user.id or is_exempt(channel.guild, culprit): return
        try:
            await channel.delete(reason="สร้างห้องมั่ว")
            await channel.guild.ban(culprit, reason="สร้างห้องมั่ว")
            await send_log(channel.guild, f"🚨 แบน {culprit} เหตุผล: สร้างห้อง {channel.name} มั่ว")
        except: pass

@bot.event
async def on_guild_channel_delete(channel):
    async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
        culprit = entry.user
        if culprit.id == bot.user.id or is_exempt(channel.guild, culprit): return
        try:
            await channel.guild.ban(culprit, reason="ลบห้องมั่ว")
            await channel.guild.create_text_channel(channel.name)
            await send_log(channel.guild, f"🚨 แบน {culprit} เหตุผล: ลบห้อง {channel.name}")
        except: pass

@bot.event
async def on_member_remove(member):
    async for entry in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
        culprit = entry.user
        if culprit.id == bot.user.id or is_exempt(member.guild, culprit): return
        try:
            await member.guild.ban(culprit, reason="เตะมือ ห้ามใช้ ต้องใช้ !kick")
            await send_log(member.guild, f"🚨 แบน {culprit} เหตุผล: กดเตะ {member} ด้วยมือ")
        except: pass

@bot.event
async def on_member_ban(guild, user):
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
        culprit = entry.user
        if culprit.id == bot.user.id or is_exempt(guild, culprit): return
        try:
            await guild.ban(culprit, reason="แบนมือ ห้ามใช้ ต้องใช้ !ban")
            await guild.unban(user)
            await send_log(guild, f"🚨 แบน {culprit} เหตุผล: กดแบน {user} ด้วยมือ")
        except: pass

@bot.event
async def on_webhooks_update(channel):
    async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.webhook_create):
        culprit = entry.user
        if culprit.id != bot.user.id and not is_exempt(channel.guild, culprit):
            try:
                await channel.guild.ban(culprit, reason="สร้าง Webhook มั่ว")
                await send_log(channel.guild, f"🚨 แบน {culprit} เหตุผล: สร้าง Webhook")
            except: pass

@bot.event
async def on_message(message):
    if message.author.bot or message.author.guild_permissions.administrator: return
    if "@everyone" in message.content or "@here" in message.content:
        await message.delete()
        await send_log(message.guild, f"⚠️ {message.author} พยายามปิง @everyone")
        return
    if "http://" in message.content or "https://" in message.content or "discord.gg/" in message.content:
        await message.delete()
        await message.channel.send(f"{message.author.mention} ห้ามส่งลิงก์")
        return
    now = time.time()
    spam_data[message.author.id].append(now)
    spam_data[message.author.id] = [t for t in spam_data[message.author.id] if now - t < 5]
    if len(spam_data[message.author.id]) >= 5:
        await message.delete()
        await message.channel.send(f"{message.author.mention} ⛔ สแปม! Mute 10 นาที")
        await send_log(message.guild, f"🔇 Mute {message.author} 10 นาที เหตุผล: สแปม")
        role = discord.utils.get(message.guild.roles, name="Muted")
        if not role: role = await message.guild.create_role(name="Muted")
        await message.author.add_roles(role)
        await asyncio.sleep(600)
        await message.author.remove_roles(role)
        spam_data[message.author.id] = []
        return
    await bot.process_commands(message)

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="ไม่มีเหตุผล"):
    await ctx.guild.ban(member, reason=reason)
    await send_log(ctx.guild, f"✅ {ctx.author} ใช้บอทแบน {member} เหตุผล: {reason}")
    await ctx.send(f"แบน {member} แล้ว")

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="ไม่มีเหตุผล"):
    await member.kick(reason=reason)
    await send_log(ctx.guild, f"✅ {ctx.author} ใช้บอทเตะ {member} เหตุผล: {reason}")
    await ctx.send(f"เตะ {member} แล้ว")

@bot.command()
@commands.has_permissions(administrator=True)
async def unlock(ctx):
    for ch in ctx.guild.text_channels:
        await ch.set_permissions(ctx.guild.default_role, send_messages=None)
    await ctx.send("✅ ปลดล็อคแล้ว")

bot.run(TOKEN)