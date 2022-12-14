
import datetime
from dotenv import load_dotenv
import flask
from flask import Response
import flask_restx
from flask_restx import Resource
from functools import wraps
import os
import jwt
from werkzeug.security import check_password_hash

from utils.api import api
from Service.UserService import UserService

load_dotenv()

auth_ns = api.namespace('auth', validate=True)

login_user_model = auth_ns.model('User login', {
    'email': flask_restx.fields.String(required=True),
    'password': flask_restx.fields.String(required=True)
})

blacklist_token = set()

def token_required(f):
    """Verify if the token is valid."""
    @wraps(f)
    def decorator(*args, **kwargs):
        token = None
        if 'HTTP_AUTHORIZATION' in flask.request.headers.environ:
            token = flask.request.headers.environ['HTTP_AUTHORIZATION']
        if not token or token in blacklist_token:
            return flask.make_response('A valid token is missing.', 401)
        try:
            user_info = jwt.decode(token, os.getenv('SECRET_KEY'), algorithms=["HS256"])
        except:
            return flask.make_response('The token is invalid.', 401)
        user = UserService().get_user_by_filter(dump=False, email=user_info['email'])
        return f(*args, **kwargs, user=user)
    return decorator


@auth_ns.route("/login")
class LoginUser(Resource):
    
    @auth_ns.doc(body=login_user_model)
    def post(self, *args, **kwargs) -> Response:
        """Logs the user and returns a token. Token needed to use the API."""
        service = UserService()
        data = flask.request.json
        user = service.get_user_by_filter(email=data['email'], dump=False)
        if user and check_password_hash(user.password, data['password']):
            exp = datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
            token = jwt.encode({'email': user.email, 'exp': exp}, 
                               os.getenv('SECRET_KEY'), algorithm="HS256")
            return flask.jsonify({'token': token})
        return flask.make_response('Could not verify.', 401, {
            'WWW.Authentication': 'Basic realm: "login required"'
        })


@auth_ns.route("/logout")
class LogoutUser(Resource):

    @token_required
    def post(self, *args, **kwargs) -> Response:
        """Logout the user (blacklist the token)."""
        token = flask.request.headers.environ['HTTP_AUTHORIZATION']
        blacklist_token.add(token)
        return flask.make_response('Logout succeed.')
