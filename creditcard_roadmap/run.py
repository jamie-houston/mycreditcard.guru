from app import create_app, db
from datetime import datetime
import os

app = create_app(os.getenv('FLASK_CONFIG') or 'default')

@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

@app.shell_context_processor
def make_shell_context():
    return dict(app=app, db=db)

if __name__ == '__main__':
    app.run(debug=True) 