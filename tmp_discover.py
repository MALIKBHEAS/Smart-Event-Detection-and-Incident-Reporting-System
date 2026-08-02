import os
import sys

sys.path.insert(0, os.path.abspath('.'))
# ensure backend added
sys.path.insert(0, os.path.abspath('backend'))
try:
    from app.db.base import Base
    print('Imported app.models OK')
    print('Tables registered on Base.metadata:')
    print(list(Base.metadata.tables.keys()))
except Exception as e:
    import traceback
    traceback.print_exc()
    print('Discovery failed:', e)
