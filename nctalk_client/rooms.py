import asyncio
import httpcore
import httpx
import random
import pygubu

import datetime as dt
import tkinter as tk
from tkinter import ttk

import pygubu.widgets.simpletooltip as tooltip

from typing import Dict, Any

from nextcloud_async import NextCloudAsync
from nextcloud_async.exceptions import NextCloudNotModified

from .icons import Icons
from .constants import PROJECT_PATH, PROJECT_UI
from .logs import Logger


class Room(object):

    __update_interval: int = 30

    def __init__(
            self,
            nca: NextCloudAsync,
            loop: asyncio.BaseEventLoop,
            logger: Logger,
            notebook: ttk.Notebook,
            user: Dict[str, Any],
            data: Dict[str, Any]):

        self.__dict__.update(data)
        self.nca = nca
        self.loop = loop
        self.logger = logger
        self.notebook = notebook

        self.user = user

        self.icons = Icons()
        self.msg_queue = asyncio.Queue()

        self.last_read = 0
        self.last_common_read = 0

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
        self.user_list = tk.Listbox(self.builder.get_object('userlist_scroll'))
        self.user_list.insert(tk.END, "Updating...")

        self.builder.get_object('chat_scroll').add_child(self.room_text)
        self.builder.get_object('userlist_scroll').add_child(self.user_list)

        self.text_entry: tk.Text = self.builder.get_object('text_entry')

        self.initialize_task = self.loop.create_task(self.initialize_room())
        self.receive_messages_task = self.loop.create_task(self.receive_messages_loop())
        self.process_messages_task = self.loop.create_task(self.process_new_messages_loop())

    @property
    def update_interval(self):
        return self.__update_interval

    @update_interval.setter
    def update_interval(self, interval: int):
        if interval < self.__update_interval:
            self.loop.remove(self.receive_messages_task)
            self.loop.create_task(self.receive_messages(timeout=1))
            self.receive_messages_task = self.loop.create_task(self.receive_messages_loop())

        self.__update_interval = interval

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

    async def initialize_room(self):
        leave_button = self.builder.get_object('leave_button')
        leave_icon = await self.icons('power', 16)
        leave_button.configure(image=leave_icon)
        leave_button.image = leave_icon
        tooltip.create(leave_button, 'Leave room')

        await self.receive_messages(look_into_future=0, limit=200)
        self.loop.remove(self.initialize_task)

    async def update_participants(self):
        """Update the participants list."""
        await self.room_status('updating')
        await self.logger(f'[{self.displayName}] Updating participant list')

        participants = await self.nca.get_conversation_participants(
            self.token, include_status=True)

        self.user_list.delete(0, tk.END)
        for part in sorted(participants, key=lambda x: x['actorId']):
            self.user_list.insert(tk.END, part['actorId'])

        await self.room_status('healthy')

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
                await self.logger(
                    f'[{self.displayName}] Server disconnected without response.')
                await self.room_status('exception')

    async def receive_messages(
            self,
            look_into_future: bool = True,
            limit: int = 0,
            timeout: int = 0):
        await self.logger(f'[{self.displayName}] Polling for new messages')
        await self.room_status('updating')

        raised = False
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
            self.logger(f'[{self.displayName}] Server closed connection prematurely.')
            raised = True
            await self.room_status('exception')
        else:
            self.last_read = headers['X-Chat-Last-Given']
            self.last_common_read = headers['X-Chat-Last-Common-Read']
        finally:
            if not raised:
                await self.room_status('healthy')
            else:
                await self.logger(f'[{self.displayName}] Setting exception health')

        for msg in sorted(response, key=lambda x: x['timestamp']):
            await self.msg_queue.put(msg)

    async def process_new_messages_loop(self):
        while True:
            while msg := await self.msg_queue.get():
                msg_dt = dt.datetime.fromtimestamp(msg['timestamp'])
                msg_timestamp = msg_dt.strftime(r'%H:%M:%S')

                if msg_dt.strftime(r'%d') != self.last_message_date:
                    await self.insert_new_message(f'\n---{msg_dt.strftime(r"%Y-%m-%d")}---\n')

                line = f'({msg_timestamp}) {msg["actorDisplayName"]}: {msg["message"]}\n'
                await self.insert_new_message(line)
                self.last_read = msg['id']
                self.last_message_date = msg_dt.strftime(r'%d')
                self.tab_configure(state='normal')
                # if self.displayName == 'Precision RV':
                #     print(msg)

            await asyncio.sleep(1/120)

    async def insert_new_message(self, msg):
        self.room_text.configure(state='normal')
        self.room_text.insert(tk.INSERT, msg)
        self.room_text.configure(state='disabled')
        self.room_text.update()
        self.room_text.see(tk.END)

    async def room_status(self, level: str):
        status_label: ttk.Label = self.builder.get_object('status_label')
        match level:
            case 'healthy':
                state_img = await self.icons('healthy', 16)
            case 'updating':
                state_img = await self.icons('updating', 16)
            case 'exception':
                state_img = await self.icons('exception', 16)

        status_label.configure(image=state_img)
        status_label.image = state_img
        status_label.update()

    def send_message(self, _):
        """Send the user's message to the server.

        Returns
        -------
            _type_: _description_
        """
        message = self.text_entry.get('1.0', tk.END).strip()
        self.text_entry.mark_set(tk.INSERT, "1.0")
        self.text_entry.delete('1.0', tk.END)
        asyncio.gather(self.nca.send_to_conversation(self.token, message))
        asyncio.gather(self.receive_messages(look_into_future=1))
        return 'break'

    def insert_newline(self, e):
        """This function intentionally left blank."""
        pass

    def close_tab(self):
        self.loop.remove(self.receive_messages_task)
        self.loop.remove(self.process_messages_task)
