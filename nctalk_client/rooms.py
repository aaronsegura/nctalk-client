import tkinter as tk

from nctalk.api import Conversation


class Room(object):

    def __init__(self, master, conversation: Conversation):
        self.conversation = conversation
        self.frame = tk.Frame(master)
