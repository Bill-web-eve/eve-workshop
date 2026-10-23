"""Persist automatic ESI attempt spacing across windows, failures and restarts."""
import time

AUTO_SECONDS=15*60

class RefreshPolicy:
    def __init__(self,store):
        self.store=store
        with store.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS refresh_attempts(domain TEXT PRIMARY KEY,attempted REAL NOT NULL)')

    def claim(self,domains,manual=False,now=None):
        now=time.time() if now is None else now;allowed=set()
        with self.store.db() as db:
            db.execute('BEGIN IMMEDIATE')
            for domain in set(domains):
                row=db.execute('SELECT attempted FROM refresh_attempts WHERE domain=?',(domain,)).fetchone()
                if manual or row is None or now>=row['attempted']+AUTO_SECONDS:
                    db.execute('INSERT OR REPLACE INTO refresh_attempts VALUES(?,?)',(domain,now));allowed.add(domain)
        return allowed

    def next_at(self,domains):
        with self.store.db() as db:
            values=[]
            for domain in domains:
                row=db.execute('SELECT attempted FROM refresh_attempts WHERE domain=?',(domain,)).fetchone()
                values.append(row['attempted']+AUTO_SECONDS if row else 0)
        return min(values,default=0)
