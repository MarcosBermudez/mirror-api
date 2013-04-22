#!/usr/bin/python

# Copyright (C) 2013 Gerwin Sturm, FoldedSoft e.U.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Notification/subscription handler

Handles subscription post requests coming from the Mirror API and forwards
the requests to the relevant demo services.

"""

__author__ = 'scarygami@gmail.com (Gerwin Sturm)'

import utils
from auth import get_auth_service
from demos import DEMOS

import logging
import json
from datetime import datetime
from google.appengine.ext import ndb

demo_services = []
for demo in DEMOS:
    demo_services.append(__import__("demos." + demo, fromlist="*"))


class TimelineNotifyHandler(utils.BaseHandler):
    def post(self):
        """Callback for Timeline updates."""
        message = self.request.body
        data = json.loads(message)
        logging.info(data)

        self.response.status = 200

        gplus_id = data["userToken"]
        verifyToken = data["verifyToken"]
        user = ndb.Key("User", gplus_id).get()
        if user is None or user.verifyToken != verifyToken:
            logging.info("Wrong user")
            return

        if data["operation"] != "UPDATE" or data["userActions"][0]["type"] != "SHARE":
            logging.info("Wrong operation")
            return

        service = get_auth_service(gplus_id)

        if service is None:
            logging.info("No valid credentials")
            return

        result = service.timeline().get(id=data["itemId"]).execute()
        logging.info(result)

        for demo_service in demo_services:
            if hasattr(demo_service, "handle_item"):
                new_item = demo_service.handle_item(result)
                if new_item is not None:
                    new_result = service.timeline().insert(body=new_item).execute()
                    logging.info(new_result)


class LocationNotifyHandler(utils.BaseHandler):
    def post(self):
        """Callback for Location updates."""
        message = self.request.body
        data = json.loads(message)

        self.response.status = 200

        gplus_id = data["userToken"]
        verifyToken = data["verifyToken"]
        user = ndb.Key("User", gplus_id).get()
        if user is None or user.verifyToken != verifyToken:
            logging.info("Wrong user")
            return

        if data["collection"] != "locations":
            logging.info("Wrong collection")
            return

        if data["operation"] != "UPDATE":
            logging.info("Wrong operation")
            return

        service = get_auth_service(gplus_id)

        if service is None:
            logging.info("No valid credentials")
            return

        result = service.locations().get(id=data["itemId"]).execute()
        logging.info(result)

        if "longitude" in result and "latitude" in result:
            user.longitude = result["longitude"]
            user.latitude = result["latitude"]
            user.locationUpdate = datetime.utcnow()
            user.put()

        # TODO: Forward information to relevant demo services


NOTIFY_ROUTES = [
    ("/timeline_update", TimelineNotifyHandler),
    ("/locations_update", LocationNotifyHandler)
]