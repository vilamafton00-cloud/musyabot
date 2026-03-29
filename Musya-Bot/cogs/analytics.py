import discord
from discord.ext import commands
from datetime import datetime, timedelta
import io
import math

import database as db
import config

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


class Analytics(commands.Cog):
    """📈 Продвинутая аналитика сервера"""

    def __init__(self, bot):
        self.bot = bot

    def _analytics_embed(self, title: str, description: str = None) -> discord.Embed:
        embed = discord.Embed(
            title=title,
            description=description,
            color=config.COLOR_ANALYTICS,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text="Musya-Bot • Аналитика", icon_url=self.bot.user.display_avatar.url)
        return embed

    # ===== ОТСЛЕЖИВАНИЕ JOIN/LEAVE =====
    @commands.Cog.listener()
    async def on_member_join(self, member):
        await db.increment_daily_join(member.guild.id)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        await db.increment_daily_leave(member.guild.id)

    # ===== КОМАНДА !serverstats =====
    @commands.command(name="serverstats", aliases=["sstats", "serverinfo"])
    async def serverstats(self, ctx):
        """Подробная информация о сервере"""
        guild = ctx.guild

        # Подсчёт участников
        total = guild.member_count
        bots = sum(1 for m in guild.members if m.bot)
        humans = total - bots
        online = sum(1 for m in guild.members
                     if m.status != discord.Status.offline and not m.bot)

        # Каналы
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)

        # В войсе сейчас
        in_voice = sum(len(vc.members) for vc in guild.voice_channels)

        # Роли
        roles_count = len(guild.roles) - 1  # -1 для @everyone

        # Дата создания
        created = guild.created_at.strftime("%d.%m.%Y")
        days_ago = (datetime.utcnow() - guild.created_at.replace(tzinfo=None)).days

        # Boost
        boost_level = guild.premium_tier
        boost_count = guild.premium_subscription_count

        embed = self._analytics_embed(f"📊 Статистика — {guild.name}")
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.add_field(
            name="👥 Участники",
            value=f"```\nВсего:     {total}\n"
                  f"Люди:      {humans}\n"
                  f"Боты:      {bots}\n"
                  f"Онлайн:    {online}\n```",
            inline=True
        )
        embed.add_field(
            name="📁 Каналы",
            value=f"```\nТекстовые: {text_channels}\n"
                  f"Голосовые: {voice_channels}\n"
                  f"Категории: {categories}\n"
                  f"В войсе:   {in_voice}\n```",
            inline=True
        )
        embed.add_field(
            name="ℹ️ Информация",
            value=f"```\nСоздан:    {created}\n"
                  f"Дней:      {days_ago}\n"
                  f"Ролей:     {roles_count}\n"
                  f"Буст:      Ур.{boost_level} ({boost_count})\n```",
            inline=True
        )

        # Статистика за сегодня
        stats = await db.get_server_stats(guild.id, 1)
        if stats:
            today = stats[-1]
            embed.add_field(
                name="📈 Сегодня",
                value=f"💬 Сообщений: **{today.get('messages_count', 0)}**\n"
                      f"📥 Пришло: **{today.get('members_joined', 0)}**\n"
                      f"📤 Ушло: **{today.get('members_left', 0)}**",
                inline=False
            )

        # Владелец
        embed.add_field(
            name="👑 Владелец",
            value=guild.owner.mention if guild.owner else "Неизвестен",
            inline=True
        )

        await ctx.send(embed=embed)

    # ===== КОМАНДА !activity =====
    @commands.command(name="activity", aliases=["graph"])
    @commands.has_permissions(manage_guild=True)
    async def activity(self, ctx, days: int = 7):
        """Показать график активности сервера за N дней
        Использование: !activity [дни]"""
        if not HAS_MATPLOTLIB:
            embed = self._analytics_embed("❌ Ошибка",
                                          "Модуль `matplotlib` не установлен.")
            return await ctx.send(embed=embed)

        days = min(days, 90)
        stats = await db.get_server_stats(ctx.guild.id, days)

        if not stats:
            embed = self._analytics_embed("📈 Активность",
                                          "Недостаточно данных для графика.")
            return await ctx.send(embed=embed)

        dates = [datetime.strptime(s['date'], "%Y-%m-%d") for s in stats]
        messages = [s['messages_count'] for s in stats]
        joins = [s['members_joined'] for s in stats]
        leaves = [s['members_left'] for s in stats]

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8),
                                        facecolor='#2C2F33')

        # График сообщений
        ax1.set_facecolor('#23272A')
        ax1.plot(dates, messages, color='#5865F2', linewidth=2, marker='o',
                 markersize=5, label='Сообщения')
        ax1.fill_between(dates, messages, alpha=0.3, color='#5865F2')
        ax1.set_title('💬 Сообщения', color='white', fontsize=14, fontweight='bold')
        ax1.tick_params(colors='white')
        ax1.spines['bottom'].set_color('#40444B')
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        ax1.spines['left'].set_color('#40444B')
        ax1.grid(True, alpha=0.2, color='#40444B')
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))

        # График участников
        ax2.set_facecolor('#23272A')
        ax2.bar([d - timedelta(hours=4) for d in dates], joins,
                width=0.35, color='#57F287', label='Пришли', alpha=0.8)
        ax2.bar([d + timedelta(hours=4) for d in dates], leaves,
                width=0.35, color='#ED4245', label='Ушли', alpha=0.8)
        ax2.set_title('👥 Участники', color='white', fontsize=14, fontweight='bold')
        ax2.tick_params(colors='white')
        ax2.spines['bottom'].set_color('#40444B')
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)
        ax2.spines['left'].set_color('#40444B')
        ax2.grid(True, alpha=0.2, color='#40444B')
        ax2.legend(facecolor='#2C2F33', edgecolor='#40444B',
                   labelcolor='white', fontsize=10)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))

        plt.tight_layout(pad=2)

        # Сохраняем в буфер
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                    facecolor='#2C2F33')
        buf.seek(0)
        plt.close(fig)

        file = discord.File(buf, filename="activity.png")
        embed = self._analytics_embed(
            f"📈 Активность сервера за {days} дней",
            f"Всего сообщений: **{sum(messages):,}**\n"
            f"Пришло участников: **{sum(joins):,}**\n"
            f"Ушло участников: **{sum(leaves):,}**"
        )
        embed.set_image(url="attachment://activity.png")
        await ctx.send(file=file, embed=embed)

    # ===== КОМАНДА !topchannels =====
    @commands.command(name="topchannels", aliases=["tchannels"])
    @commands.has_permissions(manage_guild=True)
    async def topchannels(self, ctx, days: int = 7):
        """Топ каналов по активности за N дней
        Использование: !topchannels [дни]"""
        days = min(days, 90)
        channels = await db.get_top_channels(ctx.guild.id, days, 15)

        if not channels:
            embed = self._analytics_embed("📊 Топ каналов",
                                          "Недостаточно данных.")
            return await ctx.send(embed=embed)

        embed = self._analytics_embed(
            f"📊 Топ каналов за {days} дней",
            "Самые активные каналы по количеству сообщений:"
        )

        total = sum(c['total'] for c in channels)

        for i, ch_data in enumerate(channels, 1):
            channel = ctx.guild.get_channel(ch_data['channel_id'])
            name = f"#{channel.name}" if channel else f"ID: {ch_data['channel_id']}"
            pct = (ch_data['total'] / total * 100) if total > 0 else 0

            bar_len = 15
            filled = int(bar_len * pct / 100)
            bar = "█" * filled + "░" * (bar_len - filled)

            medals = {1: "🥇", 2: "🥈", 3: "🥉"}
            medal = medals.get(i, f"**{i}.**")

            embed.add_field(
                name=f"{medal} {name}",
                value=f"`{bar}` {ch_data['total']:,} ({pct:.1f}%)",
                inline=False
            )

        await ctx.send(embed=embed)

    # ===== КОМАНДА !modstats =====
    @commands.command(name="modstats")
    @commands.has_permissions(moderate_members=True)
    async def modstats(self, ctx, days: int = 30):
        """Статистика модерации за N дней
        Использование: !modstats [дни]"""
        stats = await db.get_mod_stats(ctx.guild.id, days)

        embed = self._analytics_embed(
            f"🛡️ Статистика модерации за {days} дней"
        )

        if not stats:
            embed.description = "За этот период модерационных действий не было."
            return await ctx.send(embed=embed)

        action_names = {
            'kick': '🚪 Киков',
            'ban': '🔨 Банов',
            'unban': '🔓 Разбанов',
            'mute': '🔇 Мутов',
            'unmute': '🔊 Размутов',
            'warn': '⚠️ Варнов',
            'clear': '🧹 Очисток',
            'lock': '🔒 Блокировок',
            'unlock': '🔓 Разблокировок'
        }

        total = sum(stats.values())
        description_lines = []

        for action, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
            name = action_names.get(action, action)
            pct = (count / total * 100) if total > 0 else 0
            description_lines.append(f"{name}: **{count}** ({pct:.1f}%)")

        embed.description = "\n".join(description_lines)
        embed.add_field(name="📊 Всего действий", value=f"**{total}**", inline=False)

        await ctx.send(embed=embed)

    # ===== КОМАНДА !userstats =====
    @commands.command(name="userstats")
    async def userstats(self, ctx, member: discord.Member = None):
        """Подробная статистика участника
        Использование: !userstats [@участник]"""
        member = member or ctx.author

        embed = self._analytics_embed(f"📊 Статистика — {member.display_name}")
        embed.set_thumbnail(url=member.display_avatar.url)

        # Общая информация
        joined = member.joined_at.strftime("%d.%m.%Y %H:%M") if member.joined_at else "N/A"
        created = member.created_at.strftime("%d.%m.%Y %H:%M")
        days_on_server = (datetime.utcnow() - member.joined_at.replace(tzinfo=None)).days if member.joined_at else 0

        embed.add_field(
            name="📅 Даты",
            value=f"**Создан:** {created}\n"
                  f"**Присоединился:** {joined}\n"
                  f"**Дней на сервере:** {days_on_server}",
            inline=False
        )

        # Роли
        roles = [r.mention for r in reversed(member.roles) if r != ctx.guild.default_role]
        roles_str = ", ".join(roles[:15]) if roles else "Нет ролей"
        embed.add_field(
            name=f"🏷️ Роли ({len(roles)})",
            value=roles_str,
            inline=False
        )

        # Данные из БД
        user = await db.get_user(member.id, ctx.guild.id)
        if user:
            from cogs.levels import Levels
            levels_cog = self.bot.get_cog('Levels')
            if levels_cog:
                level = levels_cog.calculate_level(user['exp'])
            else:
                level = user['level']

            embed.add_field(name="📊 Уровень", value=f"```{level}```", inline=True)
            embed.add_field(name="✨ EXP", value=f"```{user['exp']:,}```", inline=True)
            embed.add_field(name="💬 Сообщений",
                            value=f"```{user['total_messages']:,}```", inline=True)
            embed.add_field(name="🎙️ В войсе",
                            value=f"```{user['total_voice_minutes']:,} мин```", inline=True)

            # Среднее кол-во сообщений в день
            if days_on_server > 0:
                avg_msgs = user['total_messages'] / days_on_server
                embed.add_field(name="📈 Сообщ./день",
                                value=f"```{avg_msgs:.1f}```", inline=True)

        # Предупреждения
        warns = await db.get_warnings(member.id, ctx.guild.id)
        embed.add_field(name="⚠️ Предупреждений",
                        value=f"```{len(warns)}```", inline=True)

        # Высшая роль
        embed.add_field(name="👑 Высшая роль",
                        value=member.top_role.mention if member.top_role != ctx.guild.default_role else "Нет",
                        inline=False)

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Analytics(bot))