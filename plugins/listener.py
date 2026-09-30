import asyncio
from pyrogram.types import Message
from pyrogram import Client, StopPropagation

Message._original_parse = Message._parse

@staticmethod
async def _custom_parse(client, message, users, chats, *args, **kwargs):
    msg = await Message._original_parse(client, message, users, chats, *args, **kwargs)
    if hasattr(client, "listen_futures"):
        chat_id = getattr(getattr(msg, "chat", None), "id", None)
        user_id = getattr(getattr(msg, "from_user", None), "id", None)
        key = (chat_id, user_id)
        key_chat = (chat_id, None)

        if key in client.listen_futures:
            future = client.listen_futures.pop(key)
            if not future.done():
                future.set_result(msg)
            raise StopPropagation
            
        if key_chat in client.listen_futures:
            future = client.listen_futures.pop(key_chat)
            if not future.done():
                future.set_result(msg)
            raise StopPropagation      
    return msg

Message._parse = _custom_parse


async def custom_listen(self, chat_id, filters=None, timeout=60, user_id=None):
    if not hasattr(self, "listen_futures"):
        self.listen_futures = {} 
    future = asyncio.get_running_loop().create_future()
    if user_id:
        key = (chat_id, user_id)
    else:
        key = (chat_id, None)
     
    self.listen_futures[key] = future
    try:
        if timeout:
            message = await asyncio.wait_for(future, timeout=timeout)
        else:
            message = await future 
        if filters:
            if not await filters(self, message):
                return await self.listen(chat_id, filters, timeout, user_id)       
        return message
    except asyncio.TimeoutError:
        self.listen_futures.pop(key, None)
        raise

Client.listen = custom_listen
