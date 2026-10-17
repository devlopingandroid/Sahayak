from datetime import datetime
import json
import os

# ---------------------------------
# Configuration
# ---------------------------------
BASE_DIR = os.path.dirname(__file__)
MEMORY_FILE = os.path.join(BASE_DIR, "memory_db.json")
MAX_MEMORY_ENTRIES = 500


# ---------------------------------
# Load Memory Safely
# ---------------------------------
def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return []

    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except Exception:
        print("⚠ Memory file corrupted. Resetting...")
        return []


# ---------------------------------
# Save Memory
# ---------------------------------
def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=4)


# ---------------------------------
# Create Episode
# ---------------------------------
def create_episode(patient_id, event_type, objects, image_path, person_name="Unknown"):

    memory = load_memory()

    # Remove duplicates
    objects = list(set(objects))

    # Remove generic 'person'
    if person_name != "Unknown" and "person" in objects:
        objects.remove("person")

    # 🔥 Skip useless memory (only person, no objects)
    if not objects and person_name != "Unknown":
        print("⚠ Skipping empty object memory")
        return None

    episode = {
        "Who": person_name,
        "What": objects,
        "When": datetime.now().isoformat(),
        "Where": "Room_1",
        "EventType": event_type,
        "Evidence": image_path
    }

    memory.append(episode)

    # Limit memory size
    if len(memory) > MAX_MEMORY_ENTRIES:
        memory = memory[-MAX_MEMORY_ENTRIES:]

    save_memory(memory)

    print("🧠 Episode Stored:", episode)

    return episode


# ---------------------------------
# Smart Query Engine
# ---------------------------------
def query_memory(object_name=None, person_name=None):

    memory = load_memory()

    if not memory:
        return None

    object_name = object_name.lower() if object_name else None
    person_name = person_name.lower() if person_name else None

    for episode in reversed(memory):

        match_object = True
        match_person = True

        if object_name:
            match_object = object_name in [obj.lower() for obj in episode["What"]]

        if person_name:
            match_person = person_name == episode["Who"].lower()

        if match_object and match_person:
            return episode

    return None


# ---------------------------------
# Generate Natural Language Response
# ---------------------------------
def generate_response(episode):

    who = episode["Who"]
    objects = episode["What"]
    when = episode["When"]
    where = episode["Where"]

    if objects:
        obj_text = ", ".join(objects)
        return f"{who} was last seen with {obj_text} in {where} at {when}"
    else:
        return f"{who} was last seen in {where} at {when}"