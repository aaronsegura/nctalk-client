import httpx
import pygubu
import asyncio

from nextcloud_async import NextCloudAsync
from nextcloud_async.exceptions import NextCloudException

import tkinter as tk
from tkinter import messagebox

from typing import Dict, Any

from .config import NCTalkConfiguration
from .constants import PROJECT_PATH, PROJECT_UI
from .logs import Logger


class LoginWindow:

    nca: NextCloudAsync = None
    logged_in: bool = False

    def __init__(self, loop: asyncio.BaseEventLoop, logger: Logger):
        """Present the Login window."""
        self.master = None
        self.logger = logger
        self.loop = loop
        self.logged_in = False
        self.window_open = True

        self.user: Dict[str, Any] = {}

        # Load configuration from disk, if available
        self.app_config = NCTalkConfiguration()

        self.remember_me = tk.BooleanVar(value=False)

        self.builder = builder = pygubu.Builder()
        builder.add_resource_path(PROJECT_PATH)
        builder.add_from_file(PROJECT_UI / 'login.ui')

        # Build the login window and make sure it's on top.
        self.window = builder.get_object('login_window', self.master)
        self.builder.connect_callbacks(self)
        self.window.attributes('-topmost', True)
        builder.import_variables(
            self, ["endpoint", "username", "password", "remember_me"]
        )
        # Catch the window manager event for closing the window.
        self.window.protocol('WM_DELETE_WINDOW', self.close)

        # Pre-configure the login fields if information is available
        builder.tkvariables['endpoint'].set(self.app_config.get('endpoint', ''))
        builder.tkvariables['username'].set(self.app_config.get('user', ''))

        if self.app_config.get('user', '') != '' or \
                self.app_config.get('endpoint', '') != '':
            self.remember_me.set(True)

        # Give focus to the first blank widget
        if not self.app_config.get('endpoint', ''):
            builder.get_object('endpoint_entry').focus()
        elif not self.app_config.get('user', ''):
            builder.get_object('user_entry').focus()
        else:
            builder.get_object('password_entry').focus()

    def checkbutton_fix(self, event):
        """Remember Me checkbutton hack.

        If the user hits <Return> to log in while the Remember Me box has focus
        it will be toggled before the <Return> event on the TopLevel window runs
        nextcloud_login().  This function will switch it back to whatever
        state it was in before the user hit Return.
        """
        self.builder.get_object('remember_me_checkbutton').toggle()

    def close(self, _=None):
        """Shut it down."""
        self.window_open = False
        self.window.destroy()

    async def save_credentials(self):
        """Save the supplied credentials to a config file."""
        self.app_config['user'] = self.username
        self.app_config['endpoint'] = self.endpoint
        self.app_config.save_config()

    def nextcloud_login(self, _):
        """Spawn a job to attempt login to nextcloud."""
        self.loop.create_task(self.__nextcloud_login())

    async def __nextcloud_login(self):
        login_button = self.builder.get_object('login_button')
        cancel_button = self.builder.get_object('cancel_button')

        login_button['state'] = 'disabled'
        cancel_button['state'] = 'disabled'

        self.username = self.builder.tkvariables['username'].get()
        password = self.builder.tkvariables['password'].get()
        self.endpoint = self.builder.tkvariables['endpoint'].get()
        remember_me = self.builder.tkvariables['remember_me'].get()

        await self.logger.log(f'Logging in to {self.endpoint}')
        self.nca = NextCloudAsync(
            client=httpx.AsyncClient(timeout=10),
            user=self.username,
            password=password,
            endpoint=self.endpoint)

        try:
            self.user = await self.nca.get_user()
        except NextCloudException as e:
            await self.logger.log(f'Login failed: {e}')
            messagebox.showerror(title='Login Failure', message=e, parent=self.window)
            login_button['state'] = 'normal'
            cancel_button['state'] = 'normal'
        except (httpx.ConnectError, httpx.UnsupportedProtocol):
            messagebox.showerror(
                title='Connection Error',
                message=f'Unable to connect to {self.endpoint}', parent=self.window)
            login_button['state'] = 'normal'
            cancel_button['state'] = 'normal'
        else:
            await self.logger.log(r'Success!')
            self.logged_in = True

            if remember_me:
                await self.save_credentials()

            self.window.destroy()
