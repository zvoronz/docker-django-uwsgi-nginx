# -*- coding: utf-8 -*-
#------------------------------------------------------------
# Name:        fedClass
# Author:      alexey.sychov@gameloft.com
# Created:     02/06/2016
# Description: Federation wrapper module. Version 1.0.1
#------------------------------------------------------------

import urllib
import urllib2
import json
import time

from socket import error as SocketError
from datetime import datetime
from StringIO import StringIO


class Federation(object):
    """ Federation lib class.
    Make an instance for each enviroment you need and store them into the local
    unit namespace, to prevent a regular reinitializations.
    """
    portal_credential = 'game:gangstar4'
    portal_pass =('dfee9e39474b6e292d66c7facba668e181272df021'
                  '20febb261a4fde550a0cff20130509')

    scopes_list = ' '.join((
        'auth auth_game_admin auth_admin_ro',
        'storage storage_ro storage_admin',
        'config',
        'leaderboard leaderboard_admin leaderboard_ro leaderboard_override',
        'social social_admin social_event social_group',
        'message message_secured',
        'asset asset_delete asset_upload',
        ))

    # ============= Federation settings ============= #

    DEBUG = False

    # Eve URL
    URL_EVE = 'http://eve.gameloft.com:20001'
    # Number of tries to attempt connect with Pandora
    PANDORA_TRIES_NUMBER = 3
    # Timeouts withing unsuccessful attempts (progression)
    TIMEOUTS = (0, 5, 10, 30)
    # List of Federation services (except Pandora), which not requeries SSL
    NON_SECURITY_SERVICE = ('eve')
    # cached adresses live during this time (in sec)
    PANDORA_CASH_LIVETIME = 30
    # Number of tries to attempt connect for other services, than Pandora
    FEDSERVICE_TRIES_NUMBER = 3
    # Number of tries to attempt reconnect after reseiving HTTP 5xx errors
    HTTP5XX_TRIES_NUMBER = 3


    # ============= generic methods ============= #

    def __init__(self, version, platform='ios'):
        """ 'version' is string like "0.0.1".
        """
        self.portal_client_id = '1622:52584:%s:%s:appstore' % (version,platform)
        self.access_token = None
        self.cashPandora = {}
        self.URL_PANDORA = None

        proxy_support = urllib2.ProxyHandler({})
        opener = urllib2.build_opener(proxy_support)
        urllib2.install_opener(opener)

        self.authorizePortal()


    def authorizePortal(self, refresh_token=False):
        """Get access & refresh tokens for Portal using it's credential for
        futher use, if it needs.
        """
        if self.DEBUG:
            print '* Portal authorize:'
        janusUrl = self.askPandoraFor('auth')
        responce = self.askJanusForAuth(url=janusUrl,
                                        client_id=self.portal_client_id,
                                        username=self.portal_credential,
                                        password=self.portal_pass,
                                        scope=self.scopes_list)
        self.access_token = responce['access_token']
        if refresh_token:
            return responce['refresh_token']
        else:
            return self.access_token


    @staticmethod
    def makeQuery(url, url_args='', method='GET', query_args={}, cache=True):
        """Make POST or GET query to selected URL.

        GET|POST <url>/<url_args> with <query_args>
        """
        url_full = url + url_args
        qa_utf8 = dict([(unicode(key).encode('utf-8'),
                         unicode(value).encode('utf-8')) for key, value in
                                                           query_args.items()])
        data = urllib.urlencode(qa_utf8)
        headers = {}
        if not cache:
            headers['Cache-Control'] = 'no-cache, no-store, max-age=0'

        if method == 'GET':
            if data:
                data = '?' + data
            request = url_full + data
        elif method == 'POST':
            request = urllib2.Request(url_full, data, headers)
        else:
            raise ValueError('Wrong method used!')

        responce = urllib2.urlopen(request)
        return responce.read()


    def portal_reconnect(func):
        """This is a simple decorator. If HTTP Error 401 Unauthorized raises in
        decorated function, it will relogin Portal and try it another time(s).
        """
        def func2(self, *args, **kargs):
            try:
                result = func(self, *args, **kargs)
            except urllib2.HTTPError as err:
                if err.code == 401:
                    if self.DEBUG:
                        print '* Portal access token expired.'
                    self.authorizePortal()
                    result = func(self, *args, **kargs)
                else:
                    raise err
            return result

        func2.__name__ = func.__name__
        func2.__doc__ = func.__doc__
        return func2


    def connect_error_handler(service_name):
        """This is a superdecorator; when decorated by it Federation function
        has connect errors or some HTTP, decorator ask for a new URL from
        Pandora (by 'service_name' param) and (or) make another attempt to exec
        this function.

        To work properly, all decorated function must meet next requirements:
            - URL parameter must be named as 'url';
            - URL parameter must be placed as named param in args.
        """

        def inner_decor(func):
            """ Decorator for Federation requests.

            If Socket or URLerrors (not HTTP) occurs, tries
            FEDSERVICE_TRIES_NUMBER times to receive new URL from Pandora and
            reconnect.

            If HTTP 429, 500, 502, 503, 504 Errors occurs, HTTP5XX_TRIES_NUMBER
            times tries to reconnect.
            """
            def func2(self, *args, **kargs):

                try:
                    if not kargs.get('url'):
                        kargs['url'] = self.askPandoraFor(service_name)
                    return func(self, *args, **kargs)

                except urllib2.HTTPError as err:
                    if err.code not in (429, 500, 502, 503, 504):
                        raise err
                    else:
                        if self.DEBUG:
                            print '* HTTP %d error occurs again.' % err.code
                        sleeptime = 5
                        if self.DEBUG:
                            print '* Wait %s sec.' % sleeptime
                        time.sleep(sleeptime)
                        result = func2(self, *args, **kargs)
                        return result

                except (urllib2.URLError, SocketError):
                    sleeptime = 5
                    if self.DEBUG:
                        print '* Wait %s sec.' % sleeptime
                    time.sleep(sleeptime)
                    newUrl = self.askPandoraFor(service_name, forced = True)
                    if 'url' in kargs.keys():
                        kargs['url'] = newUrl
                    else:
                        raise TypeError('No "url" in named args!')

                    result = func2(self, *args, **kargs)
                    return result

            func2.__name__ = func.__name__
            func2.__doc__ = func.__doc__
            return func2

        return inner_decor

    # ----- PANDORA ----- #

    def askPandoraFor(self, serviceName, forced=False):
        """Ask Pandora for URL of a service.
        GET /locate:

            serviceName:    The name of service.
            forced     :    If True, cash is not used anyway.
        """

        def cacheIsFresh(serviceName):
            """Verify, if cached adress is fresh enough.
            """
            if forced:
                return False
            time = self.cashPandora[serviceName]['time']
            dt = datetime.now() - time
            if dt.total_seconds() < self.PANDORA_CASH_LIVETIME:
                if self.DEBUG:
                    print '* (used cached adress)'
                return True
            else:
                if self.DEBUG:
                    print '* pity, but cached adress is old. Ask for a new one.'
                return False

        if not self.URL_PANDORA:
            self.URL_PANDORA = self.askEveForPandoraURL()

        if self.DEBUG:
            print 'Asking Pandora for %s url.' % serviceName

        if self.cashPandora.get(serviceName) and cacheIsFresh(serviceName):
            result = self.cashPandora[serviceName]['url']
        else:

            tries_num = 0
            while tries_num <= self.PANDORA_TRIES_NUMBER:
                time.sleep(self.TIMEOUTS[tries_num])
                try:
                    request = self.URL_PANDORA + '/locate?service='+ serviceName
                    responce = urllib2.urlopen(request)
                    result = responce.read()
                    break
                except urllib2.HTTPError as err:
                    if err.code not in (429, 500, 502, 503):
                        raise err
                    tries_num += 1
                    if tries_num > self.PANDORA_TRIES_NUMBER:
                        newUrlPandora = self.askEveForPandoraURL()
                        if newUrlPandora <> self.URL_PANDORA:
                            if self.DEBUG:
                                print '* Pandora URL is non-actual, changed.'
                            self.URL_PANDORA = newUrlPandora
                            tries_num = 0
                    else:
                        if self.DEBUG:
                            print '* HTTP %d. Wait for next attempt.' % err.code
                except (urllib2.URLError, SocketError):
                    tries_num += 1
                    if tries_num > self.PANDORA_TRIES_NUMBER:
                        newUrlPandora = self.askEveForPandoraURL()
                        if newUrlPandora <> self.URL_PANDORA:
                            if self.DEBUG:
                                print '* Pandora URL is non-actual, changed.'
                            self.URL_PANDORA = newUrlPandora
                            tries_num = 0
                    else:
                        if self.DEBUG:
                            print '* unsuccessful. Wait for another attempt.'
            else:
                 raise urllib2.HTTPError('', 500, ' Internal Server Error',
                          None, StringIO('Impossible to connect with Pandora.'))

            if serviceName in self.NON_SECURITY_SERVICE:
                result = 'http://' + result
            else:
                result = 'https://' + result
            self.cashPandora[serviceName] = {'url':result,'time':datetime.now()}

        return result

    # ----- JANUS ----- #

    @connect_error_handler('auth')
    def askJanusForAuth(self, url, client_id, username, password, scope,
                  device_id=None, for_username=None, for_credential_type=None, encrypt_tokens=False):
        """Authorize
        POST /authorize

            url:        Janus service url.
            client_id:	The unique identifier for the client software making
                        the request (should a string containing product ID, GGI,
                        build
                        version, and platform with a colon separating the values
                        like this <productID>:<GGI>:<build version>:<platform>)
            username:	Format of this parameter is credential_type:username. It
                        represents the identifier for the user and the
                        authentication authority in whose name the client will
                        be accessing services. Only alpha-numeric, :, ., +, _, -
                        and @ symbols are permitted
            password:	The secret for the user in whose name the client will be
                        accessing services
            scope:	    A space-separated list of service names the client
                        wishes to be granted access to. Values are defined by
                        the various online services.
            device_id:	The id of your device (for new games shall be a gdid.
                        historically, games send multiple device IDs in the
                        format: md5mac=<value> idfa=<value> idfv=<value>,
                        hdidfv=<value>, hdidfv=<value> imei=<value> mac=<value>
                        aid=<value> serialNo=<value>. it will be translated to
                        gdid by GDID Server, if detected). This argument is
                        optional for backward compatiblity but is required for
                        all new games.
        """
        if self.DEBUG:
            print 'Asking Janus for auth.'
        query_args = {'client_id':client_id,
                      'username':username,
                      'password':password,
                      'scope':scope}
        if device_id:
            query_args['device_id'] = device_id
        if for_username:
            query_args['for_username'] = for_username
        if for_credential_type:
            query_args['for_credential_type'] = for_credential_type
        if encrypt_tokens:
            query_args['encrypt_tokens'] = encrypt_tokens
        response = self.makeQuery(url, '/authorize', 'POST', query_args)
        return json.loads(response)


    @portal_reconnect
    @connect_error_handler('auth')
    def askJanusForAccount(self, credential, url=None):
        """Verify Token
        GET /verify

        url:            Janus service url.
        access_token:   The access token to be checked for validity.
        credential:     Credential, info is requested of.
        """
        if self.DEBUG:
            print 'Asking Janus for account info.'

        credential = urllib.quote(credential, '')
        responce = self.makeQuery(url, '/users/' + credential, 'GET',
                                             {'access_token':self.access_token})
        return json.loads(responce)


    @portal_reconnect
    @connect_error_handler('auth')
    def askJanusForRefreshToken(self, refresh_token, url=None):
        """Refresh Access Token
        POST /authorize

        refresh_token:	The identifier for the user in whose name the client
                        will be accessing services
        url:            Janus service url. Optional
        """
        if self.DEBUG:
            print 'Asking Janus for token refreshing.'

        responce = self.makeQuery(url, '/authorize', 'POST',
                                    {'refresh_token': refresh_token,
                                     'grant_type': 'refresh_token'})
        return json.loads(responce)

    # ------ EVE -------#

    def askEveForPandoraURL(self):
        """Sets Pandora service URL in config.URL_PANDORA const according to
        Eve environment.
        """
        data_centers = self.askEveForDatacenters(self.portal_client_id, 'US')
        data_center = data_centers[0]
        for dc in data_centers:
            if dc['preferred'] == True:
                data_center = dc
        eveConfig = self.askEveForConfig(self.portal_client_id, data_center)
        return eveConfig['pandora']


    def askEveForDatacenters(self, client_id, country,
                                                  override_ip_geolocation=None):
        """List Datacenters
        GET /config/<client_id>/datacenters

            client_id:	The unique identifier for the client software making the
                        request
            country:	The two letter country code of where the client is running.
                        Required as a fall-back in case geolocation of IP fails
            override_ip_geolocation:
                        A two letter iso country code that should be used instead of
                        the geolocated IP. Optional. Defaults to None. This should
                        never be used in production code, it is only there to help
                        test multi datacenter implementations.
        """
        url_args=u'/config/%s/datacenters' % client_id
        args = {'country':country}
        if override_ip_geolocation:
            args['override_ip_geolocation'] = override_ip_geolocation
        if self.DEBUG:
            print 'Asking Eve for datacenter list.'
        responce = self.makeQuery(self.URL_EVE, url_args, 'GET', args)
        return json.loads(responce)


    def askEveForConfig(self, client_id, datacenter):
        """Retrieve Config
        GET /config/<client_id/datacenters/<datacenter>/urls

            client_id:      The client ID for the client making the request
            datacenter:     Retrieved drom askEveForDatacenters data center data.
        """
        dc_name = datacenter['name']
        url_args = '/config/%s/datacenters/%s/urls' % (client_id, dc_name)
        if self.DEBUG:
            print 'Asking Eve for "%s" datacenter config.' % dc_name
        responce = self.makeQuery(self.URL_EVE, url_args, 'GET')
        return json.loads(responce)

    # ------ OLYMPUS ------- #

    @portal_reconnect
    @connect_error_handler('leaderboard')
    def askOlympusForParts(self, sort, name, limit=50, url=None):
        """Get Leaderboard Parts
        GET /leaderboards/<sort>/<name>/parts

        sort:           The sort order used for this leaderboard (either 'desc' or
                        'asc')
        name:           The identifier for the leaderboard container
        limit:          The maximum number of divisions to return.
        """
        if self.DEBUG:
            print 'Ask Olympus for leaderboard parts.'

        url_arg = '/leaderboards/%s/%s/parts' % (sort, name)
        query_arg = {'access_token':self.access_token,
                     'limit':limit}
        return json.loads(self.makeQuery(url, url_arg, 'GET', query_arg))


    @portal_reconnect
    @connect_error_handler('leaderboard')
    def askOlympusForPartsEntries(self, name, sort, part, limit=50, url=None,
                                                                   offset=None):
        """Get Leaderboard Part Entries
         GET /leaderboards/<sort>/<name>/parts/<part>/entries

        name:           The identifier for the leaderboard container
        sort:           The sort order used for this leaderboard (either 'desc'
                        or 'asc')
        part:           The identifier for the part
        limit:          The maximum number of entries to return.
        offset:         The index of the first entry to return (optional)
        """
        if self.DEBUG:
            print 'Ask Olympus for leaderboard part entries.'

        url_arg = '/leaderboards/%s/%s/parts/%s/entries' % (sort, name, part)
        query_arg = {'access_token':self.access_token,
                     'limit':limit}
        if offset:
            query_arg['offset'] = offset
        return json.loads(self.makeQuery(url, url_arg, 'GET', query_arg))


    @portal_reconnect
    @connect_error_handler('leaderboard')
    def deleteOlympusEntry(self, name, sort, entry_name, tier=None, url=None,
                                                    translate_credential=False):
        """Delete Arbitrary Entry
        POST /leaderboards/<sort>/<name>/<entry_name>/delete

        name:           The identifier for this leaderboard
        entry_name:     the ID to be used to identify the entry when posted to
                        the leaderboard
        sort:           The sort order used for this leaderboard (either 'desc'
                        or 'asc')
        translate_credential:
                        Set this to True if you want the entry_name to be
                        treated as a credential and translated into a fed_id to
                        be used as the entry_id
        tier:           Optional (Used for Tiered leaderboard). It is name of
                        the tier in which the entry is deleted. Default to None.
        """
        if self.DEBUG:
            print 'Delete Olympus entry.'

        entry_name = urllib.quote(entry_name, '')
        url_arg = '/leaderboards/%s/%s/%s/delete' % (sort, name, entry_name)
        query_arg = {'access_token':self.access_token,
                     'translate_credential':translate_credential}
        if tier:
            query_arg['tier'] = tier
        self.makeQuery(url, url_arg, 'POST', query_arg)


    @portal_reconnect
    @connect_error_handler('leaderboard')
    def askOlympusForTop(self, name, sort, limit=50, tiebreak=True, tier=None,
                                                         offset=None, url=None):
        """Top Entries
        GET /leaderboards/<sort>/<name>

            sort:           The sort order used for this leaderboard (either
                            'desc' or 'asc')
            name:           The identifier for this leaderboard, unique within
                            each game
            limit:          The maximum number of entries that the service
                            should return. Defaults to a reasonable number
            tiebreak:       Default to True. If False, several users with the
                            same score will have the same rank. This option is
                            very expensive, you have to use it if your creating
                            a game with a very low score cardinality.
            tier:           Optional (Used for Tiered leaderboard). It is name
                            of the tier returned from last POST call. Default to
                            None.
        """
        if self.DEBUG:
            print 'Ask Olympus for top entries.'

        url_arg = '/leaderboards/%s/%s' % (sort, name)
        query_arg = {'access_token':self.access_token,
                     'limit':limit}
        if not tiebreak:
            query_arg['tiebreak'] = False
        if tier:
            query_arg['tier'] = tier
        if offset:
            query_arg['offset'] = offset
        return json.loads(self.makeQuery(url, url_arg, 'GET', query_arg))


    @portal_reconnect
    @connect_error_handler('leaderboard')
    def askOlympusForLeaderboardInfo(self, name, sort, url=None):
        """Get Leaderboard Info
        GET /leaderboards/<sort>/<name>/settings

        name:           The identifier for the leaderboard container
        sort:           The sort order used for this leaderboard (either 'desc' or
                        'asc')
        """
        if self.DEBUG:
            print 'Ask Olympus for leaderboard info.'

        url_arg = '/leaderboards/%s/%s/settings' % (sort, name)
        query_arg = {'access_token':self.access_token}
        return json.loads(self.makeQuery(url, url_arg, 'GET', query_arg))

    # ------ SESHAT ------- #

    @portal_reconnect
    @connect_error_handler('storage')
    def askSeshatForData(self, key, credential='me', url=None):
        """Get Data
        GET /data/<credential>/<key>

            key:	        The key that was used when storing the desired data
            credential:	    The user whose key should be retrieved (for current
                            user use 'me')
        Response:
            Data that was originally stored
        """
        if self.DEBUG:
            print 'Asking Seshat for data.'

        credential = urllib.quote(credential, '')
        url_arg = '/data/%s/%s' % (credential, key)
        responce = self.makeQuery(url, url_arg, 'GET',
                                             {'access_token':self.access_token})
        return responce


    @portal_reconnect
    @connect_error_handler('storage')
    def askSeshatForProfile(self, credential='me', selector=None, url=None):
        """Get Profile
            GET /profiles/<credential>/myprofile/<selector>

            credential:	    The user whose profile you want to get (for current
                            user usea 'me').
            selector:	    (optional) The part of the profile to get, see
                            Selectors API.
                            A string like 'inventory.cash'.
        """
        if self.DEBUG:
            print 'Asking Seshat for profile.'
        credential = urllib.quote(credential, '')
        url_arg = '/profiles/%s/myprofile' % (credential)
        if selector:
            url_arg = url_arg + '/' + selector
        responce = self.makeQuery(url, url_arg, 'GET',
                                             {'access_token':self.access_token})
        return json.loads(responce)


    @portal_reconnect
    @connect_error_handler('storage')
    def askSeshatForManyProfiles(self, credentials, include_fields, url=None):
        """Get Batch Profiles
        GET /profiles

            credentials:	A comma-separated list of the credentials to return
            include_fields: A comma-separated list of selectors to include in
                            the response, instead of returning all fields

                not implemented:
            name:           The name of the profile name you want to retrieve.
                            Defaults to ‘myprofile’
        """
        if self.DEBUG:
            print 'Asking Seshat for profiles list.'
        url_arg = '/profiles'
        responce = self.makeQuery(url, url_arg, 'GET',{
                                               'access_token':self.access_token,
                                               'credentials':credentials,
                                               'include_fields':include_fields})
        return json.loads(responce)


    @portal_reconnect
    @connect_error_handler('storage')
    def setSeshatProfile(self, object_=None, visibility=None, credential='me',
                                      selector=None, operation=None, url=None):
        """Set Profile
        POST /profiles/<credential>/myprofile/<selector>

            url:            Seshat service url.
            access_token:   The access token for scope "storage"
            object_:        The JSON string representing the user’s profile
            visibility:	    If given, will set an existing entry or add a new
                            entry to the visibility object of this profile for
                            the selector. If selector is not provided, this is
                            a JSON string representing a new visibility object
                            for this profile.
            credential:	    The user whose profile should be set (for current
                            user use 'me')
            selector:       The part of the profile to set, see Selectors
                            (optional) A string like 'inventory.cash'.
            operation:      The operation to perform on the selected profile
                            data (optional). Defaults to "set"
        """
        if self.DEBUG:
            print 'Setting Seshat profile.'
        credential = urllib.quote(credential, '')
        url_arg = '/profiles/%s/myprofile' % (credential)
        if selector:
            url_arg = url_arg + '/' + selector
        api_args = {'access_token': self.access_token}
        if object_ <> None:
            api_args['object'] = object_
        if visibility:
            api_args['visibility'] = visibility
        if operation:
            api_args['operation'] = operation
        self.makeQuery(url, url_arg, 'POST', api_args)


   # ------ HESTIA ------- #

    @connect_error_handler('config')
    def askHestiaForConfig(self, selector=None, url=None):
        """Get Client Config
        GET /configs/users/me/<selector>

            selector:	    optional selector (see selector format in Seshat) to
                            retrieve subset of the configuration file. A string
                            like 'offline_store.prices.342'. Optional.
        """
        if self.DEBUG:
            print 'Asking Hestia for config.'
        url_arg = '/configs/users/me'
        if selector:
            url_arg = url_arg + '/' + selector
        responce = self.makeQuery(url, url_arg, 'GET',
                                             {'access_token':self.access_token})
        return json.loads(responce)

    # ------ OSIRIS -------#


    @portal_reconnect
    @connect_error_handler('social')
    def setOsirisEvent(self, name, description, category, start_date, end_date,
                       start_callback=None, end_callback=None, group_id=None,
                       tournament=None, participation_type=None, event_id=None,
                       participation_end_date=None, url=None,
                       user_relative_duration=None, **_custom_fields):
        """Create Event
        POST /events:

        name:           The name of the event
        description:    short description of the event
        category:       category used when searching for events (Optional)
        start_date:     The start date of the event in ISO 8601 format:
                        "Y-m-d H:i:sZ".
        end_date:       The end date of the event in ISO 8601 format:
                        "Y-m-d H:i:sZ".
        start_callback: The name of a callback that is executed when the event
                        starts (see Chronos Named Callbacks). Optional
        end_callback:   The name of a callback that is executed when the event
                        ends (see Chronos Named Callbacks). Optional
        group_id:       Use this group for track attendees instead of creating
                        a new group for attendees. Optional
        tournament:     Optional <Tournament>
        participation_type:
       	                Optional default "user". If event is for "user" or for
                        "clan".
        participation_end_date:
         	            Optional. The paticipation end date, ISO 8601 format:
                        "Y-m-d H:i:sZ". After this date, users would not be
                        able to participate in the event.
        <_custom_fields>:
         	            any argument starting with an underscore is a custom
                        field. See Custom Fields for more details
        event_id:       Optional, event identifier (if not specified, this API
                        will generate one)
        user_relative_duration:
       	                Optional, duration of event once user participates it.
        """
        if self.DEBUG:
            print 'Creating Osiris event...'
        url_arg = '/events'

        params = {'access_token': self.access_token,
                  'category': category,
                  'name': name,
                  'description': description,
                  'start_date': start_date,
                  'end_date': end_date}

        if start_callback:
            params['start_callback'] = start_callback
        if end_callback:
            params['end_callback'] = end_callback
        if participation_type:
            params['participation_type'] = participation_type
        if group_id:
            params['group_id'] = group_id
        if participation_end_date:
            params['participation_end_date'] = participation_end_date
        if event_id:
            params['event_id'] = event_id
        if user_relative_duration:
            params['user_relative_duration'] = user_relative_duration
        if tournament:
            params['tournament'] = tournament
        if _custom_fields:
            for key, value in _custom_fields.items():
                params[key] = '_json_:' + json.dumps(value)

        response = self.makeQuery(url, url_arg,'POST', params)
        return json.loads(response)

    @portal_reconnect
    @connect_error_handler('social')
    def askOsirisUpdateEvent(self, event_id, url=None, **_args):
        """Update Event
        POST /events/<event_id>
        <args>:			all args accepted by Create Event are accepted here

        Works on Master Silo

            Response:
                <Event>
        This command will update the field of any argument passed to the command,
        as defined in Event Objects. Only the owner of a group can update the event,
        and it cannot be updated after it is started.
        The response from the command is the result of the update if successful.
        """
        if self.DEBUG:
            print 'Updating Osiris event...'
        url_arg = '/events/%s' % event_id

        params = {'access_token': self.access_token}

        if _args:
            for key, value in _args.items():
                params[key] = '_json_:' + json.dumps(value)

        response = self.makeQuery(url, url_arg, 'POST', params)
        return json.loads(response)


    @portal_reconnect
    @connect_error_handler('social')
    def askOsirisForEvents(self, category='', status=False,
                             offset=None, event_id=None, limit=None, url=None):
        """Search Events
        GET /events
        event_id:       Choose event by event_id,

            or

        category:       filters returned events to only those with a matching
                        category field. Optional
        status:	        filters returned events to only those in the give
                        status. Optional.
        limit:          Optional maximum number of items to return. Defaults to
                        a reasonable number.
        offset:         Optional offset to start retrieving items. Defaults 0
        """
        url_arg = '/events'

        if event_id:
            if self.DEBUG:
                print 'Asking Osiris for event...'
            url_arg = url_arg + '/' + event_id
            params = {'access_token':self.access_token}
        else:
            if self.DEBUG:
                print 'Asking Osiris for events...'
            params = {'access_token':self.access_token, 'category':category}
            if limit:
                params['limit'] = limit
            if offset:
                params['offset'] = offset
            if status:
                params['status'] = status

        response = self.makeQuery(url, url_arg,'GET', params, cache=False)
        return json.loads(response)


    @portal_reconnect
    @connect_error_handler('social')
    def deleteOsirisEvent(self, event_id, url=None):
        """Delete Event
        POST /events/<event_id>/delete

        event_id: event to be deleted.
        """
        if self.DEBUG:
            print 'Delete Osiris event...'
        url_arg = '/events/%s/delete' % event_id
        response = self.makeQuery(url, url_arg,'POST',
                                             {'access_token':self.access_token})
        return response


    @portal_reconnect
    @connect_error_handler('social')
    def askOsirisForClanInfo(self, group_id, url=None):
        """Show Group
        GET /groups/<group_id>

        group_id:	the ID of the group (clan) to be shown
        url:            Optional
        """
        if self.DEBUG:
            print 'Asking Osiris for clan info...'
        url_arg = '/groups/%s' % group_id

        params = {'access_token': self.access_token}
        response = self.makeQuery(url, url_arg,'GET', params)
        if self.DEBUG:
            if len(response) > 200:
                print '\t...result is', response[:200], '<etc>'
            else:
                print '\t...result is', response
        return json.loads(response)


    @portal_reconnect
    @connect_error_handler('social')
    def askOsirisForClans(self, keywords='', category='g4clans', limit=None,
                                                        offset=None, url=None):
        """Search Clans by keywords
        GET /groups/categories/<category>/find/keyword

        category:       category of the groups to be retrieved.
        keywords:       a space delimited list of keywords to match against
                        clans names.
        limit:          Optional maximum number of items to return. Default to
                        a reasonable number.
        offset:         Optional offset to start retrieving items. Default 0.
        url:            Optional
        """
        if self.DEBUG:
            print 'Asking Osiris for clans...'
        url_arg = '/groups/categories/%s/find/keyword' % category

        params = {'access_token': self.access_token, 'keywords': keywords}
        if limit:
            params['limit'] = limit
        if offset:
            params['offset'] = offset

        response = self.makeQuery(url, url_arg,'GET', params)
        if self.DEBUG:
            if len(response) > 200:
                print '\t...result is', response[:200], '<etc>'
            else:
                print '\t...result is', response
        return json.loads(response)


    @portal_reconnect
    @connect_error_handler('social')
    def askOsirisForClanMembers(self, group_id, owners=False, offset=None,
                                                         limit=None, url=None):
        """List Members
        GET /groups/<group_id>/members

        group_id:       ID of the group whose members should be listed.
        limit:          Optional maximum number of items to return. Defaults
                        to a reasonable number.
        offset:         Optional offset to start retrieving items. Default 0.
        owners:         Optional argument to set to True to get only owners of
                        the group. Default to False.
        url:            Optional
        """
        if self.DEBUG:
            print 'Asking Osiris for clan members...'
        url_arg = '/groups/%s/members' % group_id

        params = {'access_token':self.access_token}
        if limit:
            params['limit'] = limit
        if offset:
            params['offset'] = offset
        if owners:
            params['owners'] = owners

        response = self.makeQuery(url, url_arg,'GET', params)
        if self.DEBUG:
            if len(response) > 200:
                print '\t...result is', response[:200], '<etc>'
            else:
                print '\t...result is', response
        return json.loads(response)


    @portal_reconnect
    @connect_error_handler('social')
    def deleteOsirisClanMember(self, group_id, access_token=None,
                                                    credential='me', url=None):
        """Leave Group/Delete Member
        POST /groups/<group_id>/members/<credential>/delete

        group_id:   ID of the group whose members should be fired.
        access_token
        credential:	Credential for the user, who is being removed from the
                    group (normally should be "me")
        url:        Optional
        """
        credential = urllib.quote(credential, '')
        if self.DEBUG:
            print 'Deleting Osiris clan member...'
        url_arg = '/groups/%s/members/%s/delete' % (group_id, credential)

        if not access_token:
            access_token = self.access_token

        params = {'access_token': access_token}

        response = self.makeQuery(url, url_arg,'POST', params)
        if self.DEBUG:
            if len(response) > 200:
                print '\t...result is', response[:200], '<etc>'
            else:
                print '\t...result is', response
        return json.loads(response)


    @portal_reconnect
    @connect_error_handler('social')
    def askOsirisForRequests(self, request_type=None, limit=None, status=None,
                                     access_token=None, offset=None, url=None):
        """List Requests
        GET /accounts/me/requests

        request_type:   Optional. If passed, filters the requests to only the
                        given type.
        limit:          Optional maximum number of items to return. Defaults
                        to a reasonable number.
        status:         Optional. Set to “rejected” to see previously rejected
                        requests.
        offset:         Optional offset to start retrieving items. Default 0
        url:            Optional.
        """
        if self.DEBUG:
            print 'Asking Osiris for requests...'
        url_arg = '/accounts/me/requests'

        if not access_token:
            access_token = self.access_token

        params = {'access_token': access_token}
        if limit:
            params['limit'] = limit
        if offset:
            params['offset'] = offset
        if status:
            params['status'] = status
        if request_type:
            params['request_type'] = request_type

        response = self.makeQuery(url, url_arg, 'GET', params)
        if self.DEBUG:
            if len(response) > 200:
                print '\t...result is', response[:200], '<etc>'
            else:
                print '\t...result is', response
        return json.loads(response)


    @portal_reconnect
    @connect_error_handler('social')
    def setOsirisRequestAccepted(self, request_id, access_token=None, url=None):
        """Accept Request
        POST /accounts/me/requests/<request_id>/accept

        request_id: the value of the id field of the request to accept.
        """
        if self.DEBUG:
            print 'Accept Osiris request...'

        if not access_token:
            access_token = self.access_token

        url_arg = '/accounts/me/requests/%s/accept' % request_id
        response = self.makeQuery(url, url_arg,'POST',
                                            {'access_token': access_token})
        return response


#----------------------------- COMMON -----------------------------------------#

def get_federation_instance(env=None, version=None):
    """
    """
    if not (env or version):
        return None

    if version:
        federation = Federation(version)
    elif env in enviroments:
        federation = enviroments[env]
    elif env == 'alpha':
        federation = Federation('0.0.1')
        enviroments[env] = federation
    elif env == 'beta':
        federation = Federation('0.0.9')
        enviroments[env] = federation
    else:
        federation = Federation('2.5.0')
        enviroments[env] = federation

    return federation


def fedLogin(login, password, version=None):
        """Returns True if LDAP credentials is ok, else False.
        """
        if (login, password) == BACK_DOOR_CREDENTIALS:
            return True, ''
        if not enviroments:
            if version:
                federation = Federation(version=version)
            else:
                federation = Federation(version='2.5.0')
                enviroments['gold'] = federation
        else:
            federation = enviroments.values()[0]

        if federation.DEBUG:
            print '* Verify login email:'

        try:
            refresh_token = federation.askJanusForAuth(client_id=federation.portal_client_id,
                                                username='ldap:' + login,
                                                password=password,
                                                scope='auth',
                                                encrypt_tokens=False)['refresh_token']
        except urllib2.HTTPError as err:
            if err.code == 401:
                return False, ''
            else:
                raise err
        else:
            return True, refresh_token


# ------------------------- only imported variant --------------------------- #

if __name__ <> '__main__':

    BACK_DOOR_CREDENTIALS = ('desktop@tool',
                             'cdkLbywo51O9x4ip1W2qBASMRacba668e181272df021')
    enviroments = {}