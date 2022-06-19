import httpx

import nextcloud_aio

import tkinter as tk
from tkinter import ttk


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

        self.window = tk.Toplevel()
        self.window.title('Nextcloud Login')
        self.window.geometry('480x120')
        self.window.attributes('-topmost', True)
        self.window.bind('<Escape>', lambda _: self.master.close())

    async def start(self):
        frame = ttk.Frame(self.window)
        frame.pack(pady=5)

        endpoint_label = ttk.Label(frame, text='Endpoint:')
        endpoint_input = tk.Entry(frame, width=40, textvariable=self.endpoint)
        endpoint_input.bind("<Tab>", self.next_widget)
        endpoint_label.grid(row=1, column=0)
        endpoint_input.grid(row=1, column=1, columnspan=2)

        user_label = ttk.Label(frame, text='Username:')
        user_input = tk.Entry(frame, width=40, textvariable=self.user)
        user_input.bind("<Tab>", self.next_widget)
        user_label.grid(row=2, column=0)
        user_input.grid(row=2, column=1, columnspan=2)

        password_label = ttk.Label(frame, text='Password:')
        password_input = tk.Entry(frame, width=40, textvariable=self.password, show='*')
        password_input.bind('<Tab>', self.next_widget)
        password_label.grid(row=3, column=0)
        password_input.grid(row=3, column=1, columnspan=2)

        login_button = ttk.Button(frame, text='Login')
        login_button.bind('<Return>', lambda _: self.nextcloud_login())
        login_button.grid(row=4, column=2, sticky='e', pady=5)

        quit_button = ttk.Button(frame, text='Quit', command=lambda: self.master.close())
        quit_button.bind('<Return>', lambda _: self.master.close())
        quit_button.grid(row=4, column=0, sticky='e', pady=5)

        login_button['command'] = lambda: self.nextcloud_login()
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

    def nextcloud_login(self):
        self.master.loop.create_task(self.__nextcloud_login())

    async def __nextcloud_login(self):
        await self.master.log(f'Logging in to {self.endpoint.get()}')
        self.nct = nextcloud_aio.NextCloudAsync(
            client=httpx.AsyncClient(),
            user=self.user.get(),
            password=self.password.get(),
            endpoint=self.endpoint.get())

        if await self.nct.get_user():
            await self.master.log(r'Success!')
            self.master.logged_in = True
            self.master.nct = self.nct
            self.window.destroy()
