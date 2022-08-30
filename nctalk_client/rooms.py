import asyncio
import httpcore
import httpx
import random
import pygubu

import tkinter as tk
from tkinter import ttk

import datetime as dt

from nextcloud_async import NextCloudAsync
from nextcloud_async.exceptions import NextCloudNotModified

from .constants import PROJECT_PATH, PROJECT_UI
from .logs import Logger


class Room(object):

    def __init__(
            self,
            nca: NextCloudAsync,
            loop: asyncio.BaseEventLoop,
            logger: Logger,
            notebook: ttk.Notebook,
            data: dict):

        self.__dict__.update(data)
        self.nca = nca
        self.loop = loop
        self.logger = logger
        self.notebook = notebook
        self.new_msgs = asyncio.Queue()

        self.last_read = 0
        self.last_common_read = 0

        self.update_interval = 30
        self.update_fudge = 0.15

        self.last_message_date = 0

        self.builder = builder = pygubu.Builder()
        builder.add_resource_path(PROJECT_PATH)
        builder.add_from_file(PROJECT_UI / 'room_tab.ui')

        self.frame = tk.Frame()
        self.tab = builder.get_object('room_tab', self.frame)
        self.frame.rowconfigure(0, weight=1)
        self.frame.columnconfigure(0, weight=1)

        self.builder.connect_callbacks(self)

        self.room_text = tk.Text(self.builder.get_object('chat_scroll'), wrap='word')
        self.user_list = tk.Text(self.builder.get_object('userlist_scroll'), wrap='word')
        self.builder.get_object('chat_scroll').add_child(self.room_text)
        self.builder.get_object('userlist_scroll').add_child(self.user_list)

        self.prepopulate_task = self.loop.create_task(self.prepopulate_latest_chat())
        self.receive_messages_task = self.loop.create_task(self.receive_messages_loop())
        self.process_messages_task = self.loop.create_task(self.process_new_messages_loop())

    @property
    def widget(self):
        return self.frame

    @property
    def this_tab(self):
        """Return widget representing tab this room.

        Raises:
            NextCloudNotFound: If room tab not found (Eek!)

        Returns:
        """
        for tab in self.notebook.tabs():
            tab_name = self.notebook.tab(tab, 'text')
            if tab_name == self.displayName:
                return tab

    def tab_configure(self, **kwargs):
        self.notebook.tab(self.this_tab, **kwargs)

    async def prepopulate_latest_chat(self):
        await self.receive_messages(look_into_future=0, limit=200)
        self.loop.remove(self.prepopulate_task)

    async def receive_messages_loop(self):
        while True:
            # Fudge the room refresh interval so we don't make a bunch
            # of requests all at once.
            randomized_sleep_interval = (
                self.update_interval + (
                    random.random() * self.update_fudge
                    * self.update_interval * random.choice([-1, 1])))
            await asyncio.sleep(randomized_sleep_interval)

            try:
                await self.receive_messages(timeout=1)
            except httpx.RemoteProtocolError:
                await self.logger.log(
                    f'{self.displayName}: Server disconnected without response.')

    async def receive_messages(
            self,
            look_into_future: bool = True,
            limit: int = 0,
            timeout: int = 0):
        await self.logger.log(f'Pulling messages for {self.displayName}')

        try:
            response, headers = await self.nca.get_conversation_messages(
                token=self.token,
                look_into_future=look_into_future,
                timeout=timeout,
                last_known_message=self.last_read,
                set_read_marker=False,
                limit=limit)
        except NextCloudNotModified:
            response, headers = [], {}
        except httpcore.RemoteProtocolError:
            self.logger.log(f'{self.displayName} - Server closed connection prematurely.')
        else:
            self.last_read = headers['X-Chat-Last-Given']
            self.last_common_read = headers['X-Chat-Last-Common-Read']

        for msg in sorted(response, key=lambda x: x['timestamp']):
            await self.new_msgs.put(msg)

        await self.logger.log(
            f'Received {self.new_msgs.qsize()} for {self.displayName}')

    async def insert_new_message(self, msg):
        self.room_text.configure(state='normal')
        self.room_text.insert(tk.INSERT, msg)
        self.room_text.configure(state='disabled')
        self.room_text.update()
        self.room_text.see(tk.END)

    async def process_new_messages_loop(self):
        while True:
            while msg := await self.new_msgs.get():
                msg_dt = dt.datetime.fromtimestamp(msg['timestamp'])
                msg_timestamp = msg_dt.strftime(r'%H:%M:%S')

                if msg_dt.strftime(r'%d') != self.last_message_date:
                    await self.insert_new_message(f'\n---{msg_dt.strftime(r"%Y-%m-%d")}---\n')

                line = f'({msg_timestamp}) {msg["actorDisplayName"]}: {msg["message"]}\n'
                await self.insert_new_message(line)
                self.last_read = msg['id']
                self.last_message_date = msg_dt.strftime(r'%d')
                self.tab_configure(state='normal')

            await asyncio.sleep(1/120)

    def close_tab(self):
        self.loop.remove(self.receive_messages_task)
        self.loop.remove(self.process_messages_task)
