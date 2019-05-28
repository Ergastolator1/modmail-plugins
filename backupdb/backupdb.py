import os
from discord.ext import commands
from motor.motor_asyncio import AsyncIOMotorClient

from core import checks
from core.models import PermissionLevel


class BackupDB(commands.Cog):
    """
    Take Backup of your mongodb database with a single command!

    **Requires `BACKUP_MONGO_URI` in Heroku environment variables**
    """
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @checks.has_permissions(PermissionLevel.OWNER)
    async def backup(self, ctx: commands.Context):
        """
        Backup Your Mongodb database using this command.

        **Deletes Existing data from the backup db**
        """
        backup_url = await os.getenv("BACKUP_MONGO_URI", None)
        if backup_url is None:
            await ctx.send(":x: | No `BACKUP_MONGO_URI` found in env variables.")
            return
        db_name = (backup_url.split("/"))[-1]
        odb_uri = os.getenv("MONGO_URI")
        odb_n = (odb_uri.split("/"))[-1]
        odb = odb_uri.replace(f"/{odb_n}", "")

        connection_string = backup_url.replace(f"/{db_name}", "")
        backup_client = AsyncIOMotorClient(connection_string)
        bdb = backup_client[db_name]
        await ctx.send("Connected to backup DB. Removing all documents")
        if bdb.collection_name:
            for collection in bdb.collection_names:
                await bdb[collection].drop()
                await ctx.send("Deleted all documents from backup db")

        await backup_client.admin.command("copydb",
                         fromdb="modmail_bot",
                         todb=db_name,
                         fromhost=odb)
        await ctx.send("DB Was Successfully Backed Up!")


def setup(bot):
    bot.add_cog(BackupDB(bot))