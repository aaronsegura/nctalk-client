"""Nextcloud Talk Client."""

import asyncio
import logging
import platformdirs as pdir
import json

import datetime as dt
import tkinter as tk

from tkinter import DISABLED, NORMAL, ttk
from tkinter.scrolledtext import ScrolledText

from .login import LoginWindow
from .rooms import Room
from .menu import MenuBar


class MyApp(tk.Tk):
    """A tkinter-based application for NextCloud Talk interaction."""

    _LOG_TAB_NAME = '#logs'

    def __init__(self, loop: asyncio.BaseEventLoop, interval: float = 1/120):
        super().__init__()

        self.logs = asyncio.Queue()

        self.nct = None
        self.logged_in = False

        self.rooms = []

        self.loop = loop
        self.tasks = [
            loop.create_task(self.mainloop(interval)),
            loop.create_task(self.watch_for_logs())]

        self.protocol("WM_DELETE_WINDOW", self.close)

    def run(self):
        self.loop.create_task(self.main_window())
        self.loop.run_forever()

    def load_config(self) -> dict:
        """Load cloud information from config file, if one exists."""

        config_dir = pdir.user_config_path("nctalk")
        if not config_dir.exists():
            return {}

        config_file = f'{config_dir}/credentials.json'

        try:
            with open(config_file, "r") as config_file:
                config = json.loads(config_file.read())
        except IOError:
            config = {}

        return config

    async def mainloop(self, interval: float = 1/120):
        while True:
            self.update()
            await asyncio.sleep(interval)

    async def log(self, text: str, level: int = logging.INFO):
        """Write a message to the application log window and console."""
        # TODO: Level filtering / debug output
        # TODO: Text colors based on log level
        now = dt.datetime.now().strftime(r'%Y/%m/%d %H:%M:%S')
        line = f'{now} - {text}'
        await self.logs.put(line)

    async def watch_for_logs(self):
        while logmsg := await self.logs.get():
            self.applog.config(state=NORMAL)
            self.applog.insert(tk.INSERT, f'{logmsg}\n')
            self.applog.config(state=DISABLED)
            self.applog.update()
            self.applog.see(tk.END)
            print(logmsg)

    async def main_window(self):
        """The main application window."""
        self.title('Nextcloud Talk')
        self.bind('<Control-q>', lambda event: self.close())

        frame = ttk.Frame(self)
        frame.pack(fill='both', expand=True)

        self.app_config = self.load_config()

        self.config(menu=MenuBar(self))

        if not self.logged_in:
            login_window = LoginWindow(self, **self.app_config)
            login_window.window.protocol("WM_DELETE_WINDOW", self.close)
            await login_window.start()
            self.loop.create_task(self.wait_for_auth())

        self.room_tabs = ttk.Notebook(frame)
        self.room_tabs.pack(fill='both', expand=True)
        self.room_tabs.enable_traversal()
        self.room_tabs.bind("<<NotebookTabChanged>>", self.room_tab_changed)

        self.applog = ScrolledText(self.room_tabs, height=50, width=120)
        self.applog.pack(fill='both', expand=True, padx=1, pady=1)

        self.room_tabs.add(self.applog, text=self._LOG_TAB_NAME)

        await self.log("Startup")

    async def wait_for_auth(self):
        """Wait for LoginWindow() to populate the NextCloudTalk client."""
        while not self.nct:
            await asyncio.sleep(1/5)
        else:
            await self.initialize_rooms()

    def room_tab_changed(self, event):
        current_tab_id = self.room_tabs.index('current')
        current_tab_name = self.room_tabs.tab(current_tab_id, 'text')

        for x in self.rooms:
            if x.displayName == current_tab_name:
                x.update_interval = 5
                self.loop.create_task(x.receive_messages(timeout=1))
            else:
                x.update_interval = 30

    async def initialize_rooms(self):
        """Open tabs for each room and initialize Room objects."""
        await self.log('Fetching active rooms...')
        rooms = await self.nct.get_conversations()

        for c in rooms:
            await self.log(f'Joining room "{c["displayName"]}"')
            self.loop.create_task(self.new_room(c))

    async def new_room(self, data):
        self.rooms.append(Room(self, data))

    def close(self):
        for task in self.tasks:
            task.cancel()
        self.loop.stop()
        self.destroy()
        return True
