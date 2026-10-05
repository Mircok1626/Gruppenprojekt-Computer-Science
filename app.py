import streamlit as st

st.title("Meine erste App")

name = st.text_input("Wie heisst du?")

if name:
    st.write(f"Hallo {name}! Schön, dass du da bist.")


Print("Hello, my name is Mirco")