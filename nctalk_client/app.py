import asyncio
import logging

import datetime as dt
import tkinter as tk

from tkinter import DISABLED, NORMAL, ttk
from tkinter.scrolledtext import ScrolledText

from nctalk_client.login import LoginWindow
from nctalk_client.rooms import Room


class MyApp(tk.Tk):

    def __init__(self, loop: asyncio.BaseEventLoop, interval: float = 1/120):
        super().__init__()

        # Set up the event loop
        self.nct = None  # NextCloudTalk client object
        self.logged_in = False

        self.rooms = []

        self.loop = loop
        self.tasks = [loop.create_task(self.mainloop(interval))]

        self.protocol("WM_DELETE_WINDOW", self.close)
        self.main_window()

    def run(self):
        self.loop.run_forever()

    async def mainloop(self, interval: float = 1/120):
        while True:
            self.update()
            await asyncio.sleep(interval)

    def log(self, text: str, level: int = logging.INFO):
        now = dt.datetime.now().strftime(r'%Y/%m/%d %H:%M:%S')
        line = f'{now} - {text}'
        self.applog['state'] = NORMAL
        self.applog.insert(tk.INSERT, f'{line}\n')
        self.applog['state'] = DISABLED
        self.applog.update()
        print(line)

    def main_window(self):
        """The main application window."""
        self.title('Nextcloud Talk')
        self.geometry('800x600')
        self.bind('<Control-q>', lambda event: self.close())

        frame = ttk.Frame(self)
        frame.pack(fill='both', expand=True)

        if not self.logged_in:
            # TODO: Remove these params
            login_window = LoginWindow(
                self,
                user='aaron',
                endpoint='https://cloud.aaronsegura.com'
            )
            login_window.window.protocol("WM_DELETE_WINDOW", self.close)
            self.loop.create_task(self.wait_for_auth())

        self.room_tabs = ttk.Notebook(frame)
        self.room_tabs.pack(fill='both', expand=True)

        applog_frame = ttk.Frame(self.room_tabs)
        applog_frame.pack(fill='both', expand=True)

        self.applog = ScrolledText(applog_frame, height=50, width=120)
        self.applog.pack(fill='both', expand=True, padx=1, pady=1)

        self.room_tabs.add(applog_frame, text='Talk Log')

        self.log("Startup")

    async def wait_for_auth(self):
        """Wait for LoginWindow() to populate the NextCloudTalk client."""
        while not self.nct:
            await asyncio.sleep(1/20)
        else:
            await self.initialize_rooms()

    def initialize_rooms(self):
        """Open tabs for each room and initialize Room objects."""
        self.log(f'Fetching rooms from {self.nct.url}')
        rooms = self.nct.conversation_list()

        for c in rooms:
            self.log(f'Joining room "{c.displayName}"')
            self.new_room(c)

    async def new_room(self, conversation):
        Room(conversation)

    def close(self):
        for task in self.tasks:
            task.cancel()
        self.loop.stop()
        self.destroy()
        return True
