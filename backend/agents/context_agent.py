class ContextAgent:

    def build_context(self, chat_history):

        context = ""

        for chat in chat_history[-5:]:

            context += f"""
User:
{chat['query']}

Assistant:
{chat['answer']}
"""

        return context