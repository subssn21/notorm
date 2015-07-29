import psycopg2.extras
from tornado import gen
import momoko
import notorm

class Game(notorm.record):
    _fields = {'id':None,
               'owner_id':None
    }
    
    insert_qry = """
    insert into game (owner_id)
    values(%(owner_id)s)
    returning id
    """
    
    update_qry = """
    """
    
    @classmethod
    @gen.coroutine
    def get(cls, game_id):
        cursor = yield momoko.Op(models.db.execute, 
                                 """select game.*::game from game where id = %(game_id)s""", 
                                 {'game_id': game_id}, 
                                 cursor_factory=psycopg2.extras.NamedTupleCursor)
        
        results = cursor.fetchall()
        games = notorm.build_relationships(user, 'game')
        if not games:
            return None
        return games[0]

class GameComposite(psycopg2.extras.CompositeCaster):
    def make(self, values):
        d = dict(zip(self.attnames, values))
        return Game(**d)