from auth.database import get_connection
from collections import defaultdict
def save_chat(user_id, chat_name, query, answer):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO chat_history
        (user_id, chat_name, query, answer)
        VALUES (?,?,?,?)
    """,
    (user_id, chat_name, query, answer))
    conn.commit()
    conn.close()
def load_chat_history(user_id):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT chat_name,query,answer
        FROM chat_history
        WHERE user_id=?
        ORDER BY id
    """,(user_id,))

    rows = cursor.fetchall()

    conn.close()

    chats = defaultdict(list)

    for chat_name, query, answer in rows:

        chats[chat_name].append({

            "query": query,

            "answer": answer

        })

    return dict(chats)    