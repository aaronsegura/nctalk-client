import asyncio


class TaskManager:

    def __init__(self, event_loop: asyncio.BaseEventLoop):
        self.event_loop: asyncio.BaseEventLoop = event_loop
        self.tasks: list = []
        self.create_task(self.check_for_exceptions())

    async def check_for_exceptions(self):
        while True:
            await asyncio.sleep(1)
            for task in self.tasks:
                if task.done():
                    try:
                        e: Exception = task.exception()
                    except asyncio.CancelledError:
                        pass
                    else:
                        if e:
                            print("Exception:", task.name, str(e))

    def create_task(self, task):
        new_task = self.event_loop.create_task(task)
        self.tasks.append(new_task)
        return new_task

    def remove(self, task):
        if not task.done():
            task.cancel()
        self.tasks.remove(task)

    def shutdown(self):
        for task in self.tasks:
            task.cancel()
        self.stop()

    def stop(self):
        self.event_loop.stop()

    def close(self):
        self.event_loop.close()
