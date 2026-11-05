"""Persist automatic ESI attempt spacing across windows, failures and restarts."""
import time

AUTO_SECONDS=15*60
DAILY_SECONDS=24*60*60

def interval(domain):
    return DAILY_SECONDS if domain in ['research','extractions','moon-universe'] else AUTO_SECONDS

def fresh_until(snapshot,domain):
    """Presentation freshness follows our polling cadence, not HTTP cache TTL."""
    return max(snapshot['expires'],snapshot['fetched']+interval(domain))

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
                if manual or row is None or now>=row['attempted']+interval(domain):
                    db.execute('INSERT OR REPLACE INTO refresh_attempts VALUES(?,?)',(domain,now));allowed.add(domain)
        return allowed

    def next_at(self,domains):
        with self.store.db() as db:
            values=[]
            for domain in domains:
                row=db.execute('SELECT attempted FROM refresh_attempts WHERE domain=?',(domain,)).fetchone()
                values.append(row['attempted']+interval(domain) if row else 0)
        return min(values,default=0)
