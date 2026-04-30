import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch, Polygon
from datetime import datetime
import warnings
from io import BytesIO

warnings.filterwarnings("ignore")

# ==================================================
# SAYFA AYARLARI
# ==================================================
st.set_page_config(page_title="Blok Yerleşim Planı", layout="wide")

st.title("🏗️ BLOK YERLEŞİM PLANI")
st.markdown("---")

# ==================================================
# SABİTLER (KODUN ORİJİNAL HALİYLE AYNI)
# ==================================================

ISKELE = 3
DARBOGAZ_PCT = 80
STEP = 0.5
A31_SON_GUN = pd.Timestamp("2026-08-15")
DIKINE_ZORUNLU_BOY = 27

ISTIF_X_SOL = 0.0
ISTIF_Y_ALT = 0.0
ISTIF_Y_UST = 35.52
ISTIF_X_UST = 100.18
ISTIF_X_ALT = 72.4
ISTIF_EGIM = (ISTIF_X_UST - ISTIF_X_ALT) / ISTIF_Y_UST

DUZ_KIZAK_TOPLAM_U = 251.0
DUZ_KIZAK_TOPLAM_G = 59.56
DUZ_KIZAK_BLOK_U = 101.0
DUZ_KIZAK_MUGEM_U = 150.0
DUZ_KIZAK_MUGEM_X_BASLANGIC = 101.0

A6_TAM_U = 230.0
A6_G = 40.3
A6_BLOK_U = 111.0
A6_NB76_U = A6_TAM_U - A6_BLOK_U
A6_EYUL = datetime(2026, 9, 1)

TRANSFER_RULES = {
    "A3 Atölyesi": {"size": (24, 12), "rotate": True},
    "A4 Atölyesi": {"size": (24, 12), "rotate": True},
    "A3 Atölyesi(Jig)": None,
    "A6 Atölyesi": {"size": (12, 27), "rotate": False},
    "A31 Atölyesi": {"size": (12, 27), "rotate": False},
    "Düz Kızak": {"size": (12, 27), "rotate": False},
}

SAHALAR = [
    {"ad": "A3 Atölyesi", "oncelik": 1,
     "kisit": lambda b, t: b["Tonaj"] <= 55,
     "alan": lambda t: (74.0, 32.0)},
    {"ad": "A3 Atölyesi(Jig)", "oncelik": 1,
     "kisit": lambda b, t: (b["Tonaj"] <= 55 and b["En"] <= 12 and b["Boy"] <= 12),
     "alan": lambda t: (52.0, 32.0)},
    {"ad": "A4 Atölyesi", "oncelik": 1,
     "kisit": lambda b, t: b["Tonaj"] <= 55,
     "alan": lambda t: (53.0, 32.0)},
    {"ad": "A6 Atölyesi", "oncelik": 1,
     "kisit": lambda b, t: b["Tonaj"] <= 240,
     "alan": lambda t: (A6_TAM_U, A6_G) if t >= A6_EYUL else (A6_BLOK_U, A6_G)},
    {"ad": "A31 Atölyesi", "oncelik": 1,
     "kisit": lambda b, t: (b["Tonaj"] <= 240 and b["Erection_Bas"] <= A31_SON_GUN),
     "alan": lambda t: (99.35, 35.98) if t <= A31_SON_GUN else (0.0, 0.0)},
    {"ad": "A29 Açık Saha", "oncelik": 2,
     "kisit": lambda b, t: b["Tonaj"] <= 55,
     "alan": lambda t: (120.0, 21.0)},
    {"ad": "Düz Kızak", "oncelik": 2,
     "kisit": lambda b, t: b["Tonaj"] <= 400,
     "alan": lambda t: (DUZ_KIZAK_TOPLAM_U, DUZ_KIZAK_TOPLAM_G)},
    {"ad": "Açık Saha(İstif)", "oncelik": 3,
     "kisit": lambda b, t: b["Tonaj"] <= 400,
     "alan": lambda t: (ISTIF_X_UST, ISTIF_Y_UST)},
]
SAHALAR = sorted(SAHALAR, key=lambda x: x["oncelik"])

# ==================================================
# YARDIMCI FONKSİYONLAR
# ==================================================

def snap(v):
    return round(round(v / STEP) * STEP, 10)

def rect_overlaps(ax1, ay1, ax2, ay2, bx1, by1, bx2, by2):
    if ax2 <= bx1 + 0.001: return False
    if ax1 >= bx2 - 0.001: return False
    if ay2 <= by1 + 0.001: return False
    if ay1 >= by2 - 0.001: return False
    return True

def blok_rotasyon_modu(blok):
    en = float(blok["En"])
    boy = float(blok["Boy"])
    if abs(en - DIKINE_ZORUNLU_BOY) < 0.1 or abs(boy - DIKINE_ZORUNLU_BOY) < 0.1:
        return "dikine"
    return "serbest"

def istif_icinde_mi(x, y, w, h):
    koseler = [(x, y), (x+w, y), (x, y+h), (x+w, y+h)]
    for cx, cy in koseler:
        if cx < 0: return False
        if cy < 0: return False
        if cy > ISTIF_Y_UST: return False
        x_max = ISTIF_X_ALT + ISTIF_EGIM * cy
        if cx > x_max + 0.001: return False
    return True

def mugem_icinde_mi(x, y, w, h):
    if x < DUZ_KIZAK_MUGEM_X_BASLANGIC - 0.001: return False
    if y < -0.001: return False
    if x + w > DUZ_KIZAK_TOPLAM_U + 0.001: return False
    if y + h > DUZ_KIZAK_TOPLAM_G + 0.001: return False
    return True

def mugem_boyut(row):
    return float(row["Boy"]), float(row["En"])

# ==================================================
# SAHA MANAGER SINIFI
# ==================================================

class SahaManager:
    def __init__(self, ad):
        self.ad = ad
        self.bloklar = []
        self.mugem_isgal = []

    def aktif_bloklar(self, tarih):
        t = pd.Timestamp(tarih)
        return [b for b in self.bloklar if pd.Timestamp(b["bas"]) <= t < pd.Timestamp(b["erc"])]

    def mugem_isgal_alanlari(self, tarih):
        t = pd.Timestamp(tarih)
        return [b for b in self.mugem_isgal if pd.Timestamp(b["bas"]) <= t]

    def transfer_rect(self):
        rule = TRANSFER_RULES.get(self.ad)
        if rule is None:
            return None
        tw, th = rule["size"]
        if rule.get("rotate", False):
            tw, th = th, tw
        return (0.0, 0.0, float(tw), float(th))

    def can_place(self, x, y, w, h, saha_u, saha_g, tarih, blok_erc=None):
        x, y, w, h = snap(x), snap(y), snap(w), snap(h)
        tarih_ts = pd.Timestamp(tarih)
        if x < 0 or y < 0:
            return False
        if self.ad == "Açık Saha(İstif)":
            if not istif_icinde_mi(x, y, w, h):
                return False
        else:
            if x + w > saha_u + 0.01 or y + h > saha_g + 0.01:
                return False
        tr = self.transfer_rect()
        if tr is not None:
            if rect_overlaps(x, y, x+w, y+h, tr[0], tr[1], tr[2], tr[3]):
                return False
        if blok_erc is not None:
            blok_erc_ts = pd.Timestamp(blok_erc)
            kontrol_bloklari = [b for b in self.bloklar if pd.Timestamp(b["bas"]) < blok_erc_ts and pd.Timestamp(b["erc"]) > tarih_ts]
        else:
            kontrol_bloklari = [b for b in self.bloklar if pd.Timestamp(b["bas"]) <= tarih_ts < pd.Timestamp(b["erc"])]
        for b in kontrol_bloklari:
            if rect_overlaps(x, y, x+w, y+h, b["x"], b["y"], b["x"]+b["w"], b["y"]+b["h"]):
                return False
        if self.ad == "Düz Kızak":
            for b in self.mugem_isgal:
                b_bas_ts = pd.Timestamp(b["bas"])
                if blok_erc is not None:
                    if b_bas_ts >= pd.Timestamp(blok_erc):
                        continue
                else:
                    if b_bas_ts > tarih_ts:
                        continue
                if rect_overlaps(x, y, x+w, y+h, b["x"], b["y"], b["x"]+b["w"], b["y"]+b["h"]):
                    return False
        return True

    def _aday_xs(self, tarih):
        tr = self.transfer_rect()
        xs = {0.0}
        if tr is not None:
            xs.add(snap(tr[2]))
        for b in self.bloklar:
            xs.add(snap(b["x"] + b["w"]))
            if b["x"] > 0:
                xs.add(snap(b["x"]))
        if self.ad == "Düz Kızak":
            for b in self.mugem_isgal:
                xs.add(snap(b["x"] + b["w"]))
                if b["x"] > 0:
                    xs.add(snap(b["x"]))
            xs.add(snap(DUZ_KIZAK_MUGEM_X_BASLANGIC))
        return sorted(xs)

    def _aday_ys(self, tarih):
        tr = self.transfer_rect()
        ys = {0.0}
        if tr is not None:
            ys.add(snap(tr[3]))
        for b in self.bloklar:
            ys.add(snap(b["y"] + b["h"]))
            if b["y"] > 0:
                ys.add(snap(b["y"]))
        if self.ad == "Düz Kızak":
            for b in self.mugem_isgal:
                ys.add(snap(b["y"] + b["h"]))
                if b["y"] > 0:
                    ys.add(snap(b["y"]))
        return sorted(ys)

    def find_spot_single(self, w, h, saha_u, saha_g, tarih, blok_erc=None):
        w, h = snap(w), snap(h)
        saha_u, saha_g = snap(saha_u), snap(saha_g)
        if w > saha_u or h > saha_g:
            return None
        aday_ys = self._aday_ys(tarih)
        aday_xs = self._aday_xs(tarih)
        for y in aday_ys:
            y = snap(y)
            if y < 0 or y + h > saha_g + 0.01:
                continue
            for x in aday_xs:
                x = snap(x)
                if x < 0:
                    continue
                if self.ad != "Açık Saha(İstif)":
                    if x + w > saha_u + 0.01:
                        continue
                if self.can_place(x, y, w, h, saha_u, saha_g, tarih, blok_erc):
                    return (x, y)
        return None

    def find_spot(self, w, h, saha_u, saha_g, tarih, mod="serbest", blok_erc=None):
        if mod == "dikine":
            if h >= w:
                pos = self.find_spot_single(w, h, saha_u, saha_g, tarih, blok_erc)
                if pos:
                    return pos[0], pos[1], False
            else:
                pos = self.find_spot_single(h, w, saha_u, saha_g, tarih, blok_erc)
                if pos:
                    return pos[0], pos[1], True
            return None
        pos_n = self.find_spot_single(w, h, saha_u, saha_g, tarih, blok_erc)
        pos_r = None
        if abs(w - h) > 0.01:
            pos_r = self.find_spot_single(h, w, saha_u, saha_g, tarih, blok_erc)
        if pos_n is None and pos_r is None:
            return None
        if pos_n is None:
            return pos_r[0], pos_r[1], True
        if pos_r is None:
            return pos_n[0], pos_n[1], False
        if (pos_r[1], pos_r[0]) < (pos_n[1], pos_n[0]):
            return pos_r[0], pos_r[1], True
        return pos_n[0], pos_n[1], False

    def add_block(self, idx, x, y, bas, erc, w_placed, h_placed):
        self.bloklar.append({
            "idx": idx, "x": snap(x), "y": snap(y),
            "w": snap(w_placed), "h": snap(h_placed),
            "bas": bas, "erc": erc,
        })

    def add_mugem_isgal(self, idx, x, y, bas, w, h):
        self.mugem_isgal.append({
            "idx": idx, "x": snap(x), "y": snap(y),
            "w": snap(w), "h": snap(h), "bas": bas,
        })

    def remove_block(self, idx):
        self.bloklar = [b for b in self.bloklar if b["idx"] != idx]
        self.mugem_isgal = [b for b in self.mugem_isgal if b["idx"] != idx]

    def cakisma_kontrol(self, tarih):
        aktif = self.aktif_bloklar(tarih)
        hatalar = []
        for i in range(len(aktif)):
            for j in range(i+1, len(aktif)):
                a, b = aktif[i], aktif[j]
                if rect_overlaps(a["x"], a["y"], a["x"]+a["w"], a["y"]+a["h"],
                                 b["x"], b["y"], b["x"]+b["w"], b["y"]+b["h"]):
                    hatalar.append((a["idx"], b["idx"]))
        if self.ad == "Düz Kızak":
            mug_aktif = self.mugem_isgal_alanlari(tarih)
            for a in aktif:
                for m in mug_aktif:
                    if rect_overlaps(a["x"], a["y"], a["x"]+a["w"], a["y"]+a["h"],
                                     m["x"], m["y"], m["x"]+m["w"], m["y"]+m["h"]):
                        hatalar.append((a["idx"], m["idx"]))
        return hatalar

    def sinir_disi_kontrol(self, saha_u, saha_g, tarih):
        hatalar = []
        for b in self.aktif_bloklar(tarih):
            if self.ad == "Açık Saha(İstif)":
                if not istif_icinde_mi(b["x"], b["y"], b["w"], b["h"]):
                    hatalar.append(b["idx"])
            else:
                if (b["x"] < 0 or b["y"] < 0 or
                    b["x"] + b["w"] > saha_u + 0.01 or
                    b["y"] + b["h"] > saha_g + 0.01):
                    hatalar.append(b["idx"])
        return hatalar


class MugemManager:
    def __init__(self):
        self.bloklar = []

    def aktif_bloklar(self, tarih):
        return [b for b in self.bloklar if b["bas"] <= tarih]

    def can_place(self, x, y, w, h, tarih):
        if not mugem_icinde_mi(x, y, w, h):
            return False
        for b in self.aktif_bloklar(tarih):
            if rect_overlaps(x, y, x+w, y+h, b["x"], b["y"], b["x"]+b["w"], b["y"]+b["h"]):
                return False
        return True

    def add_block(self, idx, x, y, bas, w_placed, h_placed):
        self.bloklar.append({
            "idx": idx, "x": snap(x), "y": snap(y),
            "w": snap(w_placed), "h": snap(h_placed), "bas": bas,
        })

    def remove_block(self, idx):
        self.bloklar = [b for b in self.bloklar if b["idx"] != idx]


# ==================================================
# YERLEŞTİRME FONKSİYONLARI
# ==================================================

def reset_df(target_df):
    target_df["Koord_X"] = np.nan
    target_df["Koord_Y"] = np.nan
    target_df["Normal_X"] = np.nan
    target_df["Normal_Y"] = np.nan
    target_df["Istif_X"] = np.nan
    target_df["Istif_Y"] = np.nan
    target_df["Mugem_Yerlesti"] = False
    target_df["Istife_Tasindi"] = False
    target_df["Donuk"] = False
    target_df["Sigmiyor"] = False
    target_df["Otelendi"] = False
    if "Orijinal_Bas" in target_df.columns:
        target_df["Baslangic"] = target_df["Orijinal_Bas"].copy()
        target_df["Bitis"] = target_df["Orijinal_Bitis"].copy()

    for i, row in target_df.iterrows():
        saha_adi = row.get("Atanacak_Saha")
        kx, ky = row.get("Kordinat_X"), row.get("Kordinat_Y")
        if pd.isna(saha_adi):
            continue
        if not isinstance(saha_adi, str):
            continue
        saha_adi = saha_adi.strip()
        saha_obj = next((s for s in SAHALAR if s["ad"] == saha_adi), None)
        if saha_obj is None:
            continue
        t = pd.Timestamp(row["Baslangic"]).to_pydatetime() if pd.notna(row["Baslangic"]) else datetime.now()
        if not saha_obj["kisit"](row, t):
            continue
        target_df.at[i, "Atanan_Saha"] = saha_adi
        if pd.notna(kx) and pd.notna(ky):
            try:
                x, y = float(kx), float(ky)
                u, g = saha_obj["alan"](t)
                gw = row["En"] + ISKELE * 2
                gh = row["Boy"] + ISKELE * 2
                if x >= 0 and y >= 0:
                    if saha_adi == "Düz Kızak":
                        if x + gw <= DUZ_KIZAK_BLOK_U and y + gh <= g:
                            target_df.at[i, "Koord_X"] = x
                            target_df.at[i, "Koord_Y"] = y
                    else:
                        if x + gw <= u and y + gh <= g:
                            target_df.at[i, "Koord_X"] = x
                            target_df.at[i, "Koord_Y"] = y
            except:
                pass

    managers = {s["ad"]: SahaManager(s["ad"]) for s in SAHALAR}
    managers["_MUGEM_"] = MugemManager()
    mgr_duz = managers["Düz Kızak"]
    for i, row in target_df.iterrows():
        mx, my = row.get("Mugem_X"), row.get("Mugem_Y")
        if pd.isna(mx) or pd.isna(my):
            continue
        if pd.isna(row.get("Erection_Bas")):
            continue
        bw, bh = mugem_boyut(row)
        erc_ts = pd.Timestamp(row["Erection_Bas"])
        mgr_duz.add_mugem_isgal(i, float(mx), float(my), erc_ts, bw, bh)
    return managers


def normal_sahaya_yerleştir(idx, tarih_ts, target_df, managers):
    blok = target_df.loc[idx]
    t = tarih_ts.to_pydatetime()
    blok_erc = blok["Erection_Bas"]
    secili_saha = blok["Atanan_Saha"] if pd.notna(blok["Atanan_Saha"]) else None
    if secili_saha is None:
        saha_listesi = [s for s in SAHALAR if s["ad"] != "Açık Saha(İstif)"]
    else:
        saha_listesi = [s for s in SAHALAR if s["ad"] == secili_saha and s["ad"] != "Açık Saha(İstif)"]
    mod = blok_rotasyon_modu(blok)
    gw, gh = snap(float(blok["Gercek_En"])), snap(float(blok["Gercek_Boy"]))
    for saha in saha_listesi:
        if not saha["kisit"](blok, t):
            continue
        u, g = saha["alan"](t)
        u, g = snap(float(u)), snap(float(g))
        if u <= 0 or g <= 0:
            continue
        if min(gw, gh) > min(u, g) or max(gw, gh) > max(u, g):
            continue
        mgr = managers[saha["ad"]]
        if pd.notna(blok["Koord_X"]) and pd.notna(blok["Koord_Y"]):
            x, y = snap(float(blok["Koord_X"])), snap(float(blok["Koord_Y"]))
            if x >= 0 and y >= 0 and x+gw <= u+0.01 and y+gh <= g+0.01:
                if mgr.can_place(x, y, gw, gh, u, g, t, blok_erc):
                    target_df.at[idx, "Atanan_Saha"] = saha["ad"]
                    target_df.at[idx, "Koord_X"] = x
                    target_df.at[idx, "Koord_Y"] = y
                    target_df.at[idx, "Normal_X"] = x
                    target_df.at[idx, "Normal_Y"] = y
                    target_df.at[idx, "Donuk"] = False
                    target_df.at[idx, "Sigmiyor"] = False
                    mgr.add_block(idx, x, y, blok["Baslangic"], blok["Erection_Bas"], gw, gh)
                    return True
        sonuc = mgr.find_spot(gw, gh, u, g, t, mod, blok_erc)
        if sonuc:
            x, y, rotated = sonuc
            w_placed = gh if rotated else gw
            h_placed = gw if rotated else gh
            if x >= 0 and y >= 0 and x+w_placed <= u+0.01 and y+h_placed <= g+0.01:
                if mgr.can_place(x, y, w_placed, h_placed, u, g, t, blok_erc):
                    target_df.at[idx, "Atanan_Saha"] = saha["ad"]
                    target_df.at[idx, "Koord_X"] = x
                    target_df.at[idx, "Koord_Y"] = y
                    target_df.at[idx, "Normal_X"] = x
                    target_df.at[idx, "Normal_Y"] = y
                    target_df.at[idx, "Donuk"] = rotated
                    target_df.at[idx, "Sigmiyor"] = False
                    mgr.add_block(idx, x, y, blok["Baslangic"], blok["Erection_Bas"], w_placed, h_placed)
                    return True
    return False


def istif_alanina_tasi(idx, target_df, managers):
    blok = target_df.loc[idx]
    bitis_ts = pd.Timestamp(blok["Bitis"])
    t = bitis_ts.to_pydatetime()
    if pd.isna(blok["Bitis"]) or pd.isna(blok["Erection_Bas"]):
        return False
    u, g = snap(ISTIF_X_UST), snap(ISTIF_Y_UST)
    mgr_istif = managers["Açık Saha(İstif)"]
    mod = blok_rotasyon_modu(blok)
    gw, gh = snap(float(blok["Gercek_En"])), snap(float(blok["Gercek_Boy"]))
    sonuc = mgr_istif.find_spot(gw, gh, u, g, t, mod)
    if not sonuc:
        return False
    x, y, rotated = sonuc
    w_placed = gh if rotated else gw
    h_placed = gw if rotated else gh
    if not istif_icinde_mi(x, y, w_placed, h_placed):
        return False
    eski_saha = blok["Atanan_Saha"]
    if pd.notna(eski_saha) and eski_saha in managers:
        managers[eski_saha].remove_block(idx)
    target_df.at[idx, "Istif_X"] = x
    target_df.at[idx, "Istif_Y"] = y
    target_df.at[idx, "Istife_Tasindi"] = True
    target_df.at[idx, "Donuk"] = rotated
    mgr_istif.add_block(idx, x, y, blok["Bitis"], blok["Erection_Bas"], w_placed, h_placed)
    return True


def mugem_erection_yerlestir(idx, target_df, managers):
    blok = target_df.loc[idx]
    mx, my = blok.get("Mugem_X"), blok.get("Mugem_Y")
    if pd.isna(mx) or pd.isna(my):
        return False
    bw, bh = mugem_boyut(blok)
    if not mugem_icinde_mi(float(mx), float(my), bw, bh):
        return False
    mgr = managers["_MUGEM_"]
    erc_ts = pd.Timestamp(blok["Erection_Bas"])
    if not mgr.can_place(float(mx), float(my), bw, bh, erc_ts.to_pydatetime()):
        return False
    eski_saha = blok["Atanan_Saha"]
    if pd.notna(eski_saha) and eski_saha in managers:
        managers[eski_saha].remove_block(idx)
    if blok["Istife_Tasindi"]:
        managers["Açık Saha(İstif)"].remove_block(idx)
    target_df.at[idx, "Mugem_Yerlesti"] = True
    mgr.add_block(idx, float(mx), float(my), erc_ts, bw, bh)
    return True


def yer_ac_ve_yerleştir(idx, tarih_ts, target_df, managers):
    istif_adaylari = target_df[
        (target_df["Bitis"] <= tarih_ts) &
        (target_df["Erection_Bas"] > tarih_ts) &
        (target_df["Koord_X"].notna()) &
        (target_df["Istife_Tasindi"] == False) &
        (target_df["Atanan_Saha"] != "Açık Saha(İstif)")
    ].copy()
    blok = target_df.loc[idx]
    secili_saha = blok["Atanan_Saha"] if pd.notna(blok["Atanan_Saha"]) else None
    if secili_saha is not None:
        ayni = istif_adaylari[istif_adaylari["Atanan_Saha"] == secili_saha]
        diger = istif_adaylari[istif_adaylari["Atanan_Saha"] != secili_saha]
        istif_adaylari = pd.concat([ayni, diger])
    for aday_idx, _ in istif_adaylari.iterrows():
        if istif_alanina_tasi(aday_idx, target_df, managers):
            if normal_sahaya_yerleştir(idx, tarih_ts, target_df, managers):
                return True
    return False


def guncelle_tarih_ve_manager(idx, tarih_ts, target_df, managers):
    orijinal_bas = pd.Timestamp(target_df.at[idx, "Orijinal_Bas"])
    orijinal_bitis = pd.Timestamp(target_df.at[idx, "Orijinal_Bitis"])
    sure = orijinal_bitis - orijinal_bas
    erc_offset = pd.Timestamp(target_df.at[idx, "Erection_Bas"]) - orijinal_bitis
    yeni_bas = tarih_ts
    yeni_bitis = tarih_ts + sure
    yeni_erc = yeni_bitis + erc_offset
    if yeni_erc <= yeni_bitis:
        yeni_erc = yeni_bitis + pd.DateOffset(days=1)
    saha_adi = target_df.at[idx, "Atanan_Saha"]
    managers[saha_adi].remove_block(idx)
    x = target_df.at[idx, "Koord_X"]
    y = target_df.at[idx, "Koord_Y"]
    rotated = target_df.at[idx, "Donuk"]
    gw = snap(float(target_df.at[idx, "Gercek_En"]))
    gh = snap(float(target_df.at[idx, "Gercek_Boy"]))
    w_placed = gh if rotated else gw
    h_placed = gw if rotated else gh
    managers[saha_adi].add_block(idx, x, y, yeni_bas, yeni_erc, w_placed, h_placed)
    target_df.at[idx, "Baslangic"] = yeni_bas
    target_df.at[idx, "Bitis"] = yeni_bitis
    target_df.at[idx, "Erection_Bas"] = yeni_erc
    target_df.at[idx, "Sigmiyor"] = False
    target_df.at[idx, "Otelendi"] = True


# ==================================================
# YERLEŞİM HESAPLA
# ==================================================

def yerlesim_hesapla(hedef_tarih, target_df):
    managers = reset_df(target_df)
    hedef_ts = pd.Timestamp(hedef_tarih)
    bekleyen = {}
    tum_tarihler = sorted(set(
        list(target_df.loc[target_df["Baslangic"] <= hedef_ts, "Baslangic"].dropna().unique()) +
        list(target_df.loc[(target_df["Bitis"] <= hedef_ts) & (target_df["Erection_Bas"] > target_df["Bitis"]), "Bitis"].dropna().unique()) +
        list(target_df.loc[target_df["Erection_Bas"] <= hedef_ts, "Erection_Bas"].dropna().unique())
    ))
    for tarih in tum_tarihler:
        tarih_ts = pd.Timestamp(tarih)
        erection_gelenler = target_df.index[
            (target_df["Erection_Bas"] == tarih_ts) &
            (target_df["Mugem_Yerlesti"] == False) &
            (target_df["Mugem_X"].notna()) &
            (target_df["Mugem_Y"].notna())
        ]
        for idx in erection_gelenler:
            mugem_erection_yerlestir(idx, target_df, managers)
        bugun_biten = target_df.index[
            (target_df["Bitis"] == tarih_ts) &
            (target_df["Erection_Bas"] > tarih_ts) &
            (target_df["Koord_X"].notna()) &
            (target_df["Istife_Tasindi"] == False)
        ]
        for idx in bugun_biten:
            blok = target_df.loc[idx]
            mevcut_saha = blok["Atanan_Saha"]
            if pd.isna(mevcut_saha) or mevcut_saha == "Açık Saha(İstif)":
                continue
            saha_obj = next((s for s in SAHALAR if s["ad"] == mevcut_saha), None)
            if saha_obj is None:
                continue
            t = tarih_ts.to_pydatetime()
            u, g = saha_obj["alan"](t)
            kullanilan = sum(float(r["Gercek_Alan"]) for _, r in target_df[
                (target_df["Atanan_Saha"] == mevcut_saha) &
                (target_df["Baslangic"] <= tarih_ts) &
                (target_df["Erection_Bas"] > tarih_ts) &
                (target_df["Koord_X"].notna()) &
                (target_df["Istife_Tasindi"] == False)
            ].iterrows())
            if u * g > 0 and (kullanilan / (u * g) * 100) >= DARBOGAZ_PCT:
                istif_alanina_tasi(idx, target_df, managers)
        for idx in list(bekleyen.keys()):
            if not target_df.at[idx, "Sigmiyor"]:
                del bekleyen[idx]
                continue
            yerlesme = normal_sahaya_yerleştir(idx, tarih_ts, target_df, managers)
            if not yerlesme:
                yerlesme = yer_ac_ve_yerleştir(idx, tarih_ts, target_df, managers)
            if yerlesme:
                guncelle_tarih_ve_manager(idx, tarih_ts, target_df, managers)
                del bekleyen[idx]
        for idx in target_df.index[target_df["Baslangic"] == tarih]:
            blok = target_df.loc[idx]
            if pd.notna(blok["Atanan_Saha"]) and pd.notna(blok["Koord_X"]) and pd.notna(blok["Koord_Y"]):
                continue
            if idx in bekleyen:
                continue
            yerlesme = normal_sahaya_yerleştir(idx, tarih_ts, target_df, managers)
            if not yerlesme:
                yerlesme = yer_ac_ve_yerleştir(idx, tarih_ts, target_df, managers)
            if not yerlesme:
                bekleyen[idx] = tarih_ts
                target_df.at[idx, "Sigmiyor"] = True
    return managers


def toplam_kapasite(tarih):
    t = pd.Timestamp(tarih).to_pydatetime()
    kap = 0
    for s in SAHALAR:
        u, g = s["alan"](t)
        if s["ad"] == "Açık Saha(İstif)":
            kap += ((ISTIF_X_UST + ISTIF_X_ALT) / 2 * ISTIF_Y_UST)
            continue
        if s["ad"] == "Düz Kızak":
            kap += DUZ_KIZAK_BLOK_U * DUZ_KIZAK_TOPLAM_G
            continue
        tr = TRANSFER_RULES.get(s["ad"])
        tr_px = 0
        if tr:
            tw, th = tr["size"]
            if tr.get("rotate", False):
                tw, th = th, tw
            tr_px = tw
        kap += max((u - tr_px) * g, 0)
    return kap


def saha_kullanim_alani(saha, target_df, tarih_ts):
    if saha["ad"] == "Açık Saha(İstif)":
        aktif = target_df[
            (target_df["Istif_X"].notna()) &
            (target_df["Bitis"] < tarih_ts) &
            (target_df["Erection_Bas"] > tarih_ts) &
            (target_df["Mugem_Yerlesti"] == False)
        ].copy()
    else:
        aktif = target_df[
            (target_df["Atanan_Saha"] == saha["ad"]) &
            (target_df["Baslangic"] <= tarih_ts) &
            (target_df["Erection_Bas"] > tarih_ts) &
            (target_df["Koord_X"].notna()) &
            (target_df["Istife_Tasindi"] == False)
        ].copy()
    blok_alani = sum(float(b["Gercek_Alan"]) for _, b in aktif.iterrows())
    tr_alan = 0.0
    tr = TRANSFER_RULES.get(saha["ad"])
    if tr:
        tw, th = tr["size"]
        if tr.get("rotate", False):
            tw, th = th, tw
        tr_alan = float(tw) * float(th)
    return aktif, blok_alani + tr_alan


def aktif_blok_say(target_df, t):
    normal = target_df[
        (target_df["Baslangic"] <= t) &
        (target_df["Erection_Bas"] > t) &
        (target_df["Koord_X"].notna()) &
        (target_df["Istife_Tasindi"] == False)
    ]
    istif = target_df[
        (target_df["Istif_X"].notna()) &
        (target_df["Bitis"] < t) &
        (target_df["Erection_Bas"] > t) &
        (target_df["Mugem_Yerlesti"] == False)
    ]
    mugem = target_df[
        (target_df["Mugem_X"].notna()) &
        (target_df["Mugem_Y"].notna()) &
        (target_df["Erection_Bas"] <= t)
    ]
    return len(normal) + len(istif) + len(mugem)


# ==================================================
# ÇİZİM FONKSİYONLARI
# ==================================================

def blok_renk(blok, tarih_ts):
    if bool(blok.get("Mugem_Yerlesti", False)):
        return "#1a5276"
    bitis = blok.get("Bitis")
    erection = blok.get("Erection_Bas")
    tarih_ts_pd = pd.Timestamp(tarih_ts)
    if pd.notna(bitis) and tarih_ts_pd <= pd.Timestamp(bitis):
        return "#1e8449"
    elif pd.notna(erection) and tarih_ts_pd < pd.Timestamp(erection):
        return "#b9770e"
    return "#1e8449"


def _blok_ciz_tek(ax, b, tarih_ts, x_offset=0.0):
    x = float(b["Koord_X"]) + x_offset
    y = float(b["Koord_Y"])
    donuk = bool(b["Donuk"])
    bw = float(b["Boy"]) if donuk else float(b["En"])
    bh = float(b["En"]) if donuk else float(b["Boy"])
    gw = bw + ISKELE * 2
    gh = bh + ISKELE * 2
    renk = blok_renk(b, tarih_ts)
    ec = "#e74c3c" if bool(b.get("Otelendi", False)) else "#17202a"
    ew = 2 if bool(b.get("Otelendi", False)) else 1
    ax.add_patch(Rectangle((x, y), gw, gh, linewidth=0.5, edgecolor="#e67e22", facecolor="#fef9e7", alpha=0.7))
    ax.add_patch(FancyBboxPatch((x + ISKELE, y + ISKELE), bw, bh, boxstyle="round,pad=0.1", linewidth=ew, edgecolor=ec, facecolor=renk, alpha=0.9))
    ax.text(x + ISKELE + bw/2, y + ISKELE + bh/2, str(b["Blok"])[:10], ha="center", va="center", fontsize=5, color="white", fontweight="bold")


def saha_ciz_a3_birlesik(ax, target_df, tarih_ts):
    a3_u, a3_g = 74.0, 32.0
    jig_u, jig_g = 52.0, 32.0
    toplam_u = a3_u + jig_u
    toplam_g = max(a3_g, jig_g)
    ax.add_patch(FancyBboxPatch((0, 0), toplam_u, toplam_g, boxstyle="round,pad=0.3", linewidth=2, linestyle="--", edgecolor="#2c3e50", facecolor="#ecf0f1", alpha=0.25))
    ax.plot([a3_u, a3_u], [0, toplam_g], color="#2c3e50", linewidth=1.5, linestyle="--")
    tr = TRANSFER_RULES.get("A3 Atölyesi")
    if tr:
        tw, th = tr["size"]
        if tr.get("rotate", False):
            tw, th = th, tw
        ax.add_patch(Rectangle((0, 0), tw, th, linewidth=1.5, edgecolor="#8e44ad", facecolor="none", linestyle="--"))
        ax.text(tw/2, th/2, f"TRANSFER\n{tw:.0f}x{th:.0f}m", ha="center", va="center", fontsize=5, color="#5b2c6f", fontweight="bold")
    a3_aktif = target_df[
        (target_df["Atanan_Saha"] == "A3 Atölyesi") &
        (target_df["Baslangic"] <= tarih_ts) &
        (target_df["Erection_Bas"] > tarih_ts) &
        (target_df["Koord_X"].notna()) &
        (target_df["Istife_Tasindi"] == False)
    ].copy()
    jig_aktif = target_df[
        (target_df["Atanan_Saha"] == "A3 Atölyesi(Jig)") &
        (target_df["Baslangic"] <= tarih_ts) &
        (target_df["Erection_Bas"] > tarih_ts) &
        (target_df["Koord_X"].notna()) &
        (target_df["Istife_Tasindi"] == False)
    ].copy()
    for _, b in a3_aktif.iterrows():
        _blok_ciz_tek(ax, b, tarih_ts, 0.0)
    for _, b in jig_aktif.iterrows():
        _blok_ciz_tek(ax, b, tarih_ts, a3_u)
    ax.text(a3_u/2, toplam_g+2.5, "A3 Atölyesi", fontsize=9, fontweight="bold", color="#1b2631", ha="center")
    ax.text(a3_u + jig_u/2, toplam_g+2.5, "A3 Atölyesi(Jig)", fontsize=9, fontweight="bold", color="#1b2631", ha="center")
    a3_saha = next(s for s in SAHALAR if s["ad"] == "A3 Atölyesi")
    jig_saha = next(s for s in SAHALAR if s["ad"] == "A3 Atölyesi(Jig)")
    a3_kul = saha_kullanim_alani(a3_saha, target_df, tarih_ts)[1]
    jig_kul = saha_kullanim_alani(jig_saha, target_df, tarih_ts)[1]
    a3_kap, jig_kap = a3_u * a3_g, jig_u * jig_g
    a3_pct = min(a3_kul / a3_kap * 100, 100) if a3_kap > 0 else 0
    jig_pct = min(jig_kul / jig_kap * 100, 100) if jig_kap > 0 else 0
    def _renk(pct): return "#e74c3c" if pct >= DARBOGAZ_PCT else "#f39c12" if pct >= 60 else "#27ae60"
    ax.text(a3_u/2, -3.5, f"%{a3_pct:.0f} ({len(a3_aktif)} blok)", fontsize=7, fontweight="bold", color=_renk(a3_pct), ha="center")
    ax.text(a3_u + jig_u/2, -3.5, f"%{jig_pct:.0f} ({len(jig_aktif)} blok)", fontsize=7, fontweight="bold", color=_renk(jig_pct), ha="center")
    ax.set_xlim(-2, toplam_u+3)
    ax.set_ylim(-6, toplam_g+6)
    ax.set_aspect("equal")
    ax.axis("off")


def saha_ciz_istif(ax, saha, target_df, tarih_ts):
    trapezoid = np.array([[ISTIF_X_SOL, ISTIF_Y_ALT], [ISTIF_X_ALT, ISTIF_Y_ALT], [ISTIF_X_UST, ISTIF_Y_UST], [ISTIF_X_SOL, ISTIF_Y_UST]])
    ax.add_patch(Polygon(trapezoid, closed=True, linewidth=2, linestyle="--", edgecolor="#2c3e50", facecolor="#ecf0f1", alpha=0.25))
    ax.annotate("", xy=(ISTIF_X_UST, ISTIF_Y_UST+2), xytext=(0, ISTIF_Y_UST+2), arrowprops=dict(arrowstyle="<->", color="#aaa", lw=1))
    ax.text(ISTIF_X_UST/2, ISTIF_Y_UST+3, f"{ISTIF_X_UST:.2f}m", ha="center", fontsize=6.5, color="#333")
    ax.annotate("", xy=(ISTIF_X_ALT, -2), xytext=(0, -2), arrowprops=dict(arrowstyle="<->", color="#aaa", lw=1))
    ax.text(ISTIF_X_ALT/2, -3.5, f"{ISTIF_X_ALT:.2f}m", ha="center", fontsize=6.5, color="#333")
    ax.annotate("", xy=(-2, ISTIF_Y_UST), xytext=(-2, 0), arrowprops=dict(arrowstyle="<->", color="#aaa", lw=1))
    ax.text(-5, ISTIF_Y_UST/2, f"{ISTIF_Y_UST:.2f}m", ha="center", fontsize=6.5, color="#333", rotation=90, va="center")
    ax.text((ISTIF_X_ALT+ISTIF_X_UST)/2+2, ISTIF_Y_UST/2, "45.21m", ha="left", fontsize=6.5, color="#333", rotation=-38)
    aktif = target_df[(target_df["Istif_X"].notna()) & (target_df["Bitis"] < tarih_ts) & (target_df["Erection_Bas"] > tarih_ts) & (target_df["Mugem_Yerlesti"] == False)].copy()
    for _, b in aktif.iterrows():
        x, y = float(b["Istif_X"]), float(b["Istif_Y"])
        donuk = bool(b["Donuk"])
        bw = float(b["Boy"]) if donuk else float(b["En"])
        bh = float(b["En"]) if donuk else float(b["Boy"])
        gw, gh = bw + ISKELE*2, bh + ISKELE*2
        ec = "#e74c3c" if bool(b.get("Otelendi", False)) else "#17202a"
        ew = 2 if bool(b.get("Otelendi", False)) else 1
        ax.add_patch(Rectangle((x, y), gw, gh, linewidth=0.5, edgecolor="#e67e22", facecolor="#fef9e7", alpha=0.7))
        ax.add_patch(FancyBboxPatch((x+ISKELE, y+ISKELE), bw, bh, boxstyle="round,pad=0.1", linewidth=ew, edgecolor=ec, facecolor="#b9770e", alpha=0.9))
        ax.text(x+ISKELE+bw/2, y+ISKELE+bh/2, str(b["Blok"])[:10], ha="center", va="center", fontsize=5, color="white", fontweight="bold")
    kullanilan_alan = saha_kullanim_alani(saha, target_df, tarih_ts)[1]
    kap = ((ISTIF_X_UST + ISTIF_X_ALT) / 2 * ISTIF_Y_UST)
    pct = min(kullanilan_alan / kap * 100, 100) if kap > 0 else 0
    renk = "#e74c3c" if pct >= DARBOGAZ_PCT else "#f39c12" if pct >= 60 else "#27ae60"
    ax.text(ISTIF_X_UST/2, ISTIF_Y_UST+5.5, "Açık Saha(İstif)", fontsize=9, fontweight="bold", color="#1b2631", ha="center")
    ax.text(ISTIF_X_UST, ISTIF_Y_UST+5.5, f"%{pct:.0f} dolu ({len(aktif)} blok)", fontsize=8, fontweight="bold", color=renk, ha="right")
    ax.set_xlim(-8, ISTIF_X_UST+8)
    ax.set_ylim(-6, ISTIF_Y_UST+10)
    ax.set_aspect("equal")
    ax.axis("off")


def saha_ciz_duz_kizak(ax, saha, target_df, tarih_ts):
    toplam_u, toplam_g = DUZ_KIZAK_TOPLAM_U, DUZ_KIZAK_TOPLAM_G
    blok_u, mugem_u = DUZ_KIZAK_BLOK_U, DUZ_KIZAK_MUGEM_U
    ax.add_patch(FancyBboxPatch((0, 0), toplam_u, toplam_g, boxstyle="round,pad=0.3", linewidth=2, linestyle="--", edgecolor="#2c3e50", facecolor="#ecf0f1", alpha=0.25))
    ax.plot([blok_u, blok_u], [0, toplam_g], color="#2c3e50", linewidth=1.5, linestyle="--")
    ax.text(blok_u + mugem_u/2, toplam_g+0.5, "⚓ MUGEM Gemisi", ha="center", va="bottom", fontsize=10, color="#2c3e50", fontweight="bold", style="italic")
    ax.add_patch(Rectangle((blok_u, 0), mugem_u, toplam_g, linewidth=1.0, edgecolor="#7f8c8d", facecolor="#f4f6f6", alpha=0.3))
    tr = TRANSFER_RULES.get("Düz Kızak")
    if tr:
        tw, th = tr["size"]
        if tr.get("rotate", False):
            tw, th = th, tw
        ax.add_patch(Rectangle((0, 0), tw, th, linewidth=1.5, edgecolor="#8e44ad", facecolor="none", linestyle="--"))
        ax.text(tw/2, th/2, f"TRANSFER\n{tw:.0f}x{th:.0f}m", ha="center", va="center", fontsize=6, color="#5b2c6f", fontweight="bold")
    aktif = target_df[
        (target_df["Atanan_Saha"] == "Düz Kızak") &
        (target_df["Baslangic"] <= tarih_ts) &
        (target_df["Erection_Bas"] > tarih_ts) &
        (target_df["Koord_X"].notna()) &
        (target_df["Istife_Tasindi"] == False)
    ].copy()
    for _, b in aktif.iterrows():
        _blok_ciz_tek(ax, b, tarih_ts, 0.0)
    mugem_aktif = target_df[(target_df["Mugem_X"].notna()) & (target_df["Mugem_Y"].notna()) & (target_df["Erection_Bas"] <= tarih_ts)].copy()
    for _, b in mugem_aktif.iterrows():
        mx, my = float(b["Mugem_X"]), float(b["Mugem_Y"])
        bw, bh = mugem_boyut(b)
        ax.add_patch(FancyBboxPatch((mx, my), bw, bh, boxstyle="round,pad=0.1", linewidth=1.5, edgecolor="#0c2461", facecolor="#1a5276", alpha=0.92))
        ax.text(mx + bw/2, my + bh/2, str(b["Blok"])[:10], ha="center", va="center", fontsize=6, color="white", fontweight="bold")
    ax.text(0, toplam_g+2.5, "Düz Kızak", fontsize=9, fontweight="bold", color="#1b2631")
    kullanilan_alan = saha_kullanim_alani(saha, target_df, tarih_ts)[1]
    kap = blok_u * toplam_g
    pct = min(kullanilan_alan / kap * 100, 100) if kap > 0 else 0
    renk = "#e74c3c" if pct >= DARBOGAZ_PCT else "#f39c12" if pct >= 60 else "#27ae60"
    ax.text(blok_u, toplam_g+2.5, f"%{pct:.0f} dolu ({len(aktif)} blok)", fontsize=8, fontweight="bold", color=renk, ha="right")
    if len(mugem_aktif) > 0:
        ax.text(toplam_u, toplam_g+2.5, f"⚓ MUGEM: {len(mugem_aktif)} blok", fontsize=8, fontweight="bold", color="#1a5276", ha="right")
    ax.set_xlim(-2, toplam_u+3)
    ax.set_ylim(-3.5, toplam_g+7)
    ax.set_aspect("equal")
    ax.axis("off")


def saha_ciz_a6(ax, saha, target_df, tarih_ts):
    t = pd.Timestamp(tarih_ts).to_pydatetime()
    eyul_sonrasi = t >= A6_EYUL
    blok_u = A6_TAM_U if eyul_sonrasi else A6_BLOK_U
    ax.add_patch(FancyBboxPatch((0, 0), A6_TAM_U, A6_G, boxstyle="round,pad=0.3", linewidth=2, linestyle="--", edgecolor="#2c3e50", facecolor="#ecf0f1", alpha=0.25))
    if not eyul_sonrasi:
        ax.plot([blok_u, blok_u], [0, A6_G], color="#2c3e50", linewidth=1.5, linestyle="--")
        nb76_ic_w, nb76_ic_h = A6_NB76_U * 0.55, A6_G * 0.45
        nb76_ic_x = blok_u + (A6_NB76_U - nb76_ic_w) / 2
        nb76_ic_y = (A6_G - nb76_ic_h) / 2
        ax.add_patch(Rectangle((nb76_ic_x, nb76_ic_y), nb76_ic_w, nb76_ic_h, linewidth=1.5, edgecolor="#2c3e50", facecolor="none"))
        ax.text(blok_u + A6_NB76_U/2, A6_G/2, "NB76", ha="center", va="center", fontsize=11, color="#2c3e50", fontweight="bold")
    tr = TRANSFER_RULES.get("A6 Atölyesi")
    if tr:
        tw, th = tr["size"]
        if tr.get("rotate", False):
            tw, th = th, tw
        ax.add_patch(Rectangle((0, 0), tw, th, linewidth=1.5, edgecolor="#8e44ad", facecolor="none", linestyle="--"))
        ax.text(tw/2, th/2, f"TRANSFER\n{tw:.0f}x{th:.0f}m", ha="center", va="center", fontsize=5, color="#5b2c6f", fontweight="bold")
    aktif = target_df[
        (target_df["Atanan_Saha"] == "A6 Atölyesi") &
        (target_df["Baslangic"] <= tarih_ts) &
        (target_df["Erection_Bas"] > tarih_ts) &
        (target_df["Koord_X"].notna()) &
        (target_df["Istife_Tasindi"] == False)
    ].copy()
    for _, b in aktif.iterrows():
        _blok_ciz_tek(ax, b, tarih_ts, 0.0)
    kullanilan_alan = saha_kullanim_alani(saha, target_df, tarih_ts)[1]
    kap = blok_u * A6_G
    pct = min(kullanilan_alan / kap * 100, 100) if kap > 0 else 0
    renk = "#e74c3c" if pct >= DARBOGAZ_PCT else "#f39c12" if pct >= 60 else "#27ae60"
    etiket = "A6 Atölyesi" if eyul_sonrasi else "A6 Atölyesi  |  NB76"
    ax.text(0, A6_G+2.5, etiket, fontsize=9, fontweight="bold", color="#1b2631")
    ax.text(A6_TAM_U, A6_G+2.5, f"%{pct:.0f} dolu ({len(aktif)} blok)", fontsize=8, fontweight="bold", color=renk, ha="right")
    ax.set_xlim(-2, A6_TAM_U+3)
    ax.set_ylim(-3.5, A6_G+7)
    ax.set_aspect("equal")
    ax.axis("off")


def saha_ciz(ax, saha, target_df, tarih_ts):
    t = pd.Timestamp(tarih_ts).to_pydatetime()
    u, g = saha["alan"](t)
    if u <= 0 or g <= 0:
        ax.axis("off")
        return
    if saha["ad"] == "A3 Atölyesi(Jig)":
        ax.axis("off")
        return
    if saha["ad"] == "A3 Atölyesi":
        saha_ciz_a3_birlesik(ax, target_df, tarih_ts)
        return
    if saha["ad"] == "Açık Saha(İstif)":
        saha_ciz_istif(ax, saha, target_df, tarih_ts)
        return
    if saha["ad"] == "Düz Kızak":
        saha_ciz_duz_kizak(ax, saha, target_df, tarih_ts)
        return
    if saha["ad"] == "A6 Atölyesi":
        saha_ciz_a6(ax, saha, target_df, tarih_ts)
        return
    ax.add_patch(FancyBboxPatch((0, 0), u, g, boxstyle="round,pad=0.3", linewidth=2, linestyle="--", edgecolor="#2c3e50", facecolor="#ecf0f1", alpha=0.25))
    tr = TRANSFER_RULES.get(saha["ad"])
    if tr:
        tw, th = tr["size"]
        if tr.get("rotate", False):
            tw, th = th, tw
        ax.add_patch(Rectangle((0, 0), tw, th, linewidth=1.5, edgecolor="#8e44ad", facecolor="none", linestyle="--"))
        ax.text(tw/2, th/2, f"TRANSFER\n{tw:.0f}x{th:.0f}m", ha="center", va="center", fontsize=5, color="#5b2c6f", fontweight="bold")
    aktif = target_df[
        (target_df["Atanan_Saha"] == saha["ad"]) &
        (target_df["Baslangic"] <= tarih_ts) &
        (target_df["Erection_Bas"] > tarih_ts) &
        (target_df["Koord_X"].notna()) &
        (target_df["Istife_Tasindi"] == False)
    ].copy()
    for _, b in aktif.iterrows():
        _blok_ciz_tek(ax, b, tarih_ts, 0.0)
    kullanilan_alan = saha_kullanim_alani(saha, target_df, tarih_ts)[1]
    kap = u * g
    pct = min(kullanilan_alan / kap * 100, 100) if kap > 0 else 0
    renk = "#e74c3c" if pct >= DARBOGAZ_PCT else "#f39c12" if pct >= 60 else "#27ae60"
    ax.text(0, g+2.5, saha["ad"], fontsize=9, fontweight="bold", color="#1b2631")
    ax.text(u, g+2.5, f"%{pct:.0f} dolu ({len(aktif)} blok)", fontsize=8, fontweight="bold", color=renk, ha="right")
    ax.set_xlim(-2, u+3)
    ax.set_ylim(-3.5, g+7)
    ax.set_aspect("equal")
    ax.axis("off")


def plan_goster(target_df, tarih_ts):
    import matplotlib.gridspec as gridspec
    t = pd.Timestamp(tarih_ts)
    aktif_sahalar = [s for s in SAHALAR if s["alan"](t.to_pydatetime())[0] > 0 and s["ad"] != "A3 Atölyesi(Jig)"]
    def saha_boyut(s):
        if s["ad"] == "Açık Saha(İstif)":
            return (ISTIF_X_UST, ISTIF_Y_UST)
        if s["ad"] == "Düz Kızak":
            return (DUZ_KIZAK_TOPLAM_U, DUZ_KIZAK_TOPLAM_G)
        if s["ad"] == "A6 Atölyesi":
            return (A6_TAM_U, A6_G)
        if s["ad"] == "A3 Atölyesi":
            return (74.0 + 52.0, 32.0)
        u, g = s["alan"](t.to_pydatetime())
        return (u, g)
    cols = 3
    rows = max(1, (len(aktif_sahalar) + cols - 1) // cols)
    row_max_g, col_max_u = [], [0] * cols
    for i, saha in enumerate(aktif_sahalar):
        r, c = i // cols, i % cols
        u, g = saha_boyut(saha)
        if len(row_max_g) <= r:
            row_max_g.append(0)
        if g > row_max_g[r]:
            row_max_g[r] = g
        if u > col_max_u[c]:
            col_max_u[c] = u
    scale = 0.05
    fig_w = max(sum(col_max_u) * scale + cols * 0.5 + 2, 20)
    fig_h = max(sum(row_max_g) * scale + rows * 1.5 + 2, rows * 4)
    fig = plt.figure(figsize=(fig_w, fig_h))
    gs = gridspec.GridSpec(rows, cols, figure=fig, width_ratios=col_max_u, height_ratios=row_max_g, hspace=0.4, wspace=0.15)
    axes = []
    for i, saha in enumerate(aktif_sahalar):
        r, c = i // cols, i % cols
        axes.append(fig.add_subplot(gs[r, c]))
    aktif_toplam = aktif_blok_say(target_df, t)
    kap = toplam_kapasite(t)
    kullanilan_toplam = sum(saha_kullanim_alani(s, target_df, t)[1] for s in aktif_sahalar)
    pct = min(kullanilan_toplam / kap * 100, 100) if kap > 0 else 0
    color = "#e74c3c" if pct >= DARBOGAZ_PCT else "#1b2631"
    sigmiyan_sayi = len(target_df[target_df["Sigmiyor"] == True])
    otelenen_sayi = len(target_df[target_df["Otelendi"] == True])
    mugem_sayi = len(target_df[(target_df["Mugem_X"].notna()) & (target_df["Mugem_Y"].notna()) & (target_df["Erection_Bas"] <= t)])
    baslik = f"🏗️ BLOK SAHASI YERLEŞİM PLANI — {t.strftime('%d.%m.%Y')}\nToplam Aktif Blok: {aktif_toplam} | Genel Doluluk: %{pct:.1f}"
    if mugem_sayi > 0:
        baslik += f" | ⚓ MUGEM: {mugem_sayi}"
    if sigmiyan_sayi > 0:
        baslik += f" | ❌ Sığmayan: {sigmiyan_sayi}"
    if otelenen_sayi > 0:
        baslik += f" | ⏰ Ötelenen: {otelenen_sayi}"
    fig.suptitle(baslik, fontsize=13, fontweight="bold", y=0.98, color=color)
    for i, saha in enumerate(aktif_sahalar):
        saha_ciz(axes[i], saha, target_df, t)
    plt.tight_layout(pad=1.5, rect=[0, 0, 1, 0.96])
    return fig


# ==================================================
# ANA STREAMLIT ARAYÜZ
# ==================================================

uploaded_file = st.file_uploader("📂 **Excel dosyasını yükle** (Blok Yerleşim Çalışması.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    try:
        # Excel'i oku
        df = pd.read_excel(uploaded_file, sheet_name="Blok(MUGEM)")
        
        # Sütun adlarını düzenle
        if len(df.columns) >= 13:
            df.columns = ["Blok", "Baslangic", "Bitis", "Erection_Bas", "En", "Boy", "Alan", "Tonaj",
                          "Atanacak_Saha", "Kordinat_X", "Kordinat_Y", "Erection_X", "Erection_Y"]
        elif len(df.columns) >= 11:
            df.columns = ["Blok", "Baslangic", "Bitis", "Erection_Bas", "En", "Boy", "Alan", "Tonaj",
                          "Atanacak_Saha", "Kordinat_X", "Kordinat_Y"]
            df["Erection_X"] = np.nan
            df["Erection_Y"] = np.nan
        else:
            df.columns = ["Blok", "Baslangic", "Bitis", "Erection_Bas", "En", "Boy", "Alan", "Tonaj"]
            df["Atanacak_Saha"] = np.nan
            df["Kordinat_X"] = np.nan
            df["Kordinat_Y"] = np.nan
            df["Erection_X"] = np.nan
            df["Erection_Y"] = np.nan
        
        for c in ["Baslangic", "Bitis", "Erection_Bas"]:
            df[c] = pd.to_datetime(df[c], dayfirst=True, errors="coerce")
        
        # Temel bilgiler
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📦 Toplam Blok", len(df))
        col2.metric("🏗️ Toplam Tonaj", f"{df['Tonaj'].sum():.0f} t")
        col3.metric("📐 Toplam Alan", f"{df['Alan'].sum():.0f} m²")
        col4.metric("📅 Başlangıç", df["Baslangic"].min().strftime("%d.%m.%Y") if pd.notna(df["Baslangic"].min()) else "-")
        
        st.markdown("---")
        
        # Gerekli sütunları ekle
        df["Gercek_En"] = df["En"] + ISKELE * 2
        df["Gercek_Boy"] = df["Boy"] + ISKELE * 2
        df["Gercek_Alan"] = df["Gercek_En"] * df["Gercek_Boy"]
        df["Atanan_Saha"] = np.nan
        df["Koord_X"] = np.nan
        df["Koord_Y"] = np.nan
        df["Normal_X"] = np.nan
        df["Normal_Y"] = np.nan
        df["Istif_X"] = np.nan
        df["Istif_Y"] = np.nan
        df["Mugem_X"] = np.nan
        df["Mugem_Y"] = np.nan
        df["Mugem_Yerlesti"] = False
        df["Istife_Tasindi"] = False
        df["Donuk"] = False
        df["Sigmiyor"] = False
        df["Otelendi"] = False
        df["Orijinal_Bas"] = df["Baslangic"].copy()
        df["Orijinal_Bitis"] = df["Bitis"].copy()
        
        # Manuel atamaları işle
        for i, row in df.iterrows():
            saha_adi = row.get("Atanacak_Saha")
            kx, ky = row.get("Kordinat_X"), row.get("Kordinat_Y")
            if pd.isna(saha_adi):
                continue
            if not isinstance(saha_adi, str):
                continue
            saha_adi = saha_adi.strip()
            saha_obj = next((s for s in SAHALAR if s["ad"] == saha_adi), None)
            if saha_obj is None:
                continue
            t = pd.Timestamp(row["Baslangic"]).to_pydatetime() if pd.notna(row["Baslangic"]) else datetime.now()
            if not saha_obj["kisit"](row, t):
                continue
            df.at[i, "Atanan_Saha"] = saha_adi
            if pd.notna(kx) and pd.notna(ky):
                try:
                    x, y = float(kx), float(ky)
                    u, g = saha_obj["alan"](t)
                    gw, gh = row["En"] + ISKELE*2, row["Boy"] + ISKELE*2
                    if x >= 0 and y >= 0:
                        if saha_adi == "Düz Kızak":
                            if x + gw <= DUZ_KIZAK_BLOK_U and y + gh <= g:
                                df.at[i, "Koord_X"] = x
                                df.at[i, "Koord_Y"] = y
                        else:
                            if x + gw <= u and y + gh <= g:
                                df.at[i, "Koord_X"] = x
                                df.at[i, "Koord_Y"] = y
                except:
                    pass
        
        df = df.sort_values(["Baslangic", "Tonaj"], ascending=[True, False]).reset_index(drop=True)
        
        # Tarih seçici
        min_date = df["Baslangic"].min()
        max_date = df["Erection_Bas"].max()
        secilen_tarih = st.date_input("📅 **Plan Görüntülenecek Tarih**", value=pd.Timestamp.now(), min_value=min_date, max_value=max_date)
        
        if st.button("🔄 **Yerleşimi Hesapla ve Göster**", type="primary", use_container_width=True):
            with st.spinner("🏗️ Yerleşim hesaplanıyor. Lütfen bekleyin..."):
                managers = yerlesim_hesapla(secilen_tarih, df)
            
            st.success(f"✅ Hesaplama tamamlandı - {secilen_tarih.strftime('%d.%m.%Y')}")
            st.markdown("---")
            
            st.subheader(f"📐 YERLEŞİM PLANI - {secilen_tarih.strftime('%d.%m.%Y')}")
            fig = plan_goster(df, secilen_tarih)
            st.pyplot(fig)
            plt.close(fig)
            
            st.markdown("---")
            st.subheader("📥 ÇIKTI İNDİR")
            
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                cikti = df.copy()
                for col in ["Baslangic", "Bitis", "Erection_Bas", "Orijinal_Bas", "Orijinal_Bitis"]:
                    if col in cikti.columns:
                        cikti[col] = pd.to_datetime(cikti[col]).dt.strftime("%d.%m.%Y")
                cols_to_keep = ["Blok", "Baslangic", "Bitis", "Erection_Bas", "Atanan_Saha",
                                "Koord_X", "Koord_Y", "Mugem_X", "Mugem_Y", "Mugem_Yerlesti",
                                "Istife_Tasindi", "Donuk", "Sigmiyor", "Otelendi",
                                "Orijinal_Bas", "Orijinal_Bitis"]
                cols_to_keep = [c for c in cols_to_keep if c in cikti.columns]
                cikti[cols_to_keep].to_excel(writer, index=False, sheet_name="Yerlesim")
            
            st.download_button(
                label="📥 **Excel Çıktısını İndir**",
                data=output.getvalue(),
                file_name=f"blok_yerlesim_{secilen_tarih.strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            
            # Raporlar
            st.markdown("---")
            st.subheader("📊 RAPORLAR")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.warning(f"❌ **Sığmayan Bloklar:** {len(df[df['Sigmiyor'] == True])} adet")
            with col2:
                st.info(f"⏰ **Ötelenen Bloklar:** {len(df[df['Otelendi'] == True])} adet")
            with col3:
                st.success(f"⚓ **MUGEM'e Yerleşen:** {len(df[df['Mugem_Yerlesti'] == True])} adet")
    
    except Exception as e:
        st.error(f"❌ Hata oluştu: {str(e)}")
        st.info("Excel dosyasının doğru formatta olduğundan emin olun.")

else:
    st.info("👈 **Lütfen Excel dosyasını yükleyin**")
    st.markdown("""
    ### 📋 Excel Dosyası Formatı:
    
    Dosyada aşağıdaki sütunlar bulunmalıdır:
    - **Blok** - Blok adı
    - **Baslangic** - Başlangıç tarihi
    - **Bitis** - Bitiş tarihi  
    - **Erection_Bas** - Erection başlangıç tarihi
    - **En** - En ölçüsü (m)
    - **Boy** - Boy ölçüsü (m)
    - **Tonaj** - Ağırlık (t)
    - **Alan** - Alan (m²)
    
    İsteğe bağlı:
    - **Atanacak_Saha** - Manuel saha ataması
    - **Kordinat_X/Y** - Manuel koordinat ataması
    - **Erection_X/Y** - MUGEM koordinatları
    """)

st.markdown("---")
st.caption("🏗️ Blok Yerleşim Planı | © 2024")
