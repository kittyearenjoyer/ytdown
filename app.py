import streamlit as st
from ultralytics import YOLOWorld
from PIL import Image
import numpy as np
import pandas as pd
import os
from datetime import datetime

# -----------------------------
# Setup
# -----------------------------
st.set_page_config(page_title="Digitales KI-Fundbüro", layout="wide")
st.title("🧠 Digitales KI-Fundbüro")
st.write("Bilder hochladen, Objekte automatisch erkennen. Fundliste auf Knopfdruck ein-/ausblenden.")

# Ordner & CSV-Datei
UPLOAD_FOLDER = "uploads"
DATA_FILE = "fundliste.csv"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -----------------------------
# Modell laden
# -----------------------------
@st.cache_resource
def load_model():
    return YOLOWorld("yolov8s-world.pt")  # Zero-shot Modell

model = load_model()

# -----------------------------
# Eingaben für KI
# -----------------------------
classes_input = st.text_input(
    "Welche Objekte soll die KI erkennen? (Komma getrennt)",
    "hat, key, wallet, phone, backpack"
)
prompt_list = [c.strip() for c in classes_input.split(",") if c.strip()]

uploaded_file = st.file_uploader(
    "Bild hochladen",
    type=["jpg","jpeg","png"]
)

# -----------------------------
# KI Analyse & Fund speichern
# -----------------------------
if uploaded_file and prompt_list:
    image = Image.open(uploaded_file)
    st.image(image, caption="Hochgeladenes Bild", use_column_width=True)

    model.set_classes(prompt_list)
    img_array = np.array(image)
    st.write("🔍 KI analysiert das Bild…")
    results = model.predict(img_array)

    annotated = results[0].plot()
    st.image(annotated, caption="Erkannte Objekte", use_column_width=True)

    labels = results[0].boxes.cls
    detected = [prompt_list[int(idx)] for idx in labels] if len(labels) > 0 else []

    if detected:
        st.success("Gefunden: " + ", ".join(set(detected)))

        # CSV laden oder erstellen
        if os.path.exists(DATA_FILE):
            df = pd.read_csv(DATA_FILE)
        else:
            df = pd.DataFrame(columns=["zeit","datei","erkannte_objekte","fundort","beschreibung"])

        # Prüfen, ob Bild + Objekte schon existieren
        exists = ((df['datei'] == uploaded_file.name) & 
                  (df['erkannte_objekte'] == ", ".join(set(detected)))).any()

        if not exists:
            entry = {
                "zeit": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "datei": uploaded_file.name,
                "erkannte_objekte": ", ".join(set(detected)),
                "fundort": "",
                "beschreibung": ""
            }
            df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
            df.to_csv(DATA_FILE, index=False)

            # Bild speichern, nur wenn es noch nicht existiert
            image_path = os.path.join(UPLOAD_FOLDER, uploaded_file.name)
            if not os.path.exists(image_path):
                image.save(image_path)

            st.success("Fund wurde gespeichert!")
        else:
            st.info("Dieses Bild mit den erkannten Objekten ist bereits gespeichert.")
    else:
        st.warning("Keine der eingegebenen Objekte erkannt. Fund nicht gespeichert.")

# -----------------------------
# Button: Alle Funde ein-/ausblenden
# -----------------------------
st.header("Funde anzeigen / verbergen")
if 'show_funde' not in st.session_state:
    st.session_state.show_funde = False

def toggle_funde():
    st.session_state.show_funde = not st.session_state.show_funde

st.button("Alle Funde ein-/ausblenden", on_click=toggle_funde)

if st.session_state.show_funde:
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        for i, row in df.iterrows():
            st.subheader(f"Fund vom {row['zeit']}")
            st.write(f"Objekte: {row['erkannte_objekte']}")
            st.write(f"Fundort: {row['fundort']}")
            st.write(f"Beschreibung: {row['beschreibung']}")
            image_path = os.path.join(UPLOAD_FOLDER, row["datei"])
            if os.path.exists(image_path):
                st.image(image_path, width=300)
            st.markdown("---")
    else:
        st.write("Noch keine Einträge vorhanden.")
