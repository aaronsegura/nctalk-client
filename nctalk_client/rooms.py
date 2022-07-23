import asyncio
import httpcore
import httpx

import tkinter as tk

import datetime as dt

from tkinter import ttk, DISABLED, NORMAL
from tkinter.scrolledtext import ScrolledText

from nextcloud_async.exceptions import NextCloudNotModified


class Room(object):

    def __init__(self, master: tk.Tk, data: dict):

        self.__dict__.update(data)

        self.ncs = master.nct
        self.master = master
        self.new_msgs = asyncio.Queue()

        self.last_read = 0
        self.last_common_read = 0

        self.update_interval = 30
        self.last_message_date = 0

        frame = ttk.Frame(self.master.room_tabs)
        frame.grid(row=0, column=0)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=0)
        frame.rowconfigure(1, weight=1)

        control_frame = ttk.Frame(frame)
        control_frame.grid(row=0, column=0, sticky='ew')
        control_frame.columnconfigure(0, weight=1)
        control_frame.rowconfigure(0, weight=0)

        quit_button = ttk.Button(control_frame, text='Leave')
        quit_button.grid(row=0, column=0, sticky='w')

        self.room_text = ScrolledText(frame, state=DISABLED, wrap=tk.WORD)
        self.room_text.grid(row=1, column=0, sticky='news')
        self.room_text.columnconfigure(0, weight=1)
        self.room_text.rowconfigure(1, weight=1)

        self.master.room_tabs.add(frame, text=self.displayName)
        self.master.room_tabs.update()

        self.master.loop.create_task(self.initialize_room())
        self.master.loop.create_task(self.receive_messages_loop())
        self.master.loop.create_task(self.process_new_messages_loop())

    async def initialize_room(self):
        await self.receive_messages(look_into_future=0, limit=200)

    async def receive_messages_loop(self):
        while True:
            await asyncio.sleep(self.update_interval)
            try:
                await self.receive_messages(timeout=1)
            except httpx.RemoteProtocolError:
                await self.master.log(f'{self.displayName}: Server disconnected without response.')

    async def receive_messages(
            self,
            look_into_future: bool = True,
            limit: int = 0,
            timeout: int = 0):
        await self.master.log(f'Pulling messages for {self.displayName}')

        try:
            response, headers = await self.master.nct.get_conversation_messages(
                token=self.token,
                look_into_future=look_into_future,
                timeout=timeout,
                last_known_message=self.last_read,
                set_read_marker=False,
                limit=limit)
        except NextCloudNotModified:
            response, headers = [], {}
        except httpcore.RemoteProtocolError:
            self.master.log(f'{self.displayName} - Server closed connection prematurely.')
        else:
            self.last_read = headers['X-Chat-Last-Given']
            self.last_common_read = headers['X-Chat-Last-Common-Read']

        for msg in sorted(response, key=lambda x: x['timestamp']):
            await self.new_msgs.put(msg)

        await self.master.log(
            f'Received {self.new_msgs.qsize()} for {self.displayName}')

    async def insert_new_message(self, msg):
        self.room_text.configure(state=NORMAL)
        self.room_text.insert(tk.INSERT, msg)
        self.room_text.configure(state=DISABLED)
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

            await asyncio.sleep(1/120)
