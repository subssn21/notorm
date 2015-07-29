import tornado.ioloop
import tornado.web

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Hello, world")

class GameHandler(tornado.web.RequestHandler):
    def get(self, game_id=None):
        self.write("Edit Game")
    
    def post(self, game_id=None):
        self.redirect("/")

def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/game/new", GameHandler),
        (r"/game/(0-9)+", GameHandler)
    ])

if __name__ == "__main__":
    app = make_app()
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()