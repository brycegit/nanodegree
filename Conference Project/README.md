App Engine application for the Udacity training course.

## Products
- [App Engine][1]

## Language
- [Python][2]

## APIs
- [Google Cloud Endpoints][3]

## Setup Instructions
1. Update the value of `application` in `app.yaml` to the app ID you
   have registered in the App Engine admin console and would like to use to host
   your instance of this sample.
1. Update the values at the top of `settings.py` to
   reflect the respective client IDs you have registered in the
   [Developer Console][4].
1. Update the value of CLIENT_ID in `static/js/app.js` to the Web client ID
1. (Optional) Mark the configuration files as unchanged as follows:
   `$ git update-index --assume-unchanged app.yaml settings.py static/js/app.js`
1. Run the app with the devserver using `dev_appserver.py DIR`, and ensure it's running by visiting
   your local server's address (by default [localhost:8080][5].)
1. Generate your client library(ies) with [the endpoints tool][6].
1. Deploy your application.

## Overview of Sessions and Speakers
Sessions: implemented by creating 3 classes that methods interact with: 1) Session 2) SessionForm 3) SessionForms
Speaker: Speaker names are stored in the Session class. The getFeaturedSpeaker method utilizes memcache since only a simple message needs to be stored.

## New Query Types - two added
- kind: Conference
  properties:
  - name: topics
  - name: name

- kind: Session
  properties:
  - name: name
  - name: startTime

##Query Problem
Problem: The problem is that you cannot have two inequality filters in one query
My Solution (implemented in FilterPlayground endpoint): Do one inequality filter on start time; 
then loop through sessions and add sessions to new list that meet the 'typeOfSession' criteria

[1]: https://developers.google.com/appengine
[2]: http://python.org
[3]: https://developers.google.com/appengine/docs/python/endpoints/
[4]: https://console.developers.google.com/
[5]: https://localhost:8080/
[6]: https://developers.google.com/appengine/docs/python/endpoints/endpoints_tool
