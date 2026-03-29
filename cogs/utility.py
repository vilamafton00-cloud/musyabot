import discord
from discord.ext import commands
from datetime import datetime

import config


class Utility(commands.Cog):
    """🔧 Полезные команды"""

    def __init__(self, bot):
        self.bot = bot

    def _util_embed(self, title: str, description: str = None,
                    color: int = config.COLOR_PRIMARY) -> discord.Embed:
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text="Musya-Bot • A-Studio", icon_url=self.bot.user.display_avatar.url)
        return embed

    # ===== AVATAR =====
    @commands.command(name="avatar", aliases=["av", "pfp"])
    async def avatar(self, ctx, member: discord.Member = None):
        """Показать аватарку участника
        Использование: !avatar [@участник]"""
        member = member or ctx.author

        embed = self._util_embed(f"🖼️ Аватар — {member.display_name}")
        embed.set_image(url=member.display_avatar.url)

        # Ссылки на разные форматы
        avatar_url = member.display_avatar
        links = []
        for fmt in ['png', 'jpg', 'webp']:
            links.append(f"[{fmt.upper()}]({avatar_url.replace(format=fmt, size=1024)})")
        if avatar_url.is_animated():
            links.append(f"[GIF]({avatar_url.replace(format='gif', size=1024)})")

        embed.add_field(name="🔗 Скачать", value=" | ".join(links), inline=False)

        await ctx.send(embed=embed)

    # ===== SERVER AVATAR =====
    @commands.command(name="serveravatar", aliases=["sav"])
    async def serveravatar(self, ctx, member: discord.Member = None):
        """Показать серверный аватар участника
        Использование: !serveravatar [@участник]"""
        member = member or ctx.author

        if member.guild_avatar:
            embed = self._util_embed(f"🖼️ Серверный аватар — {member.display_name}")
            embed.set_image(url=member.guild_avatar.url)
        else:
            embed = self._util_embed(
                "ℹ️ Информация",
                f"У **{member.display_name}** нет серверного аватара.",
                config.COLOR_WARNING
            )

        await ctx.send(embed=embed)

    # ===== BANNER =====
    @commands.command(name="banner")
    async def banner(self, ctx, member: discord.Member = None):
        """Показать баннер участника
        Использование: !banner [@участник]"""
        member = member or ctx.author

        # Нужно получить полный user объект для баннера
        user = await self.bot.fetch_user(member.id)

        if user.banner:
            embed = self._util_embed(f"🎨 Баннер — {member.display_name}")
            embed.set_image(url=user.banner.url)
        else:
            embed = self._util_embed(
                "ℹ️ Информация",
                f"У **{member.display_name}** нет баннера.",
                config.COLOR_WARNING
            )

        await ctx.send(embed=embed)

    # ===== USERINFO =====
    @commands.command(name="userinfo", aliases=["ui", "whois"])
    async def userinfo(self, ctx, member: discord.Member = None):
        """Информация об участнике
        Использование: !userinfo [@участник]"""
        member = member or ctx.author

        embed = self._util_embed(f"👤 Информация — {member}")
        embed.set_thumbnail(url=member.display_avatar.url)

        # Статус
        status_icons = {
            discord.Status.online: "🟢 Онлайн",
            discord.Status.idle: "🌙 Отошёл",
            discord.Status.dnd: "🔴 Не беспокоить",
            discord.Status.offline: "⚫ Оффлайн"
        }

        embed.add_field(name="📛 Имя", value=str(member), inline=True)
        embed.add_field(name="🆔 ID", value=f"`{member.id}`", inline=True)
        embed.add_field(name="📊 Статус",
                        value=status_icons.get(member.status, "Неизвестно"),
                        inline=True)

        embed.add_field(name="📅 Создан",
                        value=f"<t:{int(member.created_at.timestamp())}:R>",
                        inline=True)
        embed.add_field(name="📥 Присоединился",
                        value=f"<t:{int(member.joined_at.timestamp())}:R>" if member.joined_at else "N/A",
                        inline=True)

        # Бустит ли сервер
        if member.premium_since:
            embed.add_field(name="💎 Бустит с",
                            value=f"<t:{int(member.premium_since.timestamp())}:R>",
                            inline=True)

        # Роли
        roles = [r.mention for r in reversed(member.roles) if r != ctx.guild.default_role]
        if roles:
            embed.add_field(name=f"🏷️ Роли ({len(roles)})",
                            value=" ".join(roles[:20]),
                            inline=False)

        # Права
        key_perms = []
        if member.guild_permissions.administrator:
            key_perms.append("👑 Администратор")
        if member.guild_permissions.manage_guild:
            key_perms.append("⚙️ Управление сервером")
        if member.guild_permissions.manage_channels:
            key_perms.append("📁 Управление каналами")
        if member.guild_permissions.manage_roles:
            key_perms.append("🏷️ Управление ролями")
        if member.guild_permissions.ban_members:
            key_perms.append("🔨 Банить участников")
        if member.guild_permissions.kick_members:
            key_perms.append("🚪 Кикать участников")
        if member.guild_permissions.manage_messages:
            key_perms.append("💬 Управление сообщениями")

        if key_perms:
            embed.add_field(name="🔑 Ключевые права",
                            value="\n".join(key_perms),
                            inline=False)

        await ctx.send(embed=embed)

    # ===== ROLEINFO =====
    @commands.command(name="roleinfo", aliases=["ri"])
    async def roleinfo(self, ctx, role: discord.Role = None):
        """Информация о роли
        Использование: !roleinfo @роль"""
        if not role:
            embed = self._util_embed("❌ Ошибка",
                                     "Укажите роль: `!roleinfo @роль`",
                                     config.COLOR_ERROR)
            return await ctx.send(embed=embed)

        embed = self._util_embed(f"🏷️ Роль — {role.name}")
        embed.color = role.color if role.color.value else config.COLOR_PRIMARY

        embed.add_field(name="🆔 ID", value=f"`{role.id}`", inline=True)
        embed.add_field(name="🎨 Цвет", value=f"`{role.color}`", inline=True)
        embed.add_field(name="👥 Участников", value=f"`{len(role.members)}`", inline=True)
        embed.add_field(name="📍 Позиция", value=f"`{role.position}`", inline=True)
        embed.add_field(name="📡 Упоминаемая",
                        value="✅" if role.mentionable else "❌", inline=True)
        embed.add_field(name="🔝 Отдельно",
                        value="✅" if role.hoist else "❌", inline=True)
        embed.add_field(name="📅 Создана",
                        value=f"<t:{int(role.created_at.timestamp())}:R>", inline=True)

        if role.icon:
            embed.set_thumbnail(url=role.icon.url)

        await ctx.send(embed=embed)

    # ===== EMOJI LIST =====
    @commands.command(name="emojis", aliases=["emojilist"])
    async def emojis(self, ctx):
        """Список кастомных эмодзи сервера"""
        emojis = ctx.guild.emojis
        if not emojis:
            embed = self._util_embed("😀 Эмодзи", "На сервере нет кастомных эмодзи.")
            return await ctx.send(embed=embed)

        static = [str(e) for e in emojis if not e.animated]
        animated = [str(e) for e in emojis if e.animated]

        embed = self._util_embed(
            f"😀 Эмодзи сервера — {len(emojis)} шт.",
        )

        if static:
            # Разбиваем на части по 1024 символов
            text = " ".join(static)
            if len(text) > 1024:
                text = text[:1020] + "..."
            embed.add_field(name=f"Статичные ({len(static)})", value=text, inline=False)

        if animated:
            text = " ".join(animated)
            if len(text) > 1024:
                text = text[:1020] + "..."
            embed.add_field(name=f"Анимированные ({len(animated)})", value=text, inline=False)

        await ctx.send(embed=embed)

    # ===== PING =====
    @commands.command(name="ping")
    async def ping(self, ctx):
        """Проверить задержку бота"""
        latency = round(self.bot.latency * 1000)

        if latency < 100:
            status = "🟢 Отлично"
            color = config.COLOR_SUCCESS
        elif latency < 200:
            status = "🟡 Нормально"
            color = config.COLOR_WARNING
        else:
            status = "🔴 Высокая"
            color = config.COLOR_ERROR

        embed = discord.Embed(
            title="🏓 Понг!",
            description=f"**Задержка:** `{latency}ms`\n**Статус:** {status}",
            color=color,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text="Musya-Bot", icon_url=self.bot.user.display_avatar.url)
        await ctx.send(embed=embed)

    # ===== СЕРВЕРНАЯ ИКОНКА =====
    @commands.command(name="servericon", aliases=["sicon"])
    async def servericon(self, ctx):
        """Показать иконку сервера"""
        if not ctx.guild.icon:
            embed = self._util_embed("ℹ️", "У сервера нет иконки.", config.COLOR_WARNING)
            return await ctx.send(embed=embed)

        embed = self._util_embed(f"🖼️ Иконка — {ctx.guild.name}")
        embed.set_image(url=ctx.guild.icon.url)
        await ctx.send(embed=embed)

    # ===== СЕРВЕРНЫЙ БАННЕР =====
    @commands.command(name="serverbanner", aliases=["sbanner"])
    async def serverbanner(self, ctx):
        """Показать баннер сервера"""
        if not ctx.guild.banner:
            embed = self._util_embed("ℹ️", "У сервера нет баннера.", config.COLOR_WARNING)
            return await ctx.send(embed=embed)

        embed = self._util_embed(f"🎨 Баннер — {ctx.guild.name}")
        embed.set_image(url=ctx.guild.banner.url)
        await ctx.send(embed=embed)

    # ===== SUGGEST =====
    @commands.command(name="suggest", aliases=["idea"])
    async def suggest(self, ctx, *, suggestion: str = None):
        """Предложить идею
        Использование: !suggest <ваша идея>"""
        if not suggestion:
            embed = self._util_embed("❌ Ошибка",
                                     "Напишите идею: `!suggest <ваша идея>`",
                                     config.COLOR_ERROR)
            return await ctx.send(embed=embed)

        embed = discord.Embed(
            title="💡 Предложение",
            description=suggestion,
            color=config.COLOR_PRIMARY,
            timestamp=datetime.utcnow()
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text=f"ID: {ctx.author.id}")

        msg = await ctx.send(embed=embed)
        await msg.add_reaction("👍")
        await msg.add_reaction("👎")

        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

    # ===== POLL =====
    @commands.command(name="poll")
    async def poll(self, ctx, *, question: str = None):
        """Создать голосование
        Использование: !poll <вопрос>"""
        if not question:
            embed = self._util_embed("❌ Ошибка",
                                     "Напишите вопрос: `!poll <вопрос>`",
                                     config.COLOR_ERROR)
            return await ctx.send(embed=embed)

        embed = discord.Embed(
            title="📊 Голосование",
            description=question,
            color=config.COLOR_PRIMARY,
            timestamp=datetime.utcnow()
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)

        msg = await ctx.send(embed=embed)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")

        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass


async def setup(bot):
    await bot.add_cog(Utility(bot))