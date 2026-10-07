"""Startet den Server:  python run.py"""
import uvicorn

from app.config import HOST, PORT, SSL_CERT, SSL_KEY

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=HOST, port=PORT, server_header=False,
                ssl_certfile=SSL_CERT, ssl_keyfile=SSL_KEY)
