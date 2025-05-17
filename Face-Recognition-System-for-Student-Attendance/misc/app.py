import cv2
import os
import pickle
import face_recognition
import numpy as np
import cvzone
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId
import gridfs
from urllib.parse import quote_plus

# 🔹 Secure Password Encoding
password = "7860514360@Aa"
encoded_password = quote_plus(password)

# 🔹 MongoDB Connection (Ensure Credentials Are Correct)
client = MongoClient(f"mongodb+srv://AAAK:{encoded_password}@cluster0.xcc80.mongodb.net/?retryWrites=true&w=majority")
print("Connected to MongoDB successfully!")

# 🔹 Select Database & Collections
db = client["face_recognition_system"]
students_collection = db["students"]
attendance_collection = db["attendance"]
fs = gridfs.GridFS(db)

# 🔹 Load Encoding File (Trained Face Data)
print("Loading Encode File ...")
with open('EncodeFile.p', 'rb') as file:
    encodeListKnownWithIds = pickle.load(file)
encodeListKnown, studentIds = encodeListKnownWithIds
print("Encode File Loaded")

# 🔹 Initialize Video Capture
capture = cv2.VideoCapture(0)
capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# 🔹 Load Background Image
imgBackground = cv2.imread("static/Files/Resources/background.png")

# 🔹 Load Mode Images
folderModePath = "static/Files/Resources/Modes/"
modePathList = os.listdir(folderModePath)
imgModeList = [cv2.imread(os.path.join(folderModePath, path)) for path in modePathList]

# 🔹 Variables
modeType = 0
counter = 0
_id = None  # No detected face initially
imgStudent = None

while True:
    success, img = capture.read()
    if not success:
        print("ERROR: Camera not detected! Make sure the webcam is connected.")
        break

    imgS = cv2.resize(img, (0, 0), None, 0.25, 0.25)
    imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)

    faceCurFrame = face_recognition.face_locations(imgS)
    encodeCurFrame = face_recognition.face_encodings(imgS, faceCurFrame)

    imgBackground[162:162 + 480, 55:55 + 640] = img
    imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]

    if faceCurFrame:
        for encodeFace, faceLoc in zip(encodeCurFrame, faceCurFrame):
            matches = face_recognition.compare_faces(encodeListKnown, encodeFace)
            faceDis = face_recognition.face_distance(encodeListKnown, encodeFace)
            matchIndex = np.argmin(faceDis)

            if matches[matchIndex]:
                _id = studentIds[matchIndex]  # Identified student ID

                y1, x2, y2, x1 = faceLoc
                y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4
                bbox = (55 + x1, 162 + y1, x2 - x1, y2 - y1)
                imgBackground = cvzone.cornerRect(imgBackground, bbox, rt=0)

                if counter == 0:
                    cvzone.putTextRect(imgBackground, "Loading", (275, 400))
                    cv2.imshow("Face Attendance", imgBackground)
                    cv2.waitKey(1)
                    counter = 1
                    modeType = 1

        if counter != 0:
            if counter == 1:
                try:
                    # 🔹 Fetch Student Details from MongoDB (Avoid Firebase .reference())
                    studentInfo = students_collection.find_one({"_id": ObjectId(_id)})
                except:
                    print(f"ERROR: Invalid ID format {_id}")
                    studentInfo = None

                if studentInfo:
                    print("DEBUG - Student Info:", studentInfo)

                    # 🔹 Fetch Image from GridFS (If Exists)
                    file_id = studentInfo.get("image_file_id")
                    if file_id:
                        try:
                            image_data = fs.get(ObjectId(file_id)).read()
                            array = np.frombuffer(image_data, np.uint8)
                            imgStudent = cv2.imdecode(array, cv2.IMREAD_COLOR)
                        except Exception as e:
                            print(f"ERROR: Failed to retrieve image for {_id} - {e}")
                            imgStudent = None

                    # 🔹 Calculate Time Elapsed Since Last Attendance
                    last_attendance_time = studentInfo.get("last_attendance_time", "1970-01-01 00:00:00")
                    try:
                        datetimeObject = datetime.strptime(last_attendance_time, "%Y-%m-%d %H:%M:%S")
                        secondsElapsed = (datetime.now() - datetimeObject).total_seconds()
                    except ValueError:
                        print(f"ERROR: Invalid date format for {_id}. Using default.")
                        secondsElapsed = 0

                    print(f"DEBUG - Seconds Elapsed: {secondsElapsed}")

                    if secondsElapsed > 30:
                        # 🔹 Update Attendance in MongoDB
                        students_collection.update_one(
                            {"_id": ObjectId(_id)},
                            {
                                "$inc": {"total_attendance": 1},
                                "$set": {"last_attendance_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                            }
                        )
                    else:
                        modeType = 3
                        counter = 0
                        imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]

            if modeType != 3:
                if 10 < counter < 20:
                    modeType = 2

                imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]

                if counter <= 10:
                    cv2.putText(imgBackground, str(studentInfo['total_attendance']), (861, 125),
                                cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 1)
                    cv2.putText(imgBackground, str(studentInfo['major']), (1006, 550),
                                cv2.FONT_HERSHEY_COMPLEX, 0.5, (255, 255, 255), 1)
                    cv2.putText(imgBackground, str(_id), (1006, 493),
                                cv2.FONT_HERSHEY_COMPLEX, 0.5, (255, 255, 255), 1)

                    if imgStudent is not None:
                        imgBackground[175:175 + 216, 909:909 + 216] = imgStudent  # Display Student Image

                counter += 1

                if counter >= 20:
                    counter = 0
                    modeType = 0
                    studentInfo = None
                    imgStudent = None
                    imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]

    else:
        modeType = 0
        counter = 0

    cv2.imshow("Face Attendance", imgBackground)
    cv2.waitKey(1)
