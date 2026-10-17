import face_recognition
import os
import numpy as np

# ---------------------------------
# Configuration
# ---------------------------------
MATCH_THRESHOLD = 0.78   # Adjust between 0.65 – 0.75 for ESP32
BASE_DIR = os.path.dirname(__file__)
KNOWN_FACES_DIR = os.path.join(BASE_DIR, "known_faces")

# ---------------------------------
# Storage
# ---------------------------------
known_encodings = []
known_names = []


# ---------------------------------
# Load Known Faces
# ---------------------------------
def load_known_faces():
    global known_encodings, known_names

    if not os.path.exists(KNOWN_FACES_DIR):
        print("⚠ known_faces folder not found!")
        return

    print("🔄 Loading known faces...")

    for filename in os.listdir(KNOWN_FACES_DIR):

        if filename.lower().endswith((".jpg", ".jpeg", ".png")):

            path = os.path.join(KNOWN_FACES_DIR, filename)

            image = face_recognition.load_image_file(path)

            face_locations = face_recognition.face_locations(image, model="hog")
            encodings = face_recognition.face_encodings(image, face_locations)

            if len(encodings) > 0:

                known_encodings.append(encodings[0])

                # Extract name before underscore
                name = os.path.splitext(filename)[0]
                name = name.split("_")[0]

                known_names.append(name)

                print(f"   ✔ Loaded: {name}")

            else:
                print(f"   ⚠ No face found in {filename}")

    print("✅ Known faces loaded:", known_names)


# ---------------------------------
# Face Recognition Function
# ---------------------------------
def recognize_face(image_path):

    if len(known_encodings) == 0:
        print("⚠ No known encodings available")
        return "Unknown"

    image = face_recognition.load_image_file(image_path)

    face_locations = face_recognition.face_locations(image, model="hog")
    encodings = face_recognition.face_encodings(image, face_locations)

    print("🔍 Faces detected in frame:", len(encodings))

    if len(encodings) == 0:
        return "Unknown"

    for face_encoding in encodings:

        face_distances = face_recognition.face_distance(
            known_encodings,
            face_encoding
        )

        print("📏 Face distances:", face_distances)

        best_match_index = np.argmin(face_distances)
        best_distance = face_distances[best_match_index]

        print("🎯 Best distance:", best_distance)

        if best_distance < MATCH_THRESHOLD:
            matched_name = known_names[best_match_index]
            print("✅ Match found:", matched_name)
            return matched_name

    return "Unknown"


# ---------------------------------
# Initialize
# ---------------------------------
load_known_faces()