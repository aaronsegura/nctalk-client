import asyncio

import tkinter as tk

from tkinter import ttk, DISABLED, NORMAL
from tkinter.scrolledtext import ScrolledText


class Room(object):

    def __init__(self, master: tk.Tk, data: dict):

        self.__dict__.update(data)

        self.ncs = master.nct
        self.master = master
        self.new_msgs = asyncio.Queue()
        self.msgs = set()

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

        self.master.loop.create_task(self.process_new_messages())
        self.master.loop.create_task(self.initialize_history())

    async def initialize_history(self):
        await self.receive_messages(self.token)

    async def receive_messages(
            self,
            token: str,
            look_into_future: bool = False,
            limit: int = 50):
        await self.master.log(f'Pulling messages for {self.displayName}')

        response = await self.master.nct.get_conversation_messages(
            token=token,
            look_into_future=look_into_future,
            limit=limit)

        for msg in sorted(response, key=lambda x: x['timestamp']):
            await self.new_msgs.put(msg)

        await self.master.log(
            f'Received {self.new_msgs.qsize()} for {self.displayName}')

    async def process_new_messages(self):
        while True:
            while msg := await self.new_msgs.get():
                self.room_text.configure(state=NORMAL)
                line = f'{msg["timestamp"]} {msg["actorDisplayName"]}: {msg["message"]}\n'
                self.room_text.insert(tk.INSERT, line)
                # self.msgs.add(msg)
                self.room_text.configure(state=DISABLED)
                self.room_text.update()
                self.room_text.see(tk.END)

            await asyncio.sleep(1/20)
