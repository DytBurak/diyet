import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os
import random
from datetime import date, datetime

# ==========================================
# 1. AYARLAR & DİL
# ==========================================
st.set_page_config(page_title="DiyetTakibim Pro MAX", layout="wide", page_icon="💎")

st.markdown("""
    <script>document.documentElement.setAttribute('lang', 'tr');</script>
""", unsafe_allow_html=True)

# ==========================================
# 2. CSS TASARIM (PREMIUM DARK)
# ==========================================
st.markdown("""
    <style>
    .stApp { background-color: #1a1c24; color: #e0e0e0; }
    [data-testid="stSidebar"] { background-color: #13151b; border-right: 1px solid #333; }
    
    .dashboard-card {
        background-color: #262a36; padding: 20px; border-radius: 15px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3); margin-bottom: 20px; border: 1px solid #333846;
    }
    
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div>div {
        background-color: #1f222c !important; color: white !important; border: 1px solid #444 !important; border-radius: 8px;
    }
    
    .info-box {
        background-color: #2c3e50; color: white !important; padding: 15px;
        border-radius: 10px; border-left: 5px solid #3498db; margin-bottom: 10px;
    }
    .info-box h1, .info-box h2, .info-box h3, .info-box p { color: white !important; margin: 0; }
    
    .stButton>button {
        background: linear-gradient(90deg, #6c5ce7 0%, #a29bfe 100%);
        color: white; font-weight: bold; border: none; border-radius: 6px; width: 100%;
    }
    
    div[data-testid="stMetric"] { background-color: #262a36; padding: 10px; border-radius: 10px; border: 1px solid #333; }
    div[data-testid="stMetricValue"] { color: #fff; }
    
    .streamlit-expanderHeader { background-color: #2c3e50; color: white; font-weight: bold; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. YARDIMCI FONKSİYONLAR
# ==========================================
def calculate_exchange_ui(prefix):
    """Değişim Hesaplama Arayüzü"""
    vals = {
        "Süt(Tam)": [9,6,6,114,100,370,230,24], "Süt(Yarım)": [9,6,3,87,100,370,230,12],
        "Et(Orta)": [0,6,5,69,65,100,150,20], "Ekmek/Tahıl": [15,2,0,68,150,30,30,0],
        "Sebze": [6,1,0,28,20,200,20,0], "Meyve": [15,0,0,60,0,200,15,0],
        "Yağ": [0,0,5,45,0,0,0,0], "Şeker": [10,0,0,40,0,0,0,0]
    }
    cols = st.columns(4)
    inputs = {}
    for i, k in enumerate(vals.keys()):
        inputs[k] = cols[i%4].number_input(f"{k}", 0.0, step=0.5, key=f"{prefix}_{i}")

    totals = {x:0 for x in ["Karb","Prot","Yağ","Kal","Na","K","P","Chol"]}
    for k, v in vals.items():
        n = inputs[k]
        totals["Karb"]+=n*v[0]; totals["Prot"]+=n*v[1]; totals["Yağ"]+=n*v[2]; totals["Kal"]+=n*v[3]
        totals["Na"]+=n*v[4]; totals["K"]+=n*v[5]; totals["P"]+=n*v[6]; totals["Chol"]+=n*v[7]

    st.markdown("---")
    c_res1, c_res2 = st.columns([1, 1])
    with c_res1:
        st.markdown(f'<div class="dashboard-card" style="text-align:center;"><h3 style="color:#6c5ce7">{int(totals["Kal"])} kcal</h3><p>K: {int(totals["Karb"])} | P: {int(totals["Prot"])} | Y: {int(totals["Yağ"])}</p></div>', unsafe_allow_html=True)
        if totals['Kal']>0:
            fig = px.pie(values=[totals['Karb']*4, totals['Prot']*4, totals['Yağ']*9], names=["Karb","Prot","Yağ"], hole=0.5, template="plotly_dark", color_discrete_sequence=['#3498db', '#e74c3c', '#f1c40f'])
            fig.update_traces(textinfo='percent+label', hovertemplate='%{label}: %{value:.0f} kcal')
            st.plotly_chart(fig, use_container_width=True)
    with c_res2:
        st.markdown('<div class="dashboard-card"><h4>Mikro Besinler</h4>', unsafe_allow_html=True)
        mc1, mc2 = st.columns(2)
        mc1.metric("Na", f"{int(totals['Na'])}"); mc2.metric("K", f"{int(totals['K'])}")
        mc1.metric("P", f"{int(totals['P'])}"); mc2.metric("Chol", f"{int(totals['Chol'])}")
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 4. VERİTABANI (JSON)
# ==========================================
DB_FILE = "klinik_data_max.json"

def load_db():
    default_templates = {
        "🛡️ DASH Diyeti (1600 kcal)": "SABAH:\n- 1 Haşlanmış Yumurta\n- 1 Dilim Az Yağlı Peynir\n- 5 Zeytin (tuzsuz)\n- 2 Dilim TB Ekmek\n\nÖĞLE:\n- 150g Izgara Tavuk\n- Bol Salata (limonlu)\n- 1 Kase Yoğurt\n\nAKŞAM:\n- 8 Kaşık Sebze Yemeği\n- 1 Kase Çorba\n- Salata",
        "🫀 TLC Diyeti (Kolesterol)": "SABAH:\n- Yulaf Lapası (Sütlü)\n- 2 Ceviz\n- 1 Elma\n\nÖĞLE:\n- Kurubaklagil Yemeği\n- 3 Kaşık Bulgur\n- Salata\n\nAKŞAM:\n- Izgara Balık (Somon)\n- Buharda Sebze",
        "🩸 Böbrek Koruma (Düşük K/P)": "⚠️ Potasyum ve Fosfor kısıtlaması içerir.\n\nSABAH:\n- 1 Yumurta Beyazı\n- Bal/Reçel\n- Tuzsuz Ekmek\n- Açık Çay\n\nÖĞLE:\n- Pirinç Pilavı\n- Sebze (Suyu süzülmüş)\n- Beyaz Ekmek\n\nAKŞAM:\n- Az Miktarda Tavuk\n- Salata (Domates yok)",
        "📉 Kilo Verme (Standart 1500)": "SABAH:\n- 1 Yumurta + 1 Peynir\n- Yeşillik\n- 2 TB Ekmek\n\nARA:\n- 1 Meyve + 10 Badem\n\nÖĞLE:\n- 8 Kaşık Sebze\n- 1 Yoğurt + 1 Ekmek\n\nAKŞAM:\n- 120g Köfte\n- Bol Salata",
        "🍞 Glutensiz Diyet (Çölyak)": "YASAKLAR: Buğday, Arpa, Çavdar.\n\nSABAH:\n- Glutensiz Ekmek\n- Peynir, Zeytin, Yumurta\n\nÖĞLE:\n- Karabuğday Pilavı\n- Sebze Yemeği\n\nAKŞAM:\n- Balık\n- Fırın Patates",
        "🥑 Ketojenik Diyet": "SABAH:\n- Tereyağlı Omlet\n- 1/2 Avokado\n- 10 Yeşil Zeytin\n\nÖĞLE:\n- Izgara Somon\n- Kuşkonmaz (Zeytinyağlı)\n\nAKŞAM:\n- Bonfile Et\n- Bol Yeşil Salata (Bol Zeytinyağı)",
        "🌱 Düşük FODMAP (IBS)": "SABAH:\n- Glutensiz Yulaf\n- Laktozsuz Süt\n\nÖĞLE:\n- Tavuklu Pirinç Pilavı\n- Havuç Salata\n\nAKŞAM:\n- Balık\n- Patates Püresi"
    }
    
    if not os.path.exists(DB_FILE):
        return {"danisanlar": [], "randevular": [], "odemeler": [], "manuel_listeler": default_templates}
    
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "manuel_listeler" not in data: data["manuel_listeler"] = default_templates
            else:
                for k, v in default_templates.items():
                    if k not in data["manuel_listeler"]:
                        data["manuel_listeler"][k] = v
            return data
    except:
        return {"danisanlar": [], "randevular": [], "odemeler": [], "manuel_listeler": default_templates}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

db = load_db()

# ==========================================
# 5. SABİT VERİLER (AUTO DB & EGZERSİZ)
# ==========================================
@st.cache_data
def get_static_data():
    # Besinler (Akıllı Liste İçin)
    foods = pd.DataFrame({
        "Besin Adı": ["Yumurta", "Köfte", "Tavuk Göğsü", "Somon", "Beyaz Peynir", "Lor Peyniri", "Yoğurt", "Süt", "Tam Buğday Ekmek", "Yulaf Ezmesi", "Pilav", "Makarna", "Elma", "Muz", "Ceviz", "Badem", "Lahmacun", "Simit", "Mercimek Çorbası"],
        "Kalori": [155, 260, 165, 208, 310, 90, 65, 50, 250, 370, 130, 158, 52, 89, 654, 579, 150, 280, 56],
        "Protein": [13, 18, 31, 20, 17, 11, 3.5, 3.3, 10, 13, 2.5, 5, 0.3, 1.1, 15, 21, 6, 8, 4]
    })
    
    # Detaylı Egzersiz Kütüphanesi (Yazılı & Setli)
    exercises = {
        "💪 Kol (Biceps/Triceps)": [
            {"name": "Dumbbell Bicep Curl", "desc": "Ayakta, avuç içleri karşıya bakacak şekilde dambılları kaldırın.", "set": "3x12"},
            {"name": "Hammer Curl", "desc": "Avuç içleri birbirine bakacak şekilde (Çekiç tutuş) dambılları kaldırın.", "set": "3x12"},
            {"name": "Tricep Overhead Extension", "desc": "Tek dambılı iki elinizle başınızın arkasına indirin ve kaldırın.", "set": "3x12"},
            {"name": "Dumbbell Kickback", "desc": "Eğilerek dirsekleri sabitleyin ve kolu geriye doğru düzleştirin.", "set": "3x15"},
            {"name": "Concentration Curl", "desc": "Oturarak, dirseği bacağın iç kısmına dayayıp tek kolla curl yapın.", "set": "3x10"}
        ],
        "🏋️ Omuz (Shoulder)": [
            {"name": "Dumbbell Shoulder Press", "desc": "Oturarak dambılları kulak hizasından yukarı doğru presleyin.", "set": "4x10"},
            {"name": "Lateral Raise", "desc": "Ayakta dambılları yana doğru omuz hizasına kadar açın.", "set": "3x15"},
            {"name": "Front Raise", "desc": "Dambılları sırayla veya aynı anda öne doğru kaldırın.", "set": "3x12"},
            {"name": "Arnold Press", "desc": "Avuç içleri size bakarken başlayın, yukarı iterken çevirin.", "set": "3x10"}
        ],
        "🦍 Sırt (Back)": [
            {"name": "Dumbbell Row", "desc": "Bir elinizle sehpaya dayanın, diğer elinizle dambılı karnınıza çekin.", "set": "3x12"},
            {"name": "Renegade Row", "desc": "Şınav pozisyonunda sırayla dambılları çekin.", "set": "3x10"},
            {"name": "Lat Pulldown (Makine)", "desc": "Barı göğsünüze doğru çekin.", "set": "3x12"}
        ],
        "🦵 Bacak (Legs)": [
            {"name": "Goblet Squat", "desc": "Dambılı göğsünüzde tutarak çömelin.", "set": "4x12"},
            {"name": "Dumbbell Lunge", "desc": "Ellerde dambıl ile öne doğru adım atıp çökün.", "set": "3x12"},
            {"name": "Romanian Deadlift", "desc": "Dizleri hafif kırarak dambılları kaval kemiği hizasına indirin.", "set": "4x10"},
            {"name": "Calf Raise", "desc": "Ellerde ağırlıkla parmak ucuna yükselin.", "set": "4x20"}
        ],
        "🔥 Karın (Core)": [
            {"name": "Weighted Crunch", "desc": "Göğsünüzde ağırlık tutarak mekik çekin.", "set": "3x15"},
            {"name": "Russian Twist", "desc": "Oturarak ayakları kaldırın, ağırlığı sağa sola döndürün.", "set": "3x20"},
            {"name": "Plank", "desc": "Dirsekler üzerinde vücudu düz tutarak bekleyin.", "set": "3x45 sn"},
            {"name": "Leg Raise", "desc": "Sırtüstü yatarken bacakları düz şekilde kaldırıp indirin.", "set": "3x15"}
        ]
    }

    # Otomatik Diyet Motoru Veritabanı (Etiketli & Gramajlı)
    auto_db = {
        "kahvalti": [
            {"name": "Klasik: 1 Haşlanmış Yumurta + 1 Dilim (30g) Beyaz Peynir + 5 Zeytin", "cal": 250, "p": 16, "c": 3, "f": 18, "tag": "std"},
            {"name": "Menemen (2 Yumurtalı, Az Yağlı, Domatesli)", "cal": 280, "p": 14, "c": 10, "f": 18, "tag": "std"},
            {"name": "Lor Peynirli Omlet (2 Yumurta + 3 Kaşık Lor + Maydanoz)", "cal": 240, "p": 22, "c": 4, "f": 13, "tag": "high_pro"},
            {"name": "Yulaf Lapası (4 Kaşık Yulaf + 1 Su Bardağı Süt + Tarçın)", "cal": 300, "p": 12, "c": 45, "f": 7, "tag": "veg"},
            {"name": "Avokadolu Tost (1/2 Avokado + 2 Dilim Peynir)", "cal": 350, "p": 10, "c": 25, "f": 20, "tag": "veg"}
        ],
        "ekmek": [
            {"name": "2 Dilim Tam Buğday Ekmek (50g)", "cal": 140, "p": 6, "c": 26, "f": 2},
            {"name": "1 Dilim Çavdar Ekmek (30g)", "cal": 70, "p": 3, "c": 13, "f": 1},
            {"name": "1/2 Simit (50g)", "cal": 140, "p": 4, "c": 25, "f": 3}
        ],
        "ana_yemek": [
            {"name": "Izgara Köfte (150g - 5 Adet) + Köz Biber", "cal": 350, "p": 28, "c": 6, "f": 22, "tag": "std"},
            {"name": "Izgara Tavuk Göğsü (180g - Baharatlı)", "cal": 200, "p": 38, "c": 0, "f": 4, "tag": "high_pro"},
            {"name": "Fırın Somon (180g) + Roka", "cal": 350, "p": 35, "c": 0, "f": 20, "tag": "high_pro"},
            {"name": "Kuru Fasulye (Etsiz - 8 Yemek Kaşığı)", "cal": 250, "p": 14, "c": 35, "f": 3, "tag": "veg"},
            {"name": "Yeşil Mercimek Yemeği (8 Yemek Kaşığı)", "cal": 220, "p": 16, "c": 30, "f": 2, "tag": "veg"},
            {"name": "Kıymalı Sebze Yemeği (6 Yemek Kaşığı)", "cal": 280, "p": 18, "c": 12, "f": 16, "tag": "std"}
        ],
        "yan_yemek": [
            {"name": "Bulgur Pilavı (4 Yemek Kaşığı)", "cal": 110, "p": 3, "c": 22, "f": 1},
            {"name": "Kepekli Makarna (5 Yemek Kaşığı)", "cal": 150, "p": 5, "c": 30, "f": 1},
            {"name": "Mercimek Çorbası (1 Kepçe)", "cal": 70, "p": 4, "c": 10, "f": 2},
            {"name": "Yoğurt (1 Kase - Ev Yapımı)", "cal": 100, "p": 6, "c": 8, "f": 5},
            {"name": "Ayran (1 Büyük Bardak)", "cal": 80, "p": 4, "c": 6, "f": 4},
            {"name": "Cacık (1 Kase - Salatalıklı)", "cal": 90, "p": 5, "c": 7, "f": 4}
        ],
        "ara": [
            {"name": "1 Orta Boy Elma + 2 Tam Ceviz", "cal": 150, "p": 2, "c": 15, "f": 10},
            {"name": "1 Küçük Muz + 10 Çiğ Badem", "cal": 160, "p": 4, "c": 20, "f": 9},
            {"name": "1 Kuru İncir + 1 Su Bardağı Süt", "cal": 180, "p": 7, "c": 25, "f": 6},
            {"name": "2 Grissini + 1 Bardak Ayran", "cal": 130, "p": 5, "c": 18, "f": 4}
        ]
    }
    # BURASI DÜZELTİLDİ: değişken isimleri eşleşiyor
    return foods, exercises, auto_db

df_foods, egzersizler, auto_db = get_static_data()

# ==========================================
# 6. NAVİGASYON
# ==========================================
with st.sidebar:
    st.title("💎 DiyetTakibim")
    st.caption("Ultimate v30.1 (Bug-Free)")
    menu = st.radio("MENÜ", [
        "🏠 Ana Sayfa",
        "👥 Danışan Yönetimi",
        "📅 Randevu Takvimi",
        "💰 Muhasebe & Kasa",
        "🧮 Yetişkin Planlama",
        "👶 Çocuk Planlama",
        "🤖 Otomatik Diyet Motoru",
        "🍏 Diyet & Hazır Listeler",
        "🩸 Lab Analizi",
        "🏋️ Egzersiz Kütüphanesi"
    ])

# ==========================================
# MODÜL 1: ANA SAYFA
# ==========================================
if menu == "🏠 Ana Sayfa":
    st.markdown(f"""
    <div class="dashboard-card" style="border-left: 5px solid #6c5ce7;">
        <h2>👋 Hoşgeldin, Hocam!</h2>
        <p>Sistemin tüm modülleri tam kapasite çalışıyor. Lab Analizi, Çocuk Grafikleri ve Diyet Motoru detaylandırıldı.</p>
    </div>
    """, unsafe_allow_html=True)
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam Danışan", len(db['danisanlar']))
    c2.metric("Randevular", len(db['randevular']))
    c3.metric("Toplam Kasa", f"{sum(o['Tutar'] for o in db['odemeler']):,.0f} ₺")
    c4.metric("Hazır Şablon", len(db['manuel_listeler']))
    
    # HIZLI BAKIŞ GRAFİĞİ (DEMO)
    st.markdown('<div class="dashboard-card"><h3>📊 Haftalık Aktivite Özeti</h3>', unsafe_allow_html=True)
    chart_data = pd.DataFrame({'Gün': ['Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz'], 'Randevu': [4, 5, 3, 6, 5, 2, 0]})
    fig = px.bar(chart_data, x='Gün', y='Randevu', template="plotly_dark", color_discrete_sequence=['#6c5ce7'])
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# MODÜL 2: DANIŞAN YÖNETİMİ (DETAYLI)
# ==========================================
elif menu == "👥 Danışan Yönetimi":
    st.header("👥 Danışan Yönetimi")
    tab1, tab2 = st.tabs(["➕ Yeni Kayıt", "📋 Hasta Takibi"])
    
    with tab1:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        with st.form("kayit_form"):
            st.subheader("1. Kimlik Bilgileri")
            c1, c2 = st.columns(2)
            ad = c1.text_input("Ad Soyad")
            tel = c2.text_input("Telefon")
            yas = c1.number_input("Yaş", 1, 100, 25)
            boy = c2.number_input("Boy (cm)", 50, 250, 170)
            
            st.subheader("2. Antropometrik Ölçümler")
            o1, o2, o3 = st.columns(3)
            kilo = o1.number_input("Kilo (kg)", 0.0, 300.0, 70.0)
            bel = o2.number_input("Bel (cm)", 0.0)
            kalca = o3.number_input("Kalça (cm)", 0.0)
            boyun = o1.number_input("Boyun (cm)", 0.0)
            baldir = o2.number_input("Baldır (cm)", 0.0)
            
            st.subheader("3. Beslenme Anamnezi")
            sevdigi = st.text_area("Sevdiği Yemekler")
            sevmedigi = st.text_area("Sevmediği / Alerji")
            hastalik = st.text_area("Tanılı Hastalıklar / İlaçlar")
            
            if st.form_submit_button("Danışanı Kaydet"):
                yeni = {
                    "Ad": ad, "Tel": tel, "Yas": yas, "Boy": boy, 
                    "Anamnez": {"Sevdigi": sevdigi, "Sevmedigi": sevmedigi, "Hastalik": hastalik},
                    "Olcumler": [{"Tarih": str(date.today()), "Kilo": kilo, "Bel": bel, "Kalca": kalca, "Boyun": boyun, "Baldir": baldir}]
                }
                db['danisanlar'].append(yeni)
                save_db(db)
                st.success("✅ Danışan başarıyla kaydedildi!")
        st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        if db['danisanlar']:
            isim = st.selectbox("Danışan Seç", [d['Ad'] for d in db['danisanlar']])
            kisi = next(d for d in db['danisanlar'] if d['Ad'] == isim)
            idx = db['danisanlar'].index(kisi)
            
            c_detay, c_graf = st.columns([1, 2])
            with c_detay:
                st.markdown(f"""
                <div class="dashboard-card">
                    <h3>👤 {kisi['Ad']}</h3>
                    <p>📞 {kisi['Tel']}</p>
                    <p>📏 Boy: {kisi['Boy']} cm | Yaş: {kisi['Yas']}</p>
                    <hr>
                    <p><b>💊 Hastalık/İlaç:</b> {kisi.get('Anamnez', {}).get('Hastalik', '-')}</p>
                    <p><b>❤️ Sevdiği:</b> {kisi.get('Anamnez', {}).get('Sevdigi', '-')}</p>
                    <p><b>🚫 Sevmediği:</b> {kisi.get('Anamnez', {}).get('Sevmedigi', '-')}</p>
                </div>
                """, unsafe_allow_html=True)
                
                with st.expander("➕ Yeni Ölçüm Ekle"):
                    nk = st.number_input("Yeni Kilo", 0.0)
                    nb = st.number_input("Bel", 0.0)
                    if st.button("Güncelle"):
                        kisi['Olcumler'].append({"Tarih": str(date.today()), "Kilo": nk, "Bel": nb})
                        db['danisanlar'][idx] = kisi
                        save_db(db)
                        st.success("Ölçüm eklendi!")
            
            with c_graf:
                if kisi['Olcumler']:
                    df_o = pd.DataFrame(kisi['Olcumler'])
                    st.markdown("### 📉 Gelişim Grafiği")
                    fig = px.line(df_o, x="Tarih", y="Kilo", markers=True, template="plotly_dark", title="Kilo Değişimi")
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Henüz kayıtlı danışan yok.")

# ==========================================
# MODÜL 3: RANDEVU TAKVİMİ
# ==========================================
elif menu == "📅 Randevu Takvimi":
    st.header("📅 Randevu Yönetimi")
    
    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown('<div class="dashboard-card"><h3>➕ Randevu Ekle</h3>', unsafe_allow_html=True)
        with st.form("randevu_ver"):
            who = st.selectbox("Danışan", [d['Ad'] for d in db['danisanlar']]) if db['danisanlar'] else st.text_input("İsim Girin")
            when = st.date_input("Tarih")
            time = st.time_input("Saat")
            note = st.text_input("Not")
            if st.form_submit_button("Randevu Oluştur"):
                db['randevular'].append({"Danışan": who, "Tarih": str(when), "Saat": str(time), "Not": note})
                save_db(db)
                st.success("Randevu takvime işlendi.")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with c2:
        st.subheader("📆 Gelecek Randevular")
        if db['randevular']:
            df_r = pd.DataFrame(db['randevular']).sort_values("Tarih")
            st.dataframe(df_r, use_container_width=True)
        else:
            st.info("Randevu bulunamadı.")

# ==========================================
# MODÜL 4: MUHASEBE & KASA
# ==========================================
elif menu == "💰 Muhasebe & Kasa":
    st.header("💰 Finansal Takip")
    
    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown('<div class="dashboard-card"><h3>💵 Ödeme Al</h3>', unsafe_allow_html=True)
        with st.form("odeme_al"):
            who = st.text_input("Ödeyen Kişi")
            amt = st.number_input("Tutar (TL)", 0.0, step=100.0)
            desc = st.text_input("Hizmet Açıklaması")
            if st.form_submit_button("Kaydet"):
                db['odemeler'].append({"Tarih": str(date.today()), "Danışan": who, "Tutar": amt, "Aciklama": desc})
                save_db(db)
                st.success("Kasa güncellendi.")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with c2:
        if db['odemeler']:
            total = sum(o['Tutar'] for o in db['odemeler'])
            st.markdown(f"""
            <div class="dashboard-card" style="text-align:center; border-left: 5px solid #27ae60;">
                <h3>Toplam Ciro</h3>
                <h1 style="color:#27ae60;">{total:,.0f} ₺</h1>
            </div>
            """, unsafe_allow_html=True)
            st.dataframe(pd.DataFrame(db['odemeler']), use_container_width=True)

# ==========================================
# MODÜL 5: YETİŞKİN PLANLAMA
# ==========================================
elif menu == "🧮 Yetişkin Planlama":
    st.header("👨 Yetişkin Hesaplama & Planlama")
    
    with st.expander("1. Enerji Hesabı (Mifflin-St Jeor)", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        yk = c1.number_input("Kilo (kg)", 70.0)
        yb = c2.number_input("Boy (cm)", 170)
        yy = c3.number_input("Yaş", 30)
        yc = c4.selectbox("Cinsiyet", ["Erkek", "Kadın"])
        pal = st.select_slider("Aktivite", ["Sedanter (1.2)", "Hafif (1.375)", "Orta (1.55)", "Aktif (1.725)"])
        pal_val = float(pal.split("(")[1].replace(")", ""))
        
        s = 5 if yc == "Erkek" else -161
        bmh = (10 * yk) + (6.25 * yb) - (5 * yy) + s
        teh = bmh * pal_val
        bki = yk / ((yb/100)**2)
        
        ic1, ic2, ic3 = st.columns(3)
        ic1.markdown(f'<div class="info-box"><h3>BKİ: {bki:.1f}</h3></div>', unsafe_allow_html=True)
        ic2.markdown(f'<div class="info-box"><h3>BMH: {int(bmh)} kcal</h3></div>', unsafe_allow_html=True)
        ic3.markdown(f'<div class="info-box"><h3>TEH: {int(teh)} kcal</h3></div>', unsafe_allow_html=True)

    # Değişim Hesaplama
    st.subheader("2. Değişim Planlama")
    calculate_exchange_ui("adult")

# ==========================================
# MODÜL 6: ÇOCUK PLANLAMA
# ==========================================
elif menu == "👶 Çocuk Planlama":
    st.header("👶 Çocuk Hesaplama & Planlama")
    
    with st.expander("1. Gelişim & Enerji (Schofield)", expanded=True):
        c1, c2, c3 = st.columns(3)
        cy = c1.number_input("Yaş", 1, 18, 7)
        ck = c2.number_input("Kilo", 20.0)
        cc = c3.selectbox("Cinsiyet ", ["Erkek", "Kız"])
        
        c_bmh = 0
        if cy <= 3: c_bmh = (60.9 * ck) - 54 if cc == "Erkek" else (61 * ck) - 51
        elif 3 < cy <= 10: c_bmh = (22.7 * ck) + 495 if cc == "Erkek" else (22.5 * ck) + 499
        else: c_bmh = (17.5 * ck) + 651 if cc == "Erkek" else (12.2 * ck) + 746
        
        st.markdown(f'<div class="info-box"><h3>Hedef Enerji: {int(c_bmh)} kcal</h3><p>(Bazal Metabolizma)</p></div>', unsafe_allow_html=True)
    
    st.subheader("2. Değişim Planlama")
    calculate_exchange_ui("child")

# ==========================================
# MODÜL 7: OTOMATİK DİYET MOTORU (GELİŞMİŞ)
# ==========================================
elif menu == "🤖 Otomatik Diyet Motoru":
    st.header("🤖 Akıllı Menü Oluşturucu")
    
    c_in, c_out = st.columns([1, 2])
    
    with c_in:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.subheader("⚙️ Ayarlar")
        target = st.number_input("Hedef Kalori (kcal)", 1200, 4000, 1800, step=100)
        pref = st.radio("Tercih", ["Standart", "Vejetaryen", "Yüksek Protein"])
        
        if st.button("✨ Menüyü Oluştur"):
            # FİLTRELEME MANTIĞI
            f_ana = auto_db["ana_yemek"]
            f_kah = auto_db["kahvalti"]
            
            if pref == "Vejetaryen":
                f_ana = [x for x in auto_db["ana_yemek"] if x.get("tag") == "veg"]
                f_kah = [x for x in auto_db["kahvalti"] if "Sucuk" not in x["name"]]
            elif pref == "Yüksek Protein":
                f_ana = [x for x in auto_db["ana_yemek"] if x.get("tag") in ["high_pro", "std"]]
                
            if not f_ana: f_ana = auto_db["ana_yemek"] # Fallback
            
            daily_menu = {"Sabah": [], "Öğle": [], "Ara": [], "Akşam": []}
            total_stats = {"cal": 0, "p": 0, "c": 0, "f": 0}
            
            k1 = random.choice(f_kah); k2 = random.choice(auto_db["ekmek"])
            daily_menu["Sabah"].extend([k1, k2])
            
            o1 = random.choice(f_ana); o2 = random.choice(auto_db["yan_yemek"])
            daily_menu["Öğle"].extend([o1, o2])
            
            a1 = random.choice(auto_db["ara"])
            daily_menu["Ara"].extend([a1])
            
            ak1 = random.choice([x for x in f_ana if x != o1]); ak2 = random.choice(auto_db["yan_yemek"])
            daily_menu["Akşam"].extend([ak1, ak2])
            
            text_list = []
            for meal, items in daily_menu.items():
                for item in items:
                    total_stats["cal"] += item["cal"]; total_stats["p"] += item["p"]
                    total_stats["c"] += item["c"]; total_stats["f"] += item["f"]
                    text_list.append(f"{meal}: {item['name']}")
            
            st.session_state['generated_menu'] = daily_menu
            st.session_state['generated_stats'] = total_stats
            st.session_state['text_list'] = "\n".join(text_list)
        st.markdown('</div>', unsafe_allow_html=True)

    with c_out:
        if 'generated_menu' in st.session_state:
            menu_data = st.session_state['generated_menu']
            stats = st.session_state['generated_stats']
            
            st.markdown(f"""
            <div class="dashboard-card" style="text-align:center; border-left:5px solid #27ae60;">
                <h2>🔥 {int(stats['cal'])} kcal</h2>
                <div style="display:flex; justify-content:space-around; margin-top:10px;">
                    <span>🥩 P: {int(stats['p'])}g</span><span>🍞 K: {int(stats['c'])}g</span><span>🥑 Y: {int(stats['f'])}g</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            c_list, c_pie = st.columns([3, 2])
            with c_list:
                for meal, items in menu_data.items():
                    st.markdown(f"**{meal.upper()}**")
                    for item in items:
                        st.markdown(f"- {item['name']} *({item['cal']} kcal)*")
                    st.markdown("---")
            
            with c_pie:
                df_pie = pd.DataFrame({'Makro': ['Protein', 'Karbonhidrat', 'Yağ'], 'Kalori': [stats['p']*4, stats['c']*4, stats['f']*9]})
                fig = px.pie(df_pie, values='Kalori', names='Makro', hole=0.4, template="plotly_dark", color_discrete_sequence=['#e74c3c', '#3498db', '#f1c40f'])
                fig.update_traces(textinfo='percent+label', hovertemplate='%{label}: %{value:.0f} kcal')
                fig.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=250)
                st.plotly_chart(fig, use_container_width=True)
                
                st.download_button("📄 İndir (TXT)", st.session_state['text_list'], file_name=f"Diyet_{date.today()}.txt")
                
                save_name = st.text_input("Kaydet (İsim)", value=f"Oto {int(stats['cal'])}kcal")
                if st.button("💾 Listelere Ekle"):
                    db['manuel_listeler'][save_name] = st.session_state['text_list']
                    save_db(db); st.success("Kaydedildi!")

# ==========================================
# MODÜL 8: LAB ANALİZİ
# ==========================================
elif menu == "🩸 Lab Analizi":
    st.header("🩸 Kapsamlı Laboratuvar Analizi")
    
    def check(l, v, min_v, max_v, u, lo, hi):
        if v > 0:
            if v < min_v: st.error(f"📉 {l} DÜŞÜK ({v} {u})"); st.info(f"💡 {lo}")
            elif v > max_v: st.error(f"📈 {l} YÜKSEK ({v} {u})"); st.info(f"💡 {hi}")
            else: st.success(f"✅ {l} NORMAL")

    t1, t2, t3, t4, t5 = st.tabs(["Hemogram", "Biyokimya", "Hormon", "Lipid", "Elektrolit"])
    with t1:
        c1, c2 = st.columns(2)
        check("WBC", c1.number_input("WBC", 0.0), 4, 10, "K/uL", "Bağışıklık düşük.", "Enfeksiyon riski.")
        check("HGB", c2.number_input("HGB", 0.0), 12, 16, "g/dL", "Demir eksikliği.", "Sıvı alımını artır.")
        check("CRP", c1.number_input("CRP", 0.0), 0, 5, "mg/L", "", "Vücutta enfeksiyon/yangı.")
    with t2:
        c1, c2 = st.columns(2)
        check("Açlık Şekeri", c1.number_input("Glikoz", 0.0), 70, 100, "mg/dL", "Hipoglisemi.", "Diyabet riski.")
        check("Kreatinin", c2.number_input("Kreatinin", 0.0), 0.6, 1.1, "mg/dL", "Kas erimesi.", "Böbrek yükü.")
        check("AST", c1.number_input("AST", 0.0), 0, 35, "U/L", "", "Karaciğer hasarı.")
        check("ALT", c2.number_input("ALT", 0.0), 0, 35, "U/L", "", "Karaciğer yağlanması.")
    with t3:
        c1, c2 = st.columns(2)
        check("TSH", c1.number_input("TSH", 0.0), 0.4, 4.0, "mU/L", "Hipertiroidi.", "Hipotiroidi.")
        check("B12", c2.number_input("B12", 0.0), 200, 900, "pg/mL", "Eksiklik.", "")
        check("D Vit", c1.number_input("D Vit", 0.0), 30, 100, "ng/mL", "Takviye al.", "Toksik.")
    with t4:
        c1, c2 = st.columns(2)
        check("LDL", c1.number_input("LDL", 0.0), 0, 130, "mg/dL", "", "Riskli.")
        check("Trigliserid", c2.number_input("Trigliserid", 0.0), 0, 150, "mg/dL", "", "Şekeri kes.")
    with t5:
        c1, c2 = st.columns(2)
        check("Sodyum", c1.number_input("Na", 0.0), 135, 145, "mEq/L", "Hiponatremi.", "Hipernatremi.")
        check("Potasyum", c2.number_input("K", 0.0), 3.5, 5.1, "mEq/L", "Hipokalemi.", "Hiperkalemi.")
        check("Kalsiyum", c1.number_input("Ca", 0.0), 8.5, 10.5, "mg/dL", "Kemik erimesi.", "Hiperkalsemi.")

# ==========================================
# MODÜL 9: DİYET & HAZIR LİSTELER
# ==========================================
elif menu == "🍏 Diyet & Hazır Listeler":
    st.header("🍏 Diyet Planla & Yönet")
    tab_sablon, tab_akilli = st.tabs(["📚 Hazır Şablonlar", "🤖 Manuel Besin Seç"])
    
    with tab_sablon:
        st.markdown('<div class="info-box"><h3>📚 Düzenlenebilir Şablonlar</h3><p>Literatür destekli hazır listeler.</p></div>', unsafe_allow_html=True)
        templates = db.get('manuel_listeler', {})
        secilen = st.selectbox("Şablon Seç", list(templates.keys()))
        icerik = st.text_area("İçerik (Düzenle)", value=templates[secilen], height=400)
        
        c1, c2 = st.columns(2)
        with c1:
            yeni_ad = st.text_input("Farklı Kaydet İsim")
        with c2:
            st.write(""); st.write("")
            if st.button("💾 Yeni Liste Olarak Kaydet"):
                if yeni_ad: db['manuel_listeler'][yeni_ad] = icerik; save_db(db); st.success("Kaydedildi!"); st.rerun()
            if st.button("✏️ Mevcut Şablonu Güncelle"):
                 db['manuel_listeler'][secilen] = icerik; save_db(db); st.success("Güncellendi!")

    with tab_akilli:
        if 'menu_t' not in st.session_state: st.session_state['menu_t'] = []
        besin = st.selectbox("Besin", df_foods["Besin Adı"])
        gr = st.number_input("Gr", 100)
        if st.button("Ekle"):
            it = df_foods[df_foods["Besin Adı"]==besin].iloc[0]
            st.session_state['menu_t'].append({"Besin": besin, "Gr": gr, "Kal": int(it["Kalori"]*gr/100)})
        if st.session_state['menu_t']:
            df_m = pd.DataFrame(st.session_state['menu_t'])
            st.dataframe(df_m, use_container_width=True)
            st.metric("Toplam", f"{df_m['Kal'].sum()} kcal")

# ==========================================
# MODÜL 10: EGZERSİZ
# ==========================================
elif menu == "🏋️ Egzersiz Kütüphanesi":
    st.header("🏋️ Geniş Egzersiz Kütüphanesi")
    bolge = st.selectbox("Bölge Seç", list(egzersizler.keys()))
    
    for ex in egzersizler[bolge]:
        with st.expander(f"📌 {ex['name']}"):
            st.markdown(f"**Yapılış:** {ex['desc']}")
            st.info(f"**Set:** {ex['set']}")
