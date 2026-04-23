import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
from datetime import datetime

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

DATA_FILE = "raids.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

class GVGView(discord.ui.View):
    def __init__(self, raid_id):
        super().__init__(timeout=None)
        self.raid_id = raid_id

    def add_player(self, user_id, role):
        raid = data[self.raid_id]

        if str(user_id) in raid["players"]:
            return "Ты уже записан"

        if len(raid["players"]) >= 30:
            if len(raid["reserve"]) >= 10:
                return "Нет мест даже в резерве"
            raid["reserve"].append(user_id)
            save_data(data)
            return "Ты записан в резерв"

        raid["players"][str(user_id)] = role
        save_data(data)
        return "Записан"

    @discord.ui.button(label="🛡️ Танк", style=discord.ButtonStyle.primary)
    async def tank(self, interaction: discord.Interaction, button: discord.ui.Button):
        msg = self.add_player(interaction.user.id, "tank")
        await interaction.response.send_message(msg, ephemeral=True)

    @discord.ui.button(label="🍃 Хил", style=discord.ButtonStyle.success)
    async def heal(self, interaction: discord.Interaction, button: discord.ui.Button):
        msg = self.add_player(interaction.user.id, "heal")
        await interaction.response.send_message(msg, ephemeral=True)

    @discord.ui.button(label="⚔️ ДД", style=discord.ButtonStyle.secondary)
    async def dps(self, interaction: discord.Interaction, button: discord.ui.Button):
        msg = self.add_player(interaction.user.id, "dps")
        await interaction.response.send_message(msg, ephemeral=True)

    @discord.ui.button(label="❌ Отписаться", style=discord.ButtonStyle.danger)
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        raid = data[self.raid_id]

        if str(interaction.user.id) in raid["players"]:
            del raid["players"][str(interaction.user.id)]
            save_data(data)
            await interaction.response.send_message("Ты отписался", ephemeral=True)
        else:
            await interaction.response.send_message("Ты не записан", ephemeral=True)


@bot.event
async def on_ready():
    print(f"Бот запущен как {bot.user}")
    reminder_loop.start()
    await bot.tree.sync()


@bot.tree.command(name="gvg_create", description="Создать запись на ГВГ")
async def gvg_create(interaction: discord.Interaction, title: str, date: str, time_msk: str):

    await interaction.response.defer()  # 🔥 фикс ошибки "не отвечает"

    raid_id = str(len(data) + 1)

    dt = datetime.strptime(f"{date} {time_msk}", "%d.%m.%Y %H:%M")
    timestamp = int(dt.timestamp())

    data[raid_id] = {
        "title": title,
        "time": timestamp,
        "players": {},
        "reserve": []
    }

    save_data(data)

    text = f"**{title}**\n"
    text += f"🕒 <t:{timestamp}:F>\n\n"
    text += "🛡️ 2 танка | 🍃 6 хилов | ⚔️ 22 дд\n"
    text += "Резерв: 10 мест"

    view = GVGView(raid_id)
    msg = await interaction.channel.send(text, view=view)

    await msg.create_thread(name=f"Обсуждение {title}")

    await interaction.followup.send("Запись создана ✅", ephemeral=True)


@tasks.loop(minutes=1)
async def reminder_loop():
    now = datetime.utcnow().timestamp()

    for raid_id, raid in data.items():
        raid_time = raid["time"]

        for t, label in [(3600, "через 1 час"), (600, "через 10 минут"), (0, "началось")]:
            if abs(raid_time - now - t) < 30:
                guild = bot.guilds[0]
                users = [guild.get_member(int(uid)) for uid in raid["players"].keys()]
                mentions = " ".join([u.mention for u in users if u])

                channel = guild.text_channels[0]
                await channel.send(f"{mentions}\nГВГ {label}!")


bot.run(TOKEN)
