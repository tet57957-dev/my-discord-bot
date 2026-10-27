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

@bot.event
async def on_ready():
    print(f"บอทป้องกันออนไลน์แล้ว: {bot.user}")

@bot.event
async def on_guild_join(guild):
    if ALLOWED_GUILD_IDS and guild.id not in ALLOWED_GUILD_IDS:
        try: await guild.leave()
        except: pass
        return
    if guild.owner_id != OWNER_ID and ALLOWED_GUILD_IDS:
        try: await guild.leave()
        except: pass
        return

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
            try:
                await ch.set_permissions(member.guild.default_role, send_messages=False)
                await ch.send("🚨 Raid! ล็อคเซิร์ฟแล้ว")
            except: pass
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
            await member.guild.ban(culprit, reason="เตะมือ ห้ามใช้")
            await send_log(member.guild, f"🚨 แบน {culprit} เหตุผล: กดเตะ {member} ด้วยมือ")
        except: pass

@bot.event
async def on_member_ban(guild, user):
    if PAUSED: return
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
        culprit = entry.user
        if culprit.id == bot.user.id or is_exempt(guild, culprit): return
        try:
            await guild.ban(culprit, reason="แบนมือ ห้ามใช้")
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
    if message.author.bot: return
    if message.content.strip() in ["!on", "!off", "!pause"]:
        ctx2 = await bot.get_context(message)
        if message.content.strip() == "!on":
            await bot_on(ctx2)
        else:
            await bot_off(ctx2)
        return
    # !protect แบบ manual - ทำงานชัวร์ไม่ต้องผ่าน command system
    if message.content.strip() in ["!protect", "!protection"]:
        # เจ้าของเซิร์ฟใช้ได้เสมอ
        is_owner = message.author.id == OWNER_ID or (message.guild and message.author.id == message.guild.owner_id)
        if is_owner:
            ctx = await bot.get_context(message)
            await protect_cmd(ctx)
            return
        # แอดมินที่ยศสูงกว่าบอท
        try:
            bot_top = message.guild.me.top_role
            has_higher = any(r.position > bot_top.position for r in message.author.roles)
            is_admin = message.author.guild_permissions.administrator
            if is_admin and (has_higher or message.author.top_role == bot_top):
                ctx = await bot.get_context(message)
                await protect_cmd(ctx)
                return
            else:
                await message.channel.send("❌ ใช้ได้เฉพาะแอดมินที่ยศสูงกว่าบอทเท่านั้นครับ | ยศต่ำกว่าบอท เปิดผู้ดูแลก็ใช้ไม่ได้")
                return
        except Exception as e:
            await message.channel.send(f"❌ ใช้คำสั่งไม่ได้: {e}")
            return
    # ให้คำสั่งทำงานก่อนเสมอ - ไม่งั้น !protect ใช้ไม่ได้
    await bot.process_commands(message)
    if PAUSED: return
    if is_exempt(message.guild, message.author):
        return
    # 1. คำด่า พิมพ์ได้ ไม่ลบ
    # 2. ข้อความยาวเกินไป
    if len(message.content) > 1500:
        try: await message.delete()
        except: pass
        await message.channel.send(f"{message.author.mention} ⛔ ข้อความยาวเกินไป (ห้ามเกิน 1500 ตัวอักษร)", delete_after=5)
        await send_log(message.guild, f"⚠️ {message.author} ส่งข้อความยาว {len(message.content)} ตัวอักษร")
        return
    # 3. แท็กเยอะ
    if len(message.mentions) >= 4 or "@everyone" in message.content or "@here" in message.content:
        try: await message.delete()
        except: pass
        await send_log(message.guild, f"⚠️ {message.author} พยายามปิงเยอะ / @everyone")
        return
    # 4. ลิงก์
    if "http://" in message.content or "https://" in message.content or "discord.gg/" in message.content:
        try: await message.delete()
        except: pass
        await message.channel.send(f"{message.author.mention} ห้ามส่งลิงก์", delete_after=5)
        return
    # 5. อีโมจิเยอะ
    import re as _re
    emoji_count = len(_re.findall(r'<a?:\w+:\d+>', message.content)) + message.content.count("😂") + message.content.count("🔥")
    if emoji_count >= 10:
        try: await message.delete()
        except: pass
        await message.channel.send(f"{message.author.mention} ⛔ สแปมอีโมจิ", delete_after=5)
        return
    # 6. สแปมเร็ว + ข้อความซ้ำ
    now = time.time()
    spam_data[message.author.id].append(now)
    spam_data[message.author.id] = [x for x in spam_data[message.author.id] if now - x < 5]
    last_msgs[message.author.id].append((message.content, now))
    last_msgs[message.author.id] = [(c, x) for c, x in last_msgs[message.author.id] if now - x < 10]
    same = sum(1 for c, x in last_msgs[message.author.id] if c == message.content)
    is_spam = len(spam_data[message.author.id]) >= 5 or same >= 3
    if is_spam:
        try: await message.delete()
        except: pass
        try:
            await message.author.timeout(datetime.timedelta(minutes=10), reason="สแปม")
        except: pass
        await message.channel.send(f"{message.author.mention} ⛔ สแปม! หมดเวลา 10 นาที", delete_after=5)
        await send_log(message.guild, f"🔇 Mute {message.author} 10 นาที เหตุผล: สแปม / ข้อความซ้ำ")
        spam_data[message.author.id] = []
        last_msgs[message.author.id] = []
        return


@bot.event
async def on_guild_role_update(before, after):
    if PAUSED: return
    if before.permissions != after.permissions or before.name != after.name or before.color != after.color:
        async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_update):
            culprit = entry.user
            if culprit.id == bot.user.id or is_exempt(after.guild, culprit): return
            try:
                await after.edit(name=before.name, permissions=before.permissions, color=before.color, reason="แก้ยศมั่ว")
                await after.guild.ban(culprit, reason="แก้ยศมั่ว")
                await send_log(after.guild, f"🚨 แบน {culprit} เหตุผล: แก้ยศ {after.name} มั่ว")
            except: pass
            break

@bot.event
async def on_guild_channel_update(before, after):
    if PAUSED: return
    if before.name != after.name or before.overwrites != after.overwrites:
        async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_update):
            culprit = entry.user
            if culprit.id == bot.user.id or is_exempt(after.guild, culprit): return
            try:
                await after.edit(name=before.name, reason="แก้ห้องมั่ว")
                await after.guild.ban(culprit, reason="แก้ห้องมั่ว")
                await send_log(after.guild, f"🚨 แบน {culprit} เหตุผล: แก้ห้อง {after.name} มั่ว")
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
                for e in after:
                    if e not in before:
                        await guild.delete_emoji(e, reason="สร้างอีโมจิมั่ว")
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
    if invite.inviter and not is_exempt(invite.guild, invite.inviter):
        try:
            await invite.delete(reason="สร้างลิงก์เชิญมั่ว")
            await invite.guild.ban(invite.inviter, reason="สร้างลิงก์เชิญมั่ว")
            await send_log(invite.guild, f"🚨 แบน {invite.inviter} เหตุผล: สร้างลิงก์เชิญมั่ว")
        except: pass

@bot.event
async def on_guild_integrations_update(guild):
    if PAUSED: return
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.integration_create):
        culprit = entry.user
        if culprit.id == bot.user.id or is_exempt(guild, culprit): return
        try:
            await guild.ban(culprit, reason="สร้าง Integration มั่ว")
            await send_log(guild, f"🚨 แบน {culprit} เหตุผล: สร้าง Integration มั่ว")
        except: pass
        break

@bot.event
async def on_member_unban(guild, user):
    if PAUSED: return
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.unban):
        culprit = entry.user
        if culprit.id == bot.user.id or is_exempt(guild, culprit): return
        try:
            await guild.ban(culprit, reason="ปลดแบนมือ")
            await guild.ban(user, reason="โดนปลดแบนมั่ว แบนกลับ")
            await send_log(guild, f"🚨 แบน {culprit} เหตุผล: ปลดแบน {user} ด้วยมือ")
        except: pass
        break


@bot.command(name="protect")
async def protect_cmd(ctx):
    """ดูระบบป้องกันทั้งหมด - คำสั่งเดียวของตัวที่ 1"""
    # ใช้ได้เฉพาะแอดมิน + ยศสูงกว่าบอทเท่านั้น
    # ยศต่ำกว่าบอท ต่อให้เปิดผู้ดูแล (Administrator) ก็ใช้ไม่ได้
    # ตรวจสิทธิ์อีกครั้ง (กรณีเรียกจาก !protect แบบ command)
    is_owner2 = ctx.author.id == OWNER_ID or ctx.author.id == ctx.guild.owner_id
    if not is_owner2:
        bot_top2 = ctx.guild.me.top_role
        has_higher2 = any(r.position > bot_top2.position for r in ctx.author.roles)
        is_admin2 = ctx.author.guild_permissions.administrator
        if not ((is_admin2 and has_higher2) or (is_admin2 and ctx.author.top_role == bot_top2)):
            await ctx.send("❌ ใช้ได้เฉพาะแอดมินที่ยศสูงกว่าบอทเท่านั้นครับ | ยศต่ำกว่าบอท เปิดผู้ดูแลก็ใช้ไม่ได้")
            return
    embed = discord.Embed(title="🛡️ rreqzn1l - ระบบป้องกันทั้งหมด", color=0x1e1f22)
    embed.description = "ดูระบบป้องกันดิส พิมพ์ !protect | ใช้ได้เฉพาะแอดมินที่ยศสูงกว่าบอทเท่านั้น | ทั้งหมด 18 ระบบ"
    embed.add_field(name="🔒 กันเซิร์ฟ / กัน Raid", value="กันเซิร์ฟโดนดึง - โดนดึงไปเซิร์ฟอื่น บอทออกเอง\nกัน Raid - เข้า 10 คน/60 วิ = ล็อคเซิร์ฟ\nกันบอทแปลกปลอม - เข้ามาเตะทิ้ง\nกันเปลี่ยนชื่อ/รูปเซิร์ฟมั่ว - เปลี่ยนกลับ + แบน", inline=False)
    embed.add_field(name="👑 กันยศ / กันห้อง", value="กันสร้างยศมั่ว - ลบยศ + แบน / กันลบยศมั่ว - แบน\nกันใส่ยศมั่ว - ถอดยศ + แบน / กันแก้ยศมั่ว - แก้กลับ + แบน\nกันสร้างห้องมั่ว - ลบห้อง + แบน / กันลบห้องมั่ว - แบน + สร้างกลับ\nกันแก้ห้องมั่ว - แก้กลับ + แบน", inline=False)
    embed.add_field(name="🔨 กันเตะ / แบน / ปลดแบนมือ", value="กันเตะ/แบนด้วยมือ - แบนคนกด + ปลดคนที่โดนกลับ\nกันปลดแบนด้วยมือ - แบนคนกด + แบนคนที่โดนปลดกลับ", inline=False)
    embed.add_field(name="🧩 กันสร้างของมั่ว", value="กัน Webhook มั่ว - แบน / กันอีโมจิมั่ว - ลบ + แบน\nกันสติกเกอร์มั่ว - แบน / กันลิงก์เชิญมั่ว - ลบลิงก์ + แบน\nกัน Integration มั่ว - แบน", inline=False)
    embed.add_field(name="🚫 กันสแปมข้อความ", value="สแปม 5 ข้อความ/5 วิ = ลบ + Timeout 10 นาที\nข้อความซ้ำ 3 ครั้ง/10 วิ = ลบ + Timeout 10 นาที\nยาวเกิน 1,500 ตัว = ลบ / แท็ก 4 คน/@everyone = ลบ\nลิงก์ http/discord.gg = ลบ / อีโมจิเกิน 10 อัน = ลบ", inline=False)
    embed.add_field(name="💬 คำด่า", value="พิมพ์ได้ ไม่ลบ ไม่กรองคำหยาบ", inline=False)
    # ไม่มี footer - ลบติ๊กถูกข้างล่างออกแล้วตามรูป
    await ctx.send(embed=embed)

@bot.command(name="protection")
async def protection_alias(ctx):
    await protect_cmd(ctx)


# ระบบเปิด/ปิดบอท - ใช้ได้เฉพาะเจ้าของ + แอดมินยศสูงกว่าบอทเท่านั้น
async def _is_admin_owner(ctx):
    if ctx.author.id == OWNER_ID or ctx.author.id == ctx.guild.owner_id:
        return True
    bot_top = ctx.guild.me.top_role
    has_higher = any(r.position > bot_top.position for r in ctx.author.roles)
    return ctx.author.guild_permissions.administrator and (has_higher or ctx.author.top_role == bot_top)

@bot.command(name="on")
async def bot_on(ctx):
    if not await _is_admin_owner(ctx):
        await ctx.send("❌ ใช้ได้เฉพาะแอดมินที่ยศสูงกว่าบอทเท่านั้นครับ")
        return
    global PAUSED
    PAUSED = False
    await ctx.send("✅ เปิดบอทแล้ว เริ่มทำงานปกติ!")

@bot.command(name="off")
async def bot_off(ctx):
    if not await _is_admin_owner(ctx):
        await ctx.send("❌ ใช้ได้เฉพาะแอดมินที่ยศสูงกว่าบอทเท่านั้นครับ")
        return
    global PAUSED
    PAUSED = True
    await ctx.send("⏸️ ปิดบอทแล้ว ระบบป้องกันหยุดทำงานชั่วคราว (พิมพ์ !on เพื่อเปิด)")

@bot.command(name="pause")
async def bot_pause(ctx):
    await bot_off(ctx)

# ให้ !on/!off ทำงานผ่าน on_message manual ด้วย (กันกรณี command ไม่ทำงาน)

bot.run(TOKEN)