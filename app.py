import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go


# Πηγή: Πρωτόκολλο 5, σελίδες 3-4.
# Το TE ακολουθεί τον γραμμένο τύπο: SD(Trial 2 - Trial 1) / sqrt(2).
# Δεν αλλάζουμε τον τύπο για να προκύψει συγκεκριμένο αποτέλεσμα στο Β.
SWC_FACTOR = 0.2
MDC_FACTOR = 2.77

DATA = {
    "Σενάριο Α": [
        ["S1", 62, 61, 62],
        ["S2", 55, 56, 55],
        ["S3", 70, 69, 70],
        ["S4", 58, 58, 59],
        ["S5", 65, 64, 65],
    ],
    "Σενάριο Β": [
        ["S1", 62, 68, 63],
        ["S2", 55, 61, 54],
        ["S3", 70, 76, 69],
        ["S4", 58, 65, 57],
        ["S5", 65, 71, 64],
    ],
}

COLUMNS = [
    "ID", "HR_T1", "HR_T2", "HR_T3", "Mean_HR", "SD_between",
    "Diff_T2_T1", "Diff_T3_T2", "SD_diff", "TE", "SWC",
    "Signal_Noise_Ratio", "MDC95",
]


def analyse(rows: list) -> tuple[pd.DataFrame, dict]:
    """Υπολογισμοί ανά σενάριο, χωρίς ενδιάμεση στρογγυλοποίηση."""
    df = pd.DataFrame(rows, columns=COLUMNS[:4])
    hr = df[["HR_T1", "HR_T2", "HR_T3"]].to_numpy(dtype=float)
    if len(df) < 2 or not np.isfinite(hr).all():
        raise ValueError("Απαιτούνται τουλάχιστον δύο πλήρεις αριθμητικές εγγραφές.")

    df["Mean_HR"] = hr.mean(axis=1)
    df["Diff_T2_T1"] = df["HR_T2"] - df["HR_T1"]
    df["Diff_T3_T2"] = df["HR_T3"] - df["HR_T2"]

    # ddof=1: δειγματική τυπική απόκλιση, όπως το STDEV.S του Excel.
    sd_between = float(np.std(hr[:, 0], ddof=1))
    sd_diff = float(np.std(df["Diff_T2_T1"].to_numpy(), ddof=1))
    te = sd_diff / np.sqrt(2.0)
    swc = SWC_FACTOR * sd_between
    ratio = swc / te if te > 0 else (np.inf if swc > 0 else np.nan)
    mdc95 = MDC_FACTOR * te

    metrics = {
        "SD_between": sd_between,
        "SD_diff": sd_diff,
        "TE": float(te),
        "SWC": swc,
        "Signal_Noise_Ratio": float(ratio),
        "MDC95": float(mdc95),
    }
    # Οι δείκτες αφορούν το σύνολο του σεναρίου, όχι μεμονωμένο άτομο.
    for name, value in metrics.items():
        df[name] = value
    return df[COLUMNS], metrics


def format_value(value: float) -> str:
    if np.isnan(value):
        return "Δεν ορίζεται"
    if np.isinf(value):
        return "∞"
    return f"{value:.3f}"


def main() -> None:
    st.set_page_config(page_title="Πρωτόκολλο 5", page_icon="📊", layout="wide")
    st.title("Πρωτόκολλο 5 — Καρδιακή συχνότητα ηρεμίας")
    st.caption("Δεδομένα διδάσκοντα | TE • SWC • Signal-to-Noise Ratio • MDC95")

    st.sidebar.header("Επιλογή δεδομένων")
    scenario = st.sidebar.radio("Σενάριο", list(DATA))
    st.sidebar.caption("5 εξεταζόμενοι · 3 μετρήσεις ανά σενάριο · Μονάδα: bpm")
    st.sidebar.info("TE: χρησιμοποιούνται μόνο οι διαφορές Trial 2 − Trial 1.")

    results = {name: analyse(rows) for name, rows in DATA.items()}
    df, metrics = results[scenario]
    summary = pd.DataFrame([
        {
            "Σενάριο": name,
            "TE": values[1]["TE"],
            "SWC": values[1]["SWC"],
            "Signal_Noise_Ratio": values[1]["Signal_Noise_Ratio"],
            "MDC95": values[1]["MDC95"],
        }
        for name, values in results.items()
    ])

    tab1, tab2, tab3 = st.tabs([
        "Data & Reliability Metrics", "Visualizations", "Diagnostic Alerts"
    ])

    with tab1:
        st.subheader(f"{scenario} — Δεδομένα και δείκτες")
        for col, name, label in zip(
            st.columns(4),
            ["TE", "SWC", "Signal_Noise_Ratio", "MDC95"],
            ["TE (bpm)", "SWC (bpm)", "SWC / TE", "MDC95 (bpm)"],
        ):
            col.metric(label, format_value(metrics[name]))

        st.dataframe(df.round(3), hide_index=True, width="stretch")
        st.caption(
            "Οι δείκτες SD_between, SD_diff, TE, SWC, SWC/TE και MDC95 "
            "υπολογίζονται ανά σενάριο και επαναλαμβάνονται σε κάθε γραμμή. "
            "Η στρογγυλοποίηση αφορά μόνο την εμφάνιση."
        )
        st.subheader("Σύγκριση με το Excel")
        st.dataframe(summary.round(3), hide_index=True, width="stretch")

        with st.expander("Μαθηματικοί τύποι και μέθοδος"):
            st.code(
                "Mean_HR = (HR_T1 + HR_T2 + HR_T3) / 3\n"
                "SD_between = STDEV.S(HR_T1)\n"
                "Diff_T2_T1 = HR_T2 - HR_T1\n"
                "Diff_T3_T2 = HR_T3 - HR_T2\n"
                "SD_diff = STDEV.S(Diff_T2_T1)\n"
                "TE = SD_diff / SQRT(2)\n"
                "SWC = 0.2 * SD_between\n"
                "Signal_Noise_Ratio = SWC / TE\n"
                "MDC95 = 2.77 * TE",
                language="text",
            )
            st.write(
                "Πηγή: Master Prompt, σελίδα 4 του Πρωτοκόλλου 5. "
                "Τα εύρη προσαρμόστηκαν στους 5 εξεταζομένους κάθε σεναρίου. "
                "Προστέθηκαν τα σύμβολα πολλαπλασιασμού που λείπουν στο PDF. "
                "Η τρίτη μέτρηση εμφανίζεται στον πίνακα, στον μέσο όρο και "
                "στα γραφήματα, αλλά δεν συμμετέχει στον συγκεκριμένο τύπο TE."
            )

    with tab2:
        st.subheader(f"{scenario} — Διαδραστικά γραφήματα")
        fig = go.Figure()
        for _, row in df.iterrows():
            fig.add_trace(go.Scatter(
                x=["Trial 1", "Trial 2", "Trial 3"],
                y=[row["HR_T1"], row["HR_T2"], row["HR_T3"]],
                mode="lines+markers", name=row["ID"],
            ))
        fig.update_layout(
            title="Καρδιακή συχνότητα ανά εξεταζόμενο",
            xaxis_title="Μέτρηση", yaxis_title="Καρδιακή συχνότητα (bpm)",
            legend_title="Εξεταζόμενος", hovermode="x unified", height=430,
        )
        st.plotly_chart(fig, key="hr_chart", config={"displaylogo": False})

        differences = go.Figure()
        for column, label in [
            ("Diff_T2_T1", "Trial 2 − Trial 1"),
            ("Diff_T3_T2", "Trial 3 − Trial 2"),
        ]:
            differences.add_trace(go.Bar(x=df["ID"], y=df[column], name=label))
        differences.update_layout(
            title="Διαφορές διαδοχικών μετρήσεων", barmode="group",
            xaxis_title="Εξεταζόμενος", yaxis_title="Διαφορά (bpm)", height=400,
        )
        st.plotly_chart(differences, key="diff_chart", config={"displaylogo": False})

        comparison = go.Figure()
        for name in ["TE", "SWC", "MDC95"]:
            comparison.add_trace(go.Bar(
                x=summary["Σενάριο"], y=summary[name], name=name,
                text=[f"{value:.3f}" for value in summary[name]],
                textposition="auto",
            ))
        comparison.update_layout(
            title="Σύγκριση δεικτών μεταξύ σεναρίων", barmode="group",
            xaxis_title="Σενάριο", yaxis_title="Τιμή δείκτη (bpm)", height=420,
        )
        st.plotly_chart(comparison, key="metrics_chart", config={"displaylogo": False})

    with tab3:
        st.subheader(f"{scenario} — Έλεγχος Signal-to-Noise Ratio")
        ratio = metrics["Signal_Noise_Ratio"]
        st.metric("SWC / TE", format_value(ratio))
        # Ο έλεγχος βασίζεται στον υπολογισμό, όχι στο όνομα του σεναρίου.
        if metrics["TE"] == 0:
            st.warning("TE = 0: δεν προκύπτει πεπερασμένος λόγος SWC/TE.")
        elif ratio < 1.0:
            st.warning(f"SWC / TE = {ratio:.3f} < 1: ενεργοποιείται η προειδοποίηση.")
        elif ratio == 1.0:
            st.info("SWC / TE = 1: οριακή τιμή, όχι μικρότερη από 1.")
        else:
            st.info(
                f"SWC / TE = {ratio:.3f} > 1. "
                "Δεν ενεργοποιείται η προειδοποίηση χαμηλού λόγου."
            )

        st.subheader("Εκκρεμότητα στις οδηγίες του πρωτοκόλλου")
        b_ratio = results["Σενάριο Β"][1]["Signal_Noise_Ratio"]
        st.info(
            "Ο τύπος TE της σελίδας 4 χρησιμοποιεί μόνο Trial 2 − Trial 1. "
            f"Με αυτόν τον τύπο, το Σενάριο Β δίνει SWC/TE = {b_ratio:.3f}. "
            "Το checklist της σελίδας 5 αναμένει προειδοποίηση λόγω λόγου < 1. "
            "Οι δύο οδηγίες δεν συμφωνούν για τα δοσμένα δεδομένα. "
            "Απαιτείται διευκρίνιση από τον διδάσκοντα πριν την τελική υποβολή."
        )
        st.caption(
            "Η επισήμανση της ασυμφωνίας δεν αποτελεί προειδοποίηση χαμηλού "
            "SWC/TE. Δεν αλλάζουν τα δεδομένα ή οι τύποι για να εμφανιστεί τέτοια προειδοποίηση."
        )

    st.caption("Πηγή δεδομένων: Πρωτόκολλο 5, σελίδα 3. Εκπαιδευτική εφαρμογή.")


if __name__ == "__main__":
    main()
