import asyncio


class TaskManager:

    def __init__(self, event_loop: asyncio.BaseEventLoop):
        self.event_loop = event_loop
        self.tasks: list = []

    def create_task(self, task):
        new_task = self.tasks.append(self.event_loop.create_task(task))
        return new_task

    def remove(self, task):
        self.tasks.remove(task)

    def shutdown(self):
        for task in self.tasks:
            task.cancel()

    def stop(self):
        self.event_loop.stop()

    def close(self):
        self.event_loop.close()
