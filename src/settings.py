"""Central place for every tunable value in SnapClass.

Change numbers here instead of hunting through the code.
"""

APP_NAME = "SnapClass"
TAGLINE = "Attendance in a snap, powered by face & voice AI"

# ---------------- Face detection / matching ----------------
# dlib gives every detection a confidence score. Real faces usually score
# well above 1.0, animals / posters / random objects score low or get filtered
# by the landmark check below. Raise this (0.8 - 1.2) if an animal still slips
# through; lower it (0.3) if real faces in big group photos are missed.
MIN_FACE_SCORE = 0.5
MIN_FACE_SIZE = 40                # pixels, ignores tiny false detections
MAX_DETECT_SIDE = 1600            # big classroom photos are shrunk to this
CHECK_HUMAN_LANDMARKS = True      # reject "faces" whose geometry is not human

# Distance between two face embeddings (smaller = more similar).
MATCH_THRESHOLD = 0.60            # above this -> unknown person
REVIEW_THRESHOLD = 0.50           # between 0.50 and 0.60 -> teacher should review

# ---------------- Liveness (anti photo-spoofing) ----------------
LIVENESS_REQUIRED = True          # student must blink / close eyes to log in
MIN_OPEN_EAR = 0.20               # eye aspect ratio of an open eye
CLOSED_EAR_RATIO = 0.75           # closed-eye EAR must be < 75% of open-eye EAR
LIVENESS_SAME_PERSON_DISTANCE = 0.75   # both photos must show the same person

# ---------------- Business rules ----------------
ATTENDANCE_WARN_PERCENT = 75      # below this a student is "at risk"
MAX_LOGIN_ATTEMPTS = 5            # teacher password attempts before lockout
LOCKOUT_SECONDS = 60
MIN_PASSWORD_LENGTH = 6
