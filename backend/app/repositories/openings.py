import sqlite3
def for_room(conn, room_id):
    return [dict(r) for r in conn.execute("SELECT * FROM openings WHERE room_id=?", (room_id,)).fetchall()]
def insert(conn, room_id, kind, w, h):
    cur = conn.execute("INSERT INTO openings(room_id,kind,w,h) VALUES (?,?,?,?)",
        (room_id, kind, float(w), float(h)))
    conn.commit()
    return get(conn, int(cur.lastrowid))
def get(conn, opening_id):
    row = conn.execute("SELECT * FROM openings WHERE id=?", (opening_id,)).fetchone()
    return dict(row) if row else None
def delete(conn, opening_id):
    conn.execute("DELETE FROM openings WHERE id=?", (opening_id,))
    conn.commit()
