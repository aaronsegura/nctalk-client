import os
import stat
import aiofiles
import hashlib

from io import BytesIO

import platformdirs as pdir

from PIL import ImageTk, Image as ImagePIL

from nextcloud_async import NextCloudAsync


class Image:

    def __init__(self):
        self.cache_path = pdir.user_cache_path('nctalk/images')
        self.cache_path.mkdir(parents=True, exist_ok=True, mode=stat.S_IRWXU)

    async def __call__(self, *args, **kwargs):
        return await self.load_image(*args, **kwargs)

    @property
    def hashed_cache_directory(self):
        hash_dirs: str = ''
        for x in range(0, 12, 2):
            hash_dirs = f'{hash_dirs}/{self.sha256[x:x+2]}'.strip('/')

        return self.cache_path / hash_dirs

    @property
    def hashed_cache_filename(self):
        return self.hashed_cache_directory / self.sha256

    def __in_cache(self, height: int = 0):
        if height == 0:
            return os.path.exists(self.hashed_cache_filename)
        else:
            return os.path.exists(f'{self.hashed_cache_filename}_{height}')

    def __cache_mkdir(self):
        self.hashed_cache_directory.mkdir(parents=True, exist_ok=True, mode=stat.S_IRWXU)

    async def __write_cache_file(self, data):
        async with aiofiles.open(self.hashed_cache_filename, mode='wb') as image_fp:
            await image_fp.write(data)

    async def from_url(self, nca: NextCloudAsync, url: str) -> None:
        """Save image from URL."""
        self.sha256 = hashlib.sha256(bytes(url, 'utf-8')).hexdigest()
        response = await nca.request(method='GET', url=url)
        self.__cache_mkdir()
        await self.__write_cache_file(response.content)

    async def from_file(self, nca: NextCloudAsync, path: str) -> None:
        """Save image from NextCloud path."""
        self.sha256 = hashlib.sha256(bytes(f'{nca.endpoint}/{path}', 'utf-8')).hexdigest()

        if self.__in_cache():
            return

        image = await nca.download_file(path)
        self.__cache_mkdir()
        await self.__write_cache_file(image)

    def image(self, height: int = 0) -> ImageTk:
        """Return sized image from hashed disk cache.

        Returns:
            tk.PhotoImage: Image data

        """
        if height == 0:
            return ImageTk.PhotoImage(ImagePIL.open(self.hashed_cache_filename))
        else:
            if self.__in_cache(height=height):
                return ImageTk.PhotoImage(
                    ImagePIL.open(f'{self.hashed_cache_filename}_{height}'))
            else:
                full_size_image = ImagePIL.open(self.hashed_cache_filename)
                if height < full_size_image.height:
                    height_ratio = full_size_image.height / height
                    new_width = int(full_size_image.width / height_ratio)
                    resized_image = full_size_image.resize(size=(new_width, height))
                    resized_image.save(f'{self.hashed_cache_filename}_{height}', format='PNG')
                    return ImageTk.PhotoImage(resized_image)
                else:
                    return ImageTk.PhotoImage(ImagePIL.open(self.hashed_cache_filename))

    @property
    async def thumbnail(self):
        """Load full-sized PNG image from project directory.

        Args
        ----
            image_name (str): Icon basename, without .png extension

            size (int): Size squared

        Returns
        -------

        """
        with BytesIO() as buffer:
            async with aiofiles.open(self.hashed_cache_filename, mode='rb') as image_fp:
                buffer.write(await image_fp.read())
                buffer.seek(0)
                pil_image = ImagePIL.open(buffer, formats=['PNG'])
                resized_image = pil_image.resize(size=())
                tk_image = ImageTk.PhotoImage(resized_image)
                return tk_image
