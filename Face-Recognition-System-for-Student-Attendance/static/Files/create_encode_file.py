import os
import cv2
import pickle
import face_recognition

def add_image_database():
    folderPath = "C:/Users/DELL/OneDrive/Desktop/Ameer/Face-Recognition-System-for-Student-Attendance/static/Files/Images"
    imgPathList = os.listdir(folderPath)
    imgList = []
    studentIDs = []

    for path in imgPathList:
        img = cv2.imread(os.path.join(folderPath, path))
        if img is not None:  # Check if the image was loaded successfully
            imgList.append(img)
            studentIDs.append(os.path.splitext(path)[0])  # Get the student ID from the filename

    return studentIDs, imgList

def findEncodings(images):
    encodeList = []
    for img in images:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        encode = face_recognition.face_encodings(img)[0]
        encodeList.append(encode)
    return encodeList

# Main function to create EncodeFile.p
def create_encode_file():
    studentIDs, imgList = add_image_database()
    if not imgList:
        print("No images found in the specified directory.")
        return

    encodeListKnown = findEncodings(imgList)

    output_path = "C:/Users/DELL/OneDrive/Desktop/Ameer/Face-Recognition-System-for-Student-Attendance/ EncodeFile.p"
    with open(output_path, "wb") as file:
        pickle.dump([encodeListKnown, studentIDs], file)

    print("EncodeFile.p created successfully!")

if __name__ == "__main__":
    create_encode_file()