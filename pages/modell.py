"""Modell: Infektionsrisiko der nächsten 7 Tage, Modellgüte, Feature-Wichtigkeit."""
from datetime import timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import app_state as S
from core import config
from ml import predict, train
from ml.features import FEATURE_LABELS

st.title("🤖 Infektionsmodell")
st.write("Random Forest, der aus **Prognose-Wetter (Open-Meteo)** vorhersagt, ob an einem Tag eine "
         "Infektion stattfindet. Labels stammen aus den Agrometeo-Tabellen. Agrometeo meldet eine "
         "Infektion erst nach gemessener Blattnässe – das Modell warnt Tage im Voraus.")


@st.cache_resource
def get_model():
    return predict.load_model()


bundle = get_model()
if bundle is None:
    st.info("Noch kein trainiertes Modell gefunden (ml/model.joblib).")
    if st.button("Modell jetzt trainieren (lädt Open-Meteo-Archiv, ca. 1 Min.)", type="primary"):
        with st.spinner("Trainiere …"):
            try:
                train.train_and_save()
            except Exception as exc:  # noqa: BLE001
                st.error(f"Training fehlgeschlagen: {exc}")
                st.stop()
        get_model.clear()
        st.rerun()
    st.stop()

# --- Risiko der nächsten 7 Tage -------------------------------------------------------
season, notes = S.get_season()
if season is not None:
    st.subheader("Risiko der nächsten 7 Tage")
    risk = predict.predict_risk(bundle, season.daily)
    t = pd.Timestamp(season.today)
    risk = risk[(risk["date"] > t) & (risk["date"] <= t + timedelta(days=config.FORECAST_DAYS))].copy()
    if risk.empty:
        st.write("Keine Prognosetage mit vollständigen Open-Meteo-Daten (z. B. offline).")
    else:
        rule = season.daily.set_index("date")["infection_level"]
        risk["Regel (Gradstunden)"] = risk["date"].map(rule).fillna(0).astype(int).map(config.INFECTION_SYMBOLS)
        risk["Tag"] = risk["date"].dt.strftime("%a %d.%m.")
        fig = px.bar(risk, x="Tag", y="proba", range_y=[0, 1], text=risk["proba"].map("{:.0%}".format),
                     color="proba", color_continuous_scale=["#2e9d4f", "#e0a800", "#d64545"],
                     range_color=[0, 1], labels={"proba": "Wahrscheinlichkeit"})
        fig.add_hline(y=0.5, line_dash="dash", line_color="gray")
        fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10), coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(risk[["Tag", "proba", "Regel (Gradstunden)"]].rename(columns={"proba": "Modell"}),
                     hide_index=True, use_container_width=True,
                     column_config={"Modell": st.column_config.ProgressColumn(format="%.2f", min_value=0, max_value=1)})

# --- Modellgüte -------------------------------------------------------------------------
st.subheader(f"Modellgüte – Training {bundle['train_years']}, Test {bundle['test_year']}")
st.caption(f"Zeitlicher Split (kein Zufallssplit). Training: {bundle['n_train']} Tage, davon "
           f"{bundle['positives_train']} mit Infektion; Test: {bundle['n_test']} Tage, "
           f"{bundle['positives_test']} mit Infektion. Trainiert am {bundle['trained_at']}.")
rows = []
for name, m in bundle["metrics"].items():
    rows.append({"Modell": name, "Recall": m["recall"], "Precision": m["precision"],
                 "F1": m["f1"], "Accuracy": m["accuracy"]})
st.dataframe(pd.DataFrame(rows).round(2), hide_index=True, use_container_width=True)
st.caption("Recall ist am wichtigsten: eine verpasste Infektion ist teurer als ein Fehlalarm.")

cols = st.columns(len(bundle["metrics"]))
for col, (name, m) in zip(cols, bundle["metrics"].items()):
    fig = px.imshow(m["confusion"], text_auto=True, color_continuous_scale="Blues",
                    x=["keine", "Infektion"], y=["keine", "Infektion"],
                    labels=dict(x="vorhergesagt", y="tatsächlich (Agrometeo)"))
    fig.update_layout(title=name, height=320, margin=dict(l=10, r=10, t=40, b=10),
                      coloraxis_showscale=False)
    col.plotly_chart(fig, use_container_width=True)

# --- Feature-Wichtigkeit ---------------------------------------------------------------
st.subheader("Feature-Wichtigkeit")
imp = pd.DataFrame({"Feature": [FEATURE_LABELS.get(k, k) for k in bundle["importance"]],
                    "Wichtigkeit": list(bundle["importance"].values())}).sort_values("Wichtigkeit")
fig = px.bar(imp, x="Wichtigkeit", y="Feature", orientation="h", labels={"Feature": ""})
fig.update_layout(height=400, showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
st.plotly_chart(fig, use_container_width=True)

# --- Testsaison im Verlauf -------------------------------------------------------------
st.subheader(f"Testsaison {bundle['test_year']} im Verlauf")
tp = bundle["test_predictions"]
fig = go.Figure()
fig.add_trace(go.Scatter(x=tp["date"], y=tp["proba"], name="Modell-Wahrscheinlichkeit",
                         line=dict(color="#444")))
hits = tp[tp["y"] == 1]
fig.add_trace(go.Scatter(x=hits["date"], y=[1.02] * len(hits), mode="markers", name="Infektion (Agrometeo)",
                         marker=dict(symbol="triangle-down", color="#d64545", size=9)))
fig.add_hline(y=0.5, line_dash="dash", line_color="gray")
fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10), yaxis=dict(range=[0, 1.08]),
                  legend=dict(orientation="h", y=1.15))
st.plotly_chart(fig, use_container_width=True)

st.info("Trainiert auf 1 Station und wenigen Saisons – Entscheidungshilfe, keine Beratung.")
if st.button("Modell neu trainieren"):
    with st.spinner("Trainiere …"):
        train.train_and_save()
    get_model.clear()
    st.rerun()
