from bottle import request


def add_rest_interface(app, integration_manager):

    @app.post("/api/v1/threshold")
    def set_threshold():
        new_config = request.json

        status = integration_manager.set_threshold(new_config)

        return {"state": "ok",
                "status": str(status)}
