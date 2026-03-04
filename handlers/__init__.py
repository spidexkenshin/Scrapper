from pyrogram import Client
from .start     import register as r1
from .admin     import register as r2
from .search    import register as r3
from .upload    import register as r4
from .channels  import register as r5
from .broadcast import register as r6

def register_all(app: Client, db, qmgr):
    r1(app, db)
    r2(app, db)
    r3(app, db, qmgr)
    r4(app, db, qmgr)
    r5(app, db)
    r6(app, db)
