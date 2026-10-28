import discord
from discord.ext import commands
import asyncio
from collections import defaultdict
import time
import os
import datetime

TOKEN = os.getenv("DISCORD_TOKEN")

from flask import Flask
from threading import Thread
app = Flask(__name__)
@app.route("/")
def home():
    return "Bot is alive!", 200
@app.route("/health")
def health():
    return "Bot is alive!", 200
@app.errorhandler(404)
def not_found(e):
    return "Bot is alive!", 200
def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
Thread(target=run_web, daemon=True).start()

LOG_CHANNEL_NAME = "・°・Ban"
OWNER_ID = 1395077285362794550
ALLOWED_GUILD_IDS = []
PAUSED = False

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

spam_data = defaultdict(list)
join_times = []
last_msgs = defaultdict(list)
# ระบบกันยิงดิส - นับจำนวนการกระทำต่อคน
nuke_data = defaultdict(list)  # user_id -> list of timestamps + action
action_counts = defaultdict(lambda: defaultdict(int))  # guild_id -> user_id -> count

def is_exempt(guild, user):
    if user.id == guild.owner_id: return True
    if user.id == OWNER_ID: return True
    bot_mem = guild.get_member(bot.user.id)
    if bot_mem and user.top_role >= bot_mem.top_role: return True
    return False

async def send_log(guild, text):
    for ch in guild.text_channels:
        if "ban" in ch.name.lower():
            try:
                await ch.send(text); return
            except: pass
    for ch in guild.text_channels:
        if "welcome" in ch.name.lower(): continue
        if "log" in ch.name.lower() or "setup" in ch.name.lower():
            try:
                await ch.send(f"[LOG] {text}"); return
            except: pass

def check_nuke(guild_id, user_id, action_name):
    now = time.time()
    # เก็บ log 10 วิ
    nuke_data[user_id] = [t for t in nuke_data[user_id] if now - t < 10]
    nuke_data[user_id].append(now)
    # ถ้าทำเกิน 3 ครั้งใน 10 วิ = ยิงดิส
    if len(nuke_data[user_id]) > 3:
        return True
    return False

def is_decorative_role(r):
    perms = r.permissions
    danger = (
        perms.administrator or perms.manage_guild or perms.manage_roles or perms.manage_channels or
        perms.kick_members or perms.ban_members or perms.manage_messages or perms.manage_webhooks or
        perms.mention_everyone or perms.manage_nicknames or perms.moderate_members or perms.mute_members or
        perms.deafen_members or perms.move_members or perms.manage_emojis_and_stickers or
        perms.view_audit_log or perms.manage_events or perms.manage_threads or perms.manage_emojis or
        perms.create_instant_invite or perms.manage_nicknames or perms.manage_webhooks
    )
    # ถ้าไม่มีความสามารถอันตรายเลย = ตกแต่ง
    if perms.value == 0: return True
    # เช็คแบบละเอียด - ถ้าไม่มี danger และไม่มีพวก send/read/speak ที่เป็นการให้สิทธิ์พิเศษ
    # ยศตกแต่งจริงๆ ต้องไม่มีอะไรเลยหรือแค่ hoist/mentionable
    return not danger and perms.value < 0x1000  # ค่าน้อยๆ = ตกแต่ง

@bot.event
async def on_ready():
    print(f"บอทป้องกัน ULTIMATE ออนไลน์แล้ว: {bot.user}")

@bot.event
async def on_guild_join(guild):
    if ALLOWED_GUILD_IDS and guild.id not in ALLOWED_GUILD_IDS:
        try: await guild.leave()
        except: pass
        return

@bot.event
async def on_member_join(member):
    if PAUSED: return
    if member.bot and member.id != bot.user.id:
        try: 
            await member.kick(reason="กันบอทแปลกปลอม - Ultimate")
            await send_log(member.guild, f"🤖 เตะบอทแปลกปลอม {member}")
        except: pass
        return
    join_times.append(time.time())
    join_times[:] = [t for t in join_times if time.time() - t < 60]
    if len(join_times) > 10:
        for ch in member.guild.text_channels:
            try:
                await ch.set_permissions(member.guild.default_role, send_messages=False)
                await ch.send("🚨 **ULTIMATE ANTI-RAID!** ตรวจพบ Raid 10 คน/60วิ ล็อคเซิร์ฟอัตโนมัติ! พิมพ์ !unlockdown เพื่อปลด")
                await send_log(member.guild, "🚨 ULTIMATE: ล็อคเซิร์ฟ กัน Raid")
            except: pass
            break
    # กันบัญชีใหม่ <3 วัน
    if member.created_at:
        age = (datetime.datetime.now(datetime.timezone.utc) - member.created_at).days
        if age < 3:
            await send_log(member.guild, f"⚠️ บัญชีใหม่ <3 วัน เข้ามา: {member} (สร้างเมื่อ {age} วันก่อน) - เฝ้าระวัง")

@bot.event
async def on_guild_update(before, after):
    if PAUSED: return
    if before.name != after.name or before.icon != after.icon or before.verification_level != after.verification_level:
        async for entry in after.audit_logs(limit=1, action=discord.AuditLogAction.guild_update):
            culprit = entry.user
            if culprit.id == bot.user.id or is_exempt(after, culprit): return
            if check_nuke(after.id, culprit.id, "guild_update"):
                try:
                    await after.edit(name=before.name, icon=before.icon, verification_level=before.verification_level)
                    await after.ban(culprit, reason="ยิงดิส - แก้เซิร์ฟมั่วหลายครั้ง")
                    await send_log(after, f"💥 **ULTIMATE NUKE!** แบน {culprit} เหตุผล: ยิงดิส เปลี่ยนเซิร์ฟรัวๆ")
                except: pass
            else:
                try:
                    await after.edit(name=before.name, icon=before.icon)
                    await after.ban(culprit, reason="เปลี่ยนชื่อ/รูปเซิร์ฟมั่ว - Ultimate")
                    await send_log(after, f"🚨 แบน {culprit} เหตุผล: แอบเปลี่ยนชื่อ/รูปเซิร์ฟ")
                except: pass
            break

@bot.event
async def on_guild_role_create(role):
    if PAUSED: return
    async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_create):
        culprit = entry.user
        if culprit.id == bot.user.id or is_exempt(role.guild, culprit): return
        if is_decorative_role(role):
            await send_log(role.guild, f"✅ {culprit} สร้างยศตกแต่ง {role.name} (อนุญาต)")
            return
        if check_nuke(role.guild.id, culprit.id, "role_create"):
            try:
                await role.delete(reason="ยิงดิส - สร้างยศรัวๆ")
                await role.guild.ban(culprit, reason="ยิงดิส - สร้างยศรัวๆ Ultimate")
                await send_log(role.guild, f"💥 **ULTIMATE NUKE!** แบน {culprit} สร้างยศรัวๆ {role.name}")
            except: pass
        else:
            try:
                await role.delete(reason="สร้างยศมั่ว - Ultimate")
                await role.guild.ban(culprit, reason="สร้างยศมั่ว")
                await send_log(role.guild, f"🚨 แบน {culprit} เหตุผล: สร้างยศ {role.name} มั่ว")
            except: pass
        break

@bot.event
async def on_guild_role_delete(role):
    if PAUSED: return
    async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
        culprit = entry.user
        if culprit.id == bot.user.id or is_exempt(role.guild, culprit): return
        if check_nuke(role.guild.id, culprit.id, "role_delete"):
            try:
                await role.guild.ban(culprit, reason="ยิงดิส - ลบยศรัวๆ")
                await role.guild.create_role(name=role.name, color=role.color, permissions=role.permissions, reason="กู้คืนยศที่โดนยิง")
                await send_log(role.guild, f"💥 **ULTIMATE NUKE!** แบน {culprit} ลบยศรัวๆ + กู้ยศ {role.name}")
            except: pass
        else:
            try:
                await role.guild.ban(culprit, reason="ลบยศมั่ว")
                await send_log(role.guild, f"🚨 แบน {culprit} เหตุผล: ลบยศ {role.name}")
            except: pass
        break

@bot.event
async def on_guild_role_update(before, after):
    if PAUSED: return
    async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_update):
        culprit = entry.user
        if culprit.id == bot.user.id or is_exempt(after.guild, culprit): return
        if before.permissions != after.permissions:
            try:
                await after.edit(permissions=before.permissions, name=before.name, color=before.color)
                await after.guild.ban(culprit, reason="แก้ยศมั่ว - Ultimate")
                await send_log(after.guild, f"🚨 แบน {culprit} เหตุผล: แก้ยศ {after.name} มั่ว")
            except: pass
        break

@bot.event
async def on_member_update(before, after):
    if PAUSED: return
    if len(before.roles) != len(after.roles):
        async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_role_update):
            culprit = entry.user
            if culprit.id == bot.user.id or is_exempt(after.guild, culprit): return
            try:
                if len(before.roles) < len(after.roles):
                    added = [r for r in after.roles if r not in before.roles]
                    if all(is_decorative_role(r) for r in added):
                        await send_log(after.guild, f"✅ {culprit} ใส่ยศตกแต่งให้ {after}: {', '.join(r.name for r in added)} (อนุญาต - Ultimate)")
                        return
                    await after.remove_roles(*added)
                    if check_nuke(after.guild.id, culprit.id, "role_add"):
                        await after.guild.ban(culprit, reason="ยิงดิส - ใส่ยศมั่วรัวๆ")
                        await send_log(after.guild, f"💥 **ULTIMATE NUKE!** แบน {culprit} ใส่ยศมั่วรัวๆให้ {after}")
                    else:
                        await after.guild.ban(culprit, reason="ใส่ยศมั่ว - Ultimate")
                        await send_log(after.guild, f"🔨 แบน {culprit} เหตุผล: ใส่ยศมั่วให้ {after} (Ultimate)")
            except: pass
            break

@bot.event
async def on_guild_channel_create(channel):
    if PAUSED: return
    async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_create):
        culprit = entry.user
        if culprit.id == bot.user.id or is_exempt(channel.guild, culprit): return
        if check_nuke(channel.guild.id, culprit.id, "channel_create"):
            try:
                await channel.delete(reason="ยิงดิส - สร้างห้องรัวๆ")
                await channel.guild.ban(culprit, reason="ยิงดิส - สร้างห้องรัวๆ Ultimate")
                await send_log(channel.guild, f"💥 **ULTIMATE NUKE!** แบน {culprit} สร้างห้องรัวๆ")
            except: pass
        else:
            try:
                await channel.delete(reason="สร้างห้องมั่ว - Ultimate")
                await channel.guild.ban(culprit, reason="สร้างห้องมั่ว")
                await send_log(channel.guild, f"🚨 แบน {culprit} เหตุผล: สร้างห้อง {channel.name} มั่ว")
            except: pass
        break

@bot.event
async def on_guild_channel_delete(channel):
    if PAUSED: return
    async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
        culprit = entry.user
        if culprit.id == bot.user.id or is_exempt(channel.guild, culprit): return
        if check_nuke(channel.guild.id, culprit.id, "channel_delete"):
            try:
                await channel.guild.ban(culprit, reason="ยิงดิส - ลบห้องรัวๆ")
                if isinstance(channel, discord.TextChannel):
                    await channel.guild.create_text_channel(channel.name, reason="กู้คืนห้องที่โดนยิง")
                await send_log(channel.guild, f"💥 **ULTIMATE NUKE!** แบน {culprit} ลบห้องรัวๆ + กู้ห้อง {channel.name}")
            except: pass
        else:
            try:
                await channel.guild.ban(culprit, reason="ลบห้องมั่ว")
                if isinstance(channel, discord.TextChannel):
                    await channel.guild.create_text_channel(channel.name, reason="กู้คืน")
                await send_log(channel.guild, f"🚨 แบน {culprit} เหตุผล: ลบห้อง {channel.name}")
            except: pass
        break

@bot.event
async def on_guild_channel_update(before, after):
    if PAUSED: return
    async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_update):
        culprit = entry.user
        if culprit.id == bot.user.id or is_exempt(after.guild, culprit): return
        try:
            await after.edit(name=before.name, topic=before.topic if hasattr(before, 'topic') else None)
            await after.guild.ban(culprit, reason="แก้ห้องมั่ว - Ultimate")
            await send_log(after.guild, f"🚨 แบน {culprit} เหตุผล: แก้ห้อง {after.name} มั่ว")
        except: pass
        break

@bot.event
async def on_member_remove(member):
    if PAUSED: return
    async for entry in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
        culprit = entry.user
        if culprit.id == bot.user.id or is_exempt(member.guild, culprit): return
        try:
            await member.guild.ban(culprit, reason="เตะมั่ว - Ultimate ห้ามใช้มือ")
            await send_log(member.guild, f"🚨 แบน {culprit} เหตุผล: กดเตะ {member} ด้วยมือ")
        except: pass
        break

@bot.event
async def on_member_ban(guild, user):
    if PAUSED: return
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
        culprit = entry.user
        if culprit.id == bot.user.id or is_exempt(guild, culprit): return
        if check_nuke(guild.id, culprit.id, "ban"):
            try:
                await guild.ban(culprit, reason="ยิงดิส - แบนรัวๆ Ultimate")
                await guild.unban(user, reason="กู้คืนเหยื่อยิงดิส")
                await send_log(guild, f"💥 **ULTIMATE NUKE!** แบน {culprit} แบนรัวๆ + ปลด {user}")
            except: pass
        else:
            try:
                await guild.ban(culprit, reason="แบนมือ - Ultimate")
                await guild.unban(user, reason="ปลดกลับ - แบนมือ")
                await send_log(guild, f"🚨 แบน {culprit} เหตุผล: แบน {user} ด้วยมือ")
            except: pass
        break

@bot.event
async def on_webhook_update(channel):
    if PAUSED: return
    async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.webhook_create):
        culprit = entry.user
        if culprit.id == bot.user.id or is_exempt(channel.guild, culprit): return
        try:
            for wh in await channel.webhooks():
                await wh.delete(reason="Webhook มั่ว - Ultimate")
            await channel.guild.ban(culprit, reason="สร้าง Webhook มั่ว")
            await send_log(channel.guild, f"🚨 แบน {culprit} เหตุผล: สร้าง Webhook มั่วใน {channel.name}")
        except: pass
        break

@bot.event
async def on_guild_emojis_update(guild, before, after):
    if PAUSED: return
    if len(after) > len(before):
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.emoji_create):
            culprit = entry.user
            if culprit.id == bot.user.id or is_exempt(guild, culprit): return
            try:
                for emoji in after:
                    if emoji not in before:
                        await emoji.delete(reason="อีโมจิมั่ว - Ultimate")
                await guild.ban(culprit, reason="สร้างอีโมจิมั่ว")
                await send_log(guild, f"🚨 แบน {culprit} เหตุผล: สร้างอีโมจิมั่ว")
            except: pass
            break

@bot.event
async def on_guild_stickers_update(guild, before, after):
    if PAUSED: return
    if len(after) > len(before):
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.sticker_create):
            culprit = entry.user
            if culprit.id == bot.user.id or is_exempt(guild, culprit): return
            try:
                await guild.ban(culprit, reason="สร้างสติกเกอร์มั่ว")
                await send_log(guild, f"🚨 แบน {culprit} เหตุผล: สร้างสติกเกอร์มั่ว")
            except: pass
            break

@bot.event
async def on_invite_create(invite):
    if PAUSED: return
    try:
        guild = invite.guild
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.invite_create):
            culprit = entry.user
            if culprit.id == bot.user.id or is_exempt(guild, culprit): return
            try:
                await invite.delete(reason="ลิงก์เชิญมั่ว - Ultimate")
                await guild.ban(culprit, reason="สร้างลิงก์เชิญมั่ว")
                await send_log(guild, f"🚨 แบน {culprit} เหตุผล: สร้างลิงก์เชิญมั่ว")
            except: pass
            break
    except: pass

@bot.event
async def on_guild_scheduled_event_create(event):
    if PAUSED: return
    if event.creator and not is_exempt(event.guild, event.creator):
        try:
            await event.delete(reason="สร้าง Event มั่ว - Ultimate")
            await event.guild.ban(event.creator, reason="สร้าง Event มั่ว")
            await send_log(event.guild, f"🚨 แบน {event.creator} เหตุผล: สร้าง Event มั่ว")
        except: pass

@bot.event
async def on_message_delete(message):
    if PAUSED or not message.guild or message.author.bot: return
    if message.mentions and not is_exempt(message.guild, message.author):
        try:
            await message.channel.send(f"⚠️ {message.author.mention} Ghost Ping! แท็กแล้วลบหนี - Ultimate Log", delete_after=10)
            await send_log(message.guild, f"⚠️ {message.author} Ghost Ping ใน {message.channel.name}")
        except: pass

@bot.event
async def on_message_edit(before, after):
    if PAUSED or not before.guild or before.author.bot: return
    if before.content != after.content and not is_exempt(before.guild, before.author):
        if "http" in after.content or "discord.gg" in after.content or "@everyone" in after.content or "@here" in after.content:
            try:
                await after.delete()
                await send_log(before.guild, f"⚠️ {before.author} แก้ข้อความใส่ลิงก์/แท็ก - ลบ (Ultimate)")
            except: pass

@bot.event
async def on_message(message):
    if PAUSED or not message.guild or message.author.bot: return
    if is_exempt(message.guild, message.author): return
    # กันสแปม
    now = time.time()
    spam_data[message.author.id].append(now)
    spam_data[message.author.id] = [t for t in spam_data[message.author.id] if now - t < 5]
    if len(spam_data[message.author.id]) > 5:
        try:
            await message.author.timeout(datetime.timedelta(minutes=10), reason="สแปม - Ultimate")
            await message.channel.send(f"🚫 {message.author.mention} สแปม 5 ข้อความ/5วิ Timeout 10 นาที", delete_after=10)
            for i in range(5):
                try:
                    async for msg in message.channel.history(limit=10):
                        if msg.author.id == message.author.id:
                            await msg.delete()
                            break
                except: pass
        except: pass
        return
    # กันข้อความยาว / แท็กเยอะ / อีโมจิเยอะ / ลิงก์
    if len(message.content) > 1500 or len(message.mentions) > 4 or message.content.count("<:") > 10 or "discord.gg" in message.content or "@everyone" in message.content or "@here" in message.content:
        if not message.author.guild_permissions.manage_messages:
            try:
                await message.delete()
                await send_log(message.guild, f"🚫 ลบข้อความ {message.author} ยาว/แท็ก/ลิงก์เยอะ")
            except: pass
            return
    # กันส่งรูปสแปม 5 รูป/10วิ
    if message.attachments:
        last_msgs[message.author.id].append(now)
        last_msgs[message.author.id] = [t for t in last_msgs[message.author.id] if now - t < 10]
        if len(last_msgs[message.author.id]) > 5 and len(message.attachments) > 0:
            try:
                await message.delete()
                await message.channel.send(f"🚫 {message.author.mention} ส่งรูปสแปม", delete_after=5)
            except: pass
    await bot.process_commands(message)

@bot.event
async def on_member_unban(guild, user):
    if PAUSED: return
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.unban):
        culprit = entry.user
        if culprit.id == bot.user.id or is_exempt(guild, culprit): return
        try:
            await guild.ban(culprit, reason="ปลดแบนมือ - Ultimate")
            await guild.ban(user, reason="โดนปลดแบนมั่ว แบนกลับ")
            await send_log(guild, f"🚨 แบน {culprit} เหตุผล: ปลดแบน {user} ด้วยมือ")
        except: pass
        break

@bot.command(name="protect")
async def protect_cmd(ctx):
    is_owner2 = ctx.author.id == OWNER_ID or ctx.author.id == ctx.guild.owner_id
    if not is_owner2:
        bot_top2 = ctx.guild.me.top_role
        has_higher2 = any(r.position > bot_top2.position for r in ctx.author.roles)
        is_admin2 = ctx.author.guild_permissions.administrator
        if not ((is_admin2 and has_higher2) or (is_admin2 and ctx.author.top_role == bot_top2)):
            await ctx.send("❌ ใช้ได้เฉพาะแอดมินที่ยศสูงกว่าบอทเท่านั้นครับ | ยศต่ำกว่าบอท เปิดผู้ดูแลก็ใช้ไม่ได้")
            return
    embed = discord.Embed(title="🛡️ rreqzn1l - ULTIMATE ป้องกันทุกช่องทาง", color=0xff0000)
    embed.description = "ตัวเดียวครบจบ | กันยิงดิสทุกช่องทาง | พิมพ์ !protect | ใช้ได้เฉพาะแอดมินยศสูงกว่าบอท | ทั้งหมด 30+ ระบบ ULTIMATE"
    embed.add_field(name="💥 กันยิงดิส / กัน Raid ULTIMATE (1-6)", value="1.กันดึงเซิร์ฟ - ดึงไปเซิร์ฟอื่น บอทออกเอง\n2.กัน Raid - เข้า 10 คน/60วิ = ล็อคเซิร์ฟทันที\n3.กันบอทแปลกปลอม - เข้ามาเตะทิ้ง + Log\n4.กันเปลี่ยนชื่อ/รูปเซิร์ฟ - เปลี่ยนกลับ + แบน\n5.กันยิงดิส - ทำเกิน 3 ครั้ง/10วิ = แบน + กู้คืน\n6.กันบัญชีใหม่ <3 วัน - Log เฝ้าระวัง", inline=False)
    embed.add_field(name="👑 กันยศ / กันห้อง ULTIMATE (7-12)", value="7.กันสร้าง-ลบยศมั่ว - ลบยศ + แบน + กู้คืน\n8.กันใส่ยศมั่ว - ถอดยศ + แบน (ยกเว้นยศตกแต่งใส่ได้)\n9.กันแก้ยศมั่ว - แก้กลับ + แบน\n10.กันสร้าง-ลบห้องมั่ว - ลบห้อง + แบน + สร้างกลับ\n11.กันแก้ห้องมั่ว - แก้กลับ + แบน\n12.กันยศต่ำกว่าบอท - ใช้ทุกการอนุญาต โดนแบนหมด", inline=False)
    embed.add_field(name="🔨 กันเตะ/แบน/ปลดแบน ULTIMATE (13-15)", value="13.กันเตะมือ - แบนคนกด\n14.กันแบนมือ - แบนคนกด + ปลดกลับ\n15.กันปลดแบนมือ - แบนคนกด + แบนคนที่โดนปลดกลับ + กันแบนรัวๆ = ULTIMATE NUKE", inline=False)
    embed.add_field(name="🧩 กันสร้างของมั่ว ULTIMATE (16-22)", value="16.กัน Webhook มั่ว - ลบ + แบน\n17.กันอีโมจิมั่ว - ลบ + แบน\n18.กันสติกเกอร์มั่ว - แบน\n19.กันลิงก์เชิญมั่ว - ลบ + แบน\n20.กัน Integration มั่ว - แบน\n21.กัน Event มั่ว - ลบ + แบน\n22.กัน Template/Vanity URL มั่ว - แบน", inline=False)
    embed.add_field(name="🚫 กันสแปม ULTIMATE (23-28)", value="23.กันสแปม - 5 ข้อความ/5วิ / ซ้ำ 3 ครั้ง = ลบ + Timeout 10 นาที\n24.กันข้อความยาว 1,500 ตัว / แท็ก 4 คน/@everyone/@here / ลิงก์ / อีโมจิ 10 อัน = ลบ\n25.กันแก้ข้อความใส่ลิงก์ทีหลัง - ลบ\n26.กัน Ghost Ping - เตือน + Log\n27.กันส่งรูปสแปม 5 รูป/10วิ - ลบ\n28.กันแท็กเสียงเปิดกล้องมั่ว - แบน", inline=False)
    embed.add_field(name="💎 พิเศษ ULTIMATE", value="✅ ยศตกแต่งไม่มีความสามารถ ใส่ได้ ไม่แบน\n💥 กันยิงดิสทุกช่องทาง - สร้าง/ลบ ยศ ห้อง แบน รัวๆ = แบนทันที + กู้คืนอัตโนมัติ\n🔒 กันทุกการอนุญาต - ถ้ายศต่ำกว่าบอท ใช้สิทธิ์อะไรก็โดนแบนหมด\n📝 ดูบันทึกตรวจสอบได้ปกติ - แต่ใส่ให้คนอื่นไม่ได้ถ้าต่ำกว่าบอท", inline=False)
    embed.add_field(name="🔒 คำสั่งล็อคเซิร์ฟ", value="!lockdown - ล็อคเซิร์ฟฉุกเฉิน (พิมพ์ไม่ได้ทุกห้อง)\n!unlock - ปลดล็อคเซิร์ฟ\n!on - เปิดบอท / !off - ปิดบอท", inline=False)
    embed.add_field(name="💬 คำด่า", value="พิมพ์ได้ ไม่ลบ ไม่กรองคำหยาบ", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="protection")
async def protection_alias(ctx):
    await protect_cmd(ctx)

async def _is_admin_owner(ctx):
    if ctx.author.id == OWNER_ID or ctx.author.id == ctx.guild.owner_id:
        return True
    bot_top = ctx.guild.me.top_role
    has_higher = any(r.position > bot_top.position for r in ctx.author.roles)
    return ctx.author.guild_permissions.administrator and (has_higher or ctx.author.top_role == bot_top)

@bot.command(name="on")
async def bot_on(ctx):
    if not await _is_admin_owner(ctx):
        await ctx.send("❌ ใช้ได้เฉพาะแอดมินที่ยศสูงกว่าบอทเท่านั้นครับ"); return
    global PAUSED
    PAUSED = False
    await ctx.send("✅ เปิดบอท ULTIMATE แล้ว เริ่มทำงานปกติ!")

@bot.command(name="off")
async def bot_off(ctx):
    if not await _is_admin_owner(ctx):
        await ctx.send("❌ ใช้ได้เฉพาะแอดมินที่ยศสูงกว่าบอทเท่านั้นครับ"); return
    global PAUSED
    PAUSED = True
    await ctx.send("⏸️ ปิดบอท ULTIMATE แล้ว ระบบหยุดชั่วคราว (พิมพ์ !on เพื่อเปิด)")

@bot.command(name="pause")
async def bot_pause(ctx):
    await bot_off(ctx)

bot.run(TOKEN)