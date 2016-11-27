import sys, os, signal, datetime
from wit import Wit
from os import system
from user_data import UserData
from audio_handler import AudioHandler
from nlg import NLG


WIT_TOKEN = os.environ['WIT_TOKEN']
DARKSKY_TOKEN = os.environ['DARKSKY_TOKEN']

NAME = "Erik"


class Alfred(object):
    def __init__(self):
        self.nlg = NLG(user_name=NAME)
        self.user_data = UserData(weather_api_token=DARKSKY_TOKEN)
        self.audio_handler = AudioHandler(debug=True)
        self.session_id = 'session_id'
        self.context = {}

    def _active_timeout(self, signum, frame):
        print "Timeout..."
        del self.context['active']
        return self.context

    def _first_entity_value(self, entities, entity):
        if entity not in entities:
            return None
        val = entities[entity][0]['value']
        if not val:
            return None
        return val['value'] if isinstance(val, dict) else val

    def _if_wake_alfred(self, message, context):
        if 'Alfred' in message:
            self.context['active'] = 'True'

    def _converse(self, context, message):
        new_context = self.client.run_actions(self.session_id, message, self.context)
        context = new_context
        print('The session state is now: ' + str(context))

    # --------
    # ACTIONS
    # --------

    def _send(self, request, response):
        message = response['text']
        self.audio_handler.speak(message)

    def _get_team_prospect(self, request):
        context = request['context']
        entities = request['entities']

        team = self._first_entity_value(entities, 'team')
        if team:
            context['prospect'] = 'The ' + team + ' are looking really good.';
        else:
            if context.get('prospect') is not None:
                del context['prospect']
        return context

    def _get_forecast(self, request):
        context = request['context']
        entities = request['entities']

        weather_request = "currently"

        loc = self._first_entity_value(entities, 'location')

        time = self._first_entity_value(entities, 'datetime')
        if not time:
            time = datetime.datetime.now()
        else:
            w_type = entities[u'datetime'][0][u'grain']
            if w_type == "hour":
                weather_request = "hourly"
            elif w_type == "second":
                weather_request = "minutely"
            elif w_type == "day":
                weather_request = "daily"

        time_query = str(time).split('.')[0].replace(' ', 'T')    # Remove timezone


        encoded_date_obj = datetime.datetime.strptime(time.split('.')[0], '%Y-%m-%dT%H:%M:%S')

        search_phrase = self.nlg.searching()
        self.audio_handler.speak(search_phrase)
        weather_obj = self.user_data.find_weather(time_query, loc, weather_request)

        context['forecast'] = self.nlg.weather(weather_obj, encoded_date_obj)

        return context

    def _greeting(self, request):
        context = request['context']
        entities = request['entities']

        context['greeting'] = self.nlg.greet()

        return context

    def _joke(self, request):
        context = request['context']
        entities = request['entities']

        context['joke'] = self.nlg.joke()

        return context

    def _status(self, request):
        context = request['context']
        entities = request['entities']

        context['status'] = self.nlg.personal_status()

        return context

    def _exit(self, request):
        context = request['context']
        del context['active']
        return context

    def _close(self, signal, frame):
        self.nlg.close()
        print
        sys.exit(0)

    # --------
    # START BOT
    # --------
    
    def start(self):

        self.actions = {
            'send': self._send,
            'getForecast': self._get_forecast,
            'getTeamProspects': self._get_team_prospect,
            'exit': self._exit,
            'greeting': self._greeting,
            'getJoke': self._joke,
            'getStatus': self._status
        }
        self.client = Wit(access_token=WIT_TOKEN, actions=self.actions)

        # signal.signal(signal.SIGALRM, self._active_timeout)
        signal.signal(signal.SIGINT, self._close)

        while 1:
            try:
                # 20 second timeout before bot goes to passive listening
                # if 'active' in self.context:
                #     signal.alarm(20)
                input_text = self.audio_handler.get_audio_as_text()
                self._if_wake_alfred(input_text, self.context)
                if 'active' in self.context:
                    # signal.alarm(0)
                    self._converse(self.context, input_text)
            except Exception as e:
                print("Exception caught.")


if __name__ == "__main__":
    alfred = Alfred()
    alfred.start()

