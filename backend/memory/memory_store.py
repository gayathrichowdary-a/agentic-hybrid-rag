import json
import os
from datetime import datetime


class MemoryStore:
    def __init__(self, path="memory/memory.json"):
        self.path = path

        folder = os.path.dirname(self.path)

        if folder:
            os.makedirs(folder, exist_ok=True)

        self.memory = self.load_memory()

    def load_memory(self):
        if not os.path.exists(self.path):
            return []

        try:
            with open(self.path, "r", encoding="utf-8") as file:
                return json.load(file)

        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def add_memory(self, user_query, response):
        self.memory.append(
            {
                "time": str(datetime.now()),
                "query": user_query,
                "response": response
            }
        )

        # Keep only recent 50 messages
        self.memory = self.memory[-50:]

        self.save()

    def search_memory(self, query):
        return [
            item for item in self.memory
            if query.lower() in item["query"].lower()
        ]

    def clear_memory(self):
        self.memory = []
        self.save()

    def save(self):
        with open(self.path, "w", encoding="utf-8") as file:
            json.dump(self.memory, file, indent=2, ensure_ascii=False)