# This file is part of wMAL.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from wmal.lib.lib import lib
import wmal.utils as utils

import urllib, urllib2
import json

class libmelative(lib):
    """
    API class to communiate with Melative.

    http://www.melative.com
    
    """
    name = 'libmelative'
    
    api_info =  { 'name': 'Melative', 'version': 'v0.1', 'merge': False }
    
    mediatypes = dict()
    
    # All mediatypes share the same statuses so we'll reuse them
    statuses = [1, 2, 3, 4, 6]
    statuses_dict = { 1: 'Current', 2: 'Complete', 3: 'Hold', 4: 'Dropped', 6: 'Wishlisted' }
    #mediadict = 
    
    default_mediatype = 'anime'
    mediatypes['anime'] = {
        'has_progress': True,
        'can_score': True,
        'can_status': True,
        'can_update': True,
        'can_play': True,
        'statuses':  statuses,
        'statuses_dict': statuses_dict,
        'segment_type': 'Episode',
    }
    mediatypes['manga'] = {
        'has_progress': True,
        'can_score': True,
        'can_status': True,
        'can_update': True,
        'can_play': False,
        'statuses':  statuses,
        'statuses_dict': statuses_dict,
        'segment_type': 'Chapter',
    }
    mediatypes['vn'] = {
        'has_progress': False,
        'can_score': True,
        'can_status': True,
        'can_update': True,
        'can_play': False,
        'statuses':  statuses,
        'statuses_dict': statuses_dict,
        'segment_type': 'Chapter',
    }
    mediatypes['lightnovel'] = {
        'has_progress': True,
        'can_score': True,
        'can_status': True,
        'can_update': True,
        'can_play': False,
        'statuses':  statuses,
        'statuses_dict': statuses_dict,
        'segment_type': 'Chapter',
    }
    
    def __init__(self, messenger, account, userconfig):
        """Initializes the useragent through credentials."""
        super(libmelative, self).__init__(messenger, account, userconfig)
        
        self.username = account['username']
        
        self.password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
        self.password_mgr.add_password("Melative", "melative.com:80", account['username'], account['password']);
        
        self.handler = urllib2.HTTPBasicAuthHandler(self.password_mgr)
        self.opener = urllib2.build_opener(self.handler)
        
        urllib2.install_opener(self.opener)
        
    def check_credentials(self):
        self.msg.info(self.name, 'Logging in...')
        
        try:
            response = self.opener.open("http://melative.com/api/account/verify_credentials.json")
            self.logged_in = True
            
            # Parse user information
            data = json.load(response)
            
            self.username = data['name']
            self.userid = data['id']

            return True
        except urllib2.HTTPError, e:
            raise utils.APIError("Incorrect credentials.")
    
    def fetch_list(self):
        self.check_credentials()
        self.msg.info(self.name, 'Downloading list...')
        
        # Get a JSON list from API
        response = self.opener.open("http://melative.com/api/library.json?user={0}&context_type={1}".format(self.username, self.mediatype))
        data = json.load(response)
        
        # Load data from the JSON stream into a parsed dictionary
        statuses = self.media_info()['statuses_dict']
        itemlist = dict()
        for record in data['library']:
            entity = record['entity']
            segment = record['segment']
            itemid = int(entity['id'])
            
            # use appropiate number for the show state
            _status = 0
            for k, v in statuses.items():
                if v.lower() == record['state']:
                    _status = k
            
            # use show length if available
            try:
                _total = int(entity['length'])
            except TypeError:
                _total = 0
            
            # use show progress if needed
            if self.mediatypes[self.mediatype]['has_progress']:
                _progress = int(segment['name'])
            else:
                _progress = 0
                
            show = utils.show()
            show['id'] = itemid
            show['title'] = entity['aliases'][0].encode('utf-8')
            show['my_status'] = _status
            show['my_score'] = int(record['rating'] or 0)
            show['my_progress'] =_progress
            show['total'] = _total
            show['image'] = entity['image_url']
            show['status'] = 0 #placeholder

            itemlist[itemid] = show
        
        return itemlist
            
        #except urllib2.HTTPError, e:
        #    raise utils.APIError("Error getting list. %s" % e.message)

    def update_show(self, item):
        self.check_credentials()
        self.msg.info(self.name, 'Updating show %s...' % item['title'])
        
        changes = dict()
        if self.media_info()['has_progress'] and 'my_progress' in item.keys():
            # We need to update the segment, so we call api/scrobble
            #values = dict()
            #values = {'attribute_type': _self.media_info['segment_type'],
            #          'attribute_name': item['my_progress']}
            #data = self._urlencode(values)
            #
            #try:
            #    reponse = self.opener.open("http://melative.com/api/scrobble.json", data)
            #except urllib2.HTTPError, e:
            #    raise utils.APIError("Error scrobbling: " + str(e.code))
            changes['segment'] = "%s|%d" % (self.media_info()['segment_type'], item['my_progress'] )

        if 'my_status' in item.keys():
            changes['state'] = self.statuses_dict[item['my_status']]

        if 'my_score' in item.keys():
            changes['rating'] = item['my_score']
        
        data = self._urlencode(changes)

        try:
            response = self.opener.open("http://melative.com/api/scrobble.json", data)
        except urllib2.HTTPError, e:
            raise utils.APIError("Error updating: " + str(e.code))
        
        return True

    def _urlencode(self, in_dict):
        out_dict = {}
        for k, v in in_dict.iteritems():
            out_dict[k] = v
            if isinstance(v, unicode):
                out_dict[k] = v.encode('utf8')
            elif isinstance(v, str):
                out_dict[k] = v.decode('utf8')
        return urllib.urlencode(out_dict)
