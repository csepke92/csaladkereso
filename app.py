import math
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Családtörténeti Archívum", page_icon="📖", layout="wide"
)

st.title("🔍 Családtörténeti Archívum Kereső")
st.markdown("---")

# Felső választósáv: Születési, Házassági, Halotti
kategoria = st.radio(
    "Válassz anyakönyvi típust a kereséshez:",
    ["Születési anyakönyv", "Házassági anyakönyv", "Halotti anyakönyv"],
    horizontal=True,
)
st.markdown("---")


@st.cache_data
def load_data(fajlnev):
  try:
    # Fejléc nélkül olvassuk be, így a sorok/oszlopok tisztán 0, 1, 2... indexűek lesznek
    df = pd.read_excel(fajlnev, header=None)
    return df.fillna("")
  except:
    return pd.DataFrame()


if kategoria == "Halotti anyakönyv":
  df = load_data("halotti.xlsx")
elif kategoria == "Születési anyakönyv":
  df = load_data("szuletesi.xlsx")
else:
  df = load_data("hazassagi.xlsx")


try:
  if df.empty:
    st.warning(
        f"A megadott kategóriához tartozó fájl (pl. {kategoria}) még nem"
        f" található a mappában vagy üres!"
    )
  else:
    # --- KERESÉSI FELÜLETEK ---
    st.markdown("### 🔎 Keresési feltételek")
    col1, col2, col3 = st.columns(3)

    with col1:
      altalanos_kereses = st.text_input(
          "🔤 Általános keresés (név, hely, bármi...):"
      )
    with col2:
      nev_szuro = st.text_input("👤 Név szűrő (pl. Gálfi Anna):")
    with col3:
      hely_szuro = st.text_input("📍 Helyszín / Vármegye szűrő:")

    with st.expander("⚙️ Bővített keresés (Apa, Anya, Házastárs szűrés)"):
      bcol1, bcol2, bcol3 = st.columns(3)
      with bcol1:
        apa_szuro = st.text_input("👨 Apa neve:")
      with bcol2:
        anya_szuro = st.text_input("👩 Anya neve:")
      with bcol3:
        hazastars_szuro = st.text_input("💍 Házastárs neve:")

    st.markdown("---")

    van_kereses = any([
        altalanos_kereses.strip(),
        nev_szuro.strip(),
        hely_szuro.strip(),
        apa_szuro.strip(),
        anya_szuro.strip(),
        hazastars_szuro.strip(),
    ])

    if not van_kereses:
      st.info(
          "💡 Írj be egy keresési feltételt fentre, hogy megjelenjenek a"
          " kártyák!"
      )
    else:
      szurt_df = df.copy()


      def smart_search(dataframe, search_str):
        if not search_str.strip():
          return dataframe
        terms = search_str.strip().lower().split()
        mask = pd.Series(True, index=dataframe.index)
        for term in terms:
          term_mask = (
              dataframe.astype(str)
              .apply(
                  lambda col: col.str.lower().str.contains(term, na=False)
              )
              .any(axis=1)
          )
          mask = mask & term_mask
        return dataframe[mask]


      def targeted_search(dataframe, search_str, col_indices):
        if not search_str.strip():
          return dataframe
        terms = search_str.strip().lower().split()
        mask = pd.Series(True, index=dataframe.index)
        for term in terms:
          sub_mask = pd.Series(False, index=dataframe.index)
          for idx in col_indices:
            if idx < len(dataframe.columns):
              col_match = (
                  dataframe[idx]
                  .astype(str)
                  .str.lower()
                  .str.contains(term, na=False)
              )
              sub_mask = sub_mask | col_match
          mask = mask & sub_mask
        return dataframe[mask]


      if altalanos_kereses:
        szurt_df = smart_search(szurt_df, altalanos_kereses)
      if nev_szuro:
        szurt_df = smart_search(szurt_df, nev_szuro)
      if hely_szuro:
        szurt_df = smart_search(szurt_df, hely_szuro)

      # Apa: X, W, Z, AA, AB -> Indexek: 23, 22, 25, 26, 27
      if apa_szuro:
        szurt_df = targeted_search(szurt_df, apa_szuro, [23, 22, 25, 26, 27])
      # Anya: AC, AD, AE, AF, AG -> Indexek: 28, 29, 30, 31, 32
      if anya_szuro:
        szurt_df = targeted_search(szurt_df, anya_szuro, [28, 29, 30, 31, 32])
      # Házastárs: AH, AI -> Indexek: 33, 34
      if hazastars_szuro:
        szurt_df = targeted_search(szurt_df, hazastars_szuro, [33, 34])

      talalatok_szama = len(szurt_df)
      st.markdown(f"### Találatok száma: **{talalatok_szama}** bejegyzés")

      if talalatok_szama > 0:
        col_lap1, col_lap2 = st.columns([1, 3])
        with col_lap1:
          megjelenites_szama = st.selectbox(
              "Kártya oldalanként:", [10, 25, 50, 100, "Összes"]
          )

        if megjelenites_szama == "Összes":
          oldal_meret = talalatok_szama
        else:
          oldal_meret = int(megjelenites_szama)

        osszes_oldal = max(1, math.ceil(talalatok_szama / oldal_meret))

        akt_oldal = 1
        if osszes_oldal > 1:
          with col_lap2:
            akt_oldal = st.number_input(
                f"Ugrás oldalra (Összesen {osszes_oldal} oldal):",
                min_value=1,
                max_value=osszes_oldal,
                value=1,
                step=1,
            )

        kezdö_idx = (int(akt_oldal) - 1) * oldal_meret
        veg_idx = min(kezdö_idx + oldal_meret, talalatok_szama)
        lapozott_df = szurt_df.iloc[kezdö_idx:veg_idx]

        st.markdown("---")


        def get_val(row, idx):
          if idx < len(row):
            val = row.iloc[idx]
            if isinstance(val, (int, float)):
              if pd.isna(val):
                return ""
              return str(int(val)) if val == int(val) else str(val)
            val_str = str(val).strip()
            if val_str.endswith(".0"):
              val_str = val_str[:-2]
            return val_str
          return ""


        # Fix rovatnevek a bal oldali adatokhoz (A, B, C, D, E, F azaz 0, 1, 2, 3, 4, 5 indexek)
        rovatnevek = [
            "Vármegye",
            "Anyakönyvezés helye",
            "Felekezet",
            "Kötet",
            "Oldalszám",
            "Sorszám",
        ]

        if kategoria == "Halotti anyakönyv":
          for idx, row in lapozott_df.iterrows():
            # Cím: 0. oszlop (Vármegye) és 1. oszlop (Anyakönyv helye)
            varmegye = get_val(row, 0).title()
            helyszin = get_val(row, 1).title()

            cim_reszek = [r for r in [varmegye, helyszin] if r != ""]
            cim_szoveg = (
                " – ".join(cim_reszek)
                if cim_reszek
                else f"Bejegyzés #{idx+1}"
            )

            with st.expander(f"📄 {cim_szoveg}", expanded=True):
              bcol1, bcol2, bcol3 = st.columns([1.2, 2, 1])

              # Bal oldal: A, B, C, D, E, F oszlopok fixen, nagy kezdőbetűkkel
              with bcol1:
                st.markdown("#### **BEJEGYZÉSEK ADATAI**")
                for i in range(6):
                  val = get_val(row, i)
                  nev = rovatnevek[i] if i < len(rovatnevek) else f"Oszlop {i+1}"
                  if val != "" and not val.isdigit():
                    val = val.title()
                  st.markdown(
                      f"**{nev}:** <span style='color: #002b36;'>"
                      f"{val if val != '' else '-'}</span>",
                      unsafe_allow_html=True,
                  )

              # Közép rész: Halott adatai
              with bcol2:
                st.markdown("#### **ELHUNYT ADATAI**")

                g_val = get_val(row, 6)
                if g_val != "":
                  st.markdown(f"**Bejegyzés dátuma:** {g_val}")

                nev_reszek = [get_val(row, i) for i in [12, 13, 14, 15]]
                nev_szűrt = [r.title() for r in nev_reszek if r != ""]
                if nev_szűrt:
                  teljes_nev = " ".join(nev_szűrt)
                  st.markdown(
                      f"**Név:** <span style='font-size: 1.15em; font-weight:"
                      f" bold; text-decoration: underline; color:"
                      f"#859900;'>{teljes_nev}</span>",
                      unsafe_allow_html=True,
                  )

                l_val = get_val(row, 11).title()
                if l_val != "":
                  st.markdown(f"**Családi állapot:** {l_val}")

                k_val = get_val(row, 10).title()
                if k_val != "":
                  st.markdown(f"**Származási hely:** {k_val}")

                s_val = get_val(row, 18)
                t_val = get_val(row, 19)
                u_val = get_val(row, 20)
                v_val = get_val(row, 21)

                kora_darabok = []
                if s_val != "":
                  kora_darabok.append(f"{s_val} éves")
                if t_val != "":
                  kora_darabok.append(f"{t_val} hónapos")
                if u_val != "":
                  kora_darabok.append(f"{u_val} hetes")
                if v_val != "":
                  kora_darabok.append(f"{v_val} napos")

                if kora_darabok:
                  st.markdown(f"**Kora:** {' '.join(kora_darabok)}")

                w_val = get_val(row, 22)
                if w_val != "":
                  st.markdown(f"**Születési ideje:** {w_val}")

                apa_reszek = [
                    get_val(row, i).title() for i in [23, 22, 25, 26, 27]
                ]
                apa_szűrt = [r for r in apa_reszek if r != ""]
                if apa_szűrt:
                  st.markdown(f"**Apa:** {' '.join(apa_szűrt)}")

                anya_reszek = [
                    get_val(row, i).title() for i in [28, 29, 30, 31, 32]
                ]
                anya_szűrt = [r for r in anya_reszek if r != ""]
                if anya_szűrt:
                  st.markdown(f"**Anya:** {' '.join(anya_szűrt)}")

                hazastars_reszek = [get_val(row, i).title() for i in [33, 34]]
                haz_szűrt = [r for r in hazastars_reszek if r != ""]
                if haz_szűrt:
                  st.markdown(f"**Házastárs:** {' '.join(haz_szűrt)}")

              # Jobb oldal: Megjegyzés
              with bcol3:
                st.markdown("#### **Megjegyzés**")
                ap_ertek = get_val(row, 41)
                if ap_ertek != "":
                  st.markdown(
                      f"<span style='color: #002b36;'>{ap_ertek}</span>",
                      unsafe_allow_html=True,
                  )
                else:
                  st.markdown(
                      "<span style='color: gray; font-style: italic;'>Nincs"
                      " megjegyzés</span>",
                      unsafe_allow_html=True,
                  )

        elif kategoria == "Születési anyakönyv":
          st.info(
              "Itt fog megjelenni a születési anyakönyvek speciális"
              " elrendezése."
          )
        else:
          st.info(
              "Itt fog megjelenni a házassági anyakönyvek speciális"
              " elrendezése."
          )
      else:
        st.warning("Nincs találat a megadott keresési feltételekkel.")

except Exception as e:
  st.error(f"Hiba történt a futás során: {e}")