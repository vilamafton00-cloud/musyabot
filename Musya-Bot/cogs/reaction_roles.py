import discord
from discord.ext import commands
from datetime import datetime

import database as db
import config


class ReactionRoles(commands.Cog):
    """🎭 Роли по реакциям — авто-роли через реакции на сообщениях"""

    def __init__(self, bot):
        self.bot = bot

    def _rr_embed(self, title: str, description: str = None,
                  color: int = config.COLOR_PRIMARY) -> discord.Embed:
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text="Musya-Bot • Reaction Roles",
                         icon_url=self.bot.user.display_avatar.url)
        return embed

    # ===== СОЗДАНИЕ СООБЩЕНИЯ С РЕАКЦИЯМИ =====
    @commands.command(name="rrcreate")
    @commands.has_permissions(administrator=True)
    async def rrcreate(self, ctx, channel: discord.TextChannel = None, *, text: str = None):
        """Создать сообщение для reaction roles
        Использование: !rrcreate #канал Текст сообщения

        После создания используйте !rradd для добавления ролей"""
        if not channel or not text:
            embed = self._rr_embed(
                "❌ Ошибка",
                "Использование:\n"
                "`!rrcreate #канал Текст сообщения`\n\n"
                "**Пример:**\n"
                "`!rrcreate #авто-роли Выберите свои роли, нажав на реакции ниже!`",
                config.COLOR_ERROR
            )
            return await ctx.send(embed=embed)

        embed = discord.Embed(
            title="🎭 Выбор ролей",
            description=text,
            color=config.COLOR_PRIMARY
        )
        embed.set_footer(text="Нажмите на реакцию, чтобы получить роль")

        msg = await channel.send(embed=embed)

        result_embed = self._rr_embed(
            "✅ Сообщение создано",
            f"Сообщение создано в {channel.mention}\n"
            f"**ID сообщения:** `{msg.id}`\n\n"
            f"Теперь добавьте роли командой:\n"
            f"`!rradd {msg.id} 😀 @роль`",
            config.COLOR_SUCCESS
        )
        await ctx.send(embed=result_embed)

    # ===== ДОБАВЛЕНИЕ РОЛИ К СООБЩЕНИЮ =====
    @commands.command(name="rradd")
    @commands.has_permissions(administrator=True)
    async def rradd(self, ctx, message_id: int = None, emoji: str = None,
                    role: discord.Role = None):
        """Добавить роль к reaction role сообщению
        Использование: !rradd <ID_сообщения> <эмодзи> @роль"""
        if not message_id or not emoji or not role:
            embed = self._rr_embed(
                "❌ Ошибка",
                "Использование:\n"
                "`!rradd <ID_сообщения> <эмодзи> @роль`\n\n"
                "**Пример:**\n"
                "`!rradd 1234567890 🎮 @Геймер`",
                config.COLOR_ERROR
            )
            return await ctx.send(embed=embed)

        # Ищем сообщение
        msg = None
        for channel in ctx.guild.text_channels:
            try:
                msg = await channel.fetch_message(message_id)
                break
            except (discord.NotFound, discord.Forbidden):
                continue

        if not msg:
            embed = self._rr_embed("❌ Ошибка", "Сообщение не найдено.",
                                   config.COLOR_ERROR)
            return await ctx.send(embed=embed)

        # Добавляем реакцию
        try:
            await msg.add_reaction(emoji)
        except discord.HTTPException:
            embed = self._rr_embed("❌ Ошибка",
                                   "Не удалось добавить реакцию. Проверьте эмодзи.",
                                   config.COLOR_ERROR)
            return await ctx.send(embed=embed)

        # Сохраняем в БД
        await db.add_reaction_role(message_id, str(emoji), role.id,
                                   ctx.guild.id, msg.channel.id)

        # Обновляем embed сообщения
        existing_rr = await db.get_reaction_roles_for_message(message_id)

        if msg.embeds:
            embed_msg = msg.embeds[0]
            # Обновляем описание с ролями
            roles_text = embed_msg.description.split("\n\n---")[0] if embed_msg.description else ""
            roles_list = "\n\n---\n"
            for rr in existing_rr:
                rr_role = ctx.guild.get_role(rr['role_id'])
                if rr_role:
                    roles_list += f"{rr['emoji']} — {rr_role.mention}\n"
            embed_msg.description = roles_text + roles_list
            await msg.edit(embed=embed_msg)

        embed = self._rr_embed(
            "✅ Роль добавлена",
            f"Эмодзи {emoji} теперь даёт роль {role.mention}\n"
            f"На сообщении `{message_id}`",
            config.COLOR_SUCCESS
        )
        await ctx.send(embed=embed)

    # ===== УДАЛЕНИЕ РОЛИ С СООБЩЕНИЯ =====
    @commands.command(name="rrremove")
    @commands.has_permissions(administrator=True)
    async def rrremove(self, ctx, message_id: int = None, emoji: str = None):
        """Удалить роль из reaction role сообщения
        Использование: !rrremove <ID_сообщения> <эмодзи>"""
        if not message_id or not emoji:
            embed = self._rr_embed(
                "❌ Ошибка",
                "Использование: `!rrremove <ID_сообщения> <эмодзи>`",
                config.COLOR_ERROR
            )
            return await ctx.send(embed=embed)

        await db.remove_reaction_role(message_id, str(emoji))

        embed = self._rr_embed(
            "✅ Роль удалена",
            f"Реакция {emoji} больше не выдаёт роль на сообщении `{message_id}`",
            config.COLOR_SUCCESS
        )
        await ctx.send(embed=embed)

    # ===== СПИСОК REACTION ROLES =====
    @commands.command(name="rrlist")
    @commands.has_permissions(administrator=True)
    async def rrlist(self, ctx, message_id: int = None):
        """Посмотреть reaction roles на сообщении
        Использование: !rrlist <ID_сообщения>"""
        if not message_id:
            embed = self._rr_embed(
                "❌ Ошибка",
                "Использование: `!rrlist <ID_сообщения>`",
                config.COLOR_ERROR
            )
            return await ctx.send(embed=embed)

        rr_list = await db.get_reaction_roles_for_message(message_id)

        if not rr_list:
            embed = self._rr_embed("📋 Reaction Roles",
                                   f"На сообщении `{message_id}` нет reaction roles.")
            return await ctx.send(embed=embed)

        embed = self._rr_embed(
            f"📋 Reaction Roles — Сообщение {message_id}"
        )

        for rr in rr_list:
            role = ctx.guild.get_role(rr['role_id'])
            role_name = role.mention if role else f"ID: {rr['role_id']}"
            embed.add_field(
                name=f"{rr['emoji']}",
                value=f"Роль: {role_name}",
                inline=True
            )

        await ctx.send(embed=embed)

    # ===== ОБРАБОТКА ДОБАВЛЕНИЯ РЕАКЦИИ =====
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.member and payload.member.bot:
            return

        rr = await db.get_reaction_role(payload.message_id, str(payload.emoji))
        if not rr:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        role = guild.get_role(rr['role_id'])
        if not role:
            return

        member = guild.get_member(payload.user_id)
        if not member:
            return

        try:
            await member.add_roles(role, reason="Reaction Role")
        except discord.Forbidden:
            pass

    # ===== ОБРАБОТКА УДАЛЕНИЯ РЕАКЦИИ =====
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        rr = await db.get_reaction_role(payload.message_id, str(payload.emoji))
        if not rr:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        role = guild.get_role(rr['role_id'])
        if not role:
            return

        member = guild.get_member(payload.user_id)
        if not member:
            return

        try:
            await member.remove_roles(role, reason="Reaction Role removed")
        except discord.Forbidden:
            pass


async def setup(bot):
    await bot.add_cog(ReactionRoles(bot))