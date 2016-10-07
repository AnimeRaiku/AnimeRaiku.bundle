import urllib

API_BASE_URL = 'http://animeraiku.com/api/'
API_SEARCH = 'CreativeWork/lookup'

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
      except Exception, e:
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
        Log('HTTP:' + API_BASE_URL + API_SEARCH + '?q=' + media.show)
        q = { 'q' : media.show}
        series_data = JSON.ObjectFromString(ApiCall(API_BASE_URL + API_SEARCH + '?' + urllib.urlencode(q)))['data']

        for i,r in enumerate(series_data):
            Log('Top ID: ' + str(series_data[i].get('id', '')))
            self.ParseSeries(media,series_data[i],lang,results, 90)


    def update(self, metadata, media, lang, force):
        Log('update')

    def ParseSeries(self, media, series_data, lang, results, score):

        # Get attributes from the JSON
        series_id = series_data.get('id', '')
        series_lang = lang
        for i,r in enumerate(series_data.get('name', '')):
            if series_data['name'][i]['lang'] == 'JA-X' and series_data['name'][i]['type'] == 'Main':
                series_name = series_data['name'][i]['content']

        try:
          series_year = series_data['date_start'][:4]
        except:
          series_year = None

        if not series_name:
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
