"""Menu generator for nctalk."""

import tkinter as tk


class MenuBar(tk.Menu):

    def __init__(self, master):
        tk.Menu.__init__(self, master)

        self.master = master

        nctalk = tk.Menu(self, tearoff=False)
        nctalk.add_command(label="Room list")
        nctalk.add_command(label="Join room")
        nctalk.add_separator()
        nctalk.add_command(label="Quit (ctrl-Q)", underline=1, command=self.master.close)
        self.add_cascade(label="nctalk", underline=0, menu=nctalk)
