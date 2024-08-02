import pymongo
from dotenv import load_dotenv
import os

load_dotenv()

def get_database_connection():
    client = pymongo.MongoClient(os.getenv('mongoURI'))
    return client.BotDiscord

def close_database_connection(client):
    client.close()