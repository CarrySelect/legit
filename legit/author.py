from datetime import datetime


class Author:
    def __init__(self, name: str, email: str, time: datetime) -> None:
        self.name: str = name
        self.email: str = email
        self.time: datetime = time

    def __str__(self) -> str:
        timestamp: str = self.time.strftime("%s %z")
        return f"{self.name} <{self.email}> {timestamp}"

