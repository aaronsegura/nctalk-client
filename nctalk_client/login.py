import httpx
import json
import os
import stat

import nextcloud_async

import platformdirs as pdir

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox


class LoginWindow(object):

    def __init__(
            self,
            master: tk.Tk,
            user: str = None,
            password: str = None,
            endpoint: str = None):
        """Present the Login window."""
        self.master = master

        self.user = tk.StringVar(value=user)
        self.password = tk.StringVar(value=password)
        self.endpoint = tk.StringVar(value=endpoint)
        self.remember_me = tk.BooleanVar(
            value=True if self.user.get() != '' or
            self.endpoint.get() != '' else False)

        self.window = tk.Toplevel()
        self.window.title('Nextcloud Login')
        self.window.attributes('-topmost', True)
        self.window.bind('<Escape>', lambda _: self.master.close())

    async def start(self):
        frame = ttk.Frame(self.window)
        frame.pack(pady=5)

        endpoint_label = ttk.Label(frame, text='Endpoint:')
        endpoint_input = tk.Entry(frame, width=40, textvariable=self.endpoint)
        endpoint_input.bind("<Tab>", self.next_widget)
        endpoint_label.grid(row=1, column=0, sticky='e')
        endpoint_input.grid(row=1, column=1, columnspan=2, padx=10)

        user_label = ttk.Label(frame, text='Username:')
        user_input = tk.Entry(frame, width=40, textvariable=self.user)
        user_input.bind("<Tab>", self.next_widget)
        user_label.grid(row=2, column=0, sticky='e')
        user_input.grid(row=2, column=1, columnspan=2, padx=10)

        password_label = ttk.Label(frame, text='Password:')
        password_input = tk.Entry(frame, width=40, textvariable=self.password, show='*')
        password_input.bind('<Tab>', self.next_widget)
        password_label.grid(row=3, column=0, sticky='e')
        password_input.grid(row=3, column=1, columnspan=2, padx=10)

        self.remember_me_check = tk.Checkbutton(
            frame,
            text='Remember me',
            onvalue=True,
            offvalue=False,
            var=self.remember_me)
        self.remember_me_check.grid(row=4, column=1, columnspan=2, sticky='w')

        self.login_button = ttk.Button(frame, text='Login')
        self.login_button.bind('<Return>', lambda _: self.nextcloud_login())
        self.login_button.grid(row=5, column=2, sticky='e', pady=5, padx=10)

        self.quit_button = ttk.Button(frame, text='Quit', command=lambda: self.master.close())
        self.quit_button.bind('<Return>', lambda _: self.master.close())
        self.quit_button.grid(row=5, column=0, sticky='e', pady=5, padx=10)

        self.login_button['command'] = lambda: self.nextcloud_login()
        user_input.bind('<Return>', lambda _: self.nextcloud_login())
        password_input.bind('<Return>',
                            lambda _: self.nextcloud_login())
        endpoint_input.bind('<Return>',
                            lambda _: self.nextcloud_login())

        # Give proper Entry() input the focus, depending on
        # what information is already available
        if not self.endpoint.get():
            endpoint_input.focus()
        elif not self.user.get():
            user_input.focus()
        else:
            password_input.focus()

    def next_widget(self, event):
        event.widget.tk_focusNext().focus()
        return("break")

    async def save_credentials(self):
        config = {
            'user': self.user.get(),
            'endpoint': self.endpoint.get()
        }
        config_dir = pdir.user_config_path('nctalk')
        config_file = f'{config_dir}/credentials.json'
        if not config_dir.exists():
            config_dir.mkdir(parents=True, mode=stat.S_IRWXU)
        with open(config_file, 'w') as fp:
            fp.write(json.dumps(config))
        os.chmod(config_file, stat.S_IREAD | stat.S_IWRITE)

    def nextcloud_login(self):
        self.master.loop.create_task(self.__nextcloud_login())

    async def __nextcloud_login(self):
        self.login_button['state'] = 'disabled'
        self.quit_button['state'] = 'disabled'

        await self.master.log(f'Logging in to {self.endpoint.get()}')
        self.nct = nextcloud_async.NextCloudAsync(
            client=httpx.AsyncClient(timeout=10),
            user=self.user.get(),
            password=self.password.get(),
            endpoint=self.endpoint.get())

        try:
            await self.nct.get_user()
        except nextcloud_async.exceptions.NextCloudException as e:
            messagebox.showerror(title='Login Failure', message=e)
            self.login_button['state'] = 'normal'
            self.quit_button['state'] = 'normal'
        except (httpx.ConnectError, httpx.UnsupportedProtocol):
            messagebox.showerror(
                title='Connection Error',
                message=f'Unable to connect to {self.endpoint.get()}')
            self.login_button['state'] = 'normal'
            self.quit_button['state'] = 'normal'
        else:
            await self.master.log(r'Success!')
            self.master.logged_in = True
            self.master.nct = self.nct
            if self.remember_me:
                await self.save_credentials()
            self.window.destroy()
