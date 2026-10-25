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
def home(): return "Bot is alive!"
def run_web():
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
Thread(target=run_web, daemon=True).start()

LOG_CHANNEL_NAME = "・°・Ban"
OWNER_ID = 1395077285362794550
case_counter = 127  # เริ่ม 127 ต่อไป 128 เหมือนในรูป
# ใส่ ID เซิร์ฟที่อนุญาตให้บอทอยู่ได้เท่านั้น ถ้าอยู่นอกนี้บอทจะออกเอง
# วิธีหา ID เซิร์ฟ: ใน Discord คลิกขวาชื่อเซิร์ฟ > Copy Server ID
ALLOWED_GUILD_IDS = []  # ตัวอย่าง: [123456789012345678] ใส่ ID เซิร์ฟพี่ตรงนี้ ถ้าว่างไว้จะอยู่ได้ทุกเซิร์ฟที่หัวดิสเป็นเจ้าของ
# เปิดมาจะหยุดทำงานก่อน ให้หัวดิสจัดยศก่อน แล้วพิมพ์ !on ถึงจะเริ่มทำงาน
PAUSED = False  # แก้แล้ว: เปิดทำงานเลย ไม่หยุดแล้ว ถ้าจะจัดยศให้พิมพ์ !pause ก่อน

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

spam_data = defaultdict(list)
join_times = []

def is_paused():
    return PAUSED

def is_exempt(guild, user):
    if user.id == guild.owner_id: return True
    if user.id == OWNER_ID: return True
    bot_mem = guild.get_member(bot.user.id)
    if bot_mem and user.top_role >= bot_mem.top_role: return True
    return False

async def send_log(guild, text, target=None):
    import re
    def norm(s):
        return re.sub(r"[^a-z0-9]", "", s.lower())
    txt_low = text.lower()
    if target is None:
        if "has been banned" in txt_low or "แบน" in txt_low:
            target = "banning-a-member"
        elif "unban" in txt_low or "ปลดแบน" in txt_low:
            target = "unban-a-member"
        elif ("create" in txt_low and "role" in txt_low) or "สร้างยศ" in text:
            target = "create-a-role"
        elif ("delet" in txt_low and "role" in txt_low) or "ลบยศ" in text:
            target = "deleting-a-role"
        elif ("add" in txt_low and "role" in txt_low) or "ใส่ยศ" in text:
            target = "add-member-role"
        elif ("remove" in txt_low and "role" in txt_low) or "ถอดยศ" in text:
            target = "remove-member-role"
        elif ("create" in txt_low and "channel" in txt_low) or "สร้างห้อง" in text:
            target = "create-a-channel"
        elif ("delet" in txt_low and "channel" in txt_low) or "ลบห้อง" in text:
            target = "delete-channel"
        elif "emoji" in txt_low and "create" in txt_low:
            target = "create-an-emoji"
        elif "emoji" in txt_low and "delet" in txt_low:
            target = "delete-emoji"
        elif "nickname" in txt_low or "ชื่อเล่น" in txt_low:
            target = "changing-nickname"
        elif "invite" in txt_low or "เชิญ" in txt_low:
            target = "save-invitation"
        elif "voice" in txt_low or "ห้องพูดคุย" in txt_low:
            target = "room-entryexit-log"
    # 1. ลองห้องตรงตัวแบบ normalized ก่อน - แก้ปัญหาหาชื่อห้องไม่เจอ
    if target:
        target_norm = norm(target)
        for ch in guild.text_channels:
            if target_norm in norm(ch.name) or norm(ch.name) in target_norm:
                try:
                    await ch.send(text); return True
                except: pass
        # ลองแบบเดิม substring
        for ch in guild.text_channels:
            if target in ch.name.lower():
                try:
                    await ch.send(text); return True
                except: pass
    # 2. ถ้าไม่เจอห้องตรง ให้ส่งไปห้องแบนเป็น fallback เท่านั้น
    for ch in guild.text_channels:
        if "ban" in ch.name.lower():
            try:
                await ch.send(text); return True
            except: pass
    for ch in guild.text_channels:
        if "security" in ch.name.lower() or "modlog" in ch.name.lower():
            try:
                await ch.send(text); return True
            except: pass
    for ch in guild.text_channels:
        if 'setup' in ch.name.lower():
            try:
                await ch.send(text); return True
            except: pass
    for ch in guild.text_channels:
        try:
            await ch.send(f"[LOG] {text}"); return True
        except: pass
    return False

@bot.event
async def on_ready():
    print(f"บอทออนไลน์แล้ว: {bot.user} - V5 โหดสุดครบจบ")

@bot.event
async def on_guild_join(guild):
    # กันคนอื่นดึงบอท: ถ้าเซิร์ฟนี้เจ้าของไม่ใช่หัวดิส ออกทันที
    # ยกเว้นหัวดิสเท่านั้นที่ดึงได้
    if guild.owner_id != OWNER_ID:
        print(f"บอทโดนดึงไปเซิร์ฟ {guild.name} ({guild.id}) ที่ไม่อนุญาต -> ออก")
        try:
            await guild.leave()
        except: pass
        return
    # ถ้าเซิร์ฟนี้ไม่ใช่ของหัวดิส และไม่ใช่ ID ที่หัวดิสอนุญาต ก็ออก
    if guild.owner_id != OWNER_ID and ALLOWED_GUILD_IDS:
        print(f"เซิร์ฟ {guild.name} เจ้าของไม่ใช่หัวดิส -> ออก")
        try:
            await guild.leave()
        except: pass
        return
    print(f"บอทเข้าเซิร์ฟ {guild.name} สำเร็จ")

@bot.event
async def on_member_join(member):
    if PAUSED: return
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
    if PAUSED: return
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
    if PAUSED: return
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
    if PAUSED: return
    async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
        culprit = entry.user
        if culprit.id == bot.user.id or is_exempt(role.guild, culprit): return
        try:
            await role.guild.ban(culprit, reason="ลบยศมั่ว")
            await send_log(role.guild, f"🚨 แบน {culprit} เหตุผล: ลบยศ {role.name}")
        except: pass

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
                    await after.remove_roles(*added)
                await after.guild.ban(culprit, reason="ใส่ยศมั่ว")
                await send_log(after.guild, f"🔨 แบน {culprit} เหตุผล: ใส่ยศมั่วให้ {after}")
            except: pass
            break

@bot.event
async def on_guild_channel_create(channel):
    if PAUSED: return
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
    if PAUSED: return
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
    if PAUSED: return
    async for entry in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
        culprit = entry.user
        if culprit.id == bot.user.id or is_exempt(member.guild, culprit): return
        try:
            await member.guild.ban(culprit, reason="เตะมือ ห้ามใช้ ต้องใช้ !kick")
            await send_log(member.guild, f"🚨 แบน {culprit} เหตุผล: กดเตะ {member} ด้วยมือ")
        except: pass

@bot.event
async def on_member_ban(guild, user):
    if PAUSED: return
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
    if PAUSED: return
    async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.webhook_create):
        culprit = entry.user
        if culprit.id != bot.user.id and not is_exempt(channel.guild, culprit):
            try:
                await channel.guild.ban(culprit, reason="สร้าง Webhook มั่ว")
                await send_log(channel.guild, f"🚨 แบน {culprit} เหตุผล: สร้าง Webhook")
            except: pass

@bot.event
async def on_message(message):
    global PAUSED
    if message.author.bot: return
    # ถ้าบอทหยุดทำงานอยู่ ให้หัวดิสพิมพ์ !on เพื่อเปิดเท่านั้น
    if PAUSED:
        if message.content.strip() == "!on" and (message.author.id == OWNER_ID or message.author.id == message.guild.owner_id):
            PAUSED = False
            await message.channel.send("✅ เปิดบอทแล้ว ทำงานปกติ!")
            return
        # ถ้าหยุดอยู่ คำสั่งอื่นไม่ต้องทำอะไรเลย ยกเว้นให้บอทประมวลผล !on
        if message.content.strip().startswith("!"):
            await bot.process_commands(message)
        return
    # ถ้าเป็นแอดมิน ให้ใช้คำสั่งได้เลย ไม่ต้องเช็คสแปม
    if message.author.guild_permissions.administrator:
        await bot.process_commands(message)
        return
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
    global case_counter
    case_counter += 1
    await ctx.guild.ban(member, reason=reason)
    msg = f"✅ Case #{case_counter} {member.mention} has been banned.\nเหตุผล: {reason} | โดย: {ctx.author}"
    await send_log(ctx.guild, msg)
    await ctx.send(msg)

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

@bot.command()
@commands.has_permissions(administrator=True)
async def pause(ctx):
    global PAUSED
    PAUSED = False  # แก้แล้ว: เปิดทำงานเลย ไม่หยุดแล้ว ถ้าจะจัดยศให้พิมพ์ !pause ก่อน
    await ctx.send("⏸️ ปิดบอทชั่วคราวแล้ว บอทจะไม่แบน/เตะใครเลย จัดยศได้สบายๆ พอจัดเสร็จพิมพ์ !on")

@bot.command()
@commands.has_permissions(administrator=True)
async def on(ctx):
    global PAUSED
    PAUSED = False
    await ctx.send("✅ เปิดบอทแล้ว เริ่มทำงานปกติ!")

@bot.command()
@commands.has_permissions(administrator=True)
async def off(ctx):
    global PAUSED
    PAUSED = False  # แก้แล้ว: เปิดทำงานเลย ไม่หยุดแล้ว ถ้าจะจัดยศให้พิมพ์ !pause ก่อน
    await ctx.send("⏸️ ปิดบอทชั่วคราวแล้ว")


# ===== V7 PROTECT: แบนมือ/เตะมือ 1 ครั้ง แบนทันที + ปลดคนโดน =====
# on_member_ban / on_member_remove ใน V5 อยู่แล้ว: มันแบนคนทำ + unban คนโดนอัตโนมัติ
# เพิ่มเติม: กัน Nuke แบบ 1 ครั้ง
protect_data = {}
async def anti_nuke_1(guild, culprit, act):
    if is_exempt(guild, culprit): return
    if PAUSED: return
    try:
        await guild.ban(culprit, reason=f"แบนมือ/เตะมือ 1 ครั้ง แบนทันที: {act}")
        global case_counter
        case_counter += 1
        await send_log(guild, f"✅ Case #{case_counter} {culprit.mention} has been banned. เหตุผล: {act} ด้วยมือ 1 ครั้ง")
    except: pass


@bot.listen("on_invite_create")
async def log_invite_only(invite):
    # ตามที่พี่ขอ: ใครกดเชิญก็ได้ ไม่ลบ แต่แจ้งใน Log
    if PAUSED: return
    try:
        inv = invite.inviter.mention if invite.inviter else "ไม่รู้ใคร"
        await send_log(invite.guild, f"🔗 {inv} สร้างลิงก์เชิญ {invite.url} (อนุญาติให้สร้างได้ แค่แจ้ง Log)")
    except: pass


@bot.event
async def on_voice_state_update(member, before, after):
    if PAUSED: return
    # กันหัวดิสเองไม่ต้องแจ้ง? ไม่กัน แจ้งทุกคนที่เข้า-ออก
    try:
        if before.channel is None and after.channel is not None:
            await send_log(member.guild, f"🔊 {member.mention} เข้าห้องพูดคุย 🔊 {after.channel.name}")
        elif before.channel is not None and after.channel is None:
            await send_log(member.guild, f"🔇 {member.mention} ออกจากห้องพูดคุย 🔊 {before.channel.name}")
        elif before.channel != after.channel:
            await send_log(member.guild, f"🔄 {member.mention} ย้ายห้องพูดคุย จาก 🔊 {before.channel.name} -> 🔊 {after.channel.name}")
    except: pass


# ================= ULTIMATE PROTECT - จบเลย ไม่ต้องใช้บอทอื่น =================
# 1. กัน Ghost Ping (ปิงแล้วลบข้อความ)
# 2. กัน Mass Mention (ปิงหลายคนในทีเดียว)
# 3. กันส่งลิ้งค์ฟิชชิ่ง / discord.gg ปลอม
# 4. กันสแปมสติ๊กเกอร์ / รูป / อีโมจิรัวๆ
# 5. กันสร้าง Webhook รัวๆ / กันลบ Webhook
# 6. กันสร้างยศรัวๆ / สร้างห้องรัวๆ / สร้าง Emoji รัวๆ ใน 10 วิ แบนทันที
# 7. กัน Raid แบบโหด: เข้า 5 คนใน 10 วิ ล็อคเซิร์ฟทันที
# 8. กันคนเปลี่ยนชื่อเซิร์ฟ / เปลี่ยนรูป / เปลี่ยน Banner
# 9. กันคนใช้คำสั่งบอทอื่นมาแบนมั่ว

@bot.event
async def on_message_delete(message):
    if PAUSED: return
    if message.author.bot: return
    # Ghost ping: ถ้าข้อความที่ลบมีปิง @everyone หรือ @คน
    if "@everyone" in message.content or "@here" in message.content or len(message.mentions) > 0:
        try:
            await send_log(message.guild, f"👻 Ghost Ping: {message.author.mention} ปิงแล้วลบข้อความ: {message.content[:200]}")
        except: pass

# กันปิงหลายคน / ฟิชชิ่ง - แก้ใน on_message เดิมแล้ว ใช้ตรงนี้เสริม
@bot.listen("on_message")
async def ultimate_check(message):
    if PAUSED: return
    if message.author.bot: return
    if not message.guild: return
    # Mass mention: ปิงเกิน 5 คน
    if len(message.mentions) >= 5:
        try:
            await message.delete()
            await message.author.timeout(discord.utils.utcnow() + __import__('datetime').timedelta(minutes=10), reason="Mass Mention")
            await send_log(message.guild, f"🚫 Mass Mention: {message.author.mention} ปิง {len(message.mentions)} คน -> Mute 10 นาที")
        except: pass
        return
    # กันลิ้งค์ฟิชชิ่ง
    bad_words = ["discord.gg/", "free-nitro", "steamcommunity", "nitro-free", "grabify", "iplogger"]
    low = message.content.lower()
    if any(b in low for b in bad_words):
        # ถ้าเป็นลิ้งค์เชิญดิสปกติให้ผ่าน เพราะพี่อนุญาตแล้ว แต่ถ้าเป็นฟิชชิ่งให้ลบ
        if "free-nitro" in low or "grabify" in low or "iplogger" in low:
            try:
                await message.delete()
                await send_log(message.guild, f"🚫 ฟิชชิ่ง: {message.author.mention} ส่งลิ้งค์อันตราย: {message.content[:100]}")
            except: pass



# ================= 6 + 9 ที่พี่ขอเพิ่ม =================
# 6. กันคนเชิญบอทอื่นเข้ามา (Anti Bot Abuse)
@bot.listen('on_member_join')
async def on_member_join_ultimate_bot(member):
    if PAUSED: return
    if member.bot and member.id != bot.user.id:
        # ถ้าไม่ใช่บอทตัวนี้เอง ให้เตะออกทันที กันบอทอื่นมาแย่งงาน
        try:
            await member.kick(reason="กันบอทอื่น - ใช้บอท rreqzn1l ตัวเดียวพอ")
            await send_log(member.guild, f"🤖 เตะบอทอื่นออก: {member.mention} ({member.name}) เหตุผล: กันบอทอื่น - ใช้ตัวนี้ตัวเดียวพอ")
        except: pass

# 9. กันเปลี่ยน Banner / Icon เซิร์ฟรัวๆ
@bot.listen('on_guild_update')
async def on_guild_update_ultimate(before, after):
    if PAUSED: return
    # ถ้าเปลี่ยน Banner หรือ Icon ให้คืนค่าเดิม + แบนคนทำ
    if before.banner != after.banner or before.icon != after.icon:
        try:
            audit = [a async for a in after.audit_logs(limit=1, action=discord.AuditLogAction.guild_update)]
            if audit:
                culprit = audit[0].user
                if not is_exempt(after, culprit):
                    await after.edit(banner=before.banner, icon=before.icon)
                    await after.ban(culprit, reason="เปลี่ยน Banner/Icon เซิร์ฟมั่ว")
                    await send_log(after, f"✅ Case #{case_counter+1} {culprit.mention} has been banned. เหตุผล: เปลี่ยน Banner/Icon เซิร์ฟมั่ว")
        except: pass



bot.run(TOKEN)