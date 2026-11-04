from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

def generate_answer(context, question=None):
    # MemoryAgent calls this with a single ready-made prompt
    if question is None:
        prompt = context
        return _ask(prompt)

    prompt = f"""
You are an intelligent document comparison agent.
The context may originate from PDFs, Word documents,
text files, spreadsheets, CSV files, or OCR extracted
from images.

Treat all sources equally and answer only from the
provided context.
Use ONLY the provided context.

Rules:
1. Use only the supplied context.
2. Never invent information.
3. If information is missing, say it is missing.
4. If multiple documents are involved, compare them.
5. Quote supporting evidence.
6. Give a final conclusion.

Context:
{context}

Question:
{question}

Answer:
"""

    return _ask(prompt)


def _ask(prompt):
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0
    )

    return response.choices[0].message.content