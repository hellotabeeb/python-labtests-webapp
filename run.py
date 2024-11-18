from app import create_app

app = create_app()

# Remove the debug flag; Gunicorn manages it
if __name__ == '__main__':
    app.run()