"""
This module contains main endpoints of analytics backoffice API.
"""

from FlaskApp import FlaskApp

from blueprints.applications import applications_endpoints
from blueprints.audiences import audiences_endpoints
from blueprints.remote_configs import remote_configs_endpoints


app = FlaskApp(__name__)
app.register_blueprint(applications_endpoints, url_prefix="/applications")
app.register_blueprint(audiences_endpoints, url_prefix="/audiences")
app.register_blueprint(remote_configs_endpoints, url_prefix="/remote-configs")


if __name__ == "__main__":
    # Used when running locally.
    app.run(host="localhost", port=8080, debug=True)
