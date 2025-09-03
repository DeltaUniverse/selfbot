import struct

from pyrogram.types import CopyTextButton, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.utils import (
    MIN_MONOFORUM_CHANNEL_ID,
    get_channel_id,
    unpack_inline_message_id,
)


def ids(inline_message_id: str) -> tuple:
    data = unpack_inline_message_id(inline_message_id)

    try:
        cid, mid = data.owner_id, data.id
    except AttributeError:
        cid, mid = struct.unpack(">ii", data.id.to_bytes(8, signed=True))

    if cid < 0 or cid >= MIN_MONOFORUM_CHANNEL_ID:
        cid = get_channel_id(abs(cid))

    return cid, mid


def ikm(rows: list | tuple) -> InlineKeyboardMarkup:
    if isinstance(rows, tuple):
        rows = [[rows]]

    if isinstance(rows, list) and isinstance(rows[0], tuple):
        rows = [rows]

    ikb = []

    for row in rows:
        line = []

        for button in row:
            args = {"text": button[0]}
            last = button[-1]

            if len(button) == 2:
                args.update({"callback_data": last})

            elif len(button) == 3:
                arg = button[1]

                if arg == "user":
                    args.update({"user_id": last})
                elif arg == "copy":
                    args.update({"copy_text": CopyTextButton(text=last)})
                else:
                    args.update({arg: last})

            else:
                raise ValueError

            line.append(InlineKeyboardButton(**args))

        ikb.append(line)

    return InlineKeyboardMarkup(ikb)
