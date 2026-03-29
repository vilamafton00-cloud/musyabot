import os
from dotenv import load_dotenv

load_dotenv()

# ============================
# КОНФИГУРАЦИЯ MUSYA-BOT
# Бот для сервера A-Studio
# ============================

BOT_TOKEN = os.getenv("DISCORD_TOKEN", "YOUR_TOKEN_HERE")

# Префикс команд
PREFIX = "!"

# ===== СИСТЕМА УРОВНЕЙ =====
# EXP за сообщение (мин, макс)
EXP_PER_MESSAGE_MIN = 15
EXP_PER_MESSAGE_MAX = 25

# EXP за минуту в войсе
EXP_PER_VOICE_MINUTE = 15

# Кулдаун EXP за сообщения (секунды) — чтобы не спамили
MESSAGE_EXP_COOLDOWN = 10

# Формула уровня: EXP_для_уровня = BASE_EXP * level ^ EXP_EXPONENT
BASE_EXP = 100
EXP_EXPONENT = 1.5

# ===== РОЛИ ЗА УРОВНИ =====
# Формат: {уровень: ID роли}
# ЗАМЕНИ НА РЕАЛЬНЫЕ ID РОЛЕЙ СВОЕГО СЕРВЕРА!
LEVEL_ROLES = {
    5: 1487899161155207228,    # Замени на ID роли за 5 уровень
    10: 1487899598604337172,   # Замени на ID роли за 10 уровень
    15: 1487897433605275738,   # Замени на ID роли за 15 уровень
    25: 1487900389763186808,   # Замени на ID роли за 25 уровень
    50: 1487900885735444500,   # Замени на ID роли за 50 уровень
}

# ===== КАНАЛЫ =====
# ID канала для логов модерации (замени на свой)
MOD_LOG_CHANNEL = None

# ID канала для логов уровней
LEVEL_UP_CHANNEL = None

# ===== ЦВЕТА EMBED =====
COLOR_PRIMARY = 0x5865F2     # Синий (основной)
COLOR_SUCCESS = 0x57F287     # Зелёный
COLOR_WARNING = 0xFEE75C     # Жёлтый
COLOR_ERROR = 0xED4245       # Красный
COLOR_MODERATION = 0xE67E22  # Оранжевый
COLOR_LEVEL = 0x9B59B6       # Фиолетовый
COLOR_ANALYTICS = 0x1ABC9C   # Бирюзовый