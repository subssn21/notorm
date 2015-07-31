import tornado.ioloop
import tornado.web
from tornado import gen
import psycopg2.extras
import momoko
import notorm
from notorm.momoko import AsyncRecord
import tornado.autoreload

class Game(AsyncRecord):
    _fields = {'id':None,
               'name':None
    }
    
    insert_qry = """
    insert into game (name)
    values(%(name)s)
    returning id
    """
    
    update_qry = """
    update game set name=%(name)s where id = %(id)s
    """
    
    @classmethod
    @gen.coroutine
    def get(cls, game_id):
        cursor = yield notorm.db.execute( 
                                 """select game.*::game from game where id = %(game_id)s""", 
                                 {'game_id': game_id}, 
                                 cursor_factory=psycopg2.extras.NamedTupleCursor)
        
        results = cursor.fetchall()
        games = notorm.build_relationships(results, 'game')
        if not games:
            return None
        return games[0]
    
    @classmethod
    @gen.coroutine
    def get_all(cls):
        cursor = yield notorm.db.execute( 
                                 """select game.*::game from game order by name""", 
                                 {}, 
                                 cursor_factory=psycopg2.extras.NamedTupleCursor)
        
        results = cursor.fetchall()
        games = notorm.build_relationships(results, 'game')
        return games
        
class GameComposite(psycopg2.extras.CompositeCaster):
    def make(self, values):
        d = dict(zip(self.attnames, values))
        return Game(**d)
    
class ExampleRequestHandler(tornado.web.RequestHandler):
    pass

class MainHandler(ExampleRequestHandler):
    @gen.coroutine
    def get(self):
        games = yield Game.get_all()
        self.render("../main.html", games=games)

class GameHandler(ExampleRequestHandler):
    @gen.coroutine
    def get(self, game_id=None):
        if game_id:
            game = yield Game.get(game_id)
        else:
            game = Game()
        self.render("../edit.html", game=game)
    
    @gen.coroutine
    def post(self, game_id=None):
        if game_id:
            game = yield Game.get(game_id)
        else:
            game = Game()
        game.name = self.get_argument('name')
        game.save()
        self.redirect("/")

def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/game/new", GameHandler),
        (r"/game/([0-9]+)", GameHandler)
    ])

if __name__ == "__main__":
    notorm.db = momoko.Pool(
            dsn="dbname=notorm_example user=mrobellard"
            )
    future = notorm.db.connect()
    tornado.ioloop.IOLoop.current().add_future(future, lambda f: tornado.ioloop.IOLoop.current().stop())
    tornado.ioloop.IOLoop.current().start()        

    #We have to use a regular psycopg connection to register the extensions
    #This can be done through Momoko, I just haven't spent enough time on it.
    conn = psycopg2.connect(dsn="dbname=notorm_example user=mrobellard")
    
    psycopg2.extras.register_composite('game', conn, globally=True, factory = GameComposite)
    conn.close()
    app = make_app()
    app.listen(8888)
    tornado.autoreload.start(tornado.ioloop.IOLoop.current())
    tornado.ioloop.IOLoop.current().start()