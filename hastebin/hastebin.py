import discord
import os
from discord import Embed
from discord.ext import commands

from json import JSONDecodeError
from aiohttp import ClientResponseError


class Hastebin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def hastebin(self, ctx, *, message):
        """Carica il testo su Hastebin!"""
        haste_url = os.environ.get("HASTE_URL", "https://hasteb.in")

        try:
            async with self.bot.session.post(
                haste_url + "/documents", data=message
            ) as resp:
                key = (await resp.json())["key"]
                embed = Embed(
                    title="Il tuo file caricato",
                    color=self.bot.main_color,
                    description=f"{haste_url}/" + key,
                )
        except (JSONDecodeError, ClientResponseError, IndexError):
            embed = Embed(
                color=self.bot.main_color,
                description="Qualcosa è andato storto. "
                "Non siamo riusciti a caricare il tuo file su Hastebin.",
            )
            embed.set_footer(text="Hastebin")
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_ready(self):
        async with self.bot.session.post(
            "https://counter.modmail-plugins.piyush.codes/api/instances/hastebin",
            json={"id": self.bot.user.id},
        ):
            print("Postato con API del plugin")


def setup(bot):
    bot.add_cog(Hastebin(bot))
