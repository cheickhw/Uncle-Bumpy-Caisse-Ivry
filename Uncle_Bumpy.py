import streamlit as st
import pandas as pd
import json
from datetime import date
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Uncle Bumpy — Caisse",
    page_icon="🍗",
    layout="centered",
)

HISTORY_FILE = Path("historique.json")
FDC = 20.0  # Fond de caisse fixe

# ── Helpers ───────────────────────────────────────────────────────────────────
def load_history() -> list[dict]:
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return []

def save_history(data: list[dict]):
    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def fmt(v: float) -> str:
    return f"{v:,.2f} €".replace(",", " ").replace(".", ",")

# ── Init session state ────────────────────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = load_history()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## 🍗 Uncle Bumpy — Caisse Ivry")
st.caption(f"Aujourd'hui : {date.today().strftime('%A %d %B %Y').capitalize()}")
st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_saisie, tab_historique = st.tabs(["📝 Saisie du soir", "📊 Historique"])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — SAISIE
# ═══════════════════════════════════════════════════════════════════════════════
with tab_saisie:

    st.markdown("#### Canaux de vente")
    col1, col2 = st.columns(2)

    with col1:
        cb    = st.number_input("💳 CB — Carte bancaire",   min_value=0.0, step=0.5, format="%.2f")
        uber  = st.number_input("🛵 UBER — Uber Eats (brut)", min_value=0.0, step=0.5, format="%.2f")
        borne = st.number_input("📦 Borne — Autre canal",   min_value=0.0, step=0.5, format="%.2f")

    with col2:
        esp  = st.number_input("💵 ESP — Espèces",           min_value=0.0, step=0.5, format="%.2f")
        deli = st.number_input("🛵 DELI — Deliveroo (brut)", min_value=0.0, step=0.5, format="%.2f")

    coeff = st.slider(
        "Coefficient net livraison",
        min_value=0.50, max_value=1.00, value=0.64, step=0.01,
        help="Part reversée par la plateforme (ex: 0,64 = 64% du brut)"
    )
    st.caption(f"Uber net = {uber * coeff:.2f} €   |   Deli net = {deli * coeff:.2f} €")

    # ── Calculs ────────────────────────────────────────────────────────────────
    uber_net  = uber * coeff
    deli_net  = deli * coeff
    livraison_net = uber_net + deli_net
    total_ca  = cb + esp + uber_net + deli_net + borne
    cash_net  = max(0.0, esp - FDC)

    st.divider()
    st.markdown("#### Récapitulatif")

    c1, c2, c3 = st.columns(3)
    c1.metric("CA Total", fmt(total_ca))
    c2.metric("Cash à remettre", fmt(cash_net), delta=f"- {fmt(FDC)} FDC", delta_color="off")
    c3.metric("Livraisons nettes", fmt(livraison_net))

    with st.expander("Voir le détail"):
        detail = {
            "Canal": ["CB", "Espèces (brut)", "Uber Eats (net)", "Deliveroo (net)", "Borne"],
            "Montant": [fmt(cb), fmt(esp), fmt(uber_net), fmt(deli_net), fmt(borne)],
        }
        st.table(pd.DataFrame(detail))
        st.markdown(f"**Fond de caisse déduit :** {fmt(FDC)}")
        st.markdown(f"**Cash réel à remettre :** {fmt(cash_net)}")

    st.divider()

    # ── Enregistrement ─────────────────────────────────────────────────────────
    note = st.text_input("Note (facultatif)", placeholder="Ex: service tranquille, panne CB...")
    jour = st.date_input("Date du service", value=date.today())

    if st.button("✅ Enregistrer la journée", use_container_width=True, type="primary"):
        if total_ca == 0:
            st.warning("Aucune valeur saisie !")
        else:
            entry = {
                "date": str(jour),
                "cb": cb, "esp": esp,
                "uber": uber, "deli": deli, "borne": borne,
                "coeff": coeff,
                "uber_net": uber_net, "deli_net": deli_net,
                "total_ca": total_ca,
                "cash_net": cash_net,
                "note": note,
            }
            st.session_state.history.insert(0, entry)
            save_history(st.session_state.history)
            st.success(f"Journée du {jour.strftime('%d/%m/%Y')} enregistrée — CA : {fmt(total_ca)}")
            st.balloons()

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — HISTORIQUE
# ═══════════════════════════════════════════════════════════════════════════════
with tab_historique:

    hist = st.session_state.history

    if not hist:
        st.info("Aucune journée enregistrée pour l'instant.")
    else:
        # ── Totaux cumulés ────────────────────────────────────────────────────
        df = pd.DataFrame(hist)
        total_ca_cum  = df["total_ca"].sum()
        total_cash_cum = df["cash_net"].sum()
        total_livr_cum = (df["uber_net"] + df["deli_net"]).sum()

        st.markdown("#### Totaux cumulés")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("CA cumulé",       fmt(total_ca_cum))
        m2.metric("Cash remis",      fmt(total_cash_cum))
        m3.metric("Livraisons net",  fmt(total_livr_cum))
        m4.metric("Jours enregistrés", str(len(hist)))

        # ── Graphique CA ──────────────────────────────────────────────────────
        if len(hist) > 1:
            st.divider()
            st.markdown("#### Évolution du CA")
            chart_df = df[["date", "total_ca"]].rename(
                columns={"date": "Date", "total_ca": "CA (€)"}
            ).sort_values("Date")
            st.bar_chart(chart_df.set_index("Date"), color="#BA7517")

        # ── Liste détaillée ───────────────────────────────────────────────────
        st.divider()
        st.markdown("#### Détail par journée")

        for i, e in enumerate(hist):
            with st.expander(
                f"📅 {e['date']}  —  CA {fmt(e['total_ca'])}  |  cash {fmt(e['cash_net'])}"
            ):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown(f"- **CB :** {fmt(e['cb'])}")
                    st.markdown(f"- **Espèces :** {fmt(e['esp'])}")
                    st.markdown(f"- **Borne :** {fmt(e['borne'])}")
                with col_b:
                    st.markdown(f"- **Uber net :** {fmt(e['uber_net'])}")
                    st.markdown(f"- **Deli net :** {fmt(e['deli_net'])}")
                    st.markdown(f"- **Coeff :** {e['coeff']:.0%}")
                if e.get("note"):
                    st.caption(f"Note : {e['note']}")

                if st.button("🗑️ Supprimer", key=f"del_{i}"):
                    st.session_state.history.pop(i)
                    save_history(st.session_state.history)
                    st.rerun()

        # ── Export CSV ────────────────────────────────────────────────────────
        st.divider()
        export_df = df[[
            "date", "cb", "esp", "uber", "deli", "borne",
            "coeff", "uber_net", "deli_net", "total_ca", "cash_net", "note"
        ]].rename(columns={
            "date": "Date", "cb": "CB", "esp": "Espèces",
            "uber": "Uber brut", "deli": "Deli brut", "borne": "Borne",
            "coeff": "Coeff", "uber_net": "Uber net", "deli_net": "Deli net",
            "total_ca": "CA total", "cash_net": "Cash remis", "note": "Note"
        })
        st.download_button(
            label="⬇️ Exporter en CSV",
            data=export_df.to_csv(index=False, sep=";", decimal=",").encode("utf-8"),
            file_name=f"uncle_bumpy_caisse.csv",
            mime="text/csv",
            use_container_width=True,
        )