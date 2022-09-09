#!/usr/bin/python3
import tkinter as tk
import pygubu

from tkinter import ttk
from tkinter import font as tkfont
import ttkwidgets

from .config import NCTalkConfiguration
from .constants import PROJECT_PATH, PROJECT_UI


class PreferencesWindow:
    def __init__(self, style: ttk.Style, font: tkfont, master=None):

        self.app_config: NCTalkConfiguration = NCTalkConfiguration()
        self.style: ttk.Style = style
        self.font: tkfont = font

        # Import and build the UI
        self.builder: pygubu.Builder = pygubu.Builder()
        self.builder.add_resource_path(PROJECT_PATH)
        self.builder.add_from_file(PROJECT_UI / 'preferences.ui')

        self.window: tk.Toplevel = self.builder.get_object("preferences_window", master)

        # Set up empty variables for pygubu
        self.theme_list = None
        self.icon_size = None

        # Import variables, connect callbacks
        self.builder.import_variables(self, ["icon_size", "theme_list"])
        self.builder.connect_callbacks(self)

        # Configure variables
        self.theme_list.set(sorted(self.style.theme_names()))

        # Select the currently active theme
        theme_listbox: tk.Listbox = self.builder.get_object('theme_listbox')
        current_theme_index: int = theme_listbox.get(0, tk.END).index(self.style.theme_use())
        theme_listbox.select_set(current_theme_index)
        theme_listbox.see(current_theme_index)

        # Select the currently active icon size
        icon_combobox: ttk.Combobox = self.builder.get_object('icon_combobox')
        icon_combobox.set(self.app_config.get('icon_size', 16))

        # Select the currently active font size
        font_dropdown: ttkwidgets.FontSizeDropdown = \
            self.builder.get_object('font_size_dropdown')
        font_dropdown.set(self.app_config.get('font_size', 11))

    def fill_icon_sizes(self):
        icon_size_combobox: ttk.Combobox = self.builder.get_object('icon_combobox')
        icon_size_combobox.configure(values=[12, 16, 20, 24])

    def set_font_size(self, font_size):
        self.font.configure(size=font_size)

    def set_theme(self, event):
        listbox: tk.Listbox = self.builder.get_object('theme_listbox')
        theme = listbox.get(tk.ANCHOR)
        self.style.theme_use(theme)

    def save_preferences(self, event):
        self.app_config['theme'] = self.style.theme_use()
        self.app_config['font_family'] = self.font.cget('family')
        self.app_config['font_size'] = self.font.cget('size')
        self.app_config['icon_size'] = self.icon_size.get()
        self.app_config.save_config()
        self.window.destroy()
