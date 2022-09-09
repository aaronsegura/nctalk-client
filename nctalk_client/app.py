"""Nextcloud Talk Client."""

import asyncio
import pygubu

from tkinter import ttk, font as tkfont

from nextcloud_async import NextCloudAsync

from .config import NCTalkConfiguration
from .logs import Logger
from .login import LoginWindow
from .rooms import Room
from .task_manager import TaskManager
from .preferences import PreferencesWindow
from .constants import PROJECT_PATH, PROJECT_UI, UPDATE_INTERVAL

try:
    import ttkthemes
except ModuleNotFoundError:
    HAS_TTKTHEMES = False
else:
    HAS_TTKTHEMES = True


class NCTalkApp():

    nca: NextCloudAsync = None
    logger: Logger = None

    def __init__(self, loop: asyncio.BaseEventLoop, master=None):

        self.rooms = []
        self.loop = TaskManager(loop)

        self.master = master
        self.app_config = NCTalkConfiguration()
        self.nca = None
        self.tasks = [
            self.loop.create_task(self.updater())]

    async def run(self):
        self.start_app()

    def start_app(self):
        self.builder = builder = pygubu.Builder()
        builder.add_resource_path(PROJECT_PATH)
        builder.add_from_file(PROJECT_UI / 'app.ui')

        # Load the main app window
        self.window = self.builder.get_object('main_window', self.master)
        builder.connect_callbacks(self)

        # Set up theme
        if HAS_TTKTHEMES:
            self.style = ttkthemes.ThemedStyle()
        else:
            self.style = ttk.Style()

        # Set user-defined theme, if available
        user_selected_theme = self.app_config.get('theme', 'default')
        self.style.theme_use(user_selected_theme)

        self.font = tkfont.nametofont('TkDefaultFont')
        self.font.configure(size=self.app_config.get('font_size', '11'))

        # Prepare the logging subsystem
        self.applog = self.builder.get_object('applog', self.master)
        self.logger = Logger(self.applog)
        self.tasks.append(
            self.loop.create_task(self.logger.process_queue()))

        # Catch window manager close event
        self.window.protocol('WM_DELETE_WINDOW', self.close)

        # Set up notebook for chat rooms
        self.room_tabs = self.builder.get_object('rooms_notebook')
        self.room_tabs.enable_traversal()

        # Present login window
        self.login_window = LoginWindow(self.loop, self.logger)

        # Save auth task for removal later
        self.auth_task = self.loop.create_task(self.wait_for_auth())
        self.tasks.append(self.auth_task)

    async def updater(self):
        """Iterate over the asyncio event loop."""
        while True:
            self.window.update()
            await asyncio.sleep(UPDATE_INTERVAL)

    async def wait_for_auth(self):
        """Wait for LoginWindow() to populate the NextCloudTalk client."""
        while not self.login_window.logged_in:
            if not self.login_window.window_open:
                # Shut everything down if the login window is closed and we're
                # not logged in yet
                self.close()
            await asyncio.sleep(1/12)
        else:
            # Upon login, remove the wait_for_auth task from the event loop, pull
            # the NextCloudAsync client from login_window, and free up the memory
            # used by login_window.
            self.tasks.remove(self.auth_task)
            self.nca = self.login_window.nca
            self.user = self.login_window.user
            self.login_window = None
            await self.initialize_rooms()

    async def initialize_rooms(self):
        """Open tabs for each room and initialize Room objects."""
        await self.logger('Fetching active rooms...')
        rooms = await self.nca.get_conversations()

        for c in rooms:
            await self.logger(f'Joining room "{c["displayName"]}"')
            self.loop.create_task(self.new_room(c))

    async def new_room(self, data):
        room = Room(self.nca, self.loop, self.logger, self.room_tabs, self.user, data)
        self.rooms.append(room)
        self.room_tabs.add(room.widget, text=room.displayName, state='disabled')

    def room_tab_changed(self, e):
        current_tab_id = self.room_tabs.index('current')
        current_tab_name = self.room_tabs.tab(current_tab_id, 'text')

        for x in self.rooms:
            if x.displayName == current_tab_name:
                x.update_interval = 5
                asyncio.gather(x.update_participants())
            else:
                x.update_interval = 30

    def edit_preferences(self):
        self.preferences_window = PreferencesWindow(self.style, self.font)

    def close(self, _: None = None):
        self.loop.shutdown()
        self.window.destroy()
