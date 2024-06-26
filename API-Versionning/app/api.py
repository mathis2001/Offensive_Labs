from flask import Flask, request, abort, Response, send_from_directory
from flask_restful import Api, Resource, reqparse
from flasgger import Swagger, swag_from
from functools import wraps
import time
import string
import uuid
import os
import base64
import jwt
import re
import random
import requests
import json

app = Flask(__name__)
app.config["SECRET_KEY"] = "SUPER_SECURE_SECRET"
api = Api(app)

UPLOAD_DIRECTORY =  "uploads"

missioninfo = json.load(open('missioninfo.json', 'r'))

access_count = 0

roles = ["user","admin"]


class User:
    def __init__(self):
        self.file_path = 'users.json'

    def find_by_email(self, email):
        with open(self.file_path, 'r') as f:
            users = json.load(f)
            for user in users:
                if user['email'] == email:
                    return user
        return None

        def login(self, email, password):
            return self.find_by_email(email)

    def save_user(self, user_data):
        with open(self.file_path, 'r+') as f:
            users = json.load(f)
            users.append(user_data)
            f.seek(0)
            json.dump(users, f, indent=4)

    def update_user(self, email, new_data):
        with open(self.file_path, 'r+') as f:
            users = json.load(f)
            for user in users:
                if user['email'] == email:
                    user.update(new_data)
                    break
            else:
                return None

            f.seek(0)
            json.dump(users, f, indent=4)


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if "Authorization" in request.headers:
            token = request.headers["Authorization"].split(" ")[1]
        if not token:
            return {
                "message": "Your are not authenticated.",
                "data": None,
                "error": "Unauthorized"
            }, 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = data
        except jwt.ExpiredSignatureError:
            return {'message': 'Token is expired!'}, 401
        except jwt.InvalidTokenError:
            return {'message': 'Token is invalid!'}, 401

        return f(current_user, *args, **kwargs)

    return decorated

def requires_basic_auth(f):

    def check_auth(username, password):
        return username == "guest" and password == "guest"

    def authenticate():
        return Response(
            "Authentication required.", 401,
            {"WWW-Authenticate": "Basic realm='Login Required'"},
        )

    @wraps(f)
    def decorated(*args, **kwargs):
        if __name__ != "__main__":
            return f(*args, **kwargs)

        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)

    return decorated

swagger = Swagger(app, decorators=[ requires_basic_auth ])

def isAdmin(user):
    if user["role"] == "admin":
        return 1
    else:
        return 0

@app.route("/api/token", methods=["POST"])
def login():
    try:
        data = request.json
        if not data or not data.get('email'):
            return {
                "message": "Please provide a valid email",
                "data": None,
                "error": "Bad request"
            }, 400

        email = data.get('email')
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return abort(400, "Invalid email format")

        user = User().find_by_email(email)
        if user:
            try:
                token_payload = {
                    "email": email,
                    "name": user["name"],
                    "function": user["function"],
                    "mission": user["mission"],
                    "active": user["active"],
                    "launchSite": user["launchSite"],
                    "manager": user["manager"],
                    "role": user["role"]
                }
                token = jwt.encode(
                    token_payload,
                    app.config["SECRET_KEY"],
                    algorithm="HS256"
                )

                return {
                    "message": "Successfully fetched auth token",
                    "data": {
                        "user": email,
                        "token": token
                    }
                }, 200
            except Exception as e:
                return {
                    "error": "Something went wrong",
                    "message": str(e)
                }, 500
        else:
            return {
                "message": "User not found",
                "data": None,
                "error": "Unauthorized"
            }, 404

    except Exception as e:
        return {
            "message": "Something went wrong!",
            "error": str(e),
            "data": None
        }, 500


def jsonresponse(data):
    response = app.response_class(
            response=json.dumps(data, indent=2),
            status=200,
            mimetype='application/json'
            )
    return response

class CurrentUser(Resource):
    method_decorators = [token_required]

    def get(self, current_user):
        """
        View the current user information. (Contact John at the following email to create an account john.doe@example.xyz)
        ---
        tags:
          - Users
        responses:
          200:
            description: ...
          500:
            description: Something went wrong
        """
        try:
            role = current_user.get("role")

            if role == "admin":
                current_user["role"] = "flag{Weak_4uth_Everywhere}"
            return jsonresponse({
                "data": {
                    "user": current_user,
                    "flag": "flag{S3cured_But_N0t_Secur3d}"
                }
            })
        except:
            return abort(500, "An error occured")

    def patch(self, current_user):
        """
        Edit the current user information.
        ---
        tags:
          - Users
        parameters:
        - in: body
          name: user info
          consumes:
            - application/json
          schema:
            type: object
            properties:
              new_email:
                type: string
              name:
                type: string
              function:
                type: string
              mission:
                type: integer 
              role:
                type: string
              launchSite:
                type: string
              manager:
                type: string
              active:
                type: boolean
        responses:
          200:
            description: ...
          500:
            description: Something went wrong
        """
        data = request.json
        new_email = data.get("new_email")
        name = data.get("name")
        active = data.get("active")
        function = data.get("function")
        role = data.get("role")
        manager = data.get("manager")
        launchSite = data.get("launchSite")
        mission = data.get("mission")
 
        if role:
            abort(403, "The current user does not have the right to change his role")
        else:
            role = current_user["role"]

        if active:    
            if not isinstance(active, bool):
                return abort(400, "active parameter must be a boolean")

        if isAdmin(current_user) == 0:
            if active != current_user["active"]:
                active = current_user["active"]
            if manager != current_user["manager"]:
                manager = current_user["manager"]
            if launchSite != current_user["launchSite"]:
                launchSite = current_user["launchSite"]
            if mission != current_user["mission"]:
                mission = current_user["mission"]

        if not new_email:
            new_email = current_user["email"]

        if not re.match(r"[^@]+@[^@]+\.[^@]+", new_email):
            return abort(400, "Invalid email format")

        existing_user = User().find_by_email(new_email)
        if existing_user:
            flag = "flag{V4lidat1ons_Mus7_B3_D0n3_Ev3rywh3re}"
            response = {"message":"Current User updated successfully (Go check the user information for the provided new email to get the flag)"}
        else:
            flag = "No email validation ?"
            response = {"message":"Current User updated successfully"}

        jsondata = {"email":new_email, "name":flag, "active":active, "role":role, "function":function, "manager":manager, "launchSite":launchSite, "mission":mission}

        User().update_user(current_user["email"], jsondata)
        return jsonresponse(response)


class AddUserV2(Resource):
    method_decorators = [token_required]
    def put(self, current_user):
        """
        Create a new account.
        ---
        tags:
          - Users
        parameters:
        - in: body
          name: user info
          consumes:
            - application/json
          schema:
            type: object
            properties:
              email:
                type: string
              name:
                type: string
              function:
                type: string
              mission:
                type: integer
              manager:
                type: string
              active:
                type: boolean
              role:
                type: string
        responses:
          200:
            description: User successfully created
          400:
            description: Bad Request
          403:
            description: Only admin users can create account (the check is done through the var "XXXX" that use a function checking the current user role, his returned value is 1 or 0)
          500:
            description: Something went wrong
        """
        data = request.json
        email = data.get("email")
        name = data.get("name")
        active = data.get("active")
        function = data.get("function")
        role = data.get("role")
        manager = data.get("manager")
        launchSite = data.get("launchSite")
        mission = data.get("mission")
        global roles

        if not email:
            return abort(400, "Parameter email is missing")
        if not role:
            return abort(400, "Parameter role is missing")
        if role not in roles:
            return abort(400, "Role must be 'user' or 'admin'")
        if not active:
            return abort(400, "Parameter active is missing")
        elif not isinstance(active, bool):
            return abort(400, "active parameter must be a boolean") 
        if not name:
            name = "undefined"
        if not function:
            function = "undefined"
        if not manager:
            manager = "undefined"
        if not launchSite:
            launchSite = "undefined"
        if not mission:
            mission = 0

        if not re.match(r"[^@]+@example\.xyz$", email):
            return abort(400, "Invalid company email format (@example.xyz)")

        existing_user = User().find_by_email(email)
        if existing_user:
            return abort(500, f"User {email} already existing")

        jsondata = {"isAdmin":isAdmin(current_user), "userinfo":{"email":email, "name":name, "active":active, "role":role, "function":function, "manager":manager, "launchSite":launchSite, "mission":mission}}
     
        jsondata.update(data)

        if jsondata["isAdmin"] == 1:
            User().save_user(jsondata["userinfo"])
            return jsonresponse({"message":f"User {email} successfully created", "data":jsondata["userinfo"], "flag":"flag{All0w3d_F34lds_Mus7_B3_Sp3c1fi3D}"})
        else:
            return abort(403, f"Only admin users can create accounts")

class missionCrewV2(Resource):
    method_decorators = [token_required]
    def get(self, id):
        """
        View the details of the crew for a specific mission
        ---
        tags:
          - Crew
        parameters:
        - in: path
          name: id
          required: true
          type: string
        responses:
          200:
            description: Mission Crew details
          403:
            description: You are not authorized to access this endpoint
          500:
            description: An error occured
        """
        return abort(403, 'You are not authorized to access this endpoint')

    def post(self, id):
        """
        Add a crew member to a mission
        ---
        tags:
          - Crew
        parameters:
        - in: path
          name: id
          required: true
          type: string
        - in: body
          name: crew
          consumes:
            - application/json
          required: true
          schema:
            type: object
            properties:
              name:
                type: string
              role:
                type: string
              background:
                type: string
              missions:
                type: integer
        responses:
          201:
            description: Crew member successfully added
          403:
            description: You are not authorized to access this endpoint
          500:
            description: An error occured
        """
        return abort(403, 'You are not authorized to create a new crew member for the mission')

    def delete(self, id):
        """
        Delete a crew member from a mission
        ---
        tags:
          - Crew
        parameters:
        - in: path
          name: id
          required: true
          type: string
        - in: body
          name: memberID
          consumes:
            - application/json
          required: true
          schema:
            type: object
            properties:
              memberID:
                type: string
        responses:
          200:
            description: Crew member successfully deleted
          403:
            description: You are not authorized to access this endpoint
          404:
            description: Member not found
          500:
            description: An error occured
        """
        return abort(403, 'You are not authorized to delete crew member from the mission')

class missionCrewV1(Resource):
    def get(self, id):
        try:
            mission_part = {
                'mission': missioninfo['missions'][id]['missionName'],
                'isLaunched': missioninfo['missions'][id]['isLaunched']
            }
            crew_part = {'Operation crew': missioninfo['missions'][id]['crew']}
        
            full_part = {"mission details": mission_part, "crew details": crew_part}
        
            response = jsonresponse(full_part)
        
            return response
        except:
            return abort(404, 'Invalid Id')

    def post(self, id):
        return abort(500, 'An error occured')

    def delete(self,id):
        data = request.json
        memberID = data.get("memberID")

        if not memberID:
            return abort(404, "Parameter memberID missing")

        try:
            mission = missioninfo['missions'][id]
            crew_members = mission['crew']
            member_index = next((index for (index, member) in enumerate(crew_members) if member['memberID'] == memberID), None)

            if member_index is not None:
                del crew_members[member_index]
                return 'Successfully deleted crew member from the mission, well done ! flag{N0_St4rs_4nym0re}', 200
            else:
                return abort(404, f'Member not found for id: {memberID}')
        except KeyError:
            return abort(404, 'Invalid mission id')



class missionIdV2(Resource):
    method_decorators = [token_required]
    def get(self, id):
        """
        View the details of a specific mission
        ---
        tags:
          - Missions Details
        parameters:
        - in: path
          name: id
          required: true
          type: string
        responses:
          200:
            description: View the confidential mission details
          403:
            description: You are not authorized to access this endpoint
          404:
            description: Invalid Id
          500:
            description: An error occured
        """
        return abort(403, 'You are not authorized to access this endpoint')


class missionIdV1(Resource):
    def get(self, id):
        details = {'mission': missioninfo['missions'][id]}
        response = jsonresponse(details)
        try:
            return response
        except:
            return abort(404, 'Invalid Id')

class missionDetailsV2(Resource):
    method_decorators = [token_required]
    def get(self):
        """
        View the full details of a mission
        ---
        tags:
          - Missions Details
        responses:
          200:
            description: View the confidential missions details
          403:
            description: You are not authorized to access this endpoint
          500:
            description: An error occured         
        """
        return abort(403, 'You are not authorized to access this endpoint')

class missionDetailsV1(Resource):
    def get(self):

        fullmissioninfo = json.load(open('missioninfo.json', 'r'))

        details = {'mission': fullmissioninfo['missions']}

        details = {'mission': missioninfo['missions']}
        response = jsonresponse(details)
        try:
            return response
        except:
            return abort(500, 'An error occured')

class missionComV2(Resource):
    method_decorators = [token_required]
    def get(self, id):
        """
        View the communications details about a mission
        ---
        tags:
          - Communications
        parameters:
        - in: path
          name: id
          required: true
          type: string
        responses:
          200:
            description: View the mission details about communications
          403:
            description: You are not authorized to access this endpoint
          500:
            description: An error occured
        """
        return abort(403, 'You are not authorized to access this endpoint')
    def patch(self, id):
        """
        This endpoint have been deprecated (hackers loves deprecated features ;p)
        ---
        tags:
          - Communications
        parameters:
        - in: path
          name: id
          required: true
          type: string
        - in: body
          consumes:
            - application/json
          name: xxx
          required: true
          type: string
          description: Maybe you should think to fuzz that endpoint
        responses:
          200:
            description: ...
          403:
            description: You are not authorized to access this endpoint
          500:
            description: An error occured
        """
        return abort(403, 'You are not authorized to access this endpoint')

class missionComV1(Resource):
    def get(self, id):
        try:
            mission_part = {
                'mission': missioninfo['missions'][id]['missionName'],
                'isLaunched': missioninfo['missions'][id]['isLaunched']
            }
            com_part = {'Communications': missioninfo['missions'][id]['systems']['Communications']}
        
            full_part = {"mission details": mission_part, "Communications details": com_part}
        
            response = jsonresponse(full_part)
        
            return response
        except:
            return abort(404, 'Invalid Id')

    def patch(self, id):
        data = request.json
        if id == "1":
            try:
                mission = missioninfo['missions'][id]
                callback_url = data.get("callback")

                if 'Communications' in mission['systems']:
                    mission['systems']['Communications']['messages']['callback'] = callback_url

                    with open('messages.txt', 'r') as messages_file:
                        messages_content = messages_file.read()

                    if callback_url.startswith("https://internal-communications.example.xyz"):
                        headers = {
                            'user-agent': 'StellarOS/4.2.3',
                            'X-Satellite': '2',
                            'X-Rocket': 'Stellar Explorer'
                        }
                        response = requests.post(callback_url, data=messages_content, headers=headers)

                        if response.status_code == 200:
                            return jsonresponse({"message":"Callback URL changed successfully"})
                        else:
                            return abort(500, f"Error sending request to {callback_url} ({response.status_code})")
                    else:
                        return abort(403, 'Invalid callback_url')
                else:
                    return abort(404, 'Communications system not found for the given mission id')
            except KeyError:
                return abort(404, 'Invalid mission id')
        else:
            return abort(404, 'Rocket not launched')

class missionPublicV2(Resource):
    method_decorators = [token_required]
    def get(self):
        """
        View the Public missions details
        ---
        tags:
          - Public
        responses:
          200:
            description: View the Public missions details
          500:
            description: An error occured
        """
        mission_public = {}
        for mission_id, mission_data in missioninfo['missions'].items():
            mission_details = {
                'missionName': mission_data.get('missionName'),
                'isLaunched': mission_data.get('isLaunched'),
                'rocket': mission_data['rocket'].get('name'),
                'launchSite': mission_data.get('launchSite')
            }
            mission_public[mission_id] = mission_details

        full_part = {"mission details": mission_public}
        
        response = jsonresponse(full_part)
        try:
            return response
        except:
            return abort(500, 'An error occured')

class missionPublicV1(Resource):
    def get(self):
        mission_public = {}
        for mission_id, mission_data in missioninfo['missions'].items():
            mission_details = {
                'missionName': mission_data.get('missionName'),
                'isLaunched': mission_data.get('isLaunched'),
                'rocket': mission_data['rocket'].get('name'),
                'launchSite': mission_data.get('launchSite')
            }
            mission_public[mission_id] = mission_details

        full_part = {"mission details": mission_public}
        
        response = jsonresponse(full_part)
        try:
            return response
        except:
            return abort(500, 'An error occured')

class weatherPublicV2(Resource):
    def post(self):
        """
        This endpoint use a third party service to check weather. Take care, it is limited to 25 free request by day and +1€ for each additional request...
        ---
        tags:
          - Public
        parameters:
        - in: body
          consumes:
            - application/json
          name: city
          required: true
          schema:
            type: object
            properties:
              city:
                type: string
              day:
                type: string
        responses:
          200:
            description: ...
          500:
            description: An error occured
        """
        global access_count
        data = request.json
        city = data.get('city')
        access_count += 1

        if city:
            if access_count > 25:
                return 'Lack of rate limiting can cost money... flag{N0_M0n3y_D0wn}', 200

            else:

                weather_conditions = ['Sunny', 'Cloudy', 'Partly Cloudy', 'Rainy', 'Stormy', 'Snowy']
                temperature = random.randint(-10, 35)

                weather = random.choice(weather_conditions)

                weather_data = {
                    'city': city,
                    'weather': weather,
                    'temperature': f'{temperature} degrees'
                }
        else:
            return abort(400, "Parameter city missing")

        try:
            return jsonresponse(weather_data)
        except:
            return abort(500, 'An error occured')

class FileREAD(Resource):
    def get(self, filename):
        try:
            return send_from_directory(UPLOAD_DIRECTORY, filename)
        except FileNotFoundError:
            abort(404, "File not found")

class FileUpload(Resource):
    method_decorators = [token_required]
    def post(self, current_user):
        """
        Upload an avatar image
        ---
        tags:
          - Users
        parameters:
        - in: body
          consumes:
            - application/json
          name: fileinfo
          required: true
          schema:
            type: object
            properties:
              filetype:
                type: string
              content:
                type: string
        responses:
          200:
            description: Image uploaded successfully
          400: 
            description: Missing 'filetype' or 'content' in JSON data
          500:
            description: Failed to decode base64 content
        """
        ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

        data = request.json
        if not data:
            return abort(400, "No data provided")

        filetype = data.get("filetype")
        content_base64 = data.get("content")

        if not filetype or not content_base64:
            return abort(400, "Parameters missing in JSON data")

        if not filetype.startswith("image/"):
            return abort(500, "Invalid filetype")

        extension = filetype.split('/')[1]

        try:
            content = base64.b64decode(content_base64)
        except Exception as e:
            return abort(500, "Failed to decode base64 content")

        if not os.path.exists(UPLOAD_DIRECTORY):
            os.makedirs(UPLOAD_DIRECTORY)

        filename = f"image_{uuid.uuid4().hex}.{extension}"

        filepath = os.path.join(UPLOAD_DIRECTORY, filename)

        response = {"message": "Image uploaded successfully", "filepath": f'/api/v2/uploads/{filename}', "filesize":len(content)}

        if extension not in ALLOWED_EXTENSIONS:
            with open(filepath, "wb") as f:
                f.write(content)
            response = jsonresponse(response)
            response.headers['X-Flag'] = 'flag{I_L0v3_F1leUplo4ds}'
        else:    
            with open(filepath, "wb") as f:
                f.write(content)
            response = jsonresponse(response)
        return response



def confirmation_link():
    length=16
    current_time = int(time.time())
    random.seed(current_time)

    characters = string.ascii_letters + string.digits
    confirmation_code = ''.join(random.choice(characters) for _ in range(length))

    link = f"http://127.0.0.1:1337/confirm/{confirmation_code}"
    return link, confirmation_code

class DeleteAccount(Resource):
    link_user_map = {}
    duplicates = []
    method_decorators = [token_required]

    def delete(current_user, email):
        """
        Delete a user account
        ---
        tags:
          - Users
        parameters:
        - in: body
          consumes:
            - application/json
          name: email
          required: true
          schema:
            type: object
            properties:
              email:
                type: string
              reason:
                type: string
        responses:
          200:
            description: Deletion confirmation link sent successfully
          400: 
            description: Invalid email format
          500:
            description: Email not provided
        """        
        data = request.json
        email = data.get('email')


        if not email:
            return abort(500, 'Email not provided')

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return abort(400, "Invalid email format")

        link, confirmation_code = confirmation_link()
        user = User().find_by_email(email)
        if user:
            if confirmation_code in DeleteAccount.link_user_map:
                existing_user = DeleteAccount.link_user_map[confirmation_code]
                if existing_user != email:
                    DeleteAccount.duplicates.append(confirmation_code)
            else:
                DeleteAccount.link_user_map[confirmation_code] = email

            username = user["name"]
            response = jsonresponse({
                "message": "Deletion link sent successfully",
                "mock": {
                    "from": "noreply@example.xyz",
                    "to": email,
                    "subject": "Deletion confirmation link",
                    "body": f"Hi {username},\r\n\r\nWe have received a request to delete your account. To confirm the deletion of your account, please click on the following link:\r\n\r\n{link}\r\n\r\nIf you did not initiate this action, please ignore this email or contact our support team immediately.\r\n\r\nBest regards,\r\nRedacted Support Team"
                }
            })

            if DeleteAccount.duplicates:
                response.headers['X-Flag'] = 'flag{Seems_U_W0n_Th3-R4ce}'

            return response
        else:
            return abort(404, "No user found with this email")

class DeletionConfirmation(Resource):
    def get(self, confirmation_code):
        email = DeleteAccount.link_user_map[confirmation_code]
        return jsonresponse({"message":f"account {email} successfully deleted"})


api.add_resource(missionCrewV1, '/api/v1/confidential/missions/<string:id>/crew')
api.add_resource(missionCrewV2, '/api/v2/confidential/missions/<string:id>/crew')
api.add_resource(missionIdV1, '/api/v1/confidential/missions/<string:id>/details')
api.add_resource(missionIdV2, '/api/v2/confidential/missions/<string:id>/details')
api.add_resource(missionComV1, '/api/v1/confidential/missions/<string:id>/communications')
api.add_resource(missionComV2, '/api/v2/confidential/missions/<string:id>/communications')
api.add_resource(missionDetailsV1, '/api/v1/confidential/missions')
api.add_resource(missionDetailsV2, '/api/v2/confidential/missions')
api.add_resource(missionPublicV2, '/api/v2/public/missions')
api.add_resource(missionPublicV1, '/api/v1/public/missions')
api.add_resource(weatherPublicV2, '/api/v2/public/weather')
api.add_resource(CurrentUser, '/api/v2/users/me')
api.add_resource(FileUpload, '/api/v2/users/me/avatar')
api.add_resource(FileREAD, '/api/v2/uploads/<string:filename>')
api.add_resource(DeleteAccount, '/api/v2/users/delete')
api.add_resource(DeletionConfirmation, '/confirm/<string:confirmation_code>')
api.add_resource(AddUserV2, '/api/v2/users/add')

@app.route('/')
def index():
    return '404 not found'

@app.route('/api/v2/<path:subpath>')
@app.route('/api/v1/<path:subpath>')
def Unauthorized(subpath):
    if subpath:
        return abort(403, 'You are not authorized to access this endpoint.')     
    else:
        return abort(404, 'The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again.') 

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=1337)
