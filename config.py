import logging
import logging.config
from colorlog import ColoredFormatter

RSS_URL = 'http://itunes.apple.com/rss/customerreviews/id={0}/json'
REVIEWS_URL = 'http://itunes.apple.com/us/rss/customerreviews/page={0}/id={1}/sortby=mostrecent/json'

MONGO_DB = 'app'
MONGO_CONNECTION_STRING = 'mongodb://localhost/%s' % MONGO_DB

REDIS_HOSTNAME = 'x0'
REDIS_PORT = 6379

X_HOSTS = ['x{0}'.format(i) for i in xrange(0,6)]

def configure_logging():
	FORMAT = '%(log_color)s %(levelname)-8s%(reset)s %(bold_blue)s%(message)s'
	formatter = ColoredFormatter(
	    FORMAT,
	    datefmt = None,
	    reset = True,
	    log_colors = {
	        'DEBUG': 'cyan',
	        'INFO': 'green',
	        'WARNING': 'yellow',
	        'ERROR': 'red',
	        'CRITICAL': 'red'
	    }
	)

	logging.config.dictConfig({
	    'version': 1,
	    'formatters': {
	        'colored': {
	            '()': 'colorlog.ColoredFormatter',
	            'format': FORMAT
	        }
	    },
	    'handlers': {
	        'console': {
	            'class': 'logging.StreamHandler',
	            'level': 'INFO',
	            'formatter': 'colored',
	            'stream': 'ext://sys.stdout'
	        }
	    },
	    'root': {
	        'level': 'INFO',
	        'handlers': ['console']
	    }
	})
	logging.getLogger('requests').setLevel(logging.WARNING)
