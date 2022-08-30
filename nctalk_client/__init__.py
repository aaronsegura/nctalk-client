"""Run the Jewels."""

from . import app
import asyncio


def run():
    loop = asyncio.get_event_loop()
    myapp = app.NCTalkApp(loop)
    asyncio.run(myapp.run())

    # Have to stop/run_forever to clean up canceled threads.
    # https://xinhuang.github.io/posts/2017-07-31-common-mistakes-using-python3-asyncio.html#orgc09f339
    # There's got to be a better way!
    loop.run_forever()
    loop.stop()
    loop.run_forever()
    loop.close()
