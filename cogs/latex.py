import asyncio
import hashlib
import pathlib
import re
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

import discord
import matplotlib.pyplot as plt
from discord.ext import commands


plt.rcParams.update(
    {
        "font.size": 16,
        "mathtext.fontset": "cm",
        "mathtext.rm": "serif",
        "figure.facecolor": "36393F",
        "text.color": "white",
    }
)

FORMATTED_CODE_REGEX = re.compile(
    r"(?P<delim>(?P<block>```)|``?)"        
    r"(?(block)(?:(?P<lang>[a-z]+)\n)?)" 
    r"(?:[ \t]*\n)*"    
    r"(?P<code>.*?)"                        
    r"\s*"    
    r"(?P=delim)", 
    re.DOTALL | re.IGNORECASE, 
)

CACHE_DIRECTORY = pathlib.Path("_latex_cache")
CACHE_DIRECTORY.mkdir(exist_ok=True)


class Latex(commands.Cog):
    """Renders latex."""

    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def _render(text: str, filepath: pathlib.Path) -> BytesIO:
        """
        Return the rendered image if latex compiles without errors, otherwise raise a BadArgument Exception.

        Saves rendered image to cache.
        """
        fig = plt.figure()
        rendered_image = BytesIO()
        fig.text(0, 1, text, horizontalalignment="left", verticalalignment="top")

        try:
            plt.savefig(rendered_image, bbox_inches="tight", dpi=600)
        except ValueError as e:
            raise commands.BadArgument(str(e))

        rendered_image.seek(0)

        with open(filepath, "wb") as f:
            f.write(rendered_image.getbuffer())

        return rendered_image

    @staticmethod
    def _prepare_input(text: str) -> str:
        text = text.replace(r"\\", "$\n$") 

        if match := FORMATTED_CODE_REGEX.match(text):
            return match.group("code")
        else:
            return text

    @commands.command()
    @commands.max_concurrency(1, commands.BucketType.guild, wait=True)
    async def latex(self, ctx: commands.Context, *, text: str) -> None:
        """Renders the text in latex and sends the image."""
        text = self._prepare_input(text)
        query_hash = hashlib.md5(text.encode()).hexdigest()
        image_path = CACHE_DIRECTORY.joinpath(f"{query_hash}.png")
        async with ctx.typing():
            if image_path.exists():
                await ctx.send(file=discord.File(image_path))
                return

            with ThreadPoolExecutor() as pool:
                image = await asyncio.get_running_loop().run_in_executor(
                    pool, self._render, text, image_path
                )

            await ctx.send(file=discord.File(image, "latex.png"))


def setup(bot) -> None:
    bot.add_cog(Latex(bot))
