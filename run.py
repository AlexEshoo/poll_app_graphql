import os
from poll_app_graphql import create_app, db

app = create_app(os.getenv("FLASK_ENV"))

@app.shell_context_processor
def make_shell_context():
    return dict(db=db)