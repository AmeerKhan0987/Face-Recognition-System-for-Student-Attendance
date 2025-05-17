from flask import Flask, render_template, Response, request, redirect, url_for
from flask import redirect, url_for
import cv2
import os
import pickle
import cvzone
import face_recognition
import numpy as np
from pymongo import MongoClient
import gridfs
from urllib.parse import quote_plus
from datetime import datetime
import json
import bcrypt
from bson import ObjectId


app = Flask(__name__)

# MongoDB Database Connection
password = "7860514360@Aa"
encoded_password = quote_plus(password)

try:
    client = MongoClient(
        f"mongodb+srv://AAAK:{encoded_password}@cluster0.xcc80.mongodb.net/?retryWrites=true&w=majority")
    print("Connected to MongoDB successfully!")
except Exception as e:
    print(f"Failed to connect to MongoDB: {e}")

client = MongoClient("mongodb://localhost:27017/")
db = client["face_recognition_system"]
collection = db["admins"]  # 'admins' collection
students_collection = db["students"]  # 'students' collection
attendance_collection = db["attendance"]  # Define attendance collection
try:
    client.server_info()  # Will raise an exception if the connection fails
    print("MongoDB connection successful.")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")
fs = gridfs.GridFS(db)

# Load Encoded Faces and Student IDs
try:
    with open("static/Files/EncodeFile.p", "rb") as file:
        loaded_data = pickle.load(file)
        print(f"Loaded Data: {loaded_data}")
except Exception as e:
    print(f"Error loading EncodeFile.p: {e}")
    loaded_data = None

if loaded_data:
    encoded_face_known, student_ids = loaded_data
    print(f"Encoded Faces: {len(encoded_face_known)}")
    print(f"Student IDs: {len(student_ids)}")
else:
    print("Failed to load EncodeFile.p. Initializing as empty.")
    encoded_face_known, student_ids = [], []

# Optionally unpack the data
encoded_face_known, _id = loaded_data
print("Encoded Faces:", encoded_face_known)
print("Student IDs:", _id)



already_marked_id_student = []
already_marked_id_admin = []
already_marked_ids = []


# Function to generate video frames

def generate_frame():
    capture = cv2.VideoCapture(0)
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    imgBackground = cv2.imread("static/Files/Resources/background.png")
    folderModePath = "static/Files/Resources/Modes/"
    modePathList = os.listdir(folderModePath)
    imgModeList = [cv2.imread(os.path.join(folderModePath, path)) for path in modePathList]

    modeType = 0
    _id = -1
    imgStudent = []
    counter = 0

    file = open("EncodeFile.p", "rb")
    encodeListKnownWithIds = pickle.load(file)
    file.close()
    encodedFaceKnown, studentIDs = encodeListKnownWithIds

    while True:
        success, img = capture.read()
        if not success:
            break

        imgSmall = cv2.resize(img, (0, 0), None, 0.25, 0.25)
        imgSmall = cv2.cvtColor(imgSmall, cv2.COLOR_BGR2RGB)
        faceCurrentFrame = face_recognition.face_locations(imgSmall)
        encodeCurrentFrame = face_recognition.face_encodings(imgSmall, faceCurrentFrame)
        imgBackground[162:162 + 480, 55:55 + 640] = img
        imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]

        if faceCurrentFrame:
            for encodeFace, faceLocation in zip(encodeCurrentFrame, faceCurrentFrame):
                matches = face_recognition.compare_faces(encodedFaceKnown, encodeFace)
                faceDistance = face_recognition.face_distance(encodedFaceKnown, encodeFace)
                matchIndex = np.argmin(faceDistance)

                y1, x2, y2, x1 = faceLocation
                y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4
                bbox = 55 + x1, 162 + y1, x2 - x1, y2 - y1
                imgBackground = cvzone.cornerRect(imgBackground, bbox, rt=0)

                if matches[matchIndex]:
                    _id = studentIDs[matchIndex]
                    if counter == 0:
                        cvzone.putTextRect(imgBackground, "Face Detected", (65, 200), thickness=2)
                        cv2.waitKey(1)
                        counter = 1
                        modeType = 1
                else:
                    cvzone.putTextRect(imgBackground, "Face Not Found", (65, 200), thickness=2)
                    modeType = 4
                    counter = 0
                    imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]

            if counter != 0:
             if counter == 1:
                try:
                    # Get the Data from MongoDB
                    studentInfo = students_collection.find_one({"_id": _id})
                    if not studentInfo:
                        print(f"Student with ID {_id} not found.")
                        return

                    print(studentInfo)

                    # Get the Image from MongoDB's GridFS
                    file_id = studentInfo.get("image_file_id")
                    if file_id:
                        image_data = fs.get(file_id).read()
                        array = np.frombuffer(image_data, np.uint8)
                        imgStudent = cv2.imdecode(array, cv2.IMREAD_COLOR)
                    else:
                        print(f"No image found for student {_id}.")
                        imgStudent = None

                    # Update data of attendance
                    last_attendance_time = studentInfo.get("last_attendance_time", "1970-01-01 00:00:00")
                    datetimeObject = datetime.strptime(last_attendance_time, "%Y-%m-%d %H:%M:%S")
                    secondsElapsed = (datetime.now() - datetimeObject).total_seconds()
                    print(secondsElapsed)

                    if secondsElapsed > 30:
                        students_collection.update_one(
                            {"_id": _id},
                            {
                                "$set": {"last_attendance_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
                                "$inc": {"total_attendance": 1}
                            }
                        )
                        print(f"Attendance updated for student {_id}.")
                    else:
                        print("Attendance already marked recently.")

                except Exception as e:
                    print(f"Error processing student {_id}: {e}")

                else:
                        modeType = 3
                        counter = 0
                        imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]

                if modeType != 3:
                    if 5 < counter <= 10:
                        modeType = 2

                    imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]

                    if counter <= 5 and studentInfo:
                        cv2.putText(imgBackground, str(studentInfo["total_attendance"]), (861, 125),
                                    cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 1)
                        cv2.putText(imgBackground, str(studentInfo["major"]), (1006, 550),
                                    cv2.FONT_HERSHEY_COMPLEX, 0.5, (255, 255, 255), 1)
                        cv2.putText(imgBackground, str(_id), (1006, 493),
                                    cv2.FONT_HERSHEY_COMPLEX, 0.5, (255, 255, 255), 1)
                        cv2.putText(imgBackground, str(studentInfo["standing"]), (910, 625),
                                    cv2.FONT_HERSHEY_COMPLEX, 0.6, (100, 100, 100), 1)
                        cv2.putText(imgBackground, str(studentInfo["year"]), (1025, 625),
                                    cv2.FONT_HERSHEY_COMPLEX, 0.6, (100, 100, 100), 1)
                        cv2.putText(imgBackground, str(studentInfo["starting_year"]), (1125, 625),
                                    cv2.FONT_HERSHEY_COMPLEX, 0.6, (100, 100, 100), 1)
                        (w, _), _ = cv2.getTextSize(str(studentInfo["name"]), cv2.FONT_HERSHEY_COMPLEX, 1, 1)
                        offset = (414 - w) // 2
                        cv2.putText(imgBackground, str(studentInfo["name"]), (808 + offset, 445),
                                    cv2.FONT_HERSHEY_COMPLEX, 1, (50, 50, 50), 1)
                        if imgStudent is not None:
                            imgStudentResize = cv2.resize(imgStudent, (216, 216))
                            imgBackground[175:175 + 216, 909:909 + 216] = imgStudentResize
                    counter += 1

                    if counter >= 10:
                        counter = 0
                        modeType = 0
                        studentInfo = []
                        imgStudent = []
                        imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]

        else:
            modeType = 0
            counter = 0

        ret, buffer = cv2.imencode(".jpeg", imgBackground)
        frame = buffer.tobytes()
        print(f"Encoding success: {ret}")
        yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")

@app.route("/")
def index():
     return render_template("index.html")
 
 
@app.route("/video")
def video():
     return Response(
         generate_frame(), mimetype="multipart/x-mixed-replace; boundary=frame"
     )

#########################################################################################################################

# def fetch_marked_students():
#     marked_students = attendance_collection.distinct("_id")  # Get unique student IDs
#     print("DEBUG - Marked Students:", marked_students)  # Debugging print
#     return marked_students

def dataset(_id):
    try:
        # Step 1: Fetch student information
        studentInfo = students_collection.find_one({"_id": _id})
        if not studentInfo:
            print(f"Student with ID {_id} not found.")
            return None, None, None
        # Step 2: Handle image (Check local first, then GridFS)
        imgStudent = os.path.join("static/Files/Images", f"{_id}.png")  # Default image path
        if not os.path.exists(imgStudent):
            try:
                file_id = studentInfo.get("image_file_id")
                if file_id:
                    image_data = fs.get(ObjectId(file_id)).read()
                    array = np.frombuffer(image_data, np.uint8)
                    imgStudent = cv2.imdecode(array, cv2.IMREAD_COLOR)
                    if imgStudent is None:
                        print(f"Error decoding image for student {_id}.")
                        imgStudent = None
                else:
                    print(f"No image found for student {_id}.")
                    imgStudent = None
            except Exception as e:
                print(f"Error fetching image for student {_id}: {e}")
                imgStudent = None

        # Step 3: Calculate elapsed time since last attendance
        last_attendance_time = studentInfo.get("last_attendance_time", "1970-01-01 00:00:00")
        try:
            datetimeObject = datetime.strptime(last_attendance_time, "%Y-%m-%d %H:%M:%S")
            secondsElapsed = (datetime.now() - datetimeObject).total_seconds()
        except ValueError:
            print(f"Invalid date format for student {_id}. Using default time.")
            datetimeObject = datetime(1970, 1, 1, 0, 0, 0)
            secondsElapsed = 0

        return studentInfo, imgStudent, secondsElapsed

    except Exception as e:
        print(f"Error in dataset function for ID {_id}: {e}")
        return None, None, None

@app.route("/student_login", methods=["GET", "POST"])
def student_login():
    if request.method == "POST":
        _id = request.form.get("_id")
        password = request.form.get("password")
        user_data = dataset(_id)

        if user_data and user_data[0]["password"] == password:
            return redirect(url_for("student", student_ids=_id))
        else:
            # Either user not found or password incorrect
            error_message = "Invalid ID or password"
            return render_template("student_login.html", error=error_message)

    return render_template("student_login.html")

# @app.route("/student/<data>/", defaults={"title": None}, methods=["GET", "POST"])
@app.route("/student", methods=["GET", "POST"])
def student():
    _id = request.form.get('id_number')  # Avoid KeyError
    if not _id:
        return "Missing student ID", 400  # Handle missing ID error
    try:
        result = dataset(_id)
        if result is None or all(x is None for x in result):
            return render_template("error.html", message="Student not found"), 404  # Proper error page

        studentInfo, imgStudent, secondElapsed = result
        hoursElapsed = round((secondElapsed / 3600), 2) if secondElapsed is not None else "Unknown"
        info = {
            "studentInfo": studentInfo,
            "lastlogin": hoursElapsed,
            "image": imgStudent,
        }
        return render_template("student.html", data=info)

    except Exception as e:
        print(f"Error in student route: {e}")
        return render_template("error.html", message="Unexpected error occurred"), 500  # Internal Server Error


# @app.route("/student_attendance_list",methods=["GET", "POST"])
# def student_attendance_list():
#     already_marked_id_student = []  # Initialize the list
#     unique_id_student = list(set(already_marked_id_student))
#     student_info = []
#     for i in unique_id_student:
#         student_info.append(dataset(_id))
#     return render_template("student_attendance_list.html", data=student_info)

def fetch_marked_students():
    marked_students = ["2200100943", "2200100944"]  # Example student IDs
    return marked_students

@app.route("/student_attendance_list")
def student_attendance_list():

    already_marked_id_student = fetch_marked_students()  # Get IDs of students who marked attendance
    unique_id_student = list(set(already_marked_id_student))  # Ensure IDs are unique
    student_info = []
    for i in unique_id_student:
        student = dataset(i)
        if student and student[0]:  # Ensure valid data before adding
            student_info.append(student)
    print("DEBUG - Student Info Sent to Template:", student_info)  # Debugging output
    return render_template("student_attendance_list.html", data=student_info)


#########################################################################################################################

@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    try:
        # Fetch all student data
        username = request.form.get('_id')
        email = request.form.get('email')
        password = request.form.get('password')

        if username == '2200100943' and email == 'mohdameer01a@gmail.com' and password == '2022503105':
            return redirect(url_for('admin'))
        all_student_info = list(students_collection.find({}))
        #print(all_student_info)
        return render_template("admin_login.html")
    except Exception as e:
        print(f"Error in /admin route: {e}")
        return render_template("admin_login.html", data=all_student_info)

@app.route("/admin", methods=["GET", "POST"])
def admin():
    try:
        return render_template("admin.html")
    except Exception as e:
        return "Not Found"

@app.route("/admin/admin_attendance_list", methods=["GET", "POST"])
def admin_attendance_list():
    try:
        if request.method == "POST":
            if request.form.get("button_student") == "VALUE1":
                already_marked_id_student.clear()
                return redirect(url_for("admin_attendance_list"))
            elif request.form.get("button_admin") == "VALUE2":
                already_marked_id_admin.clear()
                return redirect(url_for("admin_attendance_list"))
        else:
            unique_id_admin = list(set(already_marked_id_admin))
            student_info = []
            for i in unique_id_admin:
                # students = dataset(_id)
                # if students:
                    student_info.append(dataset(_id))
            print(f"Student Info: {student_info}")
            return render_template("admin_attendance_list.html", data=student_info)
    except Exception as e:
        print(f"Error in /admin/admin_attendance_list route: {e}")
        return render_template("admin_attendance_list.html", data=[], error="An error occurred.")


#########################################################################################################################
# @app.route("/student_attendance_list")
# def student_attendance_list():
#     already_marked_id_student = fetch_marked_students()  # Get IDs of students who marked attendance
#     unique_id_student = list(set(already_marked_id_student))  # Ensure IDs are unique
#     student_info = []

#     for i in unique_id_student:
#         student = dataset(i)
#         if student and student[0]:  # Ensure valid data before adding
#             student_info.append(student)

#     print("DEBUG - Student Info Sent to Template:", student_info)  # Debugging output

#     return render_template("student_attendance_list.html", data=student_info)


def add_image_database():
    folderPath = "C:/Users/DELL/OneDrive/Desktop/Ameer/Face-Recognition-System-for-Student-Attendance/static/Files/Images"  # Path to your images
    imgPathList = os.listdir(folderPath)
    imgList = []
    studentIDs = []

    for path in imgPathList:
        imgList.append(cv2.imread(os.path.join(folderPath, path)))
        studentIDs.append(os.path.splitext(path)[0])  # Get the student ID from the filename

    return studentIDs, imgList

def findEncodings(images):
     encodeList = []
 
     for img in images:
         img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
         encode = face_recognition.face_encodings(img)[0]
         encodeList.append(encode)
 
     return encodeList


@app.route("/admin/add_user", methods=["GET", "POST"])
def add_user():
    if request.method == "POST":
        _id = request.form.get("_id")
        name = request.form.get("name")
        password = request.form.get("password")
        dob = request.form.get("dob")
        city = request.form.get("city")
        country = request.form.get("country")
        phone = request.form.get("phone")
        email = request.form.get("email")
        major = request.form.get("major")
        starting_year = int(request.form.get("starting_year"))
        standing = request.form.get("standing")
        total_attendance = int(request.form.get("total_attendance"))
        year = int(request.form.get("year"))
        last_attendance_date = request.form.get("last_attendance_date")
        last_attendance_time = request.form.get("last_attendance_time")
        content = request.form.get("content")

        address = f"{city}, {country}"
        last_attendance_datetime = f"{last_attendance_date} {last_attendance_time}:00"

        # Save image
        image = request.files["image"]
        filename = f"{_id}.png"
        image_path = os.path.join("static", "Files", "Images", filename)
        image.save(image_path)

        # Insert into DB
        students_collection = db["students"]
        student_data = {
            "_id": _id,
            "name": name,
            "password": password,
            "dob": dob,
            "address": address,
            "phone": phone,
            "email": email,
            "major": major,
            "starting_year": starting_year,
            "standing": standing,
            "total_attendance": total_attendance,
            "year": year,
            "last_attendance_time": last_attendance_datetime,
            "content": content,
        }

        result = students_collection.insert_one(student_data)

        if result.inserted_id:
            print(f"✅ Student with ID {_id} inserted successfully!")

            # Refresh image encodings
            studentIDs, imgList = add_image_database()
            encodeListKnown = findEncodings(imgList)
            encodeListKnownWithIds = [encodeListKnown, studentIDs]

            with open("EncodeFile.p", "wb") as file:
                pickle.dump(encodeListKnownWithIds, file)

            return redirect(url_for("admin"))  # redirect to admin dashboard
        else:
            print("❌ Failed to insert student.")

    return render_template("add_user.html")

#########################################################################################################################

@app.route("/admin/edit_user", methods=["POST", "GET"])
def edit_user():
    if request.method == "POST" or request.method=="GET":
        value = request.form.get("edit_user")
        # Call dataset function to fetch student data
        studentInfo, imgStudent, secondElapsed = dataset(value)
        # Default image if not found
        if not imgStudent or not os.path.exists(imgStudent):
            imgStudent = "static/Files/Images/default.png"
        # Convert seconds to hours
        hoursElapsed = round((secondElapsed / 3600), 2)
        # Create dictionary to pass to template
        info = {
            "studentInfo": studentInfo,
            "lastlogin": hoursElapsed,
            "image": imgStudent,
        }
        return render_template("edit_user.html", data=info)
    else:
        value = request.form.get("edit_user")
    
        # Call dataset function to fetch student data
        studentInfo, imgStudent, secondElapsed = dataset(value)

        # Default image if not found
        if not imgStudent or not os.path.exists(imgStudent):
            imgStudent = "static/Files/Images/default.png"
        
        # Convert seconds to hours
        hoursElapsed = round((secondElapsed / 3600), 2)

        # Create dictionary to pass to template
        info = {
            "studentInfo": studentInfo,
            "lastlogin": hoursElapsed,
            "image": imgStudent,
        }

        return render_template("admin.html")

    # "Invalid Request 1", 400  # Handle GET request or invalid methods



#########################################################################################################################
@app.route("/admin/save_changes", methods=["POST", "GET"])
def save_changes():
    content = request.get_data()
    dic_data = json.loads(content.decode("utf-8"))
    dic_data = {k: v.strip() for k, v in dic_data.items()}
    dic_data["year"] = int(dic_data["year"])
    dic_data["total_attendance"] = int(dic_data["total_attendance"])
    dic_data["starting_year"] = int(dic_data["starting_year"])
    students_collection = db["students"]
    result = students_collection.update_one(
        {"_id": dic_data["_id"]},  # Filter by student ID
        {"$set": {  # Use $set to update specific fields
            "name": dic_data["name"],
            "dob": dic_data["dob"],
            "address": dic_data["address"],
            "phone": dic_data["phone"],
            "email": dic_data["email"],
            "major": dic_data["major"],
            "starting_year": dic_data["starting_year"],
            "standing": dic_data["standing"],
            "total_attendance": dic_data["total_attendance"],
            "year": dic_data["year"],
            "last_attendance_time": dic_data["last_attendance_time"],
            "content": dic_data["content"],
        }}
    )

    if result.matched_count > 0:
        return "Data updated successfully!"
    else:
        return "No matching document found. Update failed."


#########################################################################################################################


def delete_image(_id):
    filepath = f"./static/Files/Images/{_id}.png"
    os.remove(filepath)
    return "Successful"


@app.route("/admin/delete_user", methods=["POST", "GET"])
def delete_user():
    content = request.get_data()
    _id = json.loads(content.decode("utf-8"))
    delete_student = db.reference(f"students")
    delete_student.child(_id).delete()
    delete_image(_id)
    studentIDs, imgList = add_image_database()
    encodeListKnown = findEncodings(imgList)
    encodeListKnownWithIds = [encodeListKnown, studentIDs]
    file = open("EncodeFile.p", "wb")
    pickle.dump(encodeListKnownWithIds, file)
    file.close()
    return "Successful"


#########################################################################################################################
if __name__ == "__main__":
    app.run(debug=True,port=5001,use_reloader=False)
    
