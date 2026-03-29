import discord
from discord.ext import commands, tasks
import time
import random
import math
from datetime import datetime

import database as db
import config


class Levels(commands.Cog):
    """📊 Система уровней — EXP за сообщения и голосовые каналы"""

    def __init__(self, bot):
        self.bot = bot
        self.voice_exp_loop.start()

    def cog_unload(self):
        self.voice_exp_loop.cancel()

    def _level_embed(self, title: str, description: str = None,
                     color: int = config.COLOR_LEVEL) -> discord.Embed:
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text="Musya-Bot • Уровни", icon_url=self.bot.user.display_avatar.url)
        return embed

    @staticmethod
    def calculate_level(exp: int) -> int:
        """Вычислить уровень по количеству EXP"""
        level = 0
        while True:
            required = config.BASE_EXP * ((level + 1) ** config.EXP_EXPONENT)
            if exp < required:
                return level
            level += 1

    @staticmethod
    def exp_for_level(level: int) -> int:
        """Сколько EXP нужно для определённого уровня"""
        if level <= 0:
            return 0
        return int(config.BASE_EXP * (level ** config.EXP_EXPONENT))

    @staticmethod
    def exp_for_next_level(level: int) -> int:
        """Сколько EXP нужно для следующего уровня"""
        return int(config.BASE_EXP * ((level + 1) ** config.EXP_EXPONENT))

    async def check_level_up(self, member: discord.Member, guild: discord.Guild,
                             user_data: dict, channel=None):
        """Проверить повышение уровня и выдать роли"""
        current_level = user_data['level']
        new_level = self.calculate_level(user_data['exp'])

        if new_level > current_level:
            await db.set_level(member.id, guild.id, new_level)

            # Отправляем сообщение о повышении
            embed = self._level_embed(
                "🎉 Уровень повышен!",
                f"{member.mention} достиг **{new_level} уровня**!",
                config.COLOR_SUCCESS
            )
            embed.set_thumbnail(url=member.display_avatar.url)

            # Проверяем роли за уровень
            for req_level, role_id in config.LEVEL_ROLES.items():
                if new_level >= req_level and role_id:
                    role = guild.get_role(role_id)
                    if role and role not in member.roles:
                        try:
                            await member.add_roles(role)
                            embed.add_field(
                                name="🏆 Новая роль!",
                                value=f"Получена роль: {role.mention}",
                                inline=False
                            )
                        except discord.Forbidden:
                            pass

            # Отправляем в канал уровней или текущий канал
            target_channel = None
            if config.LEVEL_UP_CHANNEL:
                target_channel = guild.get_channel(config.LEVEL_UP_CHANNEL)
            if not target_channel and channel:
                target_channel = channel

            if target_channel:
                await target_channel.send(embed=embed)

    # ===== ВЫДАЧА EXP ЗА СООБЩЕНИЯ =====
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        user = await db.get_user(message.author.id, message.guild.id)

        # Проверяем кулдаун
        if user:
            time_diff = time.time() - user['last_exp_time']
            if time_diff < config.MESSAGE_EXP_COOLDOWN:
                # Просто считаем сообщение без EXP
                await db.increment_messages(message.author.id, message.guild.id)
                await db.increment_daily_messages(message.guild.id, message.channel.id)
                return

        # Даём EXP
        exp = random.randint(config.EXP_PER_MESSAGE_MIN, config.EXP_PER_MESSAGE_MAX)
        user_data = await db.add_exp(message.author.id, message.guild.id, exp)
        await db.increment_messages(message.author.id, message.guild.id)
        await db.increment_daily_messages(message.guild.id, message.channel.id)

        # Проверяем повышение уровня
        await self.check_level_up(message.author, message.guild, user_data, message.channel)

    # ===== ОТСЛЕЖИВАНИЕ ВОЙСА =====
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return

        # Зашёл в войс
        if before.channel is None and after.channel is not None:
            await db.set_voice_join(member.id, member.guild.id)

        # Вышел из войса
        elif before.channel is not None and after.channel is None:
            user = await db.get_user(member.id, member.guild.id)
            if user and user['joined_voice_at'] > 0:
                minutes = int((time.time() - user['joined_voice_at']) / 60)
                if minutes > 0:
                    exp = minutes * config.EXP_PER_VOICE_MINUTE
                    await db.add_voice_minutes(member.id, member.guild.id, minutes)
                    user_data = await db.add_exp(member.id, member.guild.id, exp)
                    await self.check_level_up(member, member.guild, user_data)
            await db.clear_voice_join(member.id, member.guild.id)

        # Переключился между каналами — ничего не делаем
        elif before.channel is not None and after.channel is not None:
            pass

    # ===== ПЕРИОДИЧЕСКАЯ ВЫДАЧА EXP ЗА ВОЙС =====
    @tasks.loop(minutes=5)
    async def voice_exp_loop(self):
        """Каждые 5 минут проверяем сидящих в войсе и даём EXP"""
        for guild in self.bot.guilds:
            for vc in guild.voice_channels:
                # Считаем не-ботов, не замученных
                members = [m for m in vc.members if not m.bot and not m.voice.self_deaf]
                if len(members) < 1:  # Нужен хотя бы 1 человек (можно поменять на 2)
                    continue

                for member in members:
                    exp = config.EXP_PER_VOICE_MINUTE * 5  # 5 минут
                    user_data = await db.add_exp(member.id, guild.id, exp)
                    await db.add_voice_minutes(member.id, guild.id, 5)
                    await self.check_level_up(member, guild, user_data)

    @voice_exp_loop.before_loop
    async def before_voice_exp_loop(self):
        await self.bot.wait_until_ready()

    # ===== КОМАНДА !rank =====
    @commands.command(name="rank", aliases=["level", "lvl"])
    async def rank(self, ctx, member: discord.Member = None):
        """Посмотреть свой уровень или уровень другого участника
        Использование: !rank [@участник]"""
        member = member or ctx.author

        user = await db.get_user(member.id, ctx.guild.id)
        if not user:
            await db.create_user(member.id, ctx.guild.id)
            user = await db.get_user(member.id, ctx.guild.id)

        level = self.calculate_level(user['exp'])
        current_level_exp = self.exp_for_level(level)
        next_level_exp = self.exp_for_next_level(level)
        exp_progress = user['exp'] - current_level_exp
        exp_needed = next_level_exp - current_level_exp

        # Прогресс бар
        progress_pct = exp_progress / exp_needed if exp_needed > 0 else 1
        bar_length = 20
        filled = int(bar_length * progress_pct)
        bar = "█" * filled + "░" * (bar_length - filled)

        # Позиция в рейтинге
        leaderboard = await db.get_leaderboard(ctx.guild.id, 999)
        position = next(
            (i + 1 for i, u in enumerate(leaderboard) if u['user_id'] == member.id),
            len(leaderboard) + 1
        )

        embed = self._level_embed(f"📊 Профиль — {member.display_name}")
        embed.set_thumbnail(url=member.display_avatar.url)

        embed.add_field(
            name="Уровень",
            value=f"```{level}```",
            inline=True
        )
        embed.add_field(
            name="EXP",
            value=f"```{user['exp']:,}```",
            inline=True
        )
        embed.add_field(
            name="Позиция",
            value=f"```#{position}```",
            inline=True
        )
        embed.add_field(
            name=f"Прогресс до {level + 1} уровня",
            value=f"`{bar}` {int(progress_pct * 100)}%\n"
                  f"`{exp_progress:,}` / `{exp_needed:,}` EXP",
            inline=False
        )
        embed.add_field(
            name="📝 Сообщений",
            value=f"```{user['total_messages']:,}```",
            inline=True
        )
        embed.add_field(
            name="🎙️ В войсе (мин)",
            value=f"```{user['total_voice_minutes']:,}```",
            inline=True
        )

        # Следующая награда
        next_reward = None
        for req_level in sorted(config.LEVEL_ROLES.keys()):
            if level < req_level:
                next_reward = req_level
                break

        if next_reward:
            role_id = config.LEVEL_ROLES.get(next_reward)
            role_mention = f"<@&{role_id}>" if role_id else "Роль не настроена"
            embed.add_field(
                name="🎯 Следующая награда",
                value=f"Уровень **{next_reward}** — {role_mention}",
                inline=False
            )

                await ctx.reply(embed=embed, mention_author=False, delete_after=60)

    # ===== КОМАНДА !leaderboard =====
    @commands.command(name="leaderboard", aliases=["top", "lb"])
    async def leaderboard(self, ctx, page: int = 1):
        """Таблица лидеров сервера
        Использование: !leaderboard [страница]"""
        per_page = 10
        offset = (page - 1) * per_page

        all_users = await db.get_leaderboard(ctx.guild.id, 999)
        total_pages = max(1, math.ceil(len(all_users) / per_page))

        if page > total_pages:
            page = total_pages

        users = all_users[offset:offset + per_page]

        if not users:
            embed = self._level_embed("🏆 Таблица лидеров", "Пока никого нет.")
            return await ctx.send(embed=embed)

        embed = self._level_embed(
            f"🏆 Таблица лидеров — {ctx.guild.name}",
            f"Страница {page}/{total_pages}"
        )
        embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)

        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        description_lines = []

        for i, user_data in enumerate(users, start=offset + 1):
            member = ctx.guild.get_member(user_data['user_id'])
            name = member.display_name if member else f"Неизвестный ({user_data['user_id']})"
            level = self.calculate_level(user_data['exp'])
            medal = medals.get(i, f"**{i}.**")

            description_lines.append(
                f"{medal} **{name}** — Уровень {level} | `{user_data['exp']:,}` EXP"
            )

        embed.description = "\n".join(description_lines)

        # Позиция вызвавшего
        my_pos = next(
            (i + 1 for i, u in enumerate(all_users) if u['user_id'] == ctx.author.id),
            None
        )
        if my_pos:
            embed.set_footer(
                text=f"Ваша позиция: #{my_pos} • Musya-Bot",
                icon_url=ctx.author.display_avatar.url
            )

        await ctx.send(embed=embed)

    # ===== ADMIN: SET LEVEL =====
    @commands.command(name="setlevel")
    @commands.has_permissions(administrator=True)
    async def setlevel(self, ctx, member: discord.Member = None, level: int = None):
        """[Админ] Установить уровень участнику
        Использование: !setlevel @участник <уровень>"""
        if not member or level is None:
            embed = self._level_embed("❌ Ошибка",
                                      "Использование: `!setlevel @участник <уровень>`",
                                      config.COLOR_ERROR)
            return await ctx.send(embed=embed)

        exp = self.exp_for_level(level)
        await db.create_user(member.id, ctx.guild.id)
        await db.set_exp(member.id, ctx.guild.id, exp)
        await db.set_level(member.id, ctx.guild.id, level)

        embed = self._level_embed(
            "✅ Уровень установлен",
            f"**{member.display_name}** теперь имеет уровень **{level}** ({exp:,} EXP)",
            config.COLOR_SUCCESS
        )
        await ctx.send(embed=embed)

    # ===== ADMIN: SET EXP =====
    @commands.command(name="setexp")
    @commands.has_permissions(administrator=True)
    async def setexp(self, ctx, member: discord.Member = None, exp: int = None):
        """[Админ] Установить EXP участнику
        Использование: !setexp @участник <exp>"""
        if not member or exp is None:
            embed = self._level_embed("❌ Ошибка",
                                      "Использование: `!setexp @участник <exp>`",
                                      config.COLOR_ERROR)
            return await ctx.send(embed=embed)

        await db.set_exp(member.id, ctx.guild.id, exp)
        new_level = self.calculate_level(exp)
        await db.set_level(member.id, ctx.guild.id, new_level)

        embed = self._level_embed(
            "✅ EXP установлен",
            f"**{member.display_name}**: {exp:,} EXP (уровень {new_level})",
            config.COLOR_SUCCESS
        )
        await ctx.send(embed=embed)

    # ===== ADMIN: ADD EXP =====
    @commands.command(name="addexp")
    @commands.has_permissions(administrator=True)
    async def addexp(self, ctx, member: discord.Member = None, exp: int = None):
        """[Админ] Добавить EXP участнику
        Использование: !addexp @участник <exp>"""
        if not member or exp is None:
            embed = self._level_embed("❌ Ошибка",
                                      "Использование: `!addexp @участник <exp>`",
                                      config.COLOR_ERROR)
            return await ctx.send(embed=embed)

        user_data = await db.add_exp(member.id, ctx.guild.id, exp)
        await self.check_level_up(member, ctx.guild, user_data, ctx.channel)

        embed = self._level_embed(
            "✅ EXP добавлен",
            f"**{member.display_name}** получил **{exp:,}** EXP\n"
            f"Всего: **{user_data['exp'] + exp:,}** EXP",
            config.COLOR_SUCCESS
        )
        await ctx.send(embed=embed)

    # ===== REWARDS =====
    @commands.command(name="rewards", aliases=["levelroles"])
    async def rewards(self, ctx):
        """Посмотреть роли за уровни"""
        embed = self._level_embed(
            "🎁 Награды за уровни",
            "Роли, которые можно получить за достижение определённого уровня:"
        )

        for level, role_id in sorted(config.LEVEL_ROLES.items()):
            if role_id:
                role = ctx.guild.get_role(role_id)
                role_name = role.mention if role else "Роль не найдена"
            else:
                role_name = "⚙️ *Не настроена*"
            embed.add_field(
                name=f"Уровень {level}",
                value=role_name,
                inline=True
            )

        await ctx.send(embed=embed)


    @commands.command(name="synclevels")
    @commands.has_permissions(administrator=True)
    async def synclevels(self, ctx):
        """[Админ] Пересчитать и выдать роли за уровни всем участникам"""
        embed = self._level_embed("⏳ Синхронизация...", "Пересчитываю роли за уровни...")
        msg = await ctx.send(embed=embed)

        count = 0
        leaderboard = await db.get_leaderboard(ctx.guild.id, 9999)

        for user_data in leaderboard:
            member = ctx.guild.get_member(user_data['user_id'])
            if not member:
                continue

            level = self.calculate_level(user_data['exp'])
            await db.set_level(member.id, ctx.guild.id, level)

            for req_level, role_id in config.LEVEL_ROLES.items():
                if level >= req_level and role_id:
                    role = ctx.guild.get_role(role_id)
                    if role and role not in member.roles:
                        try:
                            await member.add_roles(role)
                            count += 1
                        except discord.Forbidden:
                            pass

        embed = self._level_embed(
            "✅ Синхронизация завершена",
            f"Выдано **{count}** ролей участникам.",
            config.COLOR_SUCCESS
        )
        await msg.edit(embed=embed)


    async def check_level_up(self, member: discord.Member, guild: discord.Guild,
                             user_data: dict, channel=None):
        """Проверить повышение уровня и выдать роли"""
        current_level = user_data['level']
        new_level = self.calculate_level(user_data['exp'])

        if new_level > current_level:
            await db.set_level(member.id, guild.id, new_level)

            embed = self._level_embed(
                "🎉 Уровень повышен!",
                f"{member.mention} достиг **{new_level} уровня**!",
                config.COLOR_SUCCESS
            )
            embed.set_thumbnail(url=member.display_avatar.url)

            # Проверяем роли за уровень
            for req_level, role_id in config.LEVEL_ROLES.items():
                if new_level >= req_level and role_id:
                    role = guild.get_role(role_id)
                    if role is None:
                        print(f"❌ Роль с ID {role_id} не найдена на сервере!")
                        continue
                    if role in member.roles:
                        print(f"ℹ️ У {member} уже есть роль {role.name}")
                        continue
                    try:
                        await member.add_roles(role)
                        embed.add_field(
                            name="🏆 Новая роль!",
                            value=f"Получена роль: {role.mention}",
                            inline=False
                        )
                        print(f"✅ Выдана роль {role.name} для {member}")
                    except discord.Forbidden:
                        print(f"❌ НЕТ ПРАВ выдать роль {role.name} для {member}")
                    except Exception as e:
                        print(f"❌ Ошибка выдачи роли: {e}")

            # Отправляем сообщение
            target_channel = None
            if config.LEVEL_UP_CHANNEL:
                target_channel = guild.get_channel(config.LEVEL_UP_CHANNEL)
            if not target_channel and channel:
                target_channel = channel

            if target_channel:
                await target_channel.send(embed=embed)
            
            print(f"🎉 {member} повысился до {new_level} уровня! EXP: {user_data['exp']}")


    @commands.command(name="synclevels")
    @commands.has_permissions(administrator=True)
    async def synclevels(self, ctx):
        """[Админ] Пересчитать и выдать роли за уровни всем участникам"""
        embed = self._level_embed("⏳ Синхронизация...", "Пересчитываю роли за уровни...")
        msg = await ctx.send(embed=embed)

        count = 0
        leaderboard = await db.get_leaderboard(ctx.guild.id, 9999)

        for user_data in leaderboard:
            member = ctx.guild.get_member(user_data['user_id'])
            if not member:
                continue

            level = self.calculate_level(user_data['exp'])
            await db.set_level(member.id, ctx.guild.id, level)

            for req_level, role_id in config.LEVEL_ROLES.items():
                if level >= req_level and role_id:
                    role = ctx.guild.get_role(role_id)
                    if role and role not in member.roles:
                        try:
                            await member.add_roles(role)
                            count += 1
                        except discord.Forbidden:
                            pass

        embed = self._level_embed(
            "✅ Синхронизация завершена",
            f"Выдано **{count}** ролей участникам.",
            config.COLOR_SUCCESS
        )
        await msg.edit(embed=embed)
async def setup(bot):
    await bot.add_cog(Levels(bot))
