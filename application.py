import logging
from subscriptions import app as application

if __name__ == "__main__":
    # Setting debug to True enables debug output. This line should be
    # removed before deploying a production app.
    #gunicorn_logger = logging.getLogger('gunicorn.error')
    #application.logger.handlers = gunicorn_logger.handlers
    #application.logger.setLevel(gunicorn_logger.level)

    #application.logger.error('TEST')

    application.debug = True
    application.run()
