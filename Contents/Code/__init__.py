import urllib
import dateutil.parser

# Raiz de la API de AnimeRaiku
API_BASE_URL = 'https://animeraiku.com/api/'

# Metodo de busqueda de obras por nombre
API_SEARCH = 'CreativeWork/lookup'

# Metodo para obtener el detalle de una obra
API_DETAILS = 'CreativeWork/'

# Cabeceras a mandar en todas las peticiones
HEADERS = {'User-agent': 'Plex/Nine'}


def ApiCall(url, fetchContent=True, additionalHeaders=None, data=None):
    """Realiza una llamada a la API de AnimeRaiku
    Args:
        url: Url de la Api a la que llamar
        fetchContent: Indica si debe devolver el contenido de la respuesta a la llamda
        additionalHeaders: Cabeceras adicionales que añadir a la llamada
        data: Información adicional a añadir a la llamada

    Returns:
        El contenido de la respuesta de la llamda siempre y cuando
    """

    if additionalHeaders is None:
        additionalHeaders = dict()

    local_headers = HEADERS.copy()
    local_headers.update(additionalHeaders)

    if Prefs["access_token"] is not None and Prefs["access_token"] != "":
        auth_header = {'Authorization': 'Bearer ' + Prefs["access_token"]}
        local_headers.update(auth_header)
        Log('Autentificación activada')

    try:
        result = HTTP.Request(url, headers=local_headers, timeout=60, data=data)
    except Exception:
        try:
            result = HTTP.Request(url, headers=local_headers, timeout=60, data=data)
        except:
            return None

    if fetchContent:
        try:
            result = result.content
        except Exception as e:
            Log('Content Error (%s) - %s' % (e, e.message))

    return result


class AnimeRaikuAgent(Agent.TV_Shows):
    name = 'AnimeRaiku'
    languages = [
        Locale.Language.Spanish,
    ]
    primary_provider = True
    fallback_agent = False
    accepts_from = None
    contributes_to = None

    def search(self, results, media, lang, manual):
        """ Plex llama a este metodo para buscar coincidencias potenciales
        Args:
            self: Referencia esta propia clase
            results: Un contenedor vacio a rellenar con las coincidencias encontradas
            media: Objeto con la información necesaria para realizar la busqueda
            lang: Idioma del usuario actual
            manual: Boleano indicando si la busqueda ha sido automatica o manual
        """

        try:
            Log('HTTP:' + API_BASE_URL + API_SEARCH + '?q=' + media.show)
            q = {'q': media.show, 'type': 'Anime'}
            series_data = JSON.ObjectFromString(
                ApiCall(API_BASE_URL + API_SEARCH +
                        '?' + urllib.urlencode(q)))['data']

            for i, r in enumerate(series_data):
                Log('Top ID: ' + str(series_data[i].get('id', '')))
                self.ParseSeries(series_data[i], lang, results)
        except Exception as e:
            Log('Content Error (%s) - %s' % (e, e.message))

    def ParseSeries(self, series_data, lang, results):
        """ Plex llama a este metodo para buscar coincidencias potenciales
        Args:
            self: Referencia esta propia clase
            series_data: Información de una obra obtenida de la API
            lang: Idioma del usuario actual
            results: Contenedor donde guardar los resultados
        """
        series_id = series_data.get('id', '')
        series_lang = lang
        series_name = series_data['attributes'].get('name_main')
        # date_start = dateutil.parser.parse(series_data.get('date_start'))
        p = dateutil.parser()
        date_start = p.parse(series_data['attributes'].get('date_start'))
        series_year = date_start.year

        score = 100 - int(series_data['attributes']['levenshtein'])
        Log('Coincidencia (%s) - %s (%s)' % (series_name, score, series_year))
        # Add a result for this show
        results.Append(
          MetadataSearchResult(
              id=str(series_id),
              name=series_name,
              year=series_year,
              lang=series_lang,
              score=score
          )
        )

    def update(self, metadata, media, lang, force):
        """ Plex llama a este metodo para buscar coincidencias potenciales
        Args:
            self: Referencia esta propia clase
            metadata: Un contenedor donde actualizar la información (puede venir pre relleno)
            media: Objeto con la información necesaria para realizar la busqueda
            lang: Idioma del usuario actual
            force: Indica si el usuario ha forzado la autalización de la información
        """

        try:
            Log('Actualizando información')
            series_data = JSON.ObjectFromString(
                ApiCall(API_BASE_URL + API_DETAILS + metadata.id))['data']

            metadata.title = series_data['attributes']['name_main']
            metadata.genres = series_data['attributes'].get('genre', [])
            metadata.summary = series_data['attributes'].get('plot_main', '')
            date_start = series_data['attributes'].get('date_start', None)
            if date_start is not None:
                metadata.originally_available_at = Datetime.ParseDate(date_start).date()

            metadata.duration = 0
            if 'time_required' in series_data['attributes'] and series_data['attributes']['time_required'] is not None:
                metadata.duration = series_data['attributes'].get('time_required', 0) * 1000

            if series_data['attributes'].get('country', '') == 'JP':
                metadata.countries = ['Japón']
            else:
                metadata.countries = None

            if metadata.duration == 0:
                metadata.duration = 25

            Log('Actualizando organizaciones')
            if 'organization' in series_data['attributes'] and series_data['attributes']['organization'] is not None:
                for i, r in enumerate(series_data['attributes']['organization']):
                    if series_data['attributes']['organization'][i]['task'] == 'Animation Production':
                        metadata.studio = series_data['attributes']['organization'][i]['name']

            if 'images' in series_data['attributes'] and 'cover' in series_data['attributes']['images'] and 'medium' in series_data['attributes']['images']['cover']:
                Log('New Cover: ' + series_data['attributes']['images']['cover']['medium'])
                metadata.posters[series_data['attributes']['images']['cover']['medium']] = Proxy.Preview(series_data['attributes']['images']['cover']['medium'], sort_order=1)
            else:
                Log('El anime no tiene Cover')

            if 'images' in series_data['attributes'] and 'background' in series_data['attributes']['images'] and 'big' in series_data['attributes']['images']['background'] and series_data['attributes']['images']['background']['big'] is not None:
                Log('New Cover: ' + series_data['attributes']['images']['background']['big'])
                metadata.art[series_data['attributes']['images']['background']['big']] = Proxy.Preview(series_data['attributes']['images']['background']['big'], sort_order=1)
            else:
                Log('El anime no tiene background')

            if 'user' in series_data['attributes'] and 'rating' in series_data['attributes']['user'] and series_data['attributes']['user']['rating'] is not None:
                metadata.rating = float(series_data['attributes']['user']['rating'])

        except Exception as e:
            Log('Content Error (%s) - %s' % (e, e.message))
