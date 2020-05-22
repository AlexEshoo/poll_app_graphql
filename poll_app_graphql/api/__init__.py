from flask import Blueprint, g
from flask_graphql import GraphQLView
from flask_cors import CORS
from .schema import schema

api = Blueprint('api', __name__)
CORS(api)  # Enables CORS

class CustomGraphQlView(GraphQLView):
    def dispatch_request(self):
        response = super().dispatch_request()
        for cookie in g.get("cookies", []):
            response.set_cookie(cookie.key, cookie.value, **cookie.settings)

        return response


api.add_url_rule(
    "/graphql",
    view_func=CustomGraphQlView.as_view(
        "graphql",
        schema=schema,
        graphiql=True,
        middleware=[]
    )
)
