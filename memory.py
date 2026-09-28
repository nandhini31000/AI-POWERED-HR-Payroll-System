from collections import defaultdict


class ConversationMemory:

    def __init__(self):

        self.memory = defaultdict(list)

    def add_message(self, user_id, role, message):

        self.memory[user_id].append({

            "role": role,

            "content": message

        })

        if len(self.memory[user_id]) > 10:

            self.memory[user_id] = self.memory[user_id][-10:]

    def get_history(self, user_id):

        return self.memory[user_id]

    def clear(self, user_id):

        self.memory[user_id] = []


memory = ConversationMemory()