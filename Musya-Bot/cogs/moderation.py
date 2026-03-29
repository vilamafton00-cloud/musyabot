import discord
from discord.ext import commands
import time
from datetime import datetime, timedelta

import database as db
import config


class Moderation(commands.Cog):
    """🛡️ Модуль модерации — команды для модераторов и администраторов"""

    def __init__(self, bot):
        self.bot = bot

    def _mod_embed(self, title: str, description: str = None,
                   color: int = config.COLOR_MODERATION) -> discord.Embed:
        """Создать embed для модерации"""
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text="Musya-Bot • Модерация", icon_url=self.bot.user.display_avatar.url)
        return embed

    async def _send_mod_log(self, guild: discord.Guild, embed: discord.Embed):
        """Отправить лог в канал модерации"""
        if config.MOD_LOG_CHANNEL:
            channel = guild.get_channel(config.MOD_LOG_CHANNEL)
            if channel:
                await channel.send(embed=embed)

    # ===== KICK =====
    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member = None, *, reason: str = "Причина не указана"):
        """Кикнуть участника с сервера
        Использование: !kick @участник [причина]"""
        if not member:
            embed = self._mod_embed("❌ Ошибка", "Укажите участника: `!kick @участник [причина]`",
                                    config.COLOR_ERROR)
            return await ctx.send(embed=embed)

        if member.top_role >= ctx.author.top_role:
            embed = self._mod_embed("❌ Ошибка",
                                    "Вы не можете кикнуть участника с такой же или высшей ролью.",
                                    config.COLOR_ERROR)
            return await ctx.send(embed=embed)

        if member.top_role >= ctx.guild.me.top_role:
            embed = self._mod_embed("❌ Ошибка",
                                    "Я не могу кикнуть участника с ролью выше моей.",
                                    config.COLOR_ERROR)
            return await ctx.send(embed=embed)

        # Отправляем ЛС кикнутому
        try:
            dm_embed = self._mod_embed(
                "🚪 Вы были кикнуты",
                f"**Сервер:** {ctx.guild.name}\n"
                f"**Модератор:** {ctx.author}\n"
                f"**Причина:** {reason}"
            )
            await member.send(embed=dm_embed)
        except discord.Forbidden:
            pass

        await member.kick(reason=f"{ctx.author}: {reason}")

        # Логируем
        await db.log_mod_action("kick", member.id, ctx.author.id, ctx.guild.id, reason)

        embed = self._mod_embed(
            "🚪 Участник кикнут",
            f"**Участник:** {member} ({member.id})\n"
            f"**Модератор:** {ctx.author.mention}\n"
            f"**Причина:** {reason}"
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)
        await self._send_mod_log(ctx.guild, embed)

    # ===== BAN =====
    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member = None, *, reason: str = "Причина не указана"):
        """Забанить участника
        Использование: !ban @участник [причина]"""
        if not member:
            embed = self._mod_embed("❌ Ошибка", "Укажите участника: `!ban @участник [причина]`",
                                    config.COLOR_ERROR)
            return await ctx.send(embed=embed)

        if member.top_role >= ctx.author.top_role:
            embed = self._mod_embed("❌ Ошибка",
                                    "Вы не можете забанить участника с такой же или высшей ролью.",
                                    config.COLOR_ERROR)
            return await ctx.send(embed=embed)

        if member.top_role >= ctx.guild.me.top_role:
            embed = self._mod_embed("❌ Ошибка",
                                    "Я не могу забанить участника с ролью выше моей.",
                                    config.COLOR_ERROR)
            return await ctx.send(embed=embed)

        try:
            dm_embed = self._mod_embed(
                "🔨 Вы были забанены",
                f"**Сервер:** {ctx.guild.name}\n"
                f"**Модератор:** {ctx.author}\n"
                f"**Причина:** {reason}"
            )
            await member.send(embed=dm_embed)
        except discord.Forbidden:
            pass

        await member.ban(reason=f"{ctx.author}: {reason}", delete_message_days=0)

        await db.log_mod_action("ban", member.id, ctx.author.id, ctx.guild.id, reason)

        embed = self._mod_embed(
            "🔨 Участник забанен",
            f"**Участник:** {member} ({member.id})\n"
            f"**Модератор:** {ctx.author.mention}\n"
            f"**Причина:** {reason}"
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)
        await self._send_mod_log(ctx.guild, embed)

    # ===== UNBAN =====
    @commands.command(name="unban")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user_id: int = None, *, reason: str = "Причина не указана"):
        """Разбанить участника по ID
        Использование: !unban <ID> [причина]"""
        if not user_id:
            embed = self._mod_embed("❌ Ошибка", "Укажите ID: `!unban <ID> [причина]`",
                                    config.COLOR_ERROR)
            return await ctx.send(embed=embed)

        try:
            user = await self.bot.fetch_user(user_id)
            await ctx.guild.unban(user, reason=f"{ctx.author}: {reason}")
        except discord.NotFound:
            embed = self._mod_embed("❌ Ошибка", "Пользователь не найден в банлисте.",
                                    config.COLOR_ERROR)
            return await ctx.send(embed=embed)

        await db.log_mod_action("unban", user_id, ctx.author.id, ctx.guild.id, reason)

        embed = self._mod_embed(
            "🔓 Участник разбанен",
            f"**Участник:** {user} ({user.id})\n"
            f"**Модератор:** {ctx.author.mention}\n"
            f"**Причина:** {reason}"
        )
        await ctx.send(embed=embed)
        await self._send_mod_log(ctx.guild, embed)

    # ===== MUTE (TIMEOUT) =====
    @commands.command(name="mute")
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx, member: discord.Member = None,
                   duration: str = None, *, reason: str = "Причина не указана"):
        """Замутить участника (timeout)
        Использование: !mute @участник <время> [причина]
        Время: 10s, 5m, 1h, 1d (секунды, минуты, часы, дни)"""
        if not member or not duration:
            embed = self._mod_embed(
                "❌ Ошибка",
                "Использование: `!mute @участник <время> [причина]`\n"
                "Примеры времени: `10s`, `5m`, `1h`, `1d`",
                config.COLOR_ERROR
            )
            return await ctx.send(embed=embed)

        if member.top_role >= ctx.author.top_role:
            embed = self._mod_embed("❌ Ошибка",
                                    "Вы не можете замутить участника с такой же или высшей ролью.",
                                    config.COLOR_ERROR)
            return await ctx.send(embed=embed)

        # Парсинг времени
        time_units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
        unit = duration[-1].lower()
        if unit not in time_units:
            embed = self._mod_embed("❌ Ошибка",
                                    "Неверный формат времени. Используйте: `s`, `m`, `h`, `d`",
                                    config.COLOR_ERROR)
            return await ctx.send(embed=embed)

        try:
            amount = int(duration[:-1])
        except ValueError:
            embed = self._mod_embed("❌ Ошибка", "Неверное число в формате времени.",
                                    config.COLOR_ERROR)
            return await ctx.send(embed=embed)

        seconds = amount * time_units[unit]
        if seconds > 2419200:  # Discord лимит — 28 дней
            embed = self._mod_embed("❌ Ошибка", "Максимальное время мута — 28 дней.",
                                    config.COLOR_ERROR)
            return await ctx.send(embed=embed)

        delta = timedelta(seconds=seconds)
        await member.timeout(delta, reason=f"{ctx.author}: {reason}")

        await db.log_mod_action("mute", member.id, ctx.author.id, ctx.guild.id,
                                f"{duration} | {reason}")

        time_str = f"{amount}{'сек' if unit == 's' else 'мин' if unit == 'm' else 'ч' if unit == 'h' else 'дн'}"

        embed = self._mod_embed(
            "🔇 Участник замучен",
            f"**Участник:** {member.mention} ({member.id})\n"
            f"**Модератор:** {ctx.author.mention}\n"
            f"**Длительность:** {time_str}\n"
            f"**Причина:** {reason}"
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)
        await self._send_mod_log(ctx.guild, embed)

    # ===== UNMUTE =====
    @commands.command(name="unmute")
    @commands.has_permissions(moderate_members=True)
    async def unmute(self, ctx, member: discord.Member = None):
        """Размутить участника
        Использование: !unmute @участник"""
        if not member:
            embed = self._mod_embed("❌ Ошибка", "Укажите участника: `!unmute @участник`",
                                    config.COLOR_ERROR)
            return await ctx.send(embed=embed)

        await member.timeout(None)

        await db.log_mod_action("unmute", member.id, ctx.author.id, ctx.guild.id)

        embed = self._mod_embed(
            "🔊 Участник размучен",
            f"**Участник:** {member.mention}\n"
            f"**Модератор:** {ctx.author.mention}"
        )
        await ctx.send(embed=embed)
        await self._send_mod_log(ctx.guild, embed)

    # ===== CLEAR / PURGE =====
    @commands.command(name="clear", aliases=["purge"])
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, amount: int = None):
        """Удалить сообщения из канала
        Использование: !clear <количество>"""
        if not amount:
            embed = self._mod_embed("❌ Ошибка",
                                    "Укажите количество: `!clear <количество>`\nМаксимум: 500",
                                    config.COLOR_ERROR)
            return await ctx.send(embed=embed)

        if amount > 500:
            amount = 500

        deleted = await ctx.channel.purge(limit=amount + 1)  # +1 для самой команды

        await db.log_mod_action("clear", ctx.author.id, ctx.author.id, ctx.guild.id,
                                f"{len(deleted) - 1} сообщений в #{ctx.channel.name}")

        embed = self._mod_embed(
            "🧹 Сообщения удалены",
            f"Удалено **{len(deleted) - 1}** сообщений в {ctx.channel.mention}\n"
            f"**Модератор:** {ctx.author.mention}",
            config.COLOR_SUCCESS
        )
        msg = await ctx.send(embed=embed)
        await msg.delete(delay=5)

    # ===== WARN =====
    @commands.command(name="warn")
    @commands.has_permissions(moderate_members=True)
    async def warn(self, ctx, member: discord.Member = None, *, reason: str = "Причина не указана"):
        """Выдать предупреждение участнику
        Использование: !warn @участник [причина]"""
        if not member:
            embed = self._mod_embed("❌ Ошибка", "Укажите участника: `!warn @участник [причина]`",
                                    config.COLOR_ERROR)
            return await ctx.send(embed=embed)

        await db.add_warning(member.id, ctx.guild.id, ctx.author.id, reason)
        await db.log_mod_action("warn", member.id, ctx.author.id, ctx.guild.id, reason)

        warnings = await db.get_warnings(member.id, ctx.guild.id)
        warn_count = len(warnings)

        embed = self._mod_embed(
            "⚠️ Предупреждение выдано",
            f"**Участник:** {member.mention} ({member.id})\n"
            f"**Модератор:** {ctx.author.mention}\n"
            f"**Причина:** {reason}\n"
            f"**Всего предупреждений:** {warn_count}",
            config.COLOR_WARNING
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)

        # Уведомляем пользователя в ЛС
        try:
            dm_embed = self._mod_embed(
                "⚠️ Вы получили предупреждение",
                f"**Сервер:** {ctx.guild.name}\n"
                f"**Модератор:** {ctx.author}\n"
                f"**Причина:** {reason}\n"
                f"**Всего предупреждений:** {warn_count}",
                config.COLOR_WARNING
            )
            await member.send(embed=dm_embed)
        except discord.Forbidden:
            pass

        await self._send_mod_log(ctx.guild, embed)

    # ===== WARNINGS =====
    @commands.command(name="warnings", aliases=["warns"])
    @commands.has_permissions(moderate_members=True)
    async def warnings(self, ctx, member: discord.Member = None):
        """Посмотреть предупреждения участника
        Использование: !warnings @участник"""
        if not member:
            embed = self._mod_embed("❌ Ошибка",
                                    "Укажите участника: `!warnings @участник`",
                                    config.COLOR_ERROR)
            return await ctx.send(embed=embed)

        warns = await db.get_warnings(member.id, ctx.guild.id)

        if not warns:
            embed = self._mod_embed(
                f"📋 Предупреждения — {member.display_name}",
                "У этого участника нет предупреждений.",
                config.COLOR_SUCCESS
            )
            return await ctx.send(embed=embed)

        embed = self._mod_embed(
            f"📋 Предупреждения — {member.display_name}",
            f"Всего предупреждений: **{len(warns)}**"
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        for i, warn in enumerate(warns[:15], 1):  # Максимум 15
            mod = ctx.guild.get_member(warn['moderator_id'])
            mod_name = mod.display_name if mod else f"ID: {warn['moderator_id']}"
            dt = datetime.fromtimestamp(warn['timestamp']).strftime("%d.%m.%Y %H:%M")
            embed.add_field(
                name=f"#{warn['id']} | {dt}",
                value=f"**Причина:** {warn['reason']}\n**Модератор:** {mod_name}",
                inline=False
            )

        await ctx.send(embed=embed)

    # ===== REMOVEWARN =====
    @commands.command(name="removewarn", aliases=["delwarn"])
    @commands.has_permissions(moderate_members=True)
    async def removewarn(self, ctx, warn_id: int = None):
        """Удалить предупреждение по ID
        Использование: !removewarn <ID>"""
        if not warn_id:
            embed = self._mod_embed("❌ Ошибка",
                                    "Укажите ID предупреждения: `!removewarn <ID>`",
                                    config.COLOR_ERROR)
            return await ctx.send(embed=embed)

        success = await db.remove_warning(warn_id, ctx.guild.id)
        if success:
            embed = self._mod_embed(
                "✅ Предупреждение удалено",
                f"Предупреждение **#{warn_id}** успешно удалено.",
                config.COLOR_SUCCESS
            )
        else:
            embed = self._mod_embed("❌ Ошибка",
                                    f"Предупреждение #{warn_id} не найдено.",
                                    config.COLOR_ERROR)
        await ctx.send(embed=embed)

    # ===== CLEARWARNS =====
    @commands.command(name="clearwarns")
    @commands.has_permissions(administrator=True)
    async def clearwarns(self, ctx, member: discord.Member = None):
        """Очистить все предупреждения участника (только админ)
        Использование: !clearwarns @участник"""
        if not member:
            embed = self._mod_embed("❌ Ошибка",
                                    "Укажите участника: `!clearwarns @участник`",
                                    config.COLOR_ERROR)
            return await ctx.send(embed=embed)

        await db.clear_warnings(member.id, ctx.guild.id)

        embed = self._mod_embed(
            "✅ Предупреждения очищены",
            f"Все предупреждения **{member.display_name}** были удалены.",
            config.COLOR_SUCCESS
        )
        await ctx.send(embed=embed)

    # ===== SLOWMODE =====
    @commands.command(name="slowmode")
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, seconds: int = None):
        """Установить слоумод в канале
        Использование: !slowmode <секунды> (0 = выключить)"""
        if seconds is None:
            embed = self._mod_embed("❌ Ошибка",
                                    "Укажите секунды: `!slowmode <секунды>`\n`!slowmode 0` — выключить",
                                    config.COLOR_ERROR)
            return await ctx.send(embed=embed)

        if seconds > 21600:
            seconds = 21600

        await ctx.channel.edit(slowmode_delay=seconds)

        if seconds == 0:
            embed = self._mod_embed("⏱️ Слоумод отключён",
                                    f"Слоумод в {ctx.channel.mention} отключён.",
                                    config.COLOR_SUCCESS)
        else:
            embed = self._mod_embed("⏱️ Слоумод установлен",
                                    f"Слоумод в {ctx.channel.mention}: **{seconds}** сек.",
                                    config.COLOR_SUCCESS)
        await ctx.send(embed=embed)

    # ===== LOCK / UNLOCK =====
    @commands.command(name="lock")
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx, channel: discord.TextChannel = None):
        """Заблокировать канал (запретить отправку сообщений)
        Использование: !lock [#канал]"""
        channel = channel or ctx.channel
        await channel.set_permissions(ctx.guild.default_role, send_messages=False)

        embed = self._mod_embed(
            "🔒 Канал заблокирован",
            f"{channel.mention} заблокирован.\n**Модератор:** {ctx.author.mention}"
        )
        await ctx.send(embed=embed)
        await db.log_mod_action("lock", 0, ctx.author.id, ctx.guild.id, f"#{channel.name}")
        await self._send_mod_log(ctx.guild, embed)

    @commands.command(name="unlock")
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx, channel: discord.TextChannel = None):
        """Разблокировать канал
        Использование: !unlock [#канал]"""
        channel = channel or ctx.channel
        await channel.set_permissions(ctx.guild.default_role, send_messages=True)

        embed = self._mod_embed(
            "🔓 Канал разблокирован",
            f"{channel.mention} разблокирован.\n**Модератор:** {ctx.author.mention}",
            config.COLOR_SUCCESS
        )
        await ctx.send(embed=embed)
        await db.log_mod_action("unlock", 0, ctx.author.id, ctx.guild.id, f"#{channel.name}")
        await self._send_mod_log(ctx.guild, embed)

    # ===== MODLOG =====
    @commands.command(name="modlog")
    @commands.has_permissions(moderate_members=True)
    async def modlog(self, ctx, amount: int = 10):
        """Посмотреть последние модерационные действия
        Использование: !modlog [количество]"""
        actions = await db.get_mod_actions(ctx.guild.id, min(amount, 25))

        if not actions:
            embed = self._mod_embed("📜 Журнал модерации", "Действий пока нет.")
            return await ctx.send(embed=embed)

        embed = self._mod_embed("📜 Журнал модерации",
                                f"Последние {len(actions)} действий:")

        action_icons = {
            'kick': '🚪', 'ban': '🔨', 'unban': '🔓',
            'mute': '🔇', 'unmute': '🔊', 'warn': '⚠️',
            'clear': '🧹', 'lock': '🔒', 'unlock': '🔓'
        }

        for action in actions:
            icon = action_icons.get(action['action_type'], '📋')
            user = self.bot.get_user(action['user_id'])
            user_str = str(user) if user else f"ID: {action['user_id']}"
            mod = self.bot.get_user(action['moderator_id'])
            mod_str = str(mod) if mod else f"ID: {action['moderator_id']}"
            dt = datetime.fromtimestamp(action['timestamp']).strftime("%d.%m %H:%M")

            reason_str = f" | {action['reason']}" if action['reason'] else ""
            embed.add_field(
                name=f"{icon} {action['action_type'].upper()} — {dt}",
                value=f"**Цель:** {user_str}\n**Мод:** {mod_str}{reason_str}",
                inline=False
            )

        await ctx.send(embed=embed)

    # ===== ОБРАБОТКА ОШИБОК =====
    @kick.error
    @ban.error
    @mute.error
    @unmute.error
    @clear.error
    @warn.error
    @warnings.error
    @slowmode.error
    @lock.error
    @unlock.error
    @unban.error
    @clearwarns.error
    @removewarn.error
    @modlog.error
    async def mod_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            embed = self._mod_embed("🚫 Нет прав",
                                    "У вас недостаточно прав для этой команды.",
                                    config.COLOR_ERROR)
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MemberNotFound):
            embed = self._mod_embed("❌ Ошибка",
                                    "Участник не найден.",
                                    config.COLOR_ERROR)
            await ctx.send(embed=embed)
        elif isinstance(error, commands.BadArgument):
            embed = self._mod_embed("❌ Ошибка",
                                    "Неверный аргумент команды.",
                                    config.COLOR_ERROR)
            await ctx.send(embed=embed)
        else:
            raise error


async def setup(bot):
    await bot.add_cog(Moderation(bot))