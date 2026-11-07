"""U.C. GUARD - Kivy (Android + PC) surumu.

Orijinal Tkinter uygulamasinin Kivy'ye tasinmis halidir.
Android'de Tkinter olmadigi icin eski surum acilir acilmaz kapaniyordu.
"""
import base64
import hashlib
import json
import os
import random
import smtplib
import threading
import time
from email.mime.text import MIMEText

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.utils import get_color_from_hex as hx, platform

# ---------------------------------------------------------------- AYARLAR
GENDEREN_EPOSTA = "umutyas5234oygur@gmail.com"
# DIKKAT: Eski sifre GitHub'da acik kaldi, IPTAL ET ve yenisini olustur.
# Yeni Gmail "uygulama sifresini" buraya yaz (APK icinden okunabilir, bunu unutma).
UYGULAMA_SIFRESI = "sirk mnsy qeqf ozrn"

CONFIG_FILE = "uc_guard_config.json"
LOG_FILE = "uc_guard_audit.log"
IMZA = b"UC_GUARD_SECURE_VAULT_OK|"

BG = hx("#040507")
PANEL = hx("#0b0e14")
FIELD = hx("#111522")
CYAN = hx("#00ffcc")
GREY = hx("#8892b0")
WHITE = (1, 1, 1, 1)

Window.clearcolor = BG


# ---------------------------------------------------------------- UI YARDIMCILARI
class WrapLabel(Label):
    """Metne gore yuksekligi otomatik ayarlanan etiket."""

    def __init__(self, **kw):
        kw.setdefault("size_hint_y", None)
        super().__init__(**kw)
        self.bind(width=lambda *a: setattr(self, "text_size", (self.width, None)))
        self.bind(texture_size=lambda *a: setattr(self, "height", self.texture_size[1] + dp(6)))


def lbl(text, size=15, color=WHITE, bold=False, halign="center"):
    return WrapLabel(text=text, font_size=dp(size), color=color, bold=bold, halign=halign)


def btn(text, cb, color="#0b0e14", fg=WHITE, h=48):
    b = Button(
        text=text,
        size_hint_y=None,
        height=dp(h),
        background_normal="",
        background_color=hx(color),
        color=fg,
        bold=True,
        font_size=dp(14),
    )
    b.bind(on_release=lambda *a: cb())
    return b


def entry(text="", hint="", password=False, h=46):
    return TextInput(
        text=text,
        hint_text=hint,
        password=password,
        multiline=False,
        size_hint_y=None,
        height=dp(h),
        background_color=FIELD,
        foreground_color=WHITE,
        cursor_color=WHITE,
        hint_text_color=GREY,
        padding=[dp(10), dp(12)],
        font_size=dp(15),
    )


def textbox(text="", h=200, readonly=True, color=CYAN):
    return TextInput(
        text=text,
        readonly=readonly,
        multiline=True,
        size_hint_y=None,
        height=dp(h),
        background_color=PANEL,
        foreground_color=color,
        font_size=dp(13),
    )


def popup(title, msg):
    box = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
    box.add_widget(WrapLabel(text=msg, halign="center", font_size=dp(14)))
    p = Popup(title=title, content=box, size_hint=(0.88, None), height=dp(240), auto_dismiss=True)
    box.add_widget(btn("Tamam", p.dismiss, "#00b4d8", h=42))
    p.open()


# ---------------------------------------------------------------- UYGULAMA
class UCGuardApp(App):
    title = "U.C. GUARD"

    def build(self):
        self.kullanici_adi = ""
        self.eposta = ""
        self.gonderilen_kod = None
        self.kod_zaman = 0
        self.dil = "TR"
        self.hatirla = True
        self.sayac = None
        self.zamanlayicilar = []
        self.aktif_ekran = self.giris_ekrani

        self.root_box = BoxLayout()
        self.izin_iste()
        return self.root_box

    def on_start(self):
        self.kayitli_veriyi_yukle()
        if self.hatirlandi:
            self.ana_menu()
        else:
            self.giris_ekrani()

    # ---- dosya yollari / izin / dil
    def yol(self, ad):
        return os.path.join(self.user_data_dir, ad)

    def izin_iste(self):
        if platform != "android":
            return
        try:
            from android.permissions import Permission, request_permissions

            request_permissions(
                [Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE]
            )
        except Exception:
            pass

    def t(self, tr, en):
        return tr if self.dil == "TR" else en

    def dil_degistir(self):
        self.dil = "EN" if self.dil == "TR" else "TR"
        self.aktif_ekran()

    # ---- kalici veri
    def kayitli_veriyi_yukle(self):
        self.hatirlandi = False
        try:
            if os.path.exists(self.yol(CONFIG_FILE)):
                with open(self.yol(CONFIG_FILE), "r", encoding="utf-8") as f:
                    d = json.load(f)
                self.kullanici_adi = d.get("kullanici_adi", "")
                self.eposta = d.get("eposta", "")
                self.hatirlandi = bool(self.kullanici_adi and self.eposta)
        except Exception:
            pass

    def kayitli_veriyi_kaydet(self, hatirla):
        try:
            if hatirla:
                with open(self.yol(CONFIG_FILE), "w", encoding="utf-8") as f:
                    json.dump({"kullanici_adi": self.kullanici_adi, "eposta": self.eposta}, f)
            elif os.path.exists(self.yol(CONFIG_FILE)):
                os.remove(self.yol(CONFIG_FILE))
        except Exception:
            pass

    def log_yaz(self, mesaj):
        try:
            with open(self.yol(LOG_FILE), "a", encoding="utf-8") as f:
                f.write("[%s] %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), mesaj))
        except Exception:
            pass

    # ---- sifreleme (orijinal algoritma aynen korundu)
    def anahtar_uret(self, pin, salt):
        return hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, 150000, dklen=32)

    def xor_coz(self, veri, anahtar):
        uzun = bytearray()
        while len(uzun) < len(veri):
            uzun.extend(hashlib.sha256(anahtar + bytes([len(uzun) % 256])).digest())
        return bytes(v ^ k for v, k in zip(veri, uzun))

    def dosyayi_sifrele(self, yol, pin):
        salt = os.urandom(16)
        anahtar = self.anahtar_uret(pin, salt)
        with open(yol, "rb") as f:
            veri = f.read()
        sifreli = self.xor_coz(IMZA + veri, anahtar)
        with open(yol + ".enc", "wb") as f:
            f.write(salt + sifreli)
        self.log_yaz("Guvenli Dosya Kilitlendi: " + os.path.basename(yol))

    def dosyayi_coz(self, yol, pin):
        with open(yol, "rb") as f:
            icerik = f.read()
        salt, sifreli = icerik[:16], icerik[16:]
        cozulmus = self.xor_coz(sifreli, self.anahtar_uret(pin, salt))
        if not cozulmus.startswith(IMZA):
            raise ValueError("Gecersiz sifre veya bozuk dosya")
        hedef = yol[:-4] if yol.endswith(".enc") else yol + ".cozulmus"
        with open(hedef, "wb") as f:
            f.write(cozulmus[len(IMZA):])
        self.log_yaz("Guvenli Dosya Acildi: " + os.path.basename(yol))

    # ---- e-posta (ayri thread, arayuz donmasin)
    def email_gonder(self, to, konu, icerik, callback):
        def is_parcacigi():
            ok = False
            try:
                msg = MIMEText(icerik)
                msg["Subject"] = konu
                msg["From"] = GENDEREN_EPOSTA
                msg["To"] = to
                with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as s:
                    s.login(GENDEREN_EPOSTA, UYGULAMA_SIFRESI)
                    s.send_message(msg)
                ok = True
                self.log_yaz("E-posta iletimi basarili: " + to)
            except Exception as e:
                print("E-posta hata:", e)
            Clock.schedule_once(lambda dt: callback(ok), 0)

        threading.Thread(target=is_parcacigi, daemon=True).start()

    # ---- ekran iskeleti
    def temizle(self):
        if self.sayac is not None:
            self.sayac.cancel()
            self.sayac = None
        for z in self.zamanlayicilar:
            z.cancel()
        self.zamanlayicilar = []
        self.root_box.clear_widgets()

    def sayfa(self, baslik=None, renk=CYAN, geri=True):
        """Kaydirilabilir bos sayfa dondurur; icerik 'col'a eklenir."""
        self.temizle()
        sv = ScrollView(do_scroll_x=False)
        col = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            padding=[dp(18), dp(24), dp(18), dp(24)],
            spacing=dp(10),
        )
        col.bind(minimum_height=col.setter("height"))
        sv.add_widget(col)
        self.root_box.add_widget(sv)
        if baslik:
            col.add_widget(lbl(baslik, 20, renk, True))
        self._geri_ekle = geri
        return col

    def geri_butonu(self, col, text=None):
        col.add_widget(btn(text or self.t("Ana Menuye Don", "Back to Menu"), self.ana_menu, "#1c0f14", hx("#ff9aa2")))

    def dil_butonu(self, col):
        col.add_widget(btn(self.t("English", "Turkce"), self.dil_degistir, "#0b0e14", CYAN, h=38))

    # ================================================================ 1. GIRIS
    def giris_ekrani(self):
        self.aktif_ekran = self.giris_ekrani
        col = self.sayfa()
        self.dil_butonu(col)
        col.add_widget(lbl("U.C. GUARD", 30, CYAN, True))
        col.add_widget(lbl(self.t("Yapay Zeka Destekli Siber Komuta Platformu", "AI-Powered Cyber Command Suite"), 13, GREY))
        col.add_widget(lbl(self.t("Operator Adi:", "Operator Username:"), 14, WHITE, True, "left"))
        self.txt_kullanici = entry(self.kullanici_adi)
        col.add_widget(self.txt_kullanici)
        col.add_widget(lbl(self.t("Kurumsal E-posta:", "Enterprise Email:"), 14, WHITE, True, "left"))
        self.txt_eposta = entry(self.eposta)
        col.add_widget(self.txt_eposta)

        self.hatirla = bool(self.kullanici_adi) or self.hatirla

        def hatirla_metni():
            return self.t("Oturumu Hatirla: ACIK", "Remember Me: ON") if self.hatirla else self.t("Oturumu Hatirla: KAPALI", "Remember Me: OFF")

        def degistir():
            self.hatirla = not self.hatirla
            b.text = hatirla_metni()

        b = btn(hatirla_metni(), degistir, "#111522", GREY, h=40)
        col.add_widget(b)
        self.btn_kod = btn(self.t("OTP Dogrulama Kodu Gonder (3 Dk)", "Send OTP Code (3 Min)"), self.kod_gonder, "#00b4d8", h=52)
        col.add_widget(self.btn_kod)

    def kod_gonder(self):
        self.kullanici_adi = self.txt_kullanici.text.strip()
        self.eposta = self.txt_eposta.text.strip()
        if not self.kullanici_adi or not self.eposta:
            popup("Hata", "Lutfen tum kimlik alanlarini doldurun!")
            return
        self.gonderilen_kod = "".join(str(random.randint(0, 9)) for _ in range(6))
        self.kod_zaman = time.time()
        icerik = "Sayin %s,\n\nGiris OTP Kodunuz: %s\nSure: 3 Dakika." % (self.kullanici_adi, self.gonderilen_kod)
        self.btn_kod.disabled = True
        self.btn_kod.text = self.t("Gonderiliyor...", "Sending...")

        def bitti(ok):
            if ok:
                popup("Basarili", "Dogrulama kodu %s adresine gonderildi." % self.eposta)
                self.dogrulama_ekrani()
            else:
                self.btn_kod.disabled = False
                self.btn_kod.text = self.t("OTP Dogrulama Kodu Gonder (3 Dk)", "Send OTP Code (3 Min)")
                popup("Hata", "E-posta sunucusuna baglanilamadi!\n(Internet ve uygulama sifresini kontrol et)")

        self.email_gonder(self.eposta, "U.C. GUARD - Komuta Merkezi Oturum Dogrulama", icerik, bitti)

    # ================================================================ 2. DOGRULAMA
    def dogrulama_ekrani(self):
        self.aktif_ekran = self.dogrulama_ekrani
        col = self.sayfa("Iki Asamali Guvenlik (2FA)")
        col.add_widget(lbl("E-postaniza gelen 6 haneli kodu giriniz:", 13, GREY))
        self.lbl_sayac = lbl("", 16, hx("#ff6b6b"), True)
        col.add_widget(self.lbl_sayac)
        self.txt_kod = entry("", "000000", h=54)
        self.txt_kod.input_filter = "int"
        self.txt_kod.halign = "center"
        col.add_widget(self.txt_kod)
        col.add_widget(btn("Komuta Merkezine Baglan", self.kodu_dogrula, "#06d6a0", h=52))
        col.add_widget(btn("Geri", self.giris_ekrani, "#1c0f14", hx("#ff9aa2")))
        self.kalan = 180
        self.sayac_guncelle(0)
        self.sayac = Clock.schedule_interval(self.sayac_guncelle, 1)

    def sayac_guncelle(self, dt):
        if self.kalan > 0:
            self.lbl_sayac.text = "Kalan Sure: %02d:%02d" % (self.kalan // 60, self.kalan % 60)
            self.kalan -= 1
        else:
            self.lbl_sayac.text = "Kodun suresi doldu!"
            self.gonderilen_kod = None
            if self.sayac is not None:
                self.sayac.cancel()
                self.sayac = None

    def kodu_dogrula(self):
        girilen = self.txt_kod.text.strip()
        if time.time() - self.kod_zaman > 180 or not self.gonderilen_kod:
            popup("Sure Doldu", "Dogrulama suresi bitti. Yeni kod talep edin.")
            self.giris_ekrani()
            return
        if girilen == self.gonderilen_kod:
            self.kayitli_veriyi_kaydet(self.hatirla)
            self.ana_menu()
        else:
            popup("Hata", "Hatali dogrulama kodu girdiniz.")

    # ================================================================ 3. ANA MENU
    def ana_menu(self):
        self.aktif_ekran = self.ana_menu
        col = self.sayfa()
        self.dil_butonu(col)
        col.add_widget(lbl("Hos Geldin Operator, %s" % self.kullanici_adi, 18, WHITE, True))
        col.add_widget(lbl("Kurumsal Kriptografi, Paket Analizi & Siber Savunma Ussu", 11, CYAN))
        for text, cmd, renk in [
            ("Gelismis AES Dosya Koru & Sifrele", self.ekran_dosya_sifrele, "#0b0e14"),
            ("Sifreli Dosyayi Guvenle Coz", self.ekran_dosya_coz, "#0b0e14"),
            ("E-posta ile Sifreli Veri Ilet", self.ekran_mesaj_sifrele, "#0b0e14"),
            ("Gelen Sifreli Veriyi Oku", self.ekran_mesaj_coz, "#0b0e14"),
            ("Canli Ag Paket Analizoru", self.ekran_sniffer, "#480ca8"),
            ("Hash Analizoru & Brute-Force Simulatoru", self.ekran_hash, "#3a0ca3"),
            ("Interactive Command Terminal", self.ekran_terminal, "#2b2d42"),
            ("Guvenli Sifre Ureticisi", self.ekran_sifre_uretici, "#0077b6"),
            ("2D Cyber Defense Mini Oyun", self.ekran_oyun, "#d90429"),
            ("Siber Guvenlik Bilgi Yarismasi (10 Soru)", self.ekran_quiz, "#1d3557"),
            ("Sistem Denetim Loglari (Audit Trail)", self.ekran_loglar, "#7209b7"),
            ("Kurumsal Kullanma Kilavuzu", self.ekran_kilavuz, "#3a86ff"),
        ]:
            col.add_widget(btn(text, cmd, renk))
        col.add_widget(btn("Oturumu Kapat", self.oturumu_kapat, "#1c0f14", hx("#ff6b6b")))

    def oturumu_kapat(self):
        self.kayitli_veriyi_kaydet(False)
        self.kullanici_adi = ""
        self.eposta = ""
        self.giris_ekrani()

    # ================================================================ 4. SNIFFER
    def ekran_sniffer(self):
        self.aktif_ekran = self.ekran_sniffer
        col = self.sayfa("Ag Paket Analizoru & Trafik Simulatoru", hx("#b388ff"))
        kutu = textbox("", 280)
        col.add_widget(kutu)
        paketler = [
            "[TCP] 192.168.1.15:54321 -> 142.250.185.46:443 [SYN] Guvenli Baglanti",
            "[UDP] 10.0.0.4:53 -> 8.8.8.8:53 [DNS] Sorgu: ucguard.security.net",
            "[ICMP] 192.168.1.1 -> 192.168.1.50 Echo Request (Ping)",
            "[TCP] 172.16.0.4:80 -> 192.168.1.15:49152 [ACK] Veri Akisi Aktif",
            "[ALERT] Bilinmeyen IP adresinden supheli port tarama girisimi engellendi!",
        ]

        def baslat():
            kutu.text = "Ag arabirimi dinleniyor...\n"
            sira = iter(paketler)

            def adim(dt):
                try:
                    kutu.text += next(sira) + "\n"
                except StopIteration:
                    self.log_yaz("Ag paket analizi gerceklestirildi.")
                    return False

            self.zamanlayicilar.append(Clock.schedule_interval(adim, 0.4))

        col.add_widget(btn("Trafik Dinlemeyi Baslat", baslat, "#480ca8"))
        self.geri_butonu(col)

    # ================================================================ 5. HASH
    def ekran_hash(self):
        self.aktif_ekran = self.ekran_hash
        col = self.sayfa("Hash Analizoru & Sozluk Saldiri Simulatoru", hx("#b388ff"))
        col.add_widget(lbl("Test Edilecek Metin veya Sifre:", 13, GREY, True, "left"))
        girdi = entry("admin123")
        col.add_widget(girdi)
        sonuc = textbox("", 220)
        col.add_widget(sonuc)

        def analiz():
            v = girdi.text.strip()
            if not v:
                return
            sonuc.text = (
                "[+] MD5 Hash: %s\n[+] SHA-256 Hash: %s\n"
                "[+] Sozluk taramasi: Zayif parola tespit edildi! Kirilabilirlik: Yuksek.\n"
                % (hashlib.md5(v.encode()).hexdigest(), hashlib.sha256(v.encode()).hexdigest())
            )
            self.log_yaz("Hash analizi yapildi.")

        col.add_widget(btn("Hash Hesapla & Analiz Et", analiz, "#3a0ca3"))
        self.geri_butonu(col)

    # ================================================================ 6. TERMINAL
    def ekran_terminal(self):
        self.aktif_ekran = self.ekran_terminal
        col = self.sayfa("U.C. GUARD Interactive Command Terminal")
        konsol = textbox("U.C. GUARD Secure Terminal v4.1\nKomut listesi icin 'help' yazin.\n\nroot@ucguard:~# ", 260)
        col.add_widget(konsol)
        komut = entry("", "komut...")
        col.add_widget(komut)

        def calistir(*a):
            cmd = komut.text.strip().lower()
            komut.text = ""
            konsol.text += cmd + "\n"
            if cmd == "help":
                konsol.text += "Komutlar: status, clear, encrypt, scan, exit\n"
            elif cmd == "status":
                konsol.text += "[OK] Sistem guvenli, duvar (Firewall) aktif.\n"
            elif cmd == "clear":
                konsol.text = ""
            elif cmd == "scan":
                konsol.text += "[+] Yerel ag tarandi: Hicbir zafiyet bulunamadi.\n"
            elif cmd == "exit":
                self.ana_menu()
                return
            else:
                konsol.text += "Bilinmeyen komut: %s. 'help' yazabilirsiniz.\n" % cmd
            konsol.text += "root@ucguard:~# "

        komut.bind(on_text_validate=calistir)
        col.add_widget(btn("Calistir", calistir, "#00b4d8"))
        self.geri_butonu(col)

    # ================================================================ 7. SIFRE URETICI
    def ekran_sifre_uretici(self):
        self.aktif_ekran = self.ekran_sifre_uretici
        col = self.sayfa("Guvenli Sifre Uretici & Analiz")
        gosterge = entry("", "", h=54)
        gosterge.halign = "center"
        col.add_widget(gosterge)
        durum = lbl("", 14, hx("#06d6a0"), True)
        col.add_widget(durum)

        def uret():
            k = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
            rnd = random.SystemRandom()
            gosterge.text = "".join(rnd.choice(k) for _ in range(16))
            durum.text = "Guc Duzeyi: Mukemmel (16 Haneli Karisik)"
            self.log_yaz("Guvenli sifre uretildi.")

        col.add_widget(btn("Guclu Sifre Uret", uret, "#06d6a0"))
        self.geri_butonu(col)

    # ================================================================ 8. OYUN
    def ekran_oyun(self):
        self.aktif_ekran = self.ekran_oyun
        col = self.sayfa("2D Cyber Defender - Tehdit Avcisi", hx("#ff4757"))
        durum = lbl("Puan: 0 | Can: 3", 16, CYAN, True)
        col.add_widget(durum)
        alan = FloatLayout(size_hint_y=None, height=dp(320))
        col.add_widget(alan)
        s = {"puan": 0, "can": 3, "aktif": False, "hedef": None, "zaman": None}

        def guncelle():
            durum.text = "Puan: %d | Can: %d" % (s["puan"], s["can"])

        def kacirildi(dt):
            if not s["aktif"]:
                return
            s["can"] -= 1
            guncelle()
            if s["can"] <= 0:
                s["aktif"] = False
                alan.clear_widgets()
                durum.text = "Oyun bitti! Puan: %d" % s["puan"]
                self.log_yaz("Oyun bitti. Puan: %d" % s["puan"])
                return
            yeni()

        def yeni():
            alan.clear_widgets()
            if s["zaman"]:
                s["zaman"].cancel()
            hedef = Button(
                text="VIRUS",
                size_hint=(None, None),
                size=(dp(100), dp(56)),
                pos_hint={"x": random.uniform(0.02, 0.7), "y": random.uniform(0.02, 0.85)},
                background_normal="",
                background_color=hx("#d90429"),
                bold=True,
            )
            hedef.bind(on_release=lambda *a: vuruldu())
            alan.add_widget(hedef)
            s["zaman"] = Clock.schedule_once(kacirildi, 1.6)
            self.zamanlayicilar.append(s["zaman"])

        def vuruldu():
            if not s["aktif"]:
                return
            s["puan"] += 10
            guncelle()
            yeni()

        def baslat():
            s.update(puan=0, can=3, aktif=True)
            guncelle()
            yeni()

        col.add_widget(btn("Oyunu Baslat", baslat, "#06d6a0"))
        self.geri_butonu(col)

    # ================================================================ 9. QUIZ
    SORULAR = [
        ("1. Guclu sifre seciminde asagidakilerden hangisi dogrudur?", ["A) 123456", "B) Dogum tarihi", "C) Karisik karakter ve semboller", "D) Isim"], 2),
        ("2. Oltalama (Phishing) saldirilari en yaygin hangi kanal uzerinden yapilir?", ["A) E-posta", "B) USB Bellek", "C) Hesap Makinesi", "D) Ekran Karti"], 0),
        ("3. Iki Asamali Dogrulama (2FA) sistemi ne saglar?", ["A) Hiz", "B) Ekstra guvenlik katmani", "C) Kota tasarrufu", "D) Ses kalitesi"], 1),
        ("4. Verilerin gizlenmesi ve sifrelenmesi bilimine ne ad verilir?", ["A) Kriptoloji", "B) Grafik", "C) Animasyon", "D) Donanim"], 0),
        ("5. Internetten indirilen guvenilmez dosyalarda ne riski vardir?", ["A) Hizlanma", "B) Malware / Virus", "C) Optimizasyon", "D) Temizlik"], 1),
        ("6. Sifresiz ortak Wi-Fi aglarinda guvenligi artirmak icin ne kullanilir?", ["A) VPN", "B) Bluetooth", "C) Ucak Modu", "D) Ses"], 0),
        ("7. Isletim sistemi guncellemeleri neden yapilmalidir?", ["A) Sarji bitirmek", "B) Guvenlik aciklarini kapatmak", "C) Duvar kagidi", "D) Tasarim"], 1),
        ("8. Guvenli web sitelerinin adres cubugunda ne bulunur?", ["A) Kilit simgesi", "B) Capi", "C) Cop Kutusu", "D) Hoparlor"], 0),
        ("9. Tanimadiginiz USB bellekleri bilgisayara takmak neye yol acabilir?", ["A) Hiz artisi", "B) Zararli yazilim bulasmasina", "C) Internet hizlanmasi", "D) Hicbiri"], 1),
        ("10. Her platformda farkli sifre kullanmanin temel sebebi nedir?", ["A) Unutmak", "B) Zincirleme hesap ele gecirilmesini onlemek", "C) Klavye asindirmak", "D) Doldurmak"], 1),
    ]

    def ekran_quiz(self):
        self.aktif_ekran = self.ekran_quiz
        self.q_index = 0
        self.q_cevap = {}
        self.quiz_goster()

    def quiz_goster(self):
        col = self.sayfa("Siber Guvenlik Bilgi Yarismasi", hx("#2e86de"))
        soru, secenekler, dogru = self.SORULAR[self.q_index]
        col.add_widget(lbl("Soru %d / %d" % (self.q_index + 1, len(self.SORULAR)), 15, CYAN, True))
        col.add_widget(lbl(soru, 15, WHITE, True))
        cevaplandi = self.q_index in self.q_cevap

        for i, sec in enumerate(secenekler):
            renk = "#0b0e14"
            if cevaplandi:
                if i == dogru:
                    renk = "#06d6a0"
                elif i == self.q_cevap[self.q_index]:
                    renk = "#ff4757"
            b = btn(sec, (lambda idx=i: self.quiz_cevap(idx)), renk, h=50)
            b.disabled = cevaplandi
            b.disabled_color = WHITE
            col.add_widget(b)

        if cevaplandi:
            ok = self.q_cevap[self.q_index] == dogru
            col.add_widget(lbl("Dogru Cevap!" if ok else "Yanlis Cevap!", 16, hx("#06d6a0") if ok else hx("#ff4757"), True))
        else:
            col.add_widget(lbl("Lutfen bir sik secin (kilitlenir).", 13, hx("#f1c40f")))

        nav = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
        onceki = btn("< Onceki", self.quiz_onceki, "#111522")
        onceki.disabled = self.q_index == 0
        nav.add_widget(onceki)
        son = self.q_index == len(self.SORULAR) - 1
        nav.add_widget(btn("Sonuclari Gor" if son else "Sonraki >", self.quiz_sonraki, "#111522"))
        col.add_widget(nav)
        self.geri_butonu(col)

    def quiz_cevap(self, idx):
        if self.q_index not in self.q_cevap:
            self.q_cevap[self.q_index] = idx
            self.quiz_goster()

    def quiz_onceki(self):
        if self.q_index > 0:
            self.q_index -= 1
            self.quiz_goster()

    def quiz_sonraki(self):
        if self.q_index < len(self.SORULAR) - 1:
            self.q_index += 1
            self.quiz_goster()
        else:
            dogru = sum(1 for i, c in self.q_cevap.items() if c == self.SORULAR[i][2])
            col = self.sayfa("SIBER FARKINDALIK TESTI SONUCU")
            col.add_widget(lbl("Dogru Sayisi: %d / 10" % dogru, 18))
            col.add_widget(lbl("Toplam Puaniniz: %d / 100" % (dogru * 10), 20, hx("#06d6a0"), True))
            self.log_yaz("Quiz bitti. Puan: %d" % (dogru * 10))
            self.geri_butonu(col)

    # ================================================================ 10. LOGLAR
    def ekran_loglar(self):
        self.aktif_ekran = self.ekran_loglar
        col = self.sayfa("Sistem Guvenlik ve Denetim Loglari")
        metin = "Henuz kayitli islem gunlugu bulunmuyor."
        try:
            if os.path.exists(self.yol(LOG_FILE)):
                with open(self.yol(LOG_FILE), "r", encoding="utf-8") as f:
                    metin = f.read() or metin
        except Exception:
            metin = "Loglar okunamadi."
        col.add_widget(textbox(metin, 340))
        self.geri_butonu(col)

    # ================================================================ 11. KILAVUZ
    def ekran_kilavuz(self):
        self.aktif_ekran = self.ekran_kilavuz
        col = self.sayfa("U.C. GUARD Kullanma Kilavuzu")
        col.add_widget(textbox(
            "- OTP Kimlik Dogrulama ve Oturum Koruma\n"
            "- PBKDF2 tabanli Guvenli Dosya Sifreleme\n"
            "- Canli Ag Paket Analizoru (Simulasyon)\n"
            "- Hash Analizoru & Brute-Force Simulatoru\n"
            "- Interaktif Komut Satiri Terminali\n"
            "- 2D Cyber Defense Mini Oyun ve Bilgi Yarismasi", 240, color=WHITE))
        self.geri_butonu(col)

    # ================================================================ DOSYA SECICI
    def dosya_sec(self, callback, filtre=None):
        baslangic = self.user_data_dir
        if platform == "android":
            try:
                from android.storage import primary_external_storage_path

                baslangic = primary_external_storage_path()
            except Exception:
                pass
        else:
            baslangic = os.path.expanduser("~")
        fc = FileChooserListView(path=baslangic, multiselect=True, filters=filtre or [])
        kutu = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        kutu.add_widget(fc)
        p = Popup(title="Dosya sec", content=kutu, size_hint=(0.96, 0.9))

        def tamam():
            callback(list(fc.selection))
            p.dismiss()

        satir = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        satir.add_widget(btn("Iptal", p.dismiss, "#1c0f14", h=44))
        satir.add_widget(btn("Sec", tamam, "#06d6a0", h=44))
        kutu.add_widget(satir)
        p.open()

    # ================================================================ 12/13. DOSYA SIFRELE / COZ
    def ekran_dosya_sifrele(self):
        self._dosya_ekrani(True)

    def ekran_dosya_coz(self):
        self._dosya_ekrani(False)

    def _dosya_ekrani(self, sifrele):
        self.aktif_ekran = self.ekran_dosya_sifrele if sifrele else self.ekran_dosya_coz
        col = self.sayfa("AES Dosya Sifreleme" if sifrele else "Sifreli Dosya Cozme")
        secilen = []
        bilgi = lbl("Dosya secilmedi.", 13, GREY)

        def secildi(liste):
            secilen[:] = liste
            bilgi.text = "Secilen dosya sayisi: %d" % len(secilen)

        col.add_widget(btn("Dosya(lar) Sec", lambda: self.dosya_sec(secildi, None if sifrele else ["*.enc"]), "#0b0e14"))
        col.add_widget(bilgi)
        col.add_widget(lbl("PIN Sifresi (4+ Hane):" if sifrele else "PIN Sifresi:", 13, GREY, True, "left"))
        pin = entry("", "PIN", password=True)
        pin.input_filter = "int"
        col.add_widget(pin)

        def islem():
            p = pin.text.strip()
            if not p.isdigit() or len(p) < 4 or not secilen:
                popup("Hata", "Gecersiz sifre veya dosya secilmedi!")
                return
            try:
                for d in secilen:
                    (self.dosyayi_sifrele if sifrele else self.dosyayi_coz)(d, p)
                popup("Basarili", "Dosyalar basariyla kilitlendi! (.enc)" if sifrele else "Dosyalar basariyla cozuldu!")
            except Exception as e:
                popup("Hata", ("Hata: %s" % e) if sifrele else "Yanlis Sifre veya Bozuk Dosya Butunlugu!")

        col.add_widget(btn("Sifrele ve Kaydet" if sifrele else "Sifreyi Coz", islem, "#06d6a0", h=52))
        self.geri_butonu(col)

    # ================================================================ 14. MESAJ SIFRELE
    def ekran_mesaj_sifrele(self):
        self.aktif_ekran = self.ekran_mesaj_sifrele
        col = self.sayfa("E-posta ile Sifreli Mesaj")
        col.add_widget(lbl("Alici E-posta:", 13, GREY, True, "left"))
        alici = entry("", "ornek@mail.com")
        col.add_widget(alici)
        col.add_widget(lbl("Gizli Mesaj:", 13, GREY, True, "left"))
        mesaj = textbox("", 120, readonly=False, color=WHITE)
        col.add_widget(mesaj)
        col.add_widget(lbl("PIN Sifresi:", 13, GREY, True, "left"))
        pin = entry("", "PIN", password=True)
        pin.input_filter = "int"
        col.add_widget(pin)

        def gonder():
            a, m, p = alici.text.strip(), mesaj.text.strip(), pin.text.strip()
            if not a or not m or not p.isdigit() or len(p) < 4:
                popup("Hata", "Tum alanlari doldurun!")
                return
            salt = os.urandom(16)
            sifreli = self.xor_coz(m.encode("utf-8"), self.anahtar_uret(p, salt))
            kod = base64.b64encode(salt + sifreli).decode("utf-8")

            def bitti(ok):
                popup("Basarili" if ok else "Hata", ("Mesaj %s adresine gonderildi." % a) if ok else "E-posta gonderilemedi!")

            self.email_gonder(a, "U.C. GUARD - Sifreli Mesaj", "U.C. GUARD SIFRELI MESAJ:\n\n" + kod, bitti)

        col.add_widget(btn("Sifrele ve Gonder", gonder, "#06d6a0", h=52))
        self.geri_butonu(col)

    # ================================================================ 15. MESAJ COZ
    def ekran_mesaj_coz(self):
        self.aktif_ekran = self.ekran_mesaj_coz
        col = self.sayfa("Sifreli Mesaji Coz")
        col.add_widget(lbl("Sifreli Metin (Base64):", 13, GREY, True, "left"))
        sifreli = textbox("", 120, readonly=False, color=WHITE)
        col.add_widget(sifreli)
        col.add_widget(lbl("PIN Sifresi:", 13, GREY, True, "left"))
        pin = entry("", "PIN", password=True)
        pin.input_filter = "int"
        col.add_widget(pin)
        cozulen = textbox("", 120)

        def coz():
            s, p = sifreli.text.strip(), pin.text.strip()
            if not s or not p.isdigit() or len(p) < 4:
                popup("Hata", "Eksik bilgi!")
                return
            try:
                ham = base64.b64decode(s.encode("utf-8"))
                cozuk = self.xor_coz(ham[16:], self.anahtar_uret(p, ham[:16]))
                cozulen.text = "Mesaj: " + cozuk.decode("utf-8")
                if cozulen.parent is None:
                    col.add_widget(cozulen, index=1)
            except Exception:
                popup("Hata", "Cozulemedi! Sifre yanlis.")

        col.add_widget(btn("Mesaji Coz ve Oku", coz, "#06d6a0", h=52))
        self.geri_butonu(col)


class HataApp(App):
    """Uygulama cokerse hatayi ekranda gosterir (log aramaya gerek kalmasin)."""

    def __init__(self, metin, **kw):
        super().__init__(**kw)
        self.metin = metin

    def build(self):
        kutu = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
        kutu.add_widget(Label(text="U.C. GUARD hata verdi. Bu ekranin goruntusunu gonder:", size_hint_y=None, height=dp(40)))
        kutu.add_widget(TextInput(text=self.metin, readonly=True, font_size=dp(11)))
        return kutu


if __name__ == "__main__":
    try:
        UCGuardApp().run()
    except Exception:
        import traceback

        HataApp(traceback.format_exc()).run()
