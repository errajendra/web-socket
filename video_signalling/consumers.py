import json

from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework_simplejwt.authentication import JWTAuthentication


class VideoConsumer(AsyncWebsocketConsumer):

    # Users stored here temporarily
    USERS_CONNECTED = {}
    all_messages = {}
    all_talks = []

    async def connect(self):

        # When user connects user is added to the respective room name
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = "room_%s" % self.room_name
        await (self.channel_layer.group_add)(self.room_group_name, self.channel_name)
        await self.accept()
        if self.room_group_name not in self.all_messages:
            self.all_messages[self.room_group_name] = []
        else:
            await self.send(text_data=json.dumps({"type":"message", "chat": self.all_messages[self.room_group_name]}))
        if self.room_group_name not in self.USERS_CONNECTED:
            self.USERS_CONNECTED[self.room_group_name] = []
        #else:
        #    await self.send(text_data=json.dumps({"type":"", "chat": self.all_messages[self.room_group_name]}))
        #self.all_talks = []
        await self.send(text_data=json.dumps({"type":"talk_to_astrologer", "talk_to_astrologer": self.all_talks}))

    async def disconnect(self, close_code):

        # Firing signals to other user about user who just disconneted
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "disconnected",
                "data": {"from": self.user_id, "user_name": self.user_full_name},
            },
        )

        # User data is cleared and discarded from the room
        user = self.find_user(self.user_id, self.room_group_name)
        self.USERS_CONNECTED[self.room_group_name].remove(user)
        await (self.channel_layer.group_discard)(
            self.room_group_name, self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)

        if data["type"] == "message":
            #text_data_json = json.loads(text_data)
            message = data['chat']
            self.all_messages[self.room_group_name].append(message)
            data['chat'] = self.all_messages[self.room_group_name]
            # Send the received message back to the client
            await self.channel_layer.group_send(self.room_group_name, {"type":"message", "data": data })
        elif data["type"] == "end":
            if self.room_group_name in self.all_messages:
                self.all_messages[self.room_group_name] = []
            if self.room_group_name in self.USERS_CONNECTED:
                self.USERS_CONNECTED[self.room_group_name] = []
        elif data["type"] == "talk_to_astrolger":
            #text_data_json = json.loads(text_data)
            recent_talk = data['talk_to_astrolger']
            if self.find_existing_talk(recent_talk) is None:
                self.all_talks.append(recent_talk)
            data["all_talks"] = self.all_talks
            # Send the received message back to the client
            await self.channel_layer.group_send(self.room_group_name, {"type": "talk_to_astrologer", "data": data})

        elif data["type"] == "talk_to_astrolger_a_r":
            #text_data_json = json.loads(text_data)
            recent_talk_action = data['talk_to_astrolger_a_r']
            current_talk = self.find_talk_astro(recent_talk_action)
            self.all_talks.remove(current_talk)
            #current_all_talks = [record for record in self.all_talks if record["user_from"] != recent_talk_action["user_to"] and record["astroler_to"] != recent_talk_action["astrologer_from"]]
            #self.all_talks = []
            data["all_talks"] = self.all_talks
            #self.all_talks = current_all_talks
            # Send the received message back to the client
            await self.channel_layer.group_send(self.room_group_name, {"type": "talk_to_astrolger_a_r", "data": recent_talk_action})
            await self.channel_layer.group_send(self.room_group_name, {"type": "talk_to_astrologer", "data": data})

        # Checks user is valide user or not and added to USER_CONNECTED
        if data["type"] in ["new_user_joined", "user_active"]:

            self.user_id = data["from"]
            self.user_full_name = data["user_full_name"]
            if self.find_user(self.user_id, self.room_group_name) is None:
                self.USERS_CONNECTED[self.room_group_name].append(
                    {"user_id": data["from"], "user_full_name": data["user_full_name"], "state":"joined"}
                )
            else:
                if data["type"] == "new_user_joined":
                    self.find_user(self.user_id, self.room_group_name).update({"state": "joined"})
                elif data["type"] == "user_active":
                    self.find_user(self.user_id, self.room_group_name).update({"state": "active"})
            data["users_connected"] = self.USERS_CONNECTED[self.room_group_name]

            # All the users is notified about new user joining
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "new_user_joined",
                    "data": data,
                },
            )

        elif data["type"] == "new_user_request":

            self.user_id = data["from"]
            self.user_full_name = data["user_full_name"]
            if self.find_user(self.user_id, self.room_group_name) is None:
                self.USERS_CONNECTED[self.room_group_name].append(
                    {"user_id": data["from"], "user_full_name": data["user_full_name"], "state":"requested"}
                )
            data["users_connected"] = self.USERS_CONNECTED[self.room_group_name]

            # All the users is notified about new user joining
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "new_user_request",
                    "data": data,
                },
            )
        # Offer from the user is send back to other users in the room
        elif data["type"] == "sending_offer":
            data["users_connected"] = self.USERS_CONNECTED[self.room_group_name]
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "sending_offer",
                    "data": data,
                },
            )

        # Answer from the user is send back to user who sent the offer
        elif data["type"] == "sending_answer":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "sending_answer",
                    "data": data,
                },
            )

        # Firing signals to other user about user who just disconneted
        elif data["type"] == "disconnected":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "disconnected",
                    "data": data,
                },
            )

    async def message(self, event):
        data = event["data"]
        await self.send(
            json.dumps({"type":"message", "chat": data["chat"]})
        )

    async def talk_to_astrologer(self, event):
        data=event["data"]
        await self.send(json.dumps({"type":"talk_to_astrologer", "talk_to_astrolger": data["all_talks"]}))

    async def talk_to_astrolger_a_r(self, event):
        data = event["data"]
        await self.send(json.dumps({"type":"talk_to_astrologer_a_r", "talk_to_astrologer_a_r": data}))

    # FUNCTIONS FOR THE GROUP SEND METHOD ABOVE...
    async def new_user_joined(self, event):
        data = event["data"]
        await self.send(
            json.dumps(
                {
                    "type": "new_user_joined",
                    "from": data["from"],
                    "users_connected": data["users_connected"],
                }
            )
        )

    async def new_user_request(self, event):
        data = event["data"]
        await self.send(
            json.dumps(
                {
                    "type": "new_user_request",
                    "from": data["from"],
                    "user_name": data["user_full_name"],
                    "users_connected": data["users_connected"],
                }
            )
        )

    async def sending_offer(self, event):
        data = event["data"]
        await self.send(
            json.dumps(
                {
                    "type": "sending_offer",
                    "from": data["from"],
                    "to": data["to"],
                    "offer": data["offer"],
                    "users_connected": data["users_connected"],
                }
            )
        )

    async def sending_answer(self, event):
        data = event["data"]
        await self.send(
            json.dumps(
                {
                    "type": "sending_answer",
                    "from": data["from"],
                    "to": data["to"],
                    "answer": data["answer"],
                }
            )
        )

    async def disconnected(self, event):

        data = event["data"]
        await self.send(
            json.dumps(
                {
                    "type": "disconnected",
                    "from": data["from"],
                    "user_name": data["user_name"]
                    #"users_connected": data["users_connected"],
                }
            )
        )

    # Method to find user from USER_CONNECTED
    def find_user(self, user_id, room_name):
        if room_name in self.USERS_CONNECTED:
            for user in self.USERS_CONNECTED[self.room_group_name]:
                if user["user_id"] == user_id:
                    return user

        return None

    def find_talk_astro(self, talk_a_r):
        for talk in self.all_talks:
            if talk["user_from"] == talk_a_r["user_to"] and talk["astroler_to"] == talk_a_r["astrologer_from"]:
                return talk
        return None

    def find_existing_talk(self, ctalk):
        for talk in self.all_talks:
            if talk["user_from"] == ctalk["user_from"] and talk["astroler_to"] == ctalk["astroler_to"]:
                return talk
        return None
