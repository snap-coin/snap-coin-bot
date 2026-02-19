import discord 


async def react_on_message(message: discord.Message, emoji: str):
    """Reacts to a message with the given emoji."""
    try:
        await message.add_reaction(emoji)
    except discord.HTTPException as e:
        print(f"Failed to react to message: {e}")