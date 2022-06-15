"""Run the Jewels."""

from . import app
import asyncio


def run():
    myapp = app.MyApp(asyncio.get_event_loop())
    myapp.run()
