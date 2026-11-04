from auth.database import get_connection


def save_profile_memory(user_id, key, value):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO profile_memory
        (user_id, key, value)

        VALUES (?, ?, ?)
        """,
        (user_id, key, value)
    )

    conn.commit()
    conn.close()


def load_profile_memory(user_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT key, value

        FROM profile_memory

        WHERE user_id=?
        """,
        (user_id,)
    )

    rows = cursor.fetchall()

    conn.close()

    return {k: v for k, v in rows}