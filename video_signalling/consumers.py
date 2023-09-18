import json

from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework_simplejwt.authentication import JWTAuthentication


class VideoConsumer(AsyncWebsocketConsumer):

    # Users stored here temporarily
    USERS_CONNECTED = []
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
        #self.all_talks = []

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
        user = self.find_user(self.user_id)
        self.USERS_CONNECTED.remove(user)
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
                self.USERS_CONNECTED = []
        elif data["type"] == "talk_to_astrolger":
            #text_data_json = json.loads(text_data)
            recent_talk = data['talk_to_astrolger']
            self.all_talks.append(recent_talk)
            # Send the received message back to the client
            await self.send(text_data=json.dumps({
                'type': 'talk_to_astrolger',
                'talk_to_astrologer': self.all_talks
            }))

        # Checks user is valide user or not and added to USER_CONNECTED
        if data["type"] == "new_user_joined":

            # jwt_authenticate = JWTAuthentication()
            # try:
            #     jwt_authenticate.get_validated_token(data["token"])
            # except:
            #     self.close()
            self.user_id = data["from"]
            self.user_full_name = data["user_full_name"]
            self.USERS_CONNECTED.append(
                {"user_id": data["from"], "user_full_name": data["user_full_name"]}
            )
            data["users_connected"] = self.USERS_CONNECTED

            # All the users is notified about new user joining
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "new_user_joined",
                    "data": data,
                },
            )

        # Offer from the user is send back to other users in the room
        elif data["type"] == "sending_offer":
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
    def find_user(self, user_id):
        for user in self.USERS_CONNECTED:
            if user["user_id"] == user_id:
                return user

        return None


