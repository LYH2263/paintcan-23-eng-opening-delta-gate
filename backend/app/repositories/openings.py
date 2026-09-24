import sqlite3
def for_room(conn, room_id):
    return [dict(r) for r in conn.execute("SELECT * FROM openings WHERE room_id=?", (room_id,)).fetchall()]
def insert(conn, room_id, kind, w, h):
    cur = conn.execute("INSERT INTO openings(room_id,kind,w,h) VALUES (?,?,?,?)", (room_id, kind, w, h))
    conn.commit(); return int(cur.lastrowid)
def delete(conn, oid):
    cur = conn.execute("DELETE FROM openings WHERE id=?", (oid,))
    conn.commit(); return cur.rowcount > 0
