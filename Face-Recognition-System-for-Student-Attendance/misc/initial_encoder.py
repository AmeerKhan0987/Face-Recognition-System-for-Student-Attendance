import cv2
import pickle
import face_recognition
import os
from pymongo import MongoClient
import gridfs
from urllib.parse import quote_plus

# MongoDB configuration
password = "7860514360@Aa"
encoded_password = quote_plus(password)

client = MongoClient(
    f"mongodb+srv://AAAK:{encoded_password}@cluster0.xcc80.mongodb.net/face_recognition_system?retryWrites=true&w=majority"
)
db = client["face_recognition_system"]
students_collection = db["students"]
fs = gridfs.GridFS(db)  # For storing images in MongoDB

# Path to student images
# Path to student images
folderPath = "./static/Files/Images"
imgPathList = os.listdir(folderPath)
print("Found images:", imgPathList)
imgList = []
studentIDs = []

for path in imgPathList:
    img = cv2.imread(os.path.join(folderPath, path))  # Load the image
    if img is not None:  # Validate image loading
        imgList.append(img)  # Append only loaded images
        _id = os.path.splitext(path)[0]
        studentIDs.append(_id)

        # Save image in MongoDB using GridFS
        try:
            with open(os.path.join(folderPath, path), "rb") as image_file:
                file_id = fs.put(image_file, filename=path)

            # Store metadata in MongoDB
            students_collection.update_one(
                {"_id": _id},
                {
                    "$set": {
                        "_id": _id,
                        "image_file_id": file_id,  # Reference to the stored image
                    }
                },
                upsert=True,
            )
        except Exception as e:
            print(f"Error storing image {path} in MongoDB: {e}")
    else:
        print(f"Failed to load image: {path}")

print("Student IDs:", studentIDs)


def findEncodings(images):
    encodeList = []
    for img in images:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        encodings = face_recognition.face_encodings(img)
        if encodings:  # If at least one face encoding is found
            encodeList.append(encodings[0])
        else:
            print("No face detected in image")
    return encodeList

print("Encoding Started")

encodeListKnown = findEncodings(imgList)

encodeListKnownWithIds = [encodeListKnown, studentIDs]

try:
    with open("EncodeFile.p", "wb") as file:
        pickle.dump(encodeListKnownWithIds, file)
except Exception as e:
    print(f"Error saving encodings to file: {e}")

# Save encodings in MongoDB
try:
    students_collection.update_one(
        {"_id": "encodings"},
        {"$set": {"encodings": encodeListKnownWithIds}},
        upsert=True,
    )
except Exception as e:
    print(f"Error saving encodings in MongoDB: {e}")

print("Encoding Ended")
