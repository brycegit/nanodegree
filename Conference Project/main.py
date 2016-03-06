#!/usr/bin/env python
import webapp2
from google.appengine.api import app_identity
from google.appengine.api import mail
from conference import ConferenceApi
from google.appengine.api import app_identity
from google.appengine.api import mail

class SetAnnouncementHandler(webapp2.RequestHandler):
    def get(self):
        """Set Announcement in Memcache."""

        ConferenceApi._cacheAnnouncement()

class SendConfirmationEmailHandler(webapp2.RequestHandler):
    def post(self):
        """Send email confirming Conference creation."""
        mail.send_mail(
            'noreply@%s.appspotmail.com' % (
                app_identity.get_application_id()),     # from
            self.request.get('email'),                  # to
            'You created a new Conference!',            # subj
            'Hi, you have created a following '         # body
            'conference:\r\n\r\n%s' % self.request.get(
                'conferenceInfo')
        )        

class AssignFeaturedSpeakerHandler(webapp2.RequestHandler):
    def post(self):
        """Set Announcement in Memcache."""

        featspeak = self.request.get('speaker')
        ConferenceApi._cacheFeaturedSpeaker(featspeak)


app = webapp2.WSGIApplication([
    ('/crons/set_announcement', SetAnnouncementHandler),
    ('/tasks/assign_featured_speaker', AssignFeaturedSpeakerHandler),
    ('/tasks/send_confirmation_email', SendConfirmationEmailHandler),
], debug=False)
