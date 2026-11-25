import streamlit as st
from PIL import Image, ImageOps


def _load(file):
    # phones store rotation in EXIF; apply it so faces are upright
    return ImageOps.exif_transpose(Image.open(file)).convert("RGB")


@st.dialog("Capture or upload photos")
def add_photos_dialog():
    st.write("Add classroom photos to scan for attendance. Several photos of different "
             "corners of the room give the best result.")

    if "photo_tab" not in st.session_state:
        st.session_state.photo_tab = "camera"

    t1, t2 = st.columns(2)
    with t1:
        kind = "primary" if st.session_state.photo_tab == "camera" else "tertiary"
        if st.button("Camera", type=kind, width="stretch", icon=":material/photo_camera:"):
            st.session_state.photo_tab = "camera"
    with t2:
        kind = "primary" if st.session_state.photo_tab == "upload" else "tertiary"
        if st.button("Upload photos", type=kind, width="stretch", icon=":material/upload:"):
            st.session_state.photo_tab = "upload"

    if st.session_state.photo_tab == "camera":
        cam_photo = st.camera_input("Take Snapshot", key="dialog_cam")
        if cam_photo:
            st.session_state.attendance_images.append(_load(cam_photo))
            st.toast("Photo captured")
            st.rerun()

    if st.session_state.photo_tab == "upload":
        files = st.file_uploader("Choose image files", type=["jpg", "png", "jpeg"],
                                 accept_multiple_files=True, key="dialog_upload")
        if files:
            for f in files:
                st.session_state.attendance_images.append(_load(f))
            st.toast("Photos uploaded")
            st.rerun()

    st.divider()
    if st.button("Done", type="primary", width="stretch"):
        st.rerun()
