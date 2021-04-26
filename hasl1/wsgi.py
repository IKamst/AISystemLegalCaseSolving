import sys
sys.path.insert(0, '/Users/jelmer/.virtualenvs/moriarty/lib/python3.5/site-packages')

from flup.server.fcgi import WSGIServer
from webserver.server import app

if __name__ == '__main__':
    WSGIServer(app).run()