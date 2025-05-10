import discord
from discord.ext import commands
from discord import app_commands
import requests
import qrcode
from io import BytesIO
from dotenv import load_dotenv
import os

# Load .env variables
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
LTC_ADDRESS = os.getenv("LTC_ADDRESS")
UPI_QR_PATH = os.getenv("UPI_QR_PATH")
UPI_ID = os.getenv("UPI_ID")
ALLOWED_USER_IDS = [int(id.strip()) for id in os.getenv("ALLOWED_USER_IDS", "").split(",") if id.strip().isdigit()]

intents = discord.Intents.default()
intents.message_content = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="/", intents=intents)
        self.synced = False

    async def on_ready(self):
        if not self.synced:
            await self.tree.sync()  # sync globally (includes DMs)
            self.synced = True
        print(f"✅ Logged in as {self.user}")

bot = MyBot()

# Allowlist check
async def is_allowed(interaction: discord.Interaction):
    return interaction.user.id in ALLOWED_USER_IDS

# Error handler
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True)
    else:
        await interaction.response.send_message("⚠️ An unexpected error occurred.", ephemeral=True)
        import traceback
        traceback_str = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
        print(traceback_str)

# /mybal command
@bot.tree.command(name="mybal", description="Check your LTC wallet balance", dm_permission=True)
@app_commands.check(is_allowed)
async def mybal(interaction: discord.Interaction):
    url = f'https://api.blockcypher.com/v1/ltc/main/addrs/{LTC_ADDRESS}'
    response = requests.get(url)
    if response.status_code != 200:
        await interaction.response.send_message("❌ Failed to fetch balance.")
        return

    data = response.json()
    confirmed = data.get("balance", 0) / 1e8
    unconfirmed = data.get("unconfirmed_balance", 0) / 1e8
    total_received = data.get("total_received", 0) / 1e8
    txs = data.get("txrefs", [])
    latest_tx = txs[0]['tx_hash'] if txs else "No transactions yet"

    embed = discord.Embed(title="📊 LTC Balance Checker | My_Bal")
    embed.add_field(name="Confirmed Balance", value=f"{confirmed:.8f} LTC", inline=True)
    embed.add_field(name="Unconfirmed Balance", value=f"{unconfirmed:.8f} LTC", inline=True)
    embed.add_field(name="Total Received", value=f"{total_received:.8f} LTC", inline=True)
    embed.add_field(name="Last Transaction", value=latest_tx, inline=False)
    await interaction.response.send_message(embed=embed)

# /ltc and /ltc qr command
@bot.tree.command(name="ltc", description="Get LTC address or QR", dm_permission=True)
@app_commands.describe(option="Type 'qr' for QR code", amount="Amount (for QR)")
@app_commands.check(is_allowed)
async def ltc(interaction: discord.Interaction, option: str = None, amount: float = 0.0):
    if option == "qr":
        if amount <= 0:
            await interaction.response.send_message("⚠️ Please specify a valid positive amount for the QR.", ephemeral=True)
            return
        uri = f"litecoin:{LTC_ADDRESS}?amount={amount}"
        img = qrcode.make(uri)
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        await interaction.response.send_message(file=discord.File(buffer, filename="ltc_qr.png"))
    else:
        await interaction.response.send_message(f"My LTC Address: `{LTC_ADDRESS}`")

# /upi command
@bot.tree.command(name="upi", description="Send UPI QR and ID", dm_permission=True)
@app_commands.check(is_allowed)
async def upi(interaction: discord.Interaction):
    try:
        await interaction.response.send_message(
            f"📎 My UPI ID: `{UPI_ID}`", file=discord.File(UPI_QR_PATH)
        )
    except FileNotFoundError:
        await interaction.response.send_message("❌ UPI QR code image not found.")

# In-memory stock data
stock_data = {"kitsune": 0, "dragon_west": 0}

# /stock command
@bot.tree.command(name="stock", description="Show stock details", dm_permission=True)
@app_commands.check(is_allowed)
async def stock(interaction: discord.Interaction):
    embed = discord.Embed(title="📦 Stock")
    embed.add_field(name="🐉 Dragon West", value=stock_data["dragon_west"], inline=True)
    embed.add_field(name="🦊 Kitsune", value=stock_data["kitsune"], inline=True)
    embed.set_footer(text="Made with ❤️ for Members.")
    await interaction.response.send_message(embed=embed)

# /stock_add command
@bot.tree.command(name="stock_add", description="Admin only: Add stock counts", dm_permission=True)
@app_commands.describe(kitsune="Number of Kitsune", dragon_west="Number of Dragon West")
@app_commands.check(is_allowed)
async def stock_add(interaction: discord.Interaction, kitsune: int, dragon_west: int):
    stock_data["kitsune"] = kitsune
    stock_data["dragon_west"] = dragon_west
    await interaction.response.send_message("✅ Stock updated.")

bot.run(TOKEN)
