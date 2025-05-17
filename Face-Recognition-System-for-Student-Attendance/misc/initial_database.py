import json
import urllib.parse
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, DuplicateKeyError, PyMongoError

# Load MongoDB configuration from JSON file
def load_mongo_config():
    try:
        with open("mongo_config.json", "r") as config_file:
            config = json.load(config_file)
        return config
    except FileNotFoundError:
        print("Error: mongo_config.json file not found.")
        return None
    except json.JSONDecodeError:
        print("Error: Invalid JSON format in mongo_config.json.")
        return None

# Connect to MongoDB
def connect_to_mongodb():
    config = load_mongo_config()
    if not config:
        return None

    try:
        # Encode username and password for safe URI usage
        encoded_username = urllib.parse.quote_plus(config["username"])
        encoded_password = urllib.parse.quote_plus(config["password"])

        # Construct the MongoDB URI
        mongo_uri = f"mongodb+srv://{encoded_username}:{encoded_password}@{config['cluster']}/?retryWrites=true&w=majority&appName={config['app_name']}"

        # Connect to MongoDB
        client = MongoClient(mongo_uri)
        db = client[config["database"]]
        print("Connected to MongoDB successfully!")
        return db
    except ConnectionFailure as e:
        print(f"Failed to connect to MongoDB: {e}")
        return None
    except Exception as e:
        print(f"An error occurred while connecting to MongoDB: {e}")
        return None

# Insert a document into a collection
def insert_document(collection, document):
    try:
        # Check if the document already exists
        existing_document = collection.find_one({"_id": document["_id"]})
        if existing_document:
            print(f"Document with _id {document['_id']} already exists. Skipping insertion.")
            return False
        else:
            # Insert the document
            collection.insert_one(document)
            print(f"Document with _id {document['_id']} inserted successfully!")
            return True
    except DuplicateKeyError:
        print(f"Duplicate key error: Document with _id {document['_id']} already exists.")
        return False
    except PyMongoError as e:
        print(f"An error occurred while inserting the document: {e}")
        return False

# Fetch a document from a collection
def fetch_document(collection, query):
    try:
        document = collection.find_one(query)
        if document:
            print(f"Document found: {document}")
            return document
        else:
            print("No document found matching the query.")
            return None
    except PyMongoError as e:
        print(f"An error occurred while fetching the document: {e}")
        return None

# Update a document in a collection
def update_document(collection, query, update_data):
    try:
        result = collection.update_one(query, {"$set": update_data})
        if result.matched_count > 0:
            print(f"Document updated successfully: {result.modified_count} document(s) modified.")
            return True
        else:
            print("No document found matching the query.")
            return False
    except PyMongoError as e:
        print(f"An error occurred while updating the document: {e}")
        return False

# Delete a document from a collection
def delete_document(collection, query):
    try:
        result = collection.delete_one(query)
        if result.deleted_count > 0:
            print(f"Document deleted successfully: {result.deleted_count} document(s) deleted.")
            return True
        else:
            print("No document found matching the query.")
            return False
    except PyMongoError as e:
        print(f"An error occurred while deleting the document: {e}")
        return False

# Example usage
if __name__ == "__main__":
    # Connect to MongoDB
    db = connect_to_mongodb()
    if db:
        # Define the collection
        collection = db["students"]

        # Define the admin document
        admin_data = {
            "_id": "2200100943",
            "name": "Mohammad Ameer",
            "password": "2022503105",
            "dob": "2004-10-05",
            "address": "Lucknow, India",
            "phone": "7860514360",
            "email": "mohdameer01a@gmail.com",  # Must be a Gmail address
            "major": "Computer Application",
            "starting_year": 2022,
            "standing": "D",
            "total_attendance": 4,
            "year": 3
        }

        # Insert the admin document
        insert_document(collection, admin_data)

        # Fetch the admin document
        fetched_document = fetch_document(collection, {"_id": "2200100943"})
        if fetched_document:
            print(f"Fetched document: {fetched_document}")

        # Update the admin document
        update_document(collection, {"_id": "2200100943"}, {"total_attendance": 5})

        # Delete the admin document
        delete_document(collection, {"_id": "2200100943"})