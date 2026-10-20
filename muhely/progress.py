"""Thread-local, presentation-only progress. Never changes requests or caching."""
from contextlib import contextmanager
import threading

_local=threading.local()

@contextmanager
def listen(callback):
    previous=getattr(_local,'callback',None);_local.callback=callback
    try:yield
    finally:_local.callback=previous

def report(**values):
    callback=getattr(_local,'callback',None)
    if callback:callback(values)

def items(values,name=lambda row:row['name']):
    rows=list(values)
    for index,row in enumerate(rows):
        report(subject=str(name(row)),completed=index,total=len(rows),resource='Hozzáférés ellenőrzése',mode='checking',page=None,pages=None)
        yield row
        report(completed=index+1)

def resource(label,cached=False,page=None,pages=None):
    report(resource=label,mode='cache' if cached else 'checking',page=page,pages=pages)
