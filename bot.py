import discord
from discord.ext import commands
import asyncio
from datetime import datetime

import config
import database as db

# ============================
# MUSYA-BOT
# Discord бот для сервера A-Studio
# ============================


class MusyaBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()

        super().__init__(
            command_prefix=config.PREFIX,
            intents=intents,
            help_command=None,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="за A-Studio | !help"
            ),
            status=discord.Status.online
        )

    async def setup_hook(self):
        """Загрузка модулей при запуске"""
        await db.init_db()
        print("✅ База данных инициализирована")

        cogs = [
            'cogs.moderation',
            'cogs.levels',
            'cogs.analytics',
            'cogs.reaction_roles',
            'cogs.utility',
            'cogs.welcome'
        ]

        for cog in cogs:
            try:
                await self.load_extension(cog)
                print(f"✅ Загружен модуль: {cog}")
            except Exception as e:
                print(f"❌ Ошибка загрузки {cog}: {e}")

    async def on_ready(self):
        print("=" * 50)
        print(f"  MUSYA-BOT запущен!")
        print(f"  Имя: {self.user}")
        print(f"  ID: {self.user.id}")
        print(f"  Серверов: {len(self.guilds)}")
        print(f"  Участников: {sum(g.member_count for g in self.guilds)}")
        print(f"  Префикс: {config.PREFIX}")
        print("=" * 50)


bot = MusyaBot()


# ===== КАСТОМНАЯ КОМАНДА HELP =====
@bot.command(name="help", aliases=["h", "commands"])
async def help_command(ctx, category: str = None):
    """Показать список команд"""

    if category is None:
        embed = discord.Embed(
            title="📖 Musya-Bot — Справка",
            description=(
                f"Бот для сервера **A-Studio**\n"
                f"Префикс: `{config.PREFIX}`\n\n"
                f"Выберите категорию для подробной информации:"
            ),
            color=config.COLOR_PRIMARY,
            timestamp=datetime.utcnow()
        )
        embed.set_thumbnail(url=bot.user.display_avatar.url)

        embed.add_field(
            name="🛡️ Модерация",
            value=f"`{config.PREFIX}help mod`\n"
                  "kick, ban, mute, warn, clear...",
            inline=True
        )
        embed.add_field(
            name="📊 Уровни",
            value=f"`{config.PREFIX}help levels`\n"
                  "rank, leaderboard, rewards...",
            inline=True
        )
        embed.add_field(
            name="📈 Аналитика",
            value=f"`{config.PREFIX}help analytics`\n"
                  "serverstats, activity, topchannels...",
            inline=True
        )
        embed.add_field(
            name="🎭 Reaction Roles",
            value=f"`{config.PREFIX}help rr`\n"
                  "rrcreate, rradd, rrremove...",
            inline=True
        )
        embed.add_field(
            name="🔧 Утилиты",
            value=f"`{config.PREFIX}help utility`\n"
                  "avatar, userinfo, ping, poll...",
            inline=True
        )
        embed.add_field(
            name="👋 Приветствия",
            value=f"`{config.PREFIX}help welcome`\n"
                  "setwelcome, setgoodbye, тесты...",
            inline=True
        )

        embed.set_footer(text="Musya-Bot • A-Studio",
                         icon_url=bot.user.display_avatar.url)
        return await ctx.send(embed=embed, delete_after=120)

    category = category.lower()

    if category in ["mod", "moderation", "модерация"]:
        embed = discord.Embed(
            title="🛡️ Команды модерации",
            color=config.COLOR_MODERATION,
            timestamp=datetime.utcnow()
        )
        commands_list = [
            ("`!kick @участник [причина]`", "Кикнуть участника"),
            ("`!ban @участник [причина]`", "Забанить участника"),
            ("`!unban <ID> [причина]`", "Разбанить по ID"),
            ("`!mute @участник <время> [причина]`", "Замутить (timeout)"),
            ("`!unmute @участник`", "Размутить участника"),
            ("`!clear <кол-во>`", "Удалить сообщения (макс. 500)"),
            ("`!warn @участник [причина]`", "Выдать предупреждение"),
            ("`!warnings @участник`", "Посмотреть предупреждения"),
            ("`!removewarn <ID>`", "Удалить предупреждение"),
            ("`!clearwarns @участник`", "Очистить все предупреждения"),
            ("`!slowmode <секунды>`", "Установить слоумод"),
            ("`!lock [#канал]`", "Заблокировать канал"),
            ("`!unlock [#канал]`", "Разблокировать канал"),
            ("`!modlog [кол-во]`", "Журнал модерации"),
        ]
        for cmd, desc in commands_list:
            embed.add_field(name=cmd, value=desc, inline=False)

    elif category in ["levels", "level", "уровни", "lvl"]:
        embed = discord.Embed(
            title="📊 Команды системы уровней",
            color=config.COLOR_LEVEL,
            timestamp=datetime.utcnow()
        )
        commands_list = [
            ("`!rank [@участник]`", "Посмотреть уровень и EXP"),
            ("`!leaderboard [страница]`", "Таблица лидеров"),
            ("`!rewards`", "Посмотреть роли за уровни"),
            ("`!setlevel @участник <уровень>`", "⚙️ Установить уровень (Админ)"),
            ("`!setexp @участник <exp>`", "⚙️ Установить EXP (Админ)"),
            ("`!addexp @участник <exp>`", "⚙️ Добавить EXP (Админ)"),
            ("`!synclevels`", "⚙️ Пересчитать роли всем (Админ)"),
        ]
        for cmd, desc in commands_list:
            embed.add_field(name=cmd, value=desc, inline=False)

        embed.add_field(
            name="ℹ️ Как получить EXP",
            value=f"💬 Сообщения: **{config.EXP_PER_MESSAGE_MIN}-{config.EXP_PER_MESSAGE_MAX}** EXP "
                  f"(кулдаун: {config.MESSAGE_EXP_COOLDOWN} сек)\n"
                  f"🎙️ Голосовой канал: **{config.EXP_PER_VOICE_MINUTE}** EXP/мин",
            inline=False
        )

    elif category in ["analytics", "аналитика", "stats"]:
        embed = discord.Embed(
            title="📈 Команды аналитики",
            color=config.COLOR_ANALYTICS,
            timestamp=datetime.utcnow()
        )
        commands_list = [
            ("`!serverstats`", "Подробная информация о сервере"),
            ("`!activity [дни]`", "График активности сервера"),
            ("`!topchannels [дни]`", "Топ каналов по активности"),
            ("`!modstats [дни]`", "Статистика модерации"),
            ("`!userstats [@участник]`", "Подробная статистика участника"),
        ]
        for cmd, desc in commands_list:
            embed.add_field(name=cmd, value=desc, inline=False)

    elif category in ["rr", "reactionroles", "reaction", "реакции"]:
        embed = discord.Embed(
            title="🎭 Reaction Roles",
            color=config.COLOR_PRIMARY,
            timestamp=datetime.utcnow()
        )
        commands_list = [
            ("`!rrcreate #канал <текст>`", "Создать сообщение для авто-ролей"),
            ("`!rradd <ID_сообщения> <эмодзи> @роль`", "Добавить роль к сообщению"),
            ("`!rrremove <ID_сообщения> <эмодзи>`", "Удалить роль с сообщения"),
            ("`!rrlist <ID_сообщения>`", "Список ролей на сообщении"),
        ]
        for cmd, desc in commands_list:
            embed.add_field(name=cmd, value=desc, inline=False)

        embed.add_field(
            name="📝 Пример использования",
            value=(
                "1️⃣ `!rrcreate #авто-роли Выберите роли!`\n"
                "2️⃣ `!rradd 123456789 🎮 @Геймер`\n"
                "3️⃣ `!rradd 123456789 🎨 @Художник`\n"
                "Теперь участники могут нажать на реакцию и получить роль!"
            ),
            inline=False
        )

    elif category in ["utility", "утилиты", "utils", "util"]:
        embed = discord.Embed(
            title="🔧 Утилиты",
            color=config.COLOR_PRIMARY,
            timestamp=datetime.utcnow()
        )
        commands_list = [
            ("`!avatar [@участник]`", "Аватар участника"),
            ("`!serveravatar [@участник]`", "Серверный аватар"),
            ("`!banner [@участник]`", "Баннер участника"),
            ("`!userinfo [@участник]`", "Информация об участнике"),
            ("`!roleinfo @роль`", "Информация о роли"),
            ("`!servericon`", "Иконка сервера"),
            ("`!serverbanner`", "Баннер сервера"),
            ("`!emojis`", "Список кастомных эмодзи"),
            ("`!ping`", "Проверить задержку бота"),
            ("`!suggest <идея>`", "Предложить идею"),
            ("`!poll <вопрос>`", "Создать голосование"),
        ]
        for cmd, desc in commands_list:
            embed.add_field(name=cmd, value=desc, inline=False)

    elif category in ["welcome", "приветствия", "привет"]:
        embed = discord.Embed(
            title="👋 Приветствия и прощания",
            color=config.COLOR_SUCCESS,
            timestamp=datetime.utcnow()
        )
        commands_list = [
            ("`!setwelcome #канал`", "Установить канал приветствий"),
            ("`!setgoodbye #канал`", "Установить канал прощаний"),
            ("`!testwelcome`", "Тестировать приветствие (в ЛС)"),
            ("`!testgoodbye`", "Тестировать прощание (в ЛС)"),
        ]
        for cmd, desc in commands_list:
            embed.add_field(name=cmd, value=desc, inline=False)
        embed.add_field(
            name="ℹ️ Информация",
            value="Бот автоматически отправляет приветствие в ЛС новым участникам "
                  "и прощание тем кто уходит. Также можно настроить каналы на сервере.",
            inline=False
        )

    else:
        embed = discord.Embed(
            title="❌ Категория не найдена",
            description=f"Доступные категории: `mod`, `levels`, `analytics`, `rr`, `utility`, `welcome`",
            color=config.COLOR_ERROR
        )

    embed.set_footer(text="Musya-Bot • A-Studio", icon_url=bot.user.display_avatar.url)
    await ctx.send(embed=embed, delete_after=120)


# ===== ОБРАБОТКА ГЛОБАЛЬНЫХ ОШИБОК =====
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(
            title="🚫 Нет прав",
            description="У вас недостаточно прав для этой команды.",
            color=config.COLOR_ERROR
        )
        await ctx.send(embed=embed, delete_after=10)
        return

    if isinstance(error, commands.BotMissingPermissions):
        embed = discord.Embed(
            title="🚫 Нет прав у бота",
            description=f"Мне не хватает прав: `{', '.join(error.missing_permissions)}`",
            color=config.COLOR_ERROR
        )
        await ctx.send(embed=embed, delete_after=10)
        return

    if isinstance(error, commands.CommandOnCooldown):
        embed = discord.Embed(
            title="⏳ Кулдаун",
            description=f"Подождите **{error.retry_after:.1f}** секунд.",
            color=config.COLOR_WARNING
        )
        await ctx.send(embed=embed, delete_after=5)
        return

    print(f"Ошибка в команде {ctx.command}: {error}")


# ===== ЗАПУСК =====
if __name__ == "__main__":
    if config.BOT_TOKEN == "YOUR_TOKEN_HERE":
        print("=" * 50)
        print("  ❌ ОШИБКА: Токен не установлен!")
        print("  Создайте файл .env и добавьте:")
        print("  DISCORD_TOKEN=ваш_токен_бота")
        print("=" * 50)
    else:
        bot.run(config.BOT_TOKEN)
