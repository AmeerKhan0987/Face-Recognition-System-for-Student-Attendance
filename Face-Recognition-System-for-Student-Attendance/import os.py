import pickle

# Example data to dump into EncodeFile.p
encoded_face_known = [
    [0.123, 0.456, 0.789],  # Example face encoding for person 1
    [0.987, 0.654, 0.321]   # Example face encoding for person 2
]
student_ids = ['004223', '004224']  # Corresponding student IDs

# Dump the data into EncodeFile.p


try:
    with open('EncodeFile.p', 'rb') as file:
        loaded_data = pickle.load(file)
    print("Loaded Data:", loaded_data)
    encoded_faces, ids = loaded_data
    print("Encoded Faces:", encoded_faces)
    print("Student IDs:", ids)
except Exception as e:
    print(f"Error loading file: {e}")
