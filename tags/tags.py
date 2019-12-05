import discord
from datetime import datetime
from discord.ext import commands

from core import checks
from core.models import PermissionLevel


class Tag(commands.Cog):
    """Plugin per i tag!"""
    def __init__(self, bot):
        self.bot: discord.Client = bot
        self.db = bot.plugin_db.get_partition(self)

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @checks.has_permissions(PermissionLevel.REGULAR)
    async def tags(self, ctx: commands.Context):
        """
        Crea, modifica e gestisci i tag
        """
        await ctx.send_help(ctx.command)

    @tags.command()
    async def add(self, ctx: commands.Context, name: str, *, content: str):
        """
        Crea un nuovo tag
        """
        if (await self.find_db(name=name)) is not None:
            await ctx.send(f":x: | Un tag con il nome `{name}` già esiste!")
            return
        else:
            await self.db.insert_one(
                {
                    "name": name,
                    "content": content,
                    "createdAt": datetime.utcnow(),
                    "updatedAt": datetime.utcnow(),
                    "author": ctx.author.id,
                    "uses": 0,
                }
            )

            await ctx.send(
                f":white_check_mark: | Il tag con il nome `{name}` è stato creato con successo!"
            )
            return

    @tags.command()
    async def edit(self, ctx: commands.Context, name: str, *, content: str):
        """
        Modifica un tag esistente.

        Solo il proprietario del tag oppure un utente con il permesso "Gestisci server" può usare questo comando.
        """
        tag = await self.find_db(name=name)

        if tag is None:
            await ctx.send(f":x: | Il tag con il nome `{name}` non esiste!")
            return
        else:
            member: discord.Member = ctx.author
            if ctx.author.id == tag["author"] or member.guild_permissions.manage_guild:
                await self.db.find_one_and_update(
                    {"name": name},
                    {"$set": {"content": content, "updatedAt": datetime.utcnow()}},
                )

                await ctx.send(
                    f":white_check_mark: | Il tag `{name}` è stato modificato con successo!"
                )
            else:
                await ctx.send("Non hai abbastanza permessi per modificare questo tag.")

    @tags.command()
    async def delete(self, ctx: commands.Context, name: str):
        """
        Elimina un tag.

        Solo il proprietario del tag oppure un utente con il permesso "Gestisci server" può usare questo comando.
        """
        tag = await self.find_db(name=name)
        if tag is None:
            await ctx.send(":x: | Il tag `{name}` non è stato trovato nel database.")
        else:
            if (
                ctx.author.id == tag["author"]
                or ctx.author.guild_permissions.manage_guild
            ):
                await self.db.delete_one({"name": name})

                await ctx.send(
                    f":white_check_mark: | Il tag `{name}` è stato eliminato con successo!"
                )
            else:
                await ctx.send("Non hai abbastanza permessi per eliminare questo tag.")

    @commands.command()
    async def tag(self, ctx: commands.Context, name: str):
        """
        Usa un tag!
        """
        tag = await self.find_db(name=name)
        if tag is None:
            await ctx.send(f":x: | Il tag {name} non è stato trovato.")
            return
        else:
            await ctx.send(tag["content"])
            await self.db.find_one_and_update(
                {"name": name}, {"$set": {"uses": tag["uses"] + 1}}
            )
            return

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if not msg.content.startswith(self.bot.prefix):
            return
        content = msg.content.replace(self.bot.prefix, "")
        names = content.split(" ")

        tag = await self.db.find_one({"name": names[0]})

        if tag is None:
            return
        else:
            await msg.channel.send(tag["content"])
            await self.db.find_one_and_update(
                {"name": names[0]}, {"$set": {"uses": tag["uses"] + 1}}
            )
            return

    async def find_db(self, name: str):
        return await self.db.find_one({"name": name})


def setup(bot):
    bot.add_cog(Tag(bot))
