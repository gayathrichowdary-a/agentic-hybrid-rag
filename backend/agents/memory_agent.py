from llm.groq_llm import generate_answer


class MemoryAgent:

    def should_store(self, conversation):

        prompt = f"""
You are a Memory Agent.

Conversation:

{conversation}

Should this be remembered?

Answer ONLY

YES

or

NO
"""

        answer = generate_answer(prompt).strip().upper()

        return answer == "YES"

    def extract_memory(self, conversation):

        prompt = f"""
Extract useful memory.

Conversation

{conversation}

Return one sentence only.
"""

        return generate_answer(prompt).strip()