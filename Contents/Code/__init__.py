import urllib

API_BASE_URL = 'http://animeraiku.dev.dev/api/'
CDN_BASE_URL = 'http://cdn.animeraiku.dev/'
API_SEARCH = 'CreativeWork/lookup'
API_DETAILS = 'CreativeWork/'

HEADERS = {'User-agent': 'Plex/Nine'}


def ApiCall(url, fetchContent=True, additionalHeaders=None, data=None):
    if additionalHeaders is None:
        additionalHeaders = dict()

    local_headers = HEADERS.copy()
    local_headers.update(additionalHeaders)

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
        try:
            Log('HTTP:' + API_BASE_URL + API_SEARCH + '?q=' + media.show)
            q = {'q': media.show, 'type': 'Anime'}
            series_data = JSON.ObjectFromString(
                ApiCall(API_BASE_URL + API_SEARCH +
                        '?' + urllib.urlencode(q)))['data']

            for i, r in enumerate(series_data):
                Log('Top ID: ' + str(series_data[i].get('id', '')))
                self.ParseSeries(media, series_data[i], lang, results, 90)
        except Exception as e:
            Log('Content Error (%s) - %s' % (e, e.message))

    def update(self, metadata, media, lang, force):
        try:
            series_data = JSON.ObjectFromString(
                ApiCall(API_BASE_URL + API_DETAILS + metadata.id))['data']

            metadata.title = series_data['attributes']['name_main']
            metadata.genres = series_data['attributes'].get('genre', [])
            metadata.summary = series_data['attributes'].get('plot_main', '')
            date_start = series_data['attributes'].get('date_start', None)
            if date_start is not None:
                metadata.originally_available_at = Datetime.ParseDate(date_start).date()
            metadata.duration = series_data['attributes'].get('time_required', 0) * 1000
            if series_data['attributes'].get('country', '') == 'JP':
                metadata.countries = ['Japón']
            else:
                metadata.countries = None

            if metadata.duration == 0:
                metadata.duration = None
            if 'organization' in series_data['attributes']:
                for i, r in enumerate(series_data['attributes']['organization']):
                    if series_data['attributes']['organization'][i]['task'] == 'Animation Production':
                        metadata.studio = series_data['attributes']['organization'][i]['name']

            if 'cover' in series_data['attributes'] and 'medium' in series_data['attributes']['cover'] and series_data['attributes']['cover']['medium'] != '':
                Log('New Cover: ' + CDN_BASE_URL+series_data['attributes']['cover']['medium'])
                metadata.posters[CDN_BASE_URL+series_data['attributes']['cover']['medium']] = Proxy.Preview(CDN_BASE_URL+series_data['attributes']['cover']['small'], sort_order=1)
        except Exception as e:
            Log('Content Error (%s) - %s' % (e, e.message))

    def ParseSeries(self, media, series_data, lang, results, score):
        series_id = series_data.get('id', '')
        series_lang = lang
        series_name = None

        for i, r in enumerate(series_data['attributes'].get('name', '')):
            if series_data['attributes']['name'][i]['lang'] == 'JA-X' and series_data['attributes']['name'][i]['type'] == 'MAIN':
                series_name = series_data['attributes']['name'][i]['content']

        # try:
        #     series_year = series_data['date_start'][:4]
        # except:
        series_year = None

        if not series_name:
            Log('No encontrado nombre valido')
            return

        clean_series_name = series_name.lower()

        cleanShow = media.show

        substringLen = len(Util.LongestCommonSubstring(cleanShow.lower(), clean_series_name))
        cleanShowLen = len(cleanShow)

        maxSubstringPoints = 5.0  # use a float
        score += int((maxSubstringPoints * substringLen)/cleanShowLen)  # max 15 for best substring match

        distanceFactor = .6
        score = score - int(distanceFactor * Util.LevenshteinDistance(cleanShow.lower(), clean_series_name))

        if series_year and media.year:
            if media.year == series_year:
                score += 10
            else:
                score = score - 10

        # sanity check to make sure we have SOME common substring
        if (float(substringLen) / cleanShowLen) < .15:  # if we don't have at least 15% in common, then penalize below the 80 point threshold
            score = score - 25

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
