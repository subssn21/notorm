import notorm
import momoko
from tornado import gen
import psycopg2.extras

class AsyncRecord(notorm.record):
    @gen.coroutine
    def update(self, **args):
        for k,v in args.items():
            setattr(self, k, v)
        
        cursor = yield notorm.db.execute( 
                                self.update_qry, 
                                self._asdict(), 
                                cursor_factory=psycopg2.extras.NamedTupleCursor)        
        
    @gen.coroutine
    def save(self):
        if self.id:
            self.update()
        else:
            cursor = yield notorm.db.execute(
                                    self.insert_qry, 
                                    self.__dict__, 
                                    cursor_factory=psycopg2.extras.NamedTupleCursor)        
            results = cursor.fetchone()
            if results:
                self.id = results[0]

