
# from motor.motor_asyncio import AsyncIOMotorClient
# import traceback
# import os
# import os


# from dotenv import load_dotenv
# import asyncio

# load_dotenv()

# MONGO_DB_URI = os.getenv('MONGO_DB_URI')
# # MONGO_AIR = os.getenv('MONGO_AIR')
# # MODE = os.getenv('MODE')

# def mclient():
# 	connected = False
# 	while not connected:
# 		try:
# 			client = AsyncIOMotorClient(MONGO_DB_URI)
# 			if client.is_primary:
# 				connected = True

# 			return client
# 		except Exception as e:
# 			pass

from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()
MONGO_DB_URI = os.getenv("MONGO_DB_URI")

# Create the client **once**
mclient = AsyncIOMotorClient(MONGO_DB_URI)
