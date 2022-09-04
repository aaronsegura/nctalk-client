
import os
import stat
import aiofiles
import asyncio

from io import BytesIO

import platformdirs as pdir
import tkinter as tk

from PIL import Image, ImageTk

from .constants import PROJECT_ICONS


class Icons:

    icon_memory_cache = {}
    write_lock = asyncio.Lock()

    def __init__(self):
        self.cache_path = pdir.user_cache_path('nctalk/icons')
        self.cache_path.mkdir(parents=True, exist_ok=True, mode=stat.S_IRWXU)

    async def __call__(self, *args, **kwargs):
        return await self.load_icon(*args, **kwargs)

    async def load_icon(self, icon_name: str, size: int):
        """Return icon at proper size.

        Args:
            icon_name (str): Basename of icon, without extension.

            size (int): Width/Height of resized icon

        Returns:
            tk.PhotoImage: Image sized to Size x Size

        """
        icon_key = f'{icon_name}_{size}'
        if self.__in_memory_cache(icon_key):
            icon = tk.PhotoImage(data=self.icon_memory_cache[icon_key])
        elif self.__in_disk_cache(icon_key):
            icon = await self.__from_disk_cache(icon_key)
            await self.__save_to_memory_cache(icon_key)
        else:
            with BytesIO() as buffer:
                icon = await self.__sized_icon_from_disk(icon_name, size, buffer)
                await self.__save_to_disk_cache(icon_key, icon)
                await self.__save_to_memory_cache(icon_key)
        return icon

    def __in_memory_cache(self, icon_key: str):
        if icon_key in self.icon_memory_cache.keys():
            return True
        else:
            return False

    def __in_disk_cache(self, icon_key):
        if f'{icon_key}.png' in os.listdir(self.cache_path):
            return True
        else:
            return False

    async def __from_disk_cache(self, icon_key: str):
        icon_filename = f'{self.cache_path}/{icon_key}.png'
        return tk.PhotoImage(file=icon_filename)

    async def __sized_icon_from_disk(self, icon_name: str, size: int, buffer: BytesIO):
        """Load full-sized PNG icon from project directory.

        Args
        ----
            icon_name (str): Icon basename, without .png extension

            size (int): Size squared

        Returns
        -------

        """
        icon_filename = PROJECT_ICONS / f'{icon_name}.png'
        async with aiofiles.open(icon_filename, mode='rb') as icon_fp:
            buffer.write(await icon_fp.read())
            buffer.seek(0)
            pil_image = Image.open(buffer, formats=['PNG'])
            resized_image = pil_image.resize(size=(size, size))
            tk_img = self.__pil_to_tk(resized_image, buffer)
            return tk_img

    async def __save_to_disk_cache(self, icon_key: str, icon: Image):
        """Save resized icon to cache directory and memory cache.

        Args:
        ----
            icon_name (str): Basename of icon file, without .png extension

            size (int): Size of icon

            image (Image): Image to save

        """
        icon_filename = f'{self.cache_path}/{icon_key}.png'
        async with self.write_lock:
            icon.write(icon_filename, format='PNG')

    async def __save_to_memory_cache(self, icon_key: str):
        """Save image to memory cache.

        Image must already be stored in disk cache.

        Args:
        ----
            icon_key (str): Icon type and size

        """
        icon_filename = f'{self.cache_path}/{icon_key}.png'
        async with self.write_lock:
            async with aiofiles.open(icon_filename, mode='rb') as icon_fp:
                self.icon_memory_cache[icon_key] = await icon_fp.read()

    def __pil_to_tk(self, pil_image, buffer):
        buffer.seek(0)
        pil_image.save(buffer, format='PNG')
        buffer.seek(0)
        return tk.PhotoImage(data=buffer.read())
