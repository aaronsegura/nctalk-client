import asyncio
import logging

import datetime as dt
import tkinter as tk


class Logger:

    queue = asyncio.Queue()
    lock = asyncio.Lock()

    def __init__(self, log_widget):
        self.log_widget = log_widget

    async def log(self, text: str, level: int = logging.INFO):
        """Write a message to the application log window and console."""
        # TODO: Level filtering / debug output
        # TODO: Text colors based on log level
        now = dt.datetime.now().strftime(r'%Y/%m/%d %H:%M:%S')
        line = f'{now} - {text}'
        await self.queue.put(line)

    async def process_queue(self):
        """Process logs put into the queue."""
        while logmsg := await self.queue.get():
            async with self.lock:
                self.log_widget.config(state='normal')
                self.log_widget.insert(tk.INSERT, f'{logmsg}\n')
                self.log_widget.config(state='disabled')
                self.log_widget.update()
                self.log_widget.see(tk.END)
                print(logmsg)
