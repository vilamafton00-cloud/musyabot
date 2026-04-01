import discord
from discord.ext import commands
from datetime import datetime

import config
import database as db


class Welcome(commands.Cog):
    """👋 Приветствия и прощания"""

    def __init__(self, bot):
        self.bot = bot

    # ===== ПРИВЕТСТВИЕ ПРИ ВХОДЕ НА СЕРВЕР =====
    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.bot:
            return

        # === ЛС ПРИВЕТСТВИЕ ===
        try:
            embed = discord.Embed(
                title=f"👋 Добро пожаловать на {member.guild.name}!",
                description=(
                    f"Привет, **{member.display_name}**! Мы рады видеть тебя на нашем сервере!\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"📊 **Система уровней**\n"
                    f"На нашем сервере работает система уровней! "
                    f"Ты получаешь EXP за сообщения в чате и общение в голосовых каналах.\n\n"
                    f"💬 За сообщения: **{config.EXP_PER_MESSAGE_MIN}-{config.EXP_PER_MESSAGE_MAX}** EXP\n"
                    f"🎙️ За войс: **{config.EXP_PER_VOICE_MINUTE}** EXP/мин\n\n"
                    f"🏆 **Роли за уровни:**\n"
                ),
                color=config.COLOR_SUCCESS,
                timestamp=datetime.utcnow()
            )

            # Добавляем роли за уровни
            roles_text = ""
            for level, role_id in sorted(config.LEVEL_ROLES.items()):
                if role_id:
                    role = member.guild.get_role(role_id)
                    role_name = role.name if role else "Неизвестная роль"
                else:
                    role_name = "Не настроена"
                roles_text += f"⭐ **Уровень {level}** → {role_name}\n"

            embed.description += roles_text

            embed.description += (
                f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📝 **Полезные команды:**\n"
                f"`!rank` — посмотреть свой уровень\n"
                f"`!leaderboard` — таблица лидеров\n"
                f"`!help` — все команды бота\n\n"
                f"Приятного времяпровождения! 🎉"
            )

            if member.guild.icon:
                embed.set_thumbnail(url=member.guild.icon.url)

            embed.set_footer(
                text=f"Musya-Bot • {member.guild.name}",
                icon_url=self.bot.user.display_avatar.url
            )

            await member.send(embed=embed)

        except discord.Forbidden:
            # ЛС закрыты
            pass

        # === СООБЩЕНИЕ В КАНАЛ СЕРВЕРА (опционально) ===
        if config.WELCOME_CHANNEL:
            channel = member.guild.get_channel(config.WELCOME_CHANNEL)
            if channel:
                embed = discord.Embed(
                    title="👋 Новый участник!",
                    description=(
                        f"Добро пожаловать, {member.mention}!\n"
                        f"Ты **{member.guild.member_count}-й** участник сервера!\n\n"
                        f"Не забудь ознакомиться с правилами и приятного общения! 🎉"
                    ),
                    color=config.COLOR_SUCCESS,
                    timestamp=datetime.utcnow()
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.set_footer(
                    text=f"ID: {member.id}",
                    icon_url=self.bot.user.display_avatar.url
                )
                await channel.send(embed=embed)

    # ===== ПРОЩАНИЕ ПРИ ВЫХОДЕ С СЕРВЕРА =====
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if member.bot:
            return

        # === ЛС ПРОЩАНИЕ ===
        try:
            # Получаем данные пользователя из БД
            user = await db.get_user(member.id, member.guild.id)

            embed = discord.Embed(
                title=f"😢 Ты покинул {member.guild.name}",
                description=(
                    f"Нам жаль что ты уходишь, **{member.display_name}**...\n\n"
                ),
                color=config.COLOR_ERROR,
                timestamp=datetime.utcnow()
            )

            # Показываем статистику если была
            if user and user['exp'] > 0:
                from cogs.levels import Levels
                levels_cog = self.bot.get_cog('Levels')
                level = levels_cog.calculate_level(user['exp']) if levels_cog else user['level']

                embed.description += (
                    f"📊 **Твоя статистика:**\n"
                    f"⭐ Уровень: **{level}**\n"
                    f"✨ EXP: **{user['exp']:,}**\n"
                    f"💬 Сообщений: **{user['total_messages']:,}**\n"
                    f"🎙️ В войсе: **{user['total_voice_minutes']:,}** мин\n\n"
                )

            embed.description += (
                f"Мы всегда будем рады видеть тебя снова! 💙\n"
                f"Твои данные сохранены — если вернёшься, продолжишь с того же места."
            )

            if member.guild.icon:
                embed.set_thumbnail(url=member.guild.icon.url)

            embed.set_footer(
                text=f"Musya-Bot • {member.guild.name}",
                icon_url=self.bot.user.display_avatar.url
            )

            await member.send(embed=embed)

        except discord.Forbidden:
            pass

        # === СООБЩЕНИЕ В КАНАЛ СЕРВЕРА (опционально) ===
        if config.GOODBYE_CHANNEL:
            channel = member.guild.get_channel(config.GOODBYE_CHANNEL)
            if channel:
                user = await db.get_user(member.id, member.guild.id)

                embed = discord.Embed(
                    title="😢 Участник ушёл",
                    description=(
                        f"**{member.display_name}** покинул сервер.\n"
                        f"Нас теперь **{member.guild.member_count}** участников."
                    ),
                    color=config.COLOR_ERROR,
                    timestamp=datetime.utcnow()
                )
                embed.set_thumbnail(url=member.display_avatar.url)

                if user and user['exp'] > 0:
                    from cogs.levels import Levels
                    levels_cog = self.bot.get_cog('Levels')
                    level = levels_cog.calculate_level(user['exp']) if levels_cog else user['level']
                    embed.add_field(
                        name="📊 Был на сервере",
                        value=f"Уровень: **{level}** | EXP: **{user['exp']:,}** | "
                              f"Сообщений: **{user['total_messages']:,}**",
                        inline=False
                    )

                # Роли которые были
                roles = [r.name for r in member.roles if r != member.guild.default_role]
                if roles:
                    embed.add_field(
                        name="🏷️ Роли",
                        value=", ".join(roles[:10]),
                        inline=False
                    )

                embed.set_footer(
                    text=f"ID: {member.id}",
                    icon_url=self.bot.user.display_avatar.url
                )
                await channel.send(embed=embed)

    # ===== НАСТРОЙКА КАНАЛОВ =====
    @commands.command(name="setwelcome")
    @commands.has_permissions(administrator=True)
    async def setwelcome(self, ctx, channel: discord.TextChannel = None):
        """[Админ] Установить канал приветствий
        Использование: !setwelcome #канал"""
        if not channel:
            channel = ctx.channel

        config.WELCOME_CHANNEL = channel.id

        embed = discord.Embed(
            title="✅ Канал приветствий установлен",
            description=f"Приветствия будут отправляться в {channel.mention}",
            color=config.COLOR_SUCCESS
        )
        await ctx.send(embed=embed)

    @commands.command(name="setgoodbye")
    @commands.has_permissions(administrator=True)
    async def setgoodbye(self, ctx, channel: discord.TextChannel = None):
        """[Админ] Установить канал прощаний
        Использование: !setgoodbye #канал"""
        if not channel:
            channel = ctx.channel

        config.GOODBYE_CHANNEL = channel.id

        embed = discord.Embed(
            title="✅ Канал прощаний установлен",
            description=f"Прощания будут отправляться в {channel.mention}",
            color=config.COLOR_SUCCESS
        )
        await ctx.send(embed=embed)

    # ===== ТЕСТ ПРИВЕТСТВИЯ =====
    @commands.command(name="testwelcome")
    @commands.has_permissions(administrator=True)
    async def testwelcome(self, ctx):
        """[Админ] Тестировать приветствие на себе"""
        await self.on_member_join(ctx.author)
        embed = discord.Embed(
            title="✅ Тест отправлен",
            description="Проверь свои ЛС!",
            color=config.COLOR_SUCCESS
        )
        await ctx.send(embed=embed)

    @commands.command(name="testgoodbye")
    @commands.has_permissions(administrator=True)
    async def testgoodbye(self, ctx):
        """[Админ] Тестировать прощание на себе"""
        await self.on_member_remove(ctx.author)
        embed = discord.Embed(
            title="✅ Тест отправлен",
            description="Проверь свои ЛС!",
            color=config.COLOR_SUCCESS
        )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Welcome(bot))
