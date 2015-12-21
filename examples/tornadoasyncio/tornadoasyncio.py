import tornado.ioloop
import tornado.web
from tornado import gen
import psycopg2.extras
import aiopg
import notorm
from notorm.asyncio import AsyncIORecord
import tornado.autoreload
from tornado.platform.asyncio import AsyncIOMainLoop, to_tornado_future
import asyncio

class Game(AsyncIORecord):
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
    @asyncio.coroutine
    def get(cls, game_id):
        with (yield from notorm.db.cursor(cursor_factory=psycopg2.extras.NamedTupleCursor)) as cursor:
            yield from cursor.execute(
                                 """select game.*::game from game where id = %(game_id)s""",
                                 {'game_id': game_id}
                                 )

            results = yield from cursor.fetchall()
            games = notorm.build_relationships(results, 'game')
        if not games:
            return None
        return games[0]

    @classmethod
    @asyncio.coroutine
    def get_all(cls):
        with (yield from notorm.db.cursor(cursor_factory=psycopg2.extras.NamedTupleCursor)) as cursor:
            yield from cursor.execute(
                                     """select game.*::game from game order by name""",
                                     {})

            results = yield from cursor.fetchall()
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
        games = yield from Game.get_all()
        self.render("../main.html", games=games)

class GameHandler(ExampleRequestHandler):
    @gen.coroutine
    def get(self, game_id=None):
        if game_id:
            game = yield from Game.get(game_id)
        else:
            game = Game()
        self.render("../edit.html", game=game)

    @gen.coroutine
    def post(self, game_id=None):
        if game_id:
            game = yield from Game.get(game_id)
        else:
            game = Game()
        game.name = self.get_argument('name')
        yield from game.save()
        self.redirect("/")

def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/game/new", GameHandler),
        (r"/game/([0-9]+)", GameHandler)
    ])

@asyncio.coroutine
def db_setup():
    print("DB Setup")
    notorm.db = yield from aiopg.create_pool("dbname=notorm_example user=dbuser")

    #We have to use a regular psycopg connection to register the extensions
    #This can be done through Momoko, I just haven't spent enough time on it.
    conn = psycopg2.connect(dsn="dbname=notorm_example user=dbuser")

    psycopg2.extras.register_composite('game', conn, globally=True, factory = GameComposite)
    conn.close()

if __name__ == "__main__":
    tornado.platform.asyncio.AsyncIOMainLoop().install()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(db_setup())
    app = make_app()
    app.listen(8888)

    #tornado.autoreload.start(tornado.ioloop.IOLoop.current())
    loop.run_forever()
    loop.close()
