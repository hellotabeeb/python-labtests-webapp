# run.py
from app import create_app

app = create_app()

if __name__ == '__main__':
    try:
        from waitress import serve
        serve(app, host='127.0.0.1', port=8080)
    except ImportError:
        app.run(debug=True)