import re
from django.utils.log import AdminEmailHandler
import logging
import traceback
from django.template.loader import render_to_string
from django.views.debug import ExceptionReporter

logger = logging.getLogger('django')

def remove_blank_lines(string: str = None):
    if string is None:
        return ''
    return '\n'.join(re.sub(r'\s{3,}', ' ', line) for line in string.splitlines() if line.strip())

class ApiExceptionReporter(ExceptionReporter):

    def __init__(self, request, exc_type, exc_value, tb, filter_api_frames=False):
        super().__init__(request, exc_type, exc_value, tb)
        self.filter_api_frames = filter_api_frames

    def get_traceback_data(self):
        data = super().get_traceback_data()
        request = data.get('request')
        data_post = None
        data_get = None        
        if hasattr(request, 'method'):  # Comprobación más genérica
            if request.method == 'POST':
                data_post = request.POST if hasattr(request, 'POST') else None
            elif request.method == 'GET':
                data_get = request.GET if hasattr(request, 'GET') else None        
        if isinstance(data_post, dict):
            data['filtered_POST_items'] = list(data_post.items())
        else:
            data.pop('filtered_POST_items', None)
        if isinstance(data_get, dict):
            data['request_GET_items'] = list(data_get.items())
        else:
            data.pop('request_GET_items', None)
        if data.get('user_str', None) is None or data['user_str'] == 'AnonymousUser':
            data.pop('user_str', None)
                        
        data['exception_type'] = str(self.exc_type.__name__)
        data['exception_message'] = str(self.exc_value)
        data['filter_api_frames'] = self.filter_api_frames

        return data

    def get_traceback_text(self):
        exc_traceback_str = traceback.format_exc()
        if exc_traceback_str == "NoneType: None\n":
            return 'No exception to log.'
        else:
            c = self.get_traceback_data()                        
            rendered_content = render_to_string("errors_reporter.tpl.plain", c)
            rendered_content= remove_blank_lines(rendered_content)
            return rendered_content


class LogHandlerDiscord(AdminEmailHandler):
    def emit(self, record):
        from dominoapp.connectors.discord_connector import DiscordConnector
        message = self.format(record)
        if record.exc_info:
            exc_type, exc_value, tb = record.exc_info
            request = getattr(record, 'request', None)
            reporter = ApiExceptionReporter(request=request, exc_type=exc_type, exc_value=exc_value, tb=tb, filter_api_frames=True)
            message = reporter.get_traceback_text()            

        message = remove_blank_lines(message)
        
        DiscordConnector.send_error(message)

class LogHandlerFile(logging.FileHandler):
    def __init__(self, filename, mode='a', encoding=None, delay=False):
        super().__init__(filename, mode, encoding, delay)

    def emit(self, record):
        request = getattr(record, 'request', None)
        if record.exc_info:
            exc_type, exc_value, tb = record.exc_info
            reporter = ApiExceptionReporter(request=request, exc_type=exc_type, exc_value=exc_value, tb=tb, filter_api_frames=False)
            record.exc_text = reporter.get_traceback_text()
            super().emit(record)

