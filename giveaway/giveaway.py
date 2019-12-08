import asyncio
import dateparser
import discord
import math
import random
import time
from datetime import datetime
from discord.ext import commands

from core import checks
from core.models import PermissionLevel


class GiveawayPlugin(commands.Cog):
    """
    Host giveaways on your server with this ~~amazing~~ plugin
    """

    def __init__(self, bot):
        self.bot: discord.Client = bot
        self.db = bot.plugin_db.get_partition(self)
        self.active_giveaways = {}
        asyncio.create_task(self._set_giveaways_from_db())

    async def _set_giveaways_from_db(self):
        config = await self.db.find_one({"_id": "config"})
        if config is None:
            await self.db.find_one_and_update(
                {"_id": "config"},
                {"$set": {"giveaways": dict()}},
                upsert=True,
            )
        self.active_giveaways = dict(config.get("giveaways", {}))

        for giveaway in config.get("giveaways", {}).values():
            print(giveaway["message"])
            self.bot.loop.create_task(self._handle_giveaway(giveaway))

    async def _update_db(self):
        await self.db.find_one_and_update(
            {"_id": "config"},
            {"$set": {"giveaways": self.active_giveaways}},
            upsert=True,
        )

    async def _handle_giveaway(self, giveaway):
        if str(giveaway["message"]) not in self.active_giveaways:
            return

        async def get_random_user(users, _guild, _winners):
            rnd = random.choice(users)
            in_guild = _guild.get_member(rnd)
            if rnd in _winners or in_guild is None or in_guild.id == self.bot.user.id:
                idk = await get_random_user(users, _guild, _winners)
                return idk
            win = [] + _winners
            win.append(rnd)
            return win

        while True:
            if str(giveaway["message"]) not in self.active_giveaways:
                break
            channel: discord.TextChannel = self.bot.get_channel(int(giveaway["channel"]))
            if channel is None:
                try:
                    self.active_giveaways.pop(str(giveaway["message"]))
                    await self._update_db()
                except:
                    pass
                return
            message = await channel.fetch_message(giveaway["message"])
            if message is None or not message.embeds or message.embeds[0] is None:
                try:
                    self.active_giveaways.pop(str(giveaway["message"]))
                    await self._update_db()
                except:
                    pass
                return
            guild: discord.Guild = self.bot.get_guild(giveaway["guild"])
            g_time = giveaway["time"] - time.time()

            if g_time <= 0:
                if len(message.reactions) <= 0:
                    embed = message.embeds[0]
                    embed.description = f"Giveaway has ended!\n\nSadly no one participated :("
                    embed.set_footer(
                        text=f"{giveaway['winners']} {'winners' if giveaway['winners'] > 1 else 'winner'} | Ended at")
                    await message.edit(embed=embed)
                    break

                to_break = False

                for r in message.reactions:
                    if str(giveaway["message"]) not in self.active_giveaways:
                        break

                    if r.emoji == "🎉":
                        reactions = r
                        reacted_users = await reactions.users().flatten()
                        if len(reacted_users) <= 1:
                            embed = message.embeds[0]
                            embed.description = f"Giveaway has ended!\n\nSadly no one participated :("
                            embed.set_footer(
                                text=f"{giveaway['winners']} {'winners' if giveaway['winners'] > 1 else 'winner'} | "
                                     f"Ended at")
                            await message.edit(embed=embed)
                            del guild, channel, reacted_users, embed
                            break

                        # -1 cuz 1 for self
                        if giveaway["winners"] > (len(reacted_users) - 1):
                            giveaway["winners"] = (len(reacted_users) - 1)

                        winners = []

                        for index in range(len(reacted_users)):
                            reacted_users[index] = reacted_users[index].id

                        for _ in range(giveaway["winners"]):
                            winners = await get_random_user(reacted_users, guild, winners)

                        embed = message.embeds[0]
                        winners_text = ""
                        for winner in winners:
                            winners_text += f"<@{winner}> "

                        embed.description = f"Giveaway has ended!\n\n**Winners:** {winners_text}"
                        embed.set_footer(text=f"{giveaway['winners']} {'winners' if giveaway['winners'] > 1 else 'winner'} | " 
                                              f"Ended at")
                        await message.edit(embed=embed)
                        await channel.send(f"🎉 Congratulations {winners_text} you won **{giveaway['item']}**")
                        try:
                            self.active_giveaways.pop(str(giveaway["message"]))
                            await self._update_db()
                        except:
                            pass
                        del winners_text, winners, guild, channel, reacted_users, embed
                        to_break = True
                        break

                if to_break:
                    break
            else:

                time_remaining = f"{math.floor(g_time // 86400)} Days, {math.floor(g_time // 3600 % 24)} Hours, {math.floor(g_time // 60 % 60)} Minutes, {math.floor(g_time % 60)} Seconds "

                embed = message.embeds[0]
                embed.description = f"React with 🎉 to enter the giveaway!\n\n" \
                                    f"Time Remaining **{time_remaining}**"
                await message.edit(embed=embed)
                del channel, guild
                await asyncio.sleep(60 if g_time > 60 else 5)

        return

    @commands.group(name="giveaway", aliases=["g", "giveaways", "gaway", "givea"], invoke_without_command=True)
    @commands.guild_only()
    @checks.has_permissions(PermissionLevel.ADMIN)
    async def giveaway(self, ctx: commands.Context):
        """
        Create / Stop Giveaways
        """
        await ctx.send_help(ctx.command)
        return

    @checks.has_permissions(PermissionLevel.ADMIN)
    @giveaway.command(name="start")
    async def start(self, ctx: commands.Context, channel: discord.TextChannel):
        """
        Start an giveaway in interactive mode
        """

        def check(msg: discord.Message):
            return ctx.author == msg.author and ctx.channel == msg.channel and (len(msg.content) < 2048)

        def cancel_check(msg: discord.Message):
            return msg.content == "cancel" or msg.content == f"{ctx.prefix}cancel"

        embed = discord.Embed(
            colour=0x00ff00
        )

        await ctx.send(embed=self.generate_embed("What is the giveaway item?"))
        giveaway_item = await self.bot.wait_for("message", check=check)
        if cancel_check(giveaway_item) is True:
            await ctx.send("Cancelled")
            return
        embed.title = giveaway_item.content
        await ctx.send(embed=self.generate_embed("How many winners are to be selected?"))
        giveaway_winners = await self.bot.wait_for("message", check=check)
        if cancel_check(giveaway_winners) is True:
            await ctx.send("Cancelled")
            return
        try:
            giveaway_winners = int(giveaway_winners.content)
        except:
            await ctx.send("Unable to parse Giveaway winners to numbers, exiting. Make sure to pass numbers from next "
                           "time")
            return

        await ctx.send(embed=self.generate_embed("How long the giveaway last?\n\n2d / 2days / 2day -> 2 days\n"
                                                 "2m -> 2 minutes\n2 months -> 2 months"
                                                 "\ntomorrow / in 10 minutes / 2h 10minutes work too\n"))
        time_cancel = False
        while True:
            giveaway_time = await self.bot.wait_for("message", check=check)
            if cancel_check(giveaway_time) is True:
                time_cancel = True
                await ctx.send("Cancelled")
                break
            giveaway_time = dateparser.parse(giveaway_time.content)
            if giveaway_time is None:
                await ctx.send("I was not able to parse the time properly, please try again.")
                continue
            else:
                giveaway_time = giveaway_time.timestamp()
                break
        if time_cancel is True:
            return

        embed.description = f"React with 🎉 to enter the giveaway!\n\n" \
                      f"Time Remaining **{datetime.fromtimestamp(giveaway_time).strftime('%d %H:%M:%S')}**"
        embed.set_footer(text=f"{giveaway_winners} {'winners' if giveaway_winners > 1 else 'winner'} | Ends at")
        embed.timestamp = datetime.fromtimestamp(giveaway_time)
        msg: discord.Message = await channel.send(embed=embed)
        await msg.add_reaction("🎉")
        giveaway_obj = {"item": giveaway_item.content, "winners": giveaway_winners, "time": giveaway_time, "guild": ctx.guild.id, "channel": channel.id, "message": msg.id}
        self.active_giveaways[str(msg.id)] = giveaway_obj
        await ctx.send("Done!")
        await self._update_db()
        await self._start_new_giveaway_thread(giveaway_obj)

    async def _start_new_giveaway_thread(self, obj):
        await self.bot.loop.create_task(self._handle_giveaway(obj))

    def generate_embed(self, description: str):
        embed = discord.Embed()
        embed.colour = self.bot.main_color
        embed.description = description

        return embed


def setup(bot):
    bot.add_cog(GiveawayPlugin(bot))