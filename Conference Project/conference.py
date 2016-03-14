#!/usr/bin/env python

"""
conference.py -- Udacity conference server-side Python App Engine API;
    uses Google Cloud Endpoints

$Id: conference.py,v 1.25 2014/05/24 23:42:19 wesc Exp wesc $

created by wesc on 2014 apr 21

"""

__author__ = 'wesc+api@google.com (Wesley Chun)'


from datetime import datetime

import endpoints
import time
from protorpc import messages
from protorpc import message_types
from protorpc import remote

from google.appengine.ext import ndb
from google.appengine.api import memcache
from google.appengine.api import taskqueue

from models import Profile
from models import ProfileMiniForm
from models import ProfileForm
from models import TeeShirtSize
from models import Conference
from models import ConferenceForm
from models import ConferenceForms
from models import ConferenceQueryForm
from models import ConferenceQueryForms
from models import BooleanMessage
from models import ConflictException
from models import StringMessage
from models import Session
from models import SessionForm
from models import SessionForms

from settings import WEB_CLIENT_ID

from utils import getUserId

EMAIL_SCOPE = endpoints.EMAIL_SCOPE
API_EXPLORER_CLIENT_ID = endpoints.API_EXPLORER_CLIENT_ID

DEFAULTS = {
    "city": "Default City",
    "maxAttendees": 0,
    "seatsAvailable": 0,
    "topics": [ "Default", "Topic" ],
}

OPERATORS = {
            'EQ':   '=',
            'GT':   '>',
            'GTEQ': '>=',
            'LT':   '<',
            'LTEQ': '<=',
            'NE':   '!='
            }

FIELDS =    {
            'CITY': 'city',
            'TOPIC': 'topics',
            'MONTH': 'month',
            'MAX_ATTENDEES': 'maxAttendees',
            }

CONF_GET_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    websafeConferenceKey=messages.StringField(1),
) 

SESSION_GET_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    session=messages.StringField(1),
)    

SESSION_POST_REQUEST = endpoints.ResourceContainer(
    SessionForm,
    websafeConferenceKey=messages.StringField(1),
)

SESS_BY_TYPE_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    websafeConferenceKey=messages.StringField(1),
    type=messages.StringField(2),
) 

SESS_BY_SPEAKER_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    speaker=messages.StringField(1),
) 

SESS_BY_TIME_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    startTime=messages.IntegerField(1, variant=messages.Variant.INT32),
) 

CONF_BY_CITY_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    city=messages.StringField(1),
) 

MEMCACHE_ANNOUNCEMENTS_KEY = "Recent Announcements"  

MEMCACHE_FEATURED_SPEAKER_KEY = "Featured Speaker"      

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


@endpoints.api( name='conference',
                version='v1',
                allowed_client_ids=[WEB_CLIENT_ID, API_EXPLORER_CLIENT_ID],
                scopes=[EMAIL_SCOPE])
class ConferenceApi(remote.Service):
    """Conference API v0.1"""

# - - - Profile objects - - - - - - - - - - - - - - - - - - -

    def _copyProfileToForm(self, prof):
        """Copy relevant fields from Profile to ProfileForm."""
        pf = ProfileForm()
        # Loop through all fields and copy data to form
        for field in pf.all_fields():
            if hasattr(prof, field.name):
              
                if field.name == 'teeShirtSize':
                    setattr(pf, field.name, getattr(TeeShirtSize, getattr(prof, field.name)))
                else:
                    setattr(pf, field.name, getattr(prof, field.name))
        pf.check_initialized()
        return pf


    def _getProfileFromUser(self):
        """Return user Profile from datastore, creating new one if non-existent."""
        # use endpoint method to get user info
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')

        user_id = getUserId(user)
      
        p_key = ndb.Key(Profile, user_id)
        
        profile = p_key.get()
        # if no profile exists, create one
        if not profile:
            profile = Profile(
                key = p_key, 
                displayName = user.nickname(), 
                mainEmail= user.email(),
                teeShirtSize = str(TeeShirtSize.NOT_SPECIFIED),
            )
        
            profile.put()
        return profile      


    def _doProfile(self, save_request=None):
        """Get user Profile and return to user, possibly updating it first."""
      
        prof = self._getProfileFromUser()

        # save new data
        if save_request:
            for field in ('displayName', 'teeShirtSize'):
                if hasattr(save_request, field):
                    val = getattr(save_request, field)
                    if val:
                        setattr(prof, field, str(val))
          
            prof.put()
  
        return self._copyProfileToForm(prof)


    @endpoints.method(message_types.VoidMessage, ProfileForm,
            path='profile', http_method='GET', name='getProfile')
    def getProfile(self, request):
        """Return user profile."""
        return self._doProfile()


    @endpoints.method(ProfileMiniForm, ProfileForm,
            path='profile', http_method='POST', name='saveProfile')
    def saveProfile(self, request):
        """Update & return user profile."""
        return self._doProfile(request)

# - - - Conference objects - - - - - - - - - - - - - - - - -

    def _copyConferenceToForm(self, conf, displayName):
        """Copy relevant fields from Conference to ConferenceForm."""
        cf = ConferenceForm()
        for field in cf.all_fields():
            if hasattr(conf, field.name):
                # turn date to string
                if field.name.endswith('Date'):
                    setattr(cf, field.name, str(getattr(conf, field.name)))
                else:
                    setattr(cf, field.name, getattr(conf, field.name))
            elif field.name == "websafeKey":
                setattr(cf, field.name, conf.key.urlsafe())
        if displayName:
            setattr(cf, 'organizerDisplayName', displayName)
        cf.check_initialized()
        return cf


    def _createConferenceObject(self, request):
        """Create or update Conference object, returning ConferenceForm/request."""
        
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = getUserId(user)

        if not request.name:
            raise endpoints.BadRequestException("Conference 'name' field required")

        # build out conference object
        data = {field.name: getattr(request, field.name) for field in request.all_fields()}
        del data['websafeKey']
        del data['organizerDisplayName']

        # set defaults if needed
        for df in DEFAULTS:
            if data[df] in (None, []):
                data[df] = DEFAULTS[df]
                setattr(request, df, DEFAULTS[df])

        # format dates
        if data['startDate']:
            data['startDate'] = datetime.strptime(data['startDate'][:10], "%Y-%m-%d").date()
            data['month'] = data['startDate'].month
        else:
            data['month'] = 0
        if data['endDate']:
            data['endDate'] = datetime.strptime(data['endDate'][:10], "%Y-%m-%d").date()

     
        if data["maxAttendees"] > 0:
            data["seatsAvailable"] = data["maxAttendees"]
            setattr(request, "seatsAvailable", data["maxAttendees"])

      
        p_key = ndb.Key(Profile, user_id)
       
        c_id = Conference.allocate_ids(size=1, parent=p_key)[0]
     
     
        c_key = ndb.Key(Conference, c_id, parent=p_key)
  
        data['key'] = c_key
        data['organizerUserId'] = request.organizerUserId = user_id

        # create conference and create send email task
        Conference(**data).put()
        taskqueue.add(params={'email': user.email(),
            'conferenceInfo': repr(request)},
            url='/tasks/send_confirmation_email'
        )

        return request


    @endpoints.method(ConferenceForm, ConferenceForm, path='conference',
            http_method='POST', name='createConference')
    def createConference(self, request):
        """Create new conference."""
        return self._createConferenceObject(request)

    @endpoints.method(ConferenceQueryForms, ConferenceForms,
            path='queryConferences',
            http_method='POST',
            name='queryConferences')
    def queryConferences(self, request):
        """Query for conferences."""
        conferences = self._getQuery(request)

        # return conferences within query params
        return ConferenceForms(
            items=[self._copyConferenceToForm(conf, "")
            for conf in conferences]
        )

    @endpoints.method(message_types.VoidMessage, ConferenceForms,
            path='getConferencesCreated',
            http_method='POST', name='getConferencesCreated')
    def getConferencesCreated(self, request):
        """Return conferences created by user."""
      
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')

     
        p_key = ndb.Key(Profile, getUserId(user))
       
        conferences = Conference.query(ancestor=p_key)
       
        prof = p_key.get()
        displayName = getattr(prof, 'displayName')
    
        return ConferenceForms(
            items=[self._copyConferenceToForm(conf, displayName) for conf in conferences]
        )    

    @endpoints.method(CONF_GET_REQUEST, ConferenceForm,
            path='conference/{websafeConferenceKey}',
            http_method='GET', name='getConference')
    def getConference(self, request):
        """Return requested conference (by websafeConferenceKey)."""
        
        conf = ndb.Key(urlsafe=request.websafeConferenceKey).get()
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % request.websafeConferenceKey)
        prof = conf.key.parent().get()
        return self._copyConferenceToForm(conf, getattr(prof, 'displayName'))

    @endpoints.method(message_types.VoidMessage, SessionForms,
        path='filterPlayground',
        http_method='GET', name='filterPlayground')
    def filterPlayground(self, request):
        """Filter Experimentation"""
        q = Session.query()
        q = q.order(Session.startTime)
        q = q.filter(Session.startTime < 1900)
        # create empty list for session not matching type of session criteria
        sessionsTypeExcluded = []
        for i in q:
            if i.typeOfSession != "workshop":
                sessionsTypeExcluded.append(i)

        return SessionForms(
            items=[self._copySessionToForm(sesh) for sesh in sessionsTypeExcluded]
        ) 

    @endpoints.method(SESS_BY_TIME_REQUEST, SessionForms,
        path='filterPlayground2',
        http_method='GET', name='filterPlayground2')
    def filterPlayground2(self, request):
        """Filter Experimentation #2 - Get Sessions in 4 hour window"""
        start = request.startTime
        end = request.startTime + 400
        q = Session.query()
        q = q.order(Session.startTime)
        q = q.filter(Session.startTime >= start)
        q = q.filter(Session.startTime <= end)
        
        return SessionForms(
            items=[self._copySessionToForm(sesh) for sesh in q]
        ) 

    @endpoints.method(CONF_BY_CITY_REQUEST, ConferenceForms,
        path='filterPlayground3',
        http_method='GET', name='filterPlayground3')
    def filterPlayground3(self, request):
        """Filter Experimentation #3 - Get Conferences in certain city"""
        q = Conference.query()
        q = q.order(Conference.city)
        q = q.filter(Conference.city == request.city)
        
        return ConferenceForms(
            items=[self._copyConferenceToForm(i, "") for i in q]
        )       

    def _getQuery(self, request):
        """Return formatted query from the submitted filters."""
        q = Conference.query()
        inequality_filter, filters = self._formatFilters(request.filters)

        # If exists, sort on inequality filter first
        if not inequality_filter:
            q = q.order(Conference.name)
        else:
            q = q.order(ndb.GenericProperty(inequality_filter))
            q = q.order(Conference.name)

        for filtr in filters:
            if filtr["field"] in ["month", "maxAttendees"]:
                filtr["value"] = int(filtr["value"])
            formatted_query = ndb.query.FilterNode(filtr["field"], filtr["operator"], filtr["value"])
            q = q.filter(formatted_query)
        return q


    def _formatFilters(self, filters):
        """Parse, check validity and format user supplied filters."""
        formatted_filters = []
        inequality_field = None

        for f in filters:
            filtr = {field.name: getattr(f, field.name) for field in f.all_fields()}

            try:
                filtr["field"] = FIELDS[filtr["field"]]
                filtr["operator"] = OPERATORS[filtr["operator"]]
            except KeyError:
                raise endpoints.BadRequestException("Filter contains invalid field or operator.")

            # Every operation except "=" is an inequality
            if filtr["operator"] != "=":
                # check if inequality operation has been used in previous filters
                # disallow the filter if inequality was performed on a different field before
                # track the field on which the inequality operation is performed
                if inequality_field and inequality_field != filtr["field"]:
                    raise endpoints.BadRequestException("Inequality filter is allowed on only one field.")
                else:
                    inequality_field = filtr["field"]

            formatted_filters.append(filtr)
        return (inequality_field, formatted_filters)    

# - - - Registration - - - - - - - - - - - - - - - - - - - -

    @ndb.transactional(xg=True)
    def _conferenceRegistration(self, request, reg=True):
        """Register or unregister user for selected conference."""
        retval = None
        prof = self._getProfileFromUser() 

    
        wsck = request.websafeConferenceKey
        conf = ndb.Key(urlsafe=wsck).get()
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % wsck)

        
        if reg:
            if wsck in prof.conferenceKeysToAttend:
                raise ConflictException(
                    "You have already registered for this conference")

            
            if conf.seatsAvailable <= 0:
                raise ConflictException(
                    "There are no seats available.")

           
            prof.conferenceKeysToAttend.append(wsck)
            conf.seatsAvailable -= 1
            retval = True

       
        else:
            
            if wsck in prof.conferenceKeysToAttend:

              
                prof.conferenceKeysToAttend.remove(wsck)
                conf.seatsAvailable += 1
                retval = True
            else:
                retval = False

       
        prof.put()
        conf.put()
        return BooleanMessage(data=retval)


    @endpoints.method(CONF_GET_REQUEST, BooleanMessage,
            path='conference/{websafeConferenceKey}',
            http_method='POST', name='registerForConference')
    def registerForConference(self, request):
        """Register user for selected conference."""
        return self._conferenceRegistration(request)

    @endpoints.method(message_types.VoidMessage, ConferenceForms,
            path='conferences/attending',
            http_method='GET', name='getConferencesToAttend')
    def getConferencesToAttend(self, request):
        """Get list of conferences that user has registered for."""
        
        prof = self._getProfileFromUser() 

        keys = prof.conferenceKeysToAttend

        listofkeys = []
        for i in keys:
            confFromNdb = ndb.Key(urlsafe=i)
            listofkeys.append(confFromNdb)
        
        conferences = ndb.get_multi(listofkeys)
       
        return ConferenceForms(items=[self._copyConferenceToForm(conf, "")\
        for conf in conferences]
        )

    @staticmethod
    def _cacheAnnouncement():
        """Create Announcement & assign to memcache; used by
        memcache cron job & putAnnouncement().
        """
        confs = Conference.query(ndb.AND(
            Conference.seatsAvailable <= 5,
            Conference.seatsAvailable > 0)
        ).fetch(projection=[Conference.name])

        if confs:
          
            announcement = '%s %s' % (
                'Last chance to attend! The following conferences '
                'are nearly sold out:',
                ', '.join(conf.name for conf in confs))
            memcache.set(MEMCACHE_ANNOUNCEMENTS_KEY, announcement)
        else:
       
            announcement = ""
            memcache.delete(MEMCACHE_ANNOUNCEMENTS_KEY)

        return announcement


    @endpoints.method(message_types.VoidMessage, StringMessage,
            path='conference/announcement/get',
            http_method='GET', name='getAnnouncement')
    def getAnnouncement(self, request):
        """Return Announcement from memcache."""
   
        announcement = ""
        if memcache.get(MEMCACHE_ANNOUNCEMENTS_KEY):
            announcement = memcache.get(MEMCACHE_ANNOUNCEMENTS_KEY)
        return StringMessage(data=announcement)

    @endpoints.method(CONF_GET_REQUEST, SessionForms,
            path='conference/{websafeConferenceKey}/session',
            http_method='GET', name='getConferenceSession')
    def getConferenceSession(self, request):
        """Return all sessions within a conference"""
        
        p_key = ndb.Key(Conference, request.websafeConferenceKey)
        sessions = Session.query(ancestor=p_key)
        if not sessions:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % request.websafeConferenceKey)

        return SessionForms(
            items=[self._copySessionToForm(sesh) for sesh in sessions]
        ) 


    @endpoints.method(SESSION_POST_REQUEST, SessionForm, path='session',
            http_method='POST', name='createSession')
    def createSession(self, request):
        """Create new conference."""
        return self._createSessionObject(request)

    def _copySessionToForm(self, request):
        sf = SessionForm()
        data = {field.name: getattr(request, field.name) for field in sf.all_fields()}
        for field in sf.all_fields():
            if hasattr(request, field.name):
                if field.name == 'date':
                    setattr(sf, field.name, str(getattr(request, field.name)))
                elif field.name == 'startTime':
                        if data['startTime']:
                            setattr(sf, field.name, int(getattr(request, field.name)))
                else:
                    setattr(sf, field.name, getattr(request, field.name))
        sf.check_initialized()
        return sf
            
    def _createSessionObject(self, request):
        """Create or update Session object, returning SessionForm/request."""
        
        data = {field.name: getattr(request, field.name) for field in request.all_fields()}

        if data['date']:
            data['date'] = datetime.strptime(data['date'][:10], "%Y-%m-%d").date()

        p_key = ndb.Key(Conference, request.websafeConferenceKey)

        s_id = Session.allocate_ids(size=1, parent=p_key)[0]
  
        s_key = ndb.Key(Session, s_id, parent=p_key)
 
        data['key'] = s_key
        del data['websafeConferenceKey']
        # create session and create task for assigning featured speaker to memcache
        Session(**data).put()
        if data['speaker']:
            taskqueue.add(url='/tasks/assign_featured_speaker', params={'speaker': data['speaker']})
        return self._copySessionToForm(request)    

    @endpoints.method(SESS_BY_TYPE_REQUEST, SessionForms, 
            path='conference/{websafeConferenceKey}/session/{type}', http_method='GET', name='conferenceSessionsByType')
    def getConferenceSessionsByType(self, request):
        """Get all session with a specified type"""
        p_key = ndb.Key(Conference, request.websafeConferenceKey)
        sessionType = request.type
       
        q = Session.query(ancestor=p_key)

        q = q.filter(Session.typeOfSession == sessionType)

        return SessionForms(
            items=[self._copySessionToForm(sesh) for sesh in q]
        ) 

    @endpoints.method(SESS_BY_SPEAKER_REQUEST, SessionForms, 
        path='sessions/{speaker}', http_method='GET', name='conferenceSessionsBySpeaker')
    def getConferenceSessionsBySpeaker(self, request):
        """Get all sessions with specified speaker"""
        sessionSpeaker = request.speaker
       
        q = Session.query()

        q = q.filter(Session.speaker == sessionSpeaker)

        return SessionForms(
            items=[self._copySessionToForm(sesh) for sesh in q]
        ) 

    @endpoints.method(SESSION_GET_REQUEST, BooleanMessage,
            path='sessions/{session}',
            http_method='POST', name='addSessionToWishlist')
    def addSessionToWishlist(self, request):
        """Add session to user wishlist"""
        prof = self._getProfileFromUser()
        prof.sessionWishList.append(request.session)
        prof.put()
        return BooleanMessage(data=True)

    @endpoints.method(message_types.VoidMessage, SessionForms, 
        path='conference/{websafeConferenceKey}/mysessions', http_method='GET', name='getSessionsInWishlist')
    def getSessionsInWishlist(self, request):
        """Get all sessions in logged in user's wishlist"""
        # get user
        prof = self._getProfileFromUser()
        # find sessions in conf
        q = Session.query()
        sessionsInWishlist = []
        for i in q:
            key = i.key.urlsafe()
            if key in prof.sessionWishList:
                sessionsInWishlist.append(i)
    
        return SessionForms(
            items=[self._copySessionToForm(sesh) for sesh in sessionsInWishlist]
        ) 

    @endpoints.method(SESSION_GET_REQUEST, BooleanMessage,
            path='sessions/{session}/delete', http_method="POST", name='deleteSessionInWishlist')
    def deleteSessionInWishlist(self, request):
        """Delete specified session from wishlist"""
        prof = self._getProfileFromUser()
        if request.session in prof.sessionWishList:
                wishlist = prof.sessionWishList
                index = wishlist.index(request.session)
        del prof.sessionWishList[index]
        prof.put()
        print prof.sessionWishList
        return BooleanMessage(data=True)
        

    @staticmethod
    def _cacheFeaturedSpeaker(speaker):
        """Create Featured Speaker announcement & assign to memcache"""
        featspeak = speaker

        if featspeak:
            announcement = '%s %s' % ('The featured speaker is', featspeak)
            memcache.set(MEMCACHE_FEATURED_SPEAKER_KEY, announcement)
        else:
            announcement = "Nothing now."
        return announcement
 
    @endpoints.method(message_types.VoidMessage, StringMessage,
            path='getFeaturedSpeaker', http_method='GET', name='getFeaturedSpeaker')
    def getFeaturedSpeaker(self, request):
        """Get featured speaker from memcache"""
        # key = self.request.get('key')
        announcement = memcache.get(MEMCACHE_FEATURED_SPEAKER_KEY)
        return StringMessage(data=announcement)


api = endpoints.api_server([ConferenceApi]) 

