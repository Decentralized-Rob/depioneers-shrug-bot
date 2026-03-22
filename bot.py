import discord
from discord import app_commands
import aiohttp
import os
import base64
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

TENSOR_API = "https://api.tensor.so/graphql"
HF_API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-refiner-1.0"

intents = discord.Intents.default()
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)


async def fetch_nft_image_bytes(image_url: str) -> bytes | None:
    async with aiohttp.ClientSession() as session:
        async with session.get(image_url) as resp:
            if resp.status == 200:
                return await resp.read()
    return None


async def fetch_nft_image_url(nft_id: str) -> str | None:
    query = """
    query TokenInfo($mint: String!) {
      token(mint: $mint) {
        mint
        imageUri
        name
      }
    }
    """
    headers = {"Content-Type": "application/json"}
    if os.getenv("TENSOR_API_KEY"):
        headers["X-TENSOR-API-KEY"] = os.getenv("TENSOR_API_KEY")

    async with aiohttp.ClientSession() as session:
        async with session.post(
            TENSOR_API,
            json={"query": query, "variables": {"mint": nft_id}},
            headers=headers,
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                token = data.get("data", {}).get("token")
                if token and token.get("imageUri"):
                    return token["imageUri"]
    return None


async def generate_shrug(image_url: str) -> bytes | None:
    image_bytes = await fetch_nft_image_bytes(image_url)
    if not image_bytes:
        return None

    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    prompt = (
        "cartoon cat NFT character in a shrug pose, both arms raised with palms facing up, "
        "shoulders raised, wearing same outfit, same accessories, sticker art style, "
        "white outline border, clean white background, high quality illustration"
    )

    payload = {
        "inputs": prompt,
        "parameters": {
            "image": b64_image,
            "strength": 0.6,
            "num_inference_steps": 30,
            "guidance_scale": 7.5,
        }
    }

    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(HF_API_URL, json=payload, headers=headers) as resp:
            if resp.status == 200:
                return await resp.read()
            else:
                error = await resp.text()
                print(f"HF API error {resp.status}: {error}")
                return None


@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Bot is online as {bot.user}")


@tree.command(name="shrug", description="Generate a shrug emoji version of a dePioneer NFT")
@app_commands.describe(nft_id="The mint address (e.g. HmQdroN1Dvh7uArfY4CJtrWaUaX56LuX6Gdu3guvRNY6)")
async def shrug_command(interaction: discord.Interaction, nft_id: str):
    await interaction.response.defer(thinking=True)
    try:
        image_url = await fetch_nft_image_url(nft_id)
        if not image_url:
            await interaction.followup.send(
                f"❌ Couldn't find NFT `{nft_id}`.\nTry `/shrug_url` with a direct image URL instead."
            )
            return

        await interaction.followup.send("🎨 Generating shrug... this takes ~30s")
        result_bytes = await generate_shrug(image_url)

        if not result_bytes:
            await interaction.followup.send("❌ Generation failed. Try `/shrug_url` instead.")
            return

        file = discord.File(fp=__import__("io").BytesIO(result_bytes), filename="shrug.png")
        embed = discord.Embed(title="🤷 dePioneer Shrug", color=0x00ffcc)
        embed.set_image(url="attachment://shrug.png")
        embed.set_footer(text="dePioneers • Powered by Hugging Face")
        await interaction.followup.send(embed=embed, file=file)

    except Exception as e:
        await interaction.followup.send(f"❌ Error: `{str(e)}`")
        raise e


@tree.command(name="shrug_url", description="Generate a shrug version from a direct image URL")
@app_commands.describe(image_url="Direct image URL of the NFT")
async def shrug_url_command(interaction: discord.Interaction, image_url: str):
    await interaction.response.defer(thinking=True)
    try:
        await interaction.followup.send("🎨 Generating shrug... ~30s")
        result_bytes = await generate_shrug(image_url)

        if not result_bytes:
            await interaction.followup.send("❌ Generation failed. Try again!")
            return

        file = discord.File(fp=__import__("io").BytesIO(result_bytes), filename="shrug.png")
        embed = discord.Embed(title="🤷 dePioneer Shrug", color=0x00ffcc)
        embed.set_image(url="attachment://shrug.png")
        embed.set_footer(text="dePioneers • Powered by Hugging Face")
        await interaction.followup.send(embed=embed, file=file)

    except Exception as e:
        await interaction.followup.send(f"❌ Error: `{str(e)}`")
        raise e


bot.run(DISCORD_TOKEN)
