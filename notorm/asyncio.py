import notorm
import asyncio
import psycopg2.extras

class AsyncIORecord(notorm.record):
    @asyncio.coroutine
    def update(self, **args):
        for k,v in args.items():
            setattr(self, k, v)
        
        with (yield from notorm.db.cursor(cursor_factory=psycopg2.extras.NamedTupleCursor)) as cursor:
            yield from cursor.execute( 
                            self.update_qry, 
                            self._asdict()
                            )
        return
        
    @asyncio.coroutine
    def save(self):
        if self.id:
            yield from self.update()
        else:
            with (yield from notorm.db.cursor(cursor_factory=psycopg2.extras.NamedTupleCursor)) as cursor:
                yield from cursor.execute( 
                                    self.insert_qry, 
                                    self.__dict__
                                    )        
                results = yield from cursor.fetchone()
                if results:
                    self.id = results[0]
        return

    @classmethod
    @asyncio.coroutine
    def delete(cls, game_config_id):
        with (yield from notorm.db.cursor(cursor_factory=psycopg2.extras.NamedTupleCursor)) as cursor:
            yield from cursor.execute(
                            cls.delete_qry,
                            {'id':game_config_id}
                            )
        return
