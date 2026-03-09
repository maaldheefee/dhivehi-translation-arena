from functools import wraps

from flask import jsonify, redirect, request, session, url_for


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        username = session.get("username", "Guest")
        if username == "Guest":
            # If it's an API/AJAX request, return a 401 JSON response
            if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.path.startswith("/compare/random"):
                return jsonify({"error": "Authentication required"}), 401
            # Otherwise, redirect to the home page (where the login modal is available)
            return redirect(url_for("main.index"))
        return f(*args, **kwargs)
    return decorated_function
