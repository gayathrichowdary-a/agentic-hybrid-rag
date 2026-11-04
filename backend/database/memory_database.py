from auth.database import get_connection


def save_memory(user_id, memory):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO memory(user_id, memory)

        VALUES(?, ?)
        """,
        (user_id, memory)
    )

    conn.commit()
    conn.close()


def load_memory(user_id):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT memory

        FROM memory

        WHERE user_id = ?

        ORDER BY id DESC
        """,
        (user_id,)
    )

    rows = cursor.fetchall()

    conn.close()

    return [row[0] for row in rows]