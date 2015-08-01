# Do this as early as possible in your application:
from gevent import monkey; monkey.patch_all()

import gevent
import tornado.ioloop
import tornado.web
import psycopg2.extras
import notorm
import tornado.autoreload

class Game(notorm.record):
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
    def get(cls, game_id):
        cursor = notorm.db.cursor(cursor_factory=psycopg2.extras.NamedTupleCursor)
        cursor.execute("""select game.*::game from game where id = %(game_id)s""",
                                 {'game_id': game_id})

        results = cursor.fetchall()
        games = notorm.build_relationships(results, 'game')
        if not games:
            return None
        return games[0]

    @classmethod
    def get_all(cls):
        cursor = notorm.db.cursor(cursor_factory=psycopg2.extras.NamedTupleCursor)
        cursor.execute("""select game.*::game from game order by name""")

        results = cursor.fetchall()
        games = notorm.build_relationships(results, 'game')
        return games

class GameComposite(psycopg2.extras.CompositeCaster):
    def make(self, values):
        d = dict(zip(self.attnames, values))
        return Game(**d)

class ExampleRequestHandler(tornado.web.RequestHandler):
    def on_finish(self):
        notorm.db.commit()

    def log_exception(self, typ, value, tb):
        print("Exception")
        notorm.db.rollback()
        return super(ExampleRequestHandler, self).log_exception(typ, value, tb)

class MainHandler(ExampleRequestHandler):
    @tornado.web.asynchronous
    def get(self):
        def async_task():
            games = Game.get_all()
            self.render("../main.html", games=games)
        gevent.spawn(async_task)

class GameHandler(ExampleRequestHandler):
    @tornado.web.asynchronous
    def get(self, game_id=None):
        def async_task():
            if game_id:
                game = Game.get(game_id)
            else:
                game = Game()
            self.render("../edit.html", game=game)
        gevent.spawn(async_task)

    @tornado.web.asynchronous
    def post(self, game_id=None):
        def async_task():
            if game_id:
                game = Game.get(game_id)
            else:
                game = Game()
            game.name = self.get_argument('name')
            game.save()
            self.redirect("/")
        gevent.spawn(async_task)

def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/game/new", GameHandler),
        (r"/game/([0-9]+)", GameHandler)
    ])

if __name__ == "__main__":
    notorm.db = psycopg2.connect("dbname=notorm_example user=dbuser")

    cursor = notorm.db.cursor()
    psycopg2.extras.register_composite('game', cursor, globally=True, factory = GameComposite)
    app = make_app()
    app.listen(8888)
    tornado.autoreload.start(tornado.ioloop.IOLoop.current())
    tornado.ioloop.IOLoop.current().start()