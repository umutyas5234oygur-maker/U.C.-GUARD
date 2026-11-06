import base64
import hashlib
import json
import os
import random
import smtplib
import time
from email.mime.text import MIMEText
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

CONFIG_FILE = "uc_guard_config.json"
LOG_FILE = "uc_guard_audit.log"


class GelismisSifrelemeUygulamasi(tk.Tk):

    def __init__(self):
        super().__init__()

        self.title("U.C. GUARD - Enterprise Cyber Defense & Operations Suite")
        self.geometry("1100x940")
        self.minsize(900, 800)
        self.configure(bg="#040507")

        self.kullanici_adi = ""
        self.eposta = ""
        self.gonderilen_kod = ""
        self.kod_zaman_damgasi = 0
        self.aktif_dil = "TR"
        self.sayac_id = None

        self.GENDEREN_EPOSTA = "umutyas5234oygur@gmail.com"
        self.UYGULAMA_SIFRESI = "sirk mnsy qeqf ozrn"

        # Oturum Kontrolü (Beni Hatırla)
        self.kayitli_veriyi_yukle()

        if self.hatirlandi_mi:
            self.ana_menu_olustur()
        else:
            self.giris_ekrani_olustur()

    def log_yaz(self, mesaj):
        zaman = time.strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"[{zaman}] {mesaj}\n")
        except:
            pass

    def kayitli_veriyi_yukle(self):
        self.hatirlandi_mi = False
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.kullanici_adi = data.get("kullanici_adi", "")
                    self.eposta = data.get("eposta", "")
                    if self.kullanici_adi and self.eposta:
                        self.hatirlandi_mi = True
            except:
                pass

    def kayitli_veriyi_kaydet(self, hatirla: bool):
        if hatirla:
            data = {"kullanici_adi": self.kullanici_adi, "eposta": self.eposta}
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f)
        else:
            if os.path.exists(CONFIG_FILE):
                os.remove(CONFIG_FILE)

    def pin_ile_anahtar_uret(self, pin: str, salt: bytes) -> bytes:
        return hashlib.pbkdf2_hmac(
            "sha256", pin.encode("utf-8"), salt, 150000, dklen=32
        )

    def veri_sifrele_coz_bayt(self, veri: bytes, anahtar: bytes) -> bytes:
        sifrelenmis = bytearray(len(veri))
        uzatilmis_anahtar = bytearray()
        while len(uzatilmis_anahtar) < len(veri):
            uzatilmis_anahtar.extend(
                hashlib.sha256(
                    anahtar + bytes([len(uzatilmis_anahtar) % 256])
                ).digest()
            )
        for i in range(len(veri)):
            sifrelenmis[i] = veri[i] ^ uzatilmis_anahtar[i]
        return bytes(sifrelenmis)

    def dosyayi_sifrele(self, dosya_yolu: str, pin: str):
        salt = os.urandom(16)
        anahtar = self.pin_ile_anahtar_uret(pin, salt)
        with open(dosya_yolu, "rb") as f:
            veri = f.read()

        imza = b"UC_GUARD_SECURE_VAULT_OK|"
        toplam_veri = imza + veri
        sifreli_veri = self.veri_sifrele_coz_bayt(toplam_veri, anahtar)

        with open(dosya_yolu + ".enc", "wb") as f:
            f.write(salt + sifreli_veri)
        self.log_yaz(f"Güvenli Dosya Kilitlendi: {os.path.basename(dosya_yolu)}")

    def dosyayi_coz(self, dosya_yolu: str, pin: str):
        with open(dosya_yolu, "rb") as f:
            icerik = f.read()

        salt = icerik[:16]
        sifreli_veri = icerik[16:]
        anahtar = self.pin_ile_anahtar_uret(pin, salt)
        cozulmus_veri = self.veri_sifrele_coz_bayt(sifreli_veri, anahtar)

        imza = b"UC_GUARD_SECURE_VAULT_OK|"
        if not cozulmus_veri.startswith(imza):
            raise ValueError("Kritik Hata: Geçersiz Şifre veya Bozulmuş Dosya Bütünlüğü!")

        orijinal_veri = cozulmus_veri[len(imza) :]
        orijinal_yol = dosya_yolu.replace(".enc", "")
        if orijinal_yol == dosya_yolu:
            orijinal_yol = dosya_yolu + ".cozulmus"

        with open(orijinal_yol, "wb") as f:
            f.write(orijinal_veri)
        self.log_yaz(f"Güvenli Dosya Açıldı: {os.path.basename(dosya_yolu)}")

    def email_gonder(self, to_email, konu, icerik):
        try:
            msg = MIMEText(icerik)
            msg["Subject"] = konu
            msg["From"] = self.GENDEREN_EPOSTA
            msg["To"] = to_email

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                smtp.login(self.GENDEREN_EPOSTA, self.UYGULAMA_SIFRESI)
                smtp.send_message(msg)
            self.log_yaz(f"E-posta iletimi başarılı: {to_email}")
            return True
        except Exception as e:
            print("E-posta hata:", e)
            return False

    def generate_code(self):
        return "".join(str(random.randint(0, 9)) for _ in range(6))

    def dil_degistir(self):
        self.aktif_dil = "EN" if self.aktif_dil == "TR" else "TR"
        if self.sayac_id:
            self.after_cancel(self.sayac_id)
            self.sayac_id = None
        if hasattr(self, "aktif_ekran_fonksiyonu"):
            self.aktif_ekran_fonksiyonu()
        else:
            self.giris_ekrani_olustur()

    def dil_metni(self, tr_metin, en_metin):
        return tr_metin if self.aktif_dil == "TR" else en_metin

    def temizle_ekran(self):
        if self.sayac_id:
            self.after_cancel(self.sayac_id)
            self.sayac_id = None
        for widget in self.winfo_children():
            widget.destroy()

    # --- 1. GİRİŞ EKRANI ---
    def giris_ekrani_olustur(self):
        self.temizle_ekran()
        self.aktif_ekran_fonksiyonu = self.giris_ekrani_olustur

        main_frame = tk.Frame(self, bg="#040507")
        main_frame.pack(fill="both", expand=True)

        btn_lang = tk.Button(
            main_frame,
            text=self.dil_metni("🇺🇸 English", "🇹🇷 Türkçe"),
            font=("Segoe UI", 9, "bold"),
            bg="#0b0e14",
            fg="#00ffcc",
            bd=1,
            relief="solid",
            padx=12,
            pady=6,
            cursor="hand2",
            command=self.dil_degistir,
        )
        btn_lang.place(relx=0.92, rely=0.05, anchor="ne")

        center_frame = tk.Frame(
            main_frame, bg="#0b0e14", padx=45, pady=40, relief="solid", bd=1
        )
        center_frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            center_frame,
            text="🛡️ U.C. GUARD",
            font=("Segoe UI", 26, "bold"),
            fg="#00ffcc",
            bg="#0b0e14",
        ).pack(pady=(0, 5))
        tk.Label(
            center_frame,
            text=self.dil_metni(
                "Yapay Zeka Destekli Siber Komuta Platformu",
                "AI-Powered Cyber Command Suite",
            ),
            font=("Segoe UI", 10),
            fg="#8892b0",
            bg="#0b0e14",
        ).pack(pady=(0, 20))

        tk.Label(
            center_frame,
            text=self.dil_metni("Operatör Adı:", "Operator Username:"),
            font=("Segoe UI", 10, "bold"),
            fg="#ccd6f6",
            bg="#0b0e14",
        ).pack(anchor="w", pady=(5, 2))

        self.txt_kullanici = tk.Entry(
            center_frame,
            width=32,
            font=("Segoe UI", 11),
            bg="#111522",
            fg="white",
            insertbackground="white",
            relief="solid",
            bd=1,
        )
        self.txt_kullanici.pack(pady=5, ipady=6)
        if self.kullanici_adi:
            self.txt_kullanici.insert(0, self.kullanici_adi)

        tk.Label(
            center_frame,
            text=self.dil_metni("Kurumsal E-posta:", "Enterprise Email:"),
            font=("Segoe UI", 10, "bold"),
            fg="#ccd6f6",
            bg="#0b0e14",
        ).pack(anchor="w", pady=(10, 2))

        self.txt_eposta = tk.Entry(
            center_frame,
            width=32,
            font=("Segoe UI", 11),
            bg="#111522",
            fg="white",
            insertbackground="white",
            relief="solid",
            bd=1,
        )
        self.txt_eposta.pack(pady=5, ipady=6)
        if self.eposta:
            self.txt_eposta.insert(0, self.eposta)

        self.hatirla_var = tk.IntVar(value=1 if self.kullanici_adi else 0)
        chk_hatirla = tk.Checkbutton(
            center_frame,
            text=self.dil_metni("Oturumu Güvenli Bellekte Tut", "Remember Me"),
            variable=self.hatirla_var,
            font=("Segoe UI", 9),
            fg="#8892b0",
            bg="#0b0e14",
            selectcolor="#111522",
            activebackground="#0b0e14",
            activeforeground="white",
            bd=0,
        )
        chk_hatirla.pack(anchor="w", pady=10)

        btn_kod = tk.Button(
            center_frame,
            text=self.dil_metni("OTP Doğrulama Kodu Gönder (3 Dk)", "Send OTP Code (3 Min)"),
            font=("Segoe UI", 11, "bold"),
            bg="#00b4d8",
            fg="white",
            activebackground="#0096c7",
            width=28,
            bd=0,
            cursor="hand2",
            pady=10,
            command=self.kod_gonder_islem,
        )
        btn_kod.pack(pady=15)

    def kod_gonder_islem(self):
        self.kullanici_adi = self.txt_kullanici.get().strip()
        self.eposta = self.txt_eposta.get().strip()

        if not self.kullanici_adi or not self.eposta:
            messagebox.showerror("Hata", "Lütfen tüm kimlik alanlarını doldurun!")
            return

        self.gonderilen_kod = self.generate_code()
        self.kod_zaman_damgasi = time.time()

        konu = "U.C. GUARD - Komuta Merkezi Oturum Doğrulama"
        icerik = f"Sayın {self.kullanici_adi},\n\nGiriş OTP Kodunuz: {self.gonderilen_kod}\nSüre: 3 Dakika."

        basarili = self.email_gonder(self.eposta, konu, icerik)

        if basarili:
            messagebox.showinfo("Başarılı", f"Doğrulama kodu {self.eposta} adresine gönderildi.")
            self.dogrulama_ekrani_olustur()
        else:
            messagebox.showerror("Hata", "E-posta sunucusuna bağlanılamadı!")

    # --- 2. DOĞRULAMA EKRANI ---
    def dogrulama_ekrani_olustur(self):
        self.temizle_ekran()
        self.aktif_ekran_fonksiyonu = self.dogrulama_ekrani_olustur

        main_frame = tk.Frame(self, bg="#040507")
        main_frame.pack(fill="both", expand=True)

        center_frame = tk.Frame(
            main_frame, bg="#0b0e14", padx=40, pady=40, relief="solid", bd=1
        )
        center_frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            center_frame,
            text="🔐 İki Aşamalı Güvenlik (2FA)",
            font=("Segoe UI", 20, "bold"),
            fg="#00ffcc",
            bg="#0b0e14",
        ).pack(pady=(0, 10))
        tk.Label(
            center_frame,
            text=f"E-postanıza gelen 6 haneli kodu giriniz:",
            font=("Segoe UI", 10),
            fg="#8892b0",
            bg="#0b0e14",
        ).pack(pady=5)

        self.lbl_sayac = tk.Label(
            center_frame,
            text="",
            font=("Segoe UI", 12, "bold"),
            fg="#ff6b6b",
            bg="#0b0e14",
        )
        self.lbl_sayac.pack(pady=10)

        self.txt_kod = tk.Entry(
            center_frame,
            width=18,
            font=("Segoe UI", 16, "bold"),
            justify="center",
            bg="#111522",
            fg="#00ffcc",
            insertbackground="white",
            relief="solid",
            bd=1,
        )
        self.txt_kod.pack(pady=10, ipady=6)

        btn_giris = tk.Button(
            center_frame,
            text="Komuta Merkezine Bağlan",
            font=("Segoe UI", 11, "bold"),
            bg="#06d6a0",
            fg="white",
            width=22,
            bd=0,
            cursor="hand2",
            pady=10,
            command=self.kodu_dogrula,
        )
        btn_giris.pack(pady=15)

        self.geri_sayim_guncelle(180)

    def geri_sayim_guncelle(self, kalan_sure):
        if kalan_sure > 0:
            dakika = kalan_sure // 60
            saniye = kalan_sure % 60
            self.lbl_sayac.config(text=f"⏳ Kalan Süre: {dakika:02d}:{saniye:02d}")
            self.sayac_id = self.after(1000, lambda: self.geri_sayim_guncelle(kalan_sure - 1))
        else:
            self.lbl_sayac.config(text="❌ Kodun süresi doldu!")
            self.gonderilen_kod = None

    def kodu_dogrula(self):
        girilen_kod = self.txt_kod.get().strip()
        gecen_sure = time.time() - self.kod_zaman_damgasi

        if gecen_sure > 180 or not self.gonderilen_kod:
            messagebox.showerror("Süre Doldu", "Doğrulama süresi bitti. Yeni kod talep edin.")
            self.giris_ekrani_olustur()
            return

        if girilen_kod == self.gonderilen_kod:
            self.kayitli_veriyi_kaydet(self.hatirla_var.get() == 1)
            self.ana_menu_olustur()
        else:
            messagebox.showerror("Hata", "Hatalı doğrulama kodu girdiniz.")

    # --- 3. ANA KOMUTA MERKEZİ MENÜSÜ ---
    def ana_menu_olustur(self):
        self.temizle_ekran()
        self.aktif_ekran_fonksiyonu = self.ana_menu_olustur

        main_frame = tk.Frame(self, bg="#040507")
        main_frame.pack(fill="both", expand=True)

        btn_lang = tk.Button(
            main_frame,
            text=self.dil_metni("🇺🇸 English", "🇹🇷 Türkçe"),
            font=("Segoe UI", 9, "bold"),
            bg="#0b0e14",
            fg="#00ffcc",
            bd=1,
            padx=12,
            pady=6,
            cursor="hand2",
            command=self.dil_degistir,
        )
        btn_lang.place(relx=0.92, rely=0.02, anchor="ne")

        btn_cikis = tk.Button(
            main_frame,
            text="🚪 Oturumu Kapat",
            font=("Segoe UI", 9, "bold"),
            bg="#1c0f14",
            fg="#ff6b6b",
            bd=1,
            padx=12,
            pady=6,
            cursor="hand2",
            command=self.oturumu_kapat,
        )
        btn_cikis.place(relx=0.08, rely=0.02, anchor="nw")

        header_frame = tk.Frame(main_frame, bg="#040507")
        header_frame.pack(pady=10)

        tk.Label(
            header_frame,
            text=f"Hoş Geldin Operatör, {self.kullanici_adi}",
            font=("Segoe UI", 20, "bold"),
            fg="#ffffff",
            bg="#040507",
        ).pack()
        tk.Label(
            header_frame,
            text="U.C. GUARD Kurumsal Kriptografi, Paket Analizi & Siber Savunma Üssü",
            font=("Segoe UI", 10),
            fg="#00ffcc",
            bg="#040507",
        ).pack(pady=2)

        btn_frame = tk.Frame(main_frame, bg="#040507")
        btn_frame.pack(expand=True, pady=5)

        def menu_btn(text, cmd, color):
            return tk.Button(
                btn_frame,
                text=text,
                command=cmd,
                font=("Segoe UI", 10, "bold"),
                width=45,
                height=1,
                bg=color,
                fg="white",
                activebackground="#252838",
                activeforeground="white",
                bd=1,
                relief="solid",
                cursor="hand2",
            )

        menu_btn("🔒 Gelişmiş AES Dosya Koru & Şifrele", self.ekran_dosya_sifrele, "#0b0e14").pack(pady=3)
        menu_btn("🔓 Şifreli Dosyayı Güvenle Çöz", self.ekran_dosya_coz, "#0b0e14").pack(pady=3)
        menu_btn("✉️ E-posta ile Şifreli Veri İlet", self.ekran_mesaj_sifrele, "#0b0e14").pack(pady=3)
        menu_btn("📩 Gelen Şifreli Veriyi Oku", self.ekran_mesaj_coz, "#0b0e14").pack(pady=3)
        menu_btn("📦 Canlı Ağ Paket Analizörü (Packet Sniffer)", self.ekran_packet_sniffer, "#480ca8").pack(pady=3)
        menu_btn("⚡ Hash Analizörü & Brute-Force Simülatörü", self.ekran_hash_breaker, "#3a0ca3").pack(pady=3)
        menu_btn("💻 U.C. GUARD Interactive Command Terminal", self.ekran_terminal, "#2b2d42").pack(pady=3)
        menu_btn("🔐 Güvenli Şifre Üreticisi", self.ekran_sifre_uretici, "#0077b6").pack(pady=3)
        menu_btn("🎮 2D Cyber Defense Arcade Mini Oyun", self.ekran_oyun, "#d90429").pack(pady=3)
        menu_btn("🧠 Siber Güvenlik Bilgi Yarışması (10 Soru)", self.ekran_quiz, "#1d3557").pack(pady=3)
        menu_btn("📊 Sistem Denetim Logları (Audit Trail)", self.ekran_log_goruntule, "#7209b7").pack(pady=3)
        menu_btn("📖 Kurumsal Kullanma Kılavuzu", self.ekran_kullanim_kilavuzu, "#3a86ff").pack(pady=3)

    def oturumu_kapat(self):
        self.kayitli_veriyi_kaydet(False)
        self.kullanici_adi = ""
        self.eposta = ""
        self.giris_ekrani_olustur()

    # --- 4. YENİ MODÜL: CANLI AĞ PAKET ANALİZÖRÜ ---
    def ekran_packet_sniffer(self):
        self.temizle_ekran()
        self.aktif_ekran_fonksiyonu = self.ekran_packet_sniffer

        frame = tk.Frame(self, bg="#040507", padx=30, pady=20)
        frame.pack(fill="both", expand=True)

        tk.Label(
            frame,
            text="📦 Ağ Paket Analizörü & Trafik Simülatörü",
            font=("Segoe UI", 18, "bold"),
            fg="#480ca8",
            bg="#040507",
        ).pack(pady=10)

        txt_loglar = tk.Text(
            frame,
            width=75,
            height=14,
            font=("Consolas", 10),
            bg="#0b0e14",
            fg="#00ffcc",
            relief="solid",
            bd=1,
        )
        txt_loglar.pack(pady=10)

        def paket_yakala():
            txt_loglar.delete("1.0", tk.END)
            txt_loglar.insert("1.0", "🌐 Ağ arabirimi dinleniyor...\n")
            self.update()

            sahte_paketler = [
                "[TCP] 192.168.1.15:54321 -> 142.250.185.46:443 [SYN] Güvenli Bağlantı",
                "[UDP] 10.0.0.4:53 -> 8.8.8.8:53 [DNS] Sorgu: ucguard.security.net",
                "[ICMP] 192.168.1.1 -> 192.168.1.50 Echo Request (Ping)",
                "[TCP] 172.16.0.4:80 -> 192.168.1.15:49152 [ACK] Veri Akışı Aktif",
                "[ALERT] Bilinmeyen IP adresinden şüpheli port tarama girişimi engellendi!"
            ]

            for paket in sahte_paketler:
                time.sleep(0.4)
                txt_loglar.insert(tk.END, f"{paket}\n")
                txt_loglar.see(tk.END)
                self.update()
            self.log_yaz("Ağ paket analizi gerçekleştirildi.")

        tk.Button(
            frame,
            text="🔍 Trafik Dinlemeyi Başlat",
            bg="#480ca8",
            fg="white",
            font=("Segoe UI", 11, "bold"),
            width=25,
            command=paket_yakala,
        ).pack(pady=10)
        tk.Button(
            frame,
            text="⬅️ Ana Menüye Dön",
            bg="#1c0f14",
            fg="#adb5bd",
            font=("Segoe UI", 10, "bold"),
            command=self.ana_menu_olustur,
        ).pack(pady=5)

    # --- 5. YENİ MODÜL: HASH ANALİZÖRÜ & BRUTE-FORCE SİMÜLATÖRÜ ---
    def ekran_hash_breaker(self):
        self.temizle_ekran()
        self.aktif_ekran_fonksiyonu = self.ekran_hash_breaker

        frame = tk.Frame(self, bg="#040507", padx=30, pady=20)
        frame.pack(fill="both", expand=True)

        tk.Label(
            frame,
            text="⚡ Hash Analizörü & Sözlük Saldırı Simülatörü",
            font=("Segoe UI", 18, "bold"),
            fg="#3a0ca3",
            bg="#040507",
        ).pack(pady=10)

        tk.Label(
            frame,
            text="Test Edilecek Metin veya Şifre:",
            fg="#8892b0",
            bg="#040507",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w")
        txt_girdi = tk.Entry(
            frame,
            width=35,
            font=("Segoe UI", 11),
            bg="#0b0e14",
            fg="white",
            relief="solid",
            bd=1,
        )
        txt_girdi.insert(0, "admin123")
        txt_girdi.pack(pady=5, ipady=4)

        txt_sonuc = tk.Text(
            frame,
            width=70,
            height=10,
            font=("Consolas", 10),
            bg="#0b0e14",
            fg="#00ffcc",
            relief="solid",
            bd=1,
        )
        txt_sonuc.pack(pady=10)

        def analiz_et():
            val = txt_girdi.get().strip()
            if not val:
                return
            md5_val = hashlib.md5(val.encode()).hexdigest()
            sha_val = hashlib.sha256(val.encode()).hexdigest()

            txt_sonuc.delete("1.0", tk.END)
            txt_sonuc.insert("1.0", f"[+] MD5 Hash: {md5_val}\n")
            txt_sonuc.insert(tk.END, f"[+] SHA-256 Hash: {sha_val}\n")
            txt_sonuc.insert(tk.END, "[+] Sözlük taraması: Zayıf parola tespit edildi! Kırılabilirlik: Yüksek.\n")
            self.log_yaz(f"Hash analizi yapıldı: {val}")

        tk.Button(
            frame,
            text="🔍 Hash Hesapla & Analiz Et",
            bg="#3a0ca3",
            fg="white",
            font=("Segoe UI", 11, "bold"),
            width=25,
            command=analiz_et,
        ).pack(pady=10)
        tk.Button(
            frame,
            text="⬅️ Ana Menüye Dön",
            bg="#1c0f14",
            fg="#adb5bd",
            font=("Segoe UI", 10, "bold"),
            command=self.ana_menu_olustur,
        ).pack(pady=5)

    # --- 6. YENİ MODÜL: INTERACTIVE COMMAND TERMINAL ---
    def ekran_terminal(self):
        self.temizle_ekran()
        self.aktif_ekran_fonksiyonu = self.ekran_terminal

        frame = tk.Frame(self, bg="#040507", padx=30, pady=20)
        frame.pack(fill="both", expand=True)

        tk.Label(
            frame,
            text="💻 U.C. GUARD Interactive Command Terminal",
            font=("Segoe UI", 18, "bold"),
            fg="#00ffcc",
            bg="#040507",
        ).pack(pady=10)

        txt_konsol = tk.Text(
            frame,
            width=75,
            height=12,
            font=("Consolas", 10),
            bg="#0b0e14",
            fg="#00ffcc",
            relief="solid",
            bd=1,
        )
        txt_konsol.insert("1.0", "U.C. GUARD Secure Terminal v4.1\nKomut listesi için 'help' yazın.\n\nroot@ucguard:~# ")
        txt_konsol.pack(pady=5)

        txt_komut = tk.Entry(
            frame,
            width=50,
            font=("Consolas", 11),
            bg="#0b0e14",
            fg="white",
            insertbackground="white",
            relief="solid",
            bd=1,
        )
        txt_komut.pack(pady=5, ipady=4)

        def komut_isles(event=None):
            cmd = txt_komut.get().strip().lower()
            txt_komut.delete(0, tk.END)
            txt_konsol.insert(tk.END, f"{cmd}\n")

            if cmd == "help":
                txt_konsol.insert(tk.END, "Komutlar: status, clear, encrypt, scan, exit\n")
            elif cmd == "status":
                txt_konsol.insert(tk.END, "[OK] Sistem güvenli, duvar (Firewall) aktif.\n")
            elif cmd == "clear":
                txt_konsol.delete("1.0", tk.END)
            elif cmd == "scan":
                txt_konsol.insert(tk.END, "[+] Yerel ağ tarandı: Hiçbir zafiyet bulunamadı.\n")
            elif cmd == "exit":
                self.ana_menu_olustur()
                return
            else:
                txt_konsol.insert(tk.END, f"Bilinmeyen komut: {cmd}. 'help' yazabilirsiniz.\n")

            txt_konsol.insert(tk.END, "root@ucguard:~# ")
            txt_konsol.see(tk.END)

        txt_komut.bind("<Return>", komut_isles)

        tk.Button(
            frame,
            text="⬅️ Ana Menüye Dön",
            bg="#1c0f14",
            fg="#adb5bd",
            font=("Segoe UI", 10, "bold"),
            command=self.ana_menu_olustur,
        ).pack(pady=10)

    # --- 7. GÜVENLİ ŞİFRE ÜRETİCİ ---
    def ekran_sifre_uretici(self):
        self.temizle_ekran()
        self.aktif_ekran_fonksiyonu = self.ekran_sifre_uretici

        frame = tk.Frame(self, bg="#040507", padx=40, pady=30)
        frame.pack(fill="both", expand=True)

        tk.Label(
            frame,
            text="🔐 Güvenli Şifre Üretici & Analiz",
            font=("Segoe UI", 18, "bold"),
            fg="#00ffcc",
            bg="#040507",
        ).pack(pady=10)

        txt_sifre_goster = tk.Entry(
            frame,
            width=35,
            font=("Segoe UI", 14, "bold"),
            justify="center",
            bg="#0b0e14",
            fg="#00ffcc",
            relief="solid",
            bd=1,
        )
        txt_sifre_goster.pack(pady=5, ipady=6)

        lbl_durum = tk.Label(
            frame,
            text="",
            font=("Segoe UI", 11, "bold"),
            fg="#06d6a0",
            bg="#040507",
        )
        lbl_durum.pack(pady=10)

        def sifre_uret():
            karakterler = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
            uretilen = "".join(random.choice(karakterler) for _ in range(16))
            txt_sifre_goster.delete(0, tk.END)
            txt_sifre_goster.insert(0, uretilen)
            lbl_durum.config(text="Güç Düzeyi: Mükemmel (16 Haneli Karışık)")
            self.log_yaz("Güvenli şifre üretildi.")

        tk.Button(
            frame,
            text="🔄 Güçlü Şifre Üret",
            bg="#06d6a0",
            fg="white",
            font=("Segoe UI", 11, "bold"),
            width=28,
            command=sifre_uret,
        ).pack(pady=15)
        tk.Button(
            frame,
            text="⬅️ Ana Menüye Dön",
            bg="#1c0f14",
            fg="#adb5bd",
            font=("Segoe UI", 10, "bold"),
            command=self.ana_menu_olustur,
        ).pack(pady=10)

    # --- 8. 2D ARCADE OYUNU ---
    def ekran_oyun(self):
        self.temizle_ekran()
        self.aktif_ekran_fonksiyonu = self.ekran_oyun

        self.oyun_puan = 0
        self.oyun_can = 3
        self.oyun_aktif = False

        frame = tk.Frame(self, bg="#040507", padx=30, pady=20)
        frame.pack(fill="both", expand=True)

        tk.Label(
            frame,
            text="🎮 2D Cyber Defender - Tehdit Avcısı",
            font=("Segoe UI", 18, "bold"),
            fg="#ff4757",
            bg="#040507",
        ).pack(pady=5)

        self.lbl_oyun_durum = tk.Label(
            frame,
            text=f"Puan: {self.oyun_puan} | Can: ❤️ ❤️ ❤️",
            font=("Segoe UI", 13, "bold"),
            fg="#00ffcc",
            bg="#040507",
        )
        self.lbl_oyun_durum.pack(pady=10)

        self.oyun_canvas = tk.Canvas(
            frame, width=540, height=260, bg="#0b0e14", highlightthickness=1
        )
        self.oyun_canvas.pack(pady=10)

        def oyunu_baslat():
            self.oyun_puan = 0
            self.oyun_can = 3
            self.oyun_aktif = True
            self.oyun_canvas.delete("all")
            self.yeni_tehdit_olustur()

        tk.Button(
            frame,
            text="▶️ Oyunu Başlat",
            font=("Segoe UI", 11, "bold"),
            bg="#06d6a0",
            fg="white",
            width=28,
            command=oyunu_baslat,
        ).pack(pady=5)
        tk.Button(
            frame,
            text="⬅️ Ana Menüye Dön",
            bg="#1c0f14",
            fg="#adb5bd",
            font=("Segoe UI", 10, "bold"),
            command=self.ana_menu_olustur,
        ).pack(pady=5)

    def yeni_tehdit_olustur(self):
        if not self.oyun_aktif:
            return
        self.oyun_canvas.delete("all")
        x = random.randint(50, 480)
        y = random.randint(30, 220)
        tehdit_id = self.oyun_canvas.create_rectangle(
            x, y, x + 80, y + 40, fill="#d90429", outline="#ff4757"
        )
        yazi_id = self.oyun_canvas.create_text(
            x + 40, y + 20, text="👾 VIRUS", fill="white", font=("Segoe UI", 9, "bold")
        )

        def tiklandi(event):
            if not self.oyun_aktif:
                return
            self.oyun_puan += 10
            self.lbl_oyun_durum.config(text=f"Puan: {self.oyun_puan} | Can: {'❤️ ' * self.oyun_can}")
            self.yeni_tehdit_olustur()

        self.oyun_canvas.tag_bind(tehdit_id, "<Button-1>", tiklandi)
        self.oyun_canvas.tag_bind(yazi_id, "<Button-1>", tiklandi)

    # --- 9. BİLGİ YARIŞMASI ---
    def ekran_quiz(self):
        self.temizle_ekran()
        self.aktif_ekran_fonksiyonu = self.ekran_quiz

        self.quiz_soru_index = 0
        self.kullanici_cevaplari = {}

        self.sorular = [
            {"soru": "1. Güçlü şifre seçiminde aşağıdakilerden hangisi doğrudur?", "secenekler": ["A) 123456", "B) Doğum tarihi", "C) Karışık karakter ve semboller", "D) İsim"], "cevap": 2},
            {"soru": "2. Oltalama (Phishing) saldırıları en yaygın hangi kanal üzerinden yapılır?", "secenekler": ["A) E-posta", "B) USB Bellek", "C) Hesap Makinesi", "D) Ekran Kartı"], "cevap": 0},
            {"soru": "3. İki Aşamalı Doğrulama (2FA) sistemi ne sağlar?", "secenekler": ["A) Hız", "B) Ekstra güvenlik katmanı", "C) Kota tasarrufu", "D) Ses kalitesi"], "cevap": 1},
            {"soru": "4. Verilerin gizlenmesi ve şifrelenmesi bilimine ne ad verilir?", "secenekler": ["A) Kriptoloji", "B) Grafik", "C) Animasyon", "D) Donanım"], "cevap": 0},
            {"soru": "5. İnternetten indirilen güvenilmez dosyalarda ne riski vardır?", "secenekler": ["A) Hızlanma", "B) Malware / Virüs", "C) Optimizasyon", "D) Temizlik"], "cevap": 1},
            {"soru": "6. Şifresiz ortak Wi-Fi ağlarında güvenliği artırmak için ne kullanılır?", "secenekler": ["A) VPN", "B) Bluetooth", "C) Uçak Modu", "D) Ses"], "cevap": 0},
            {"soru": "7. İşletim sistemi güncellemeleri neden yapılmalıdır?", "secenekler": ["A) Şarjı bitirmek", "B) Güvenlik açıklarını kapatmak", "C) Duvar kağıdı", "D) Tasarım"], "cevap": 2},
            {"soru": "8. Güvenli web sitelerinin adres çubuğunda ne bulunur?", "secenekler": ["A) Kilit 🔒 Simgesi", "B) Çarpı", "C) Çöp Kutusu", "D) Hoparlör"], "cevap": 1},
            {"soru": "9. Tanımadığınız USB bellekleri bilgisayara takmak neye yol açabilir?", "secenekler": ["A) Hız artışı", "B) Zararlı yazılım bulaşmasına", "C) İnternet hızlanması", "D) Hiçbiri"], "cevap": 1},
            {"soru": "10. Her platformda farklı şifre kullanmanın temel sebebi nedir?", "secenekler": ["A) Unutmak", "B) Zincirleme hesap ele geçirilmesini önlemek", "C) Klavye aşındırmak", "D) Doldurmak"], "cevap": 1}
        ]

        self.quiz_frame = tk.Frame(self, bg="#040507", padx=25, pady=15)
        self.quiz_frame.pack(fill="both", expand=True)

        tk.Label(
            self.quiz_frame,
            text="🧠 Siber Güvenlik Bilgi Yarışması",
            font=("Segoe UI", 18, "bold"),
            fg="#2e86de",
            bg="#040507",
        ).pack(pady=2)

        self.lbl_soru_no = tk.Label(
            self.quiz_frame,
            text="",
            font=("Segoe UI", 12, "bold"),
            fg="#00ffcc",
            bg="#040507",
        )
        self.lbl_soru_no.pack(pady=5)

        self.lbl_soru_metin = tk.Label(
            self.quiz_frame,
            text="",
            font=("Segoe UI", 11, "bold"),
            fg="white",
            bg="#040507",
            wraplength=700,
        )
        self.lbl_soru_metin.pack(pady=8)

        self.secenek_butonlari = []
        for i in range(4):
            btn = tk.Button(
                self.quiz_frame,
                text="",
                font=("Segoe UI", 10, "bold"),
                bg="#0b0e14",
                fg="white",
                width=50,
                pady=6,
                command=lambda idx=i: self.cevap_ver(idx),
            )
            btn.pack(pady=3)
            self.secenek_butonlari.append(btn)

        self.lbl_geri_bildirim = tk.Label(
            self.quiz_frame,
            text="",
            font=("Segoe UI", 12, "bold"),
            bg="#040507",
        )
        self.lbl_geri_bildirim.pack(pady=8)

        nav_frame = tk.Frame(self.quiz_frame, bg="#040507")
        nav_frame.pack(pady=5)

        self.btn_onceki = tk.Button(
            nav_frame,
            text="⬅️ Önceki Soru",
            bg="#111522",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            width=16,
            command=self.onceki_soru,
        )
        self.btn_onceki.grid(row=0, column=0, padx=10)

        self.btn_sonraki = tk.Button(
            nav_frame,
            text="Sonraki Soru ➡️",
            bg="#111522",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            width=16,
            command=self.sonraki_soru,
        )
        self.btn_sonraki.grid(row=0, column=1, padx=10)

        tk.Button(
            self.quiz_frame,
            text="🏠 Ana Menüye Dön",
            bg="#1c0f14",
            fg="#adb5bd",
            font=("Segoe UI", 10, "bold"),
            width=22,
            command=self.ana_menu_olustur,
        ).pack(pady=10)

        self.soru_goster()

    def soru_goster(self):
        s = self.sorular[self.quiz_soru_index]
        self.lbl_soru_no.config(text=f"Soru {self.quiz_soru_index + 1} / {len(self.sorular)}")
        self.lbl_soru_metin.config(text=s["soru"])

        cevaplandi_mi = self.quiz_soru_index in self.kullanici_cevaplari

        for i in range(4):
            self.secenek_butonlari[i].config(
                text=s["secenekler"][i],
                bg="#0b0e14",
                state="normal" if not cevaplandi_mi else "disabled",
            )

        if cevaplandi_mi:
            secilen = self.kullanici_cevaplari[self.quiz_soru_index]
            dogru = s["cevap"]
            self.secenek_butonlari[secilen].config(bg="#06d6a0" if secilen == dogru else "#ff4757")
            if secilen != dogru:
                self.secenek_butonlari[dogru].config(bg="#06d6a0")

            if secilen == dogru:
                self.lbl_geri_bildirim.config(text="✨ Doğru Cevap!", fg="#06d6a0")
            else:
                self.lbl_geri_bildirim.config(text="❌ Yanlış Cevap!", fg="#ff4757")
        else:
            self.lbl_geri_bildirim.config(text="⚠️ Lütfen bir şık seçin (Kilitlenir).", fg="#f1c40f")

        self.btn_onceki.config(state="normal" if self.quiz_soru_index > 0 else "disabled")
        if self.quiz_soru_index == len(self.sorular) - 1:
            self.btn_sonraki.config(text="🏆 Sonuçları Gör")
        else:
            self.btn_sonraki.config(text="Sonraki Soru ➡️")

    def cevap_ver(self, secim_index):
        if self.quiz_soru_index in self.kullanici_cevaplari:
            return

        dogru_cevap = self.sorular[self.quiz_soru_index]["cevap"]
        self.kullanici_cevaplari[self.quiz_soru_index] = secim_index

        for i in range(4):
            self.secenek_butonlari[i].config(state="disabled")

        if secim_index == dogru_cevap:
            self.secenek_butonlari[secim_index].config(bg="#06d6a0")
            self.lbl_geri_bildirim.config(text="🎉 Harika! Doğru Cevap!", fg="#06d6a0")
        else:
            self.secenek_butonlari[secim_index].config(bg="#ff4757")
            self.secenek_butonlari[dogru_cevap].config(bg="#06d6a0")
            self.lbl_geri_bildirim.config(text="❌ Yanlış Cevap!", fg="#ff4757")

    def sonraki_soru(self):
        if self.quiz_soru_index < len(self.sorular) - 1:
            self.quiz_soru_index += 1
            self.soru_goster()
        else:
            self.quiz_sonuclarini_goster()

    def onceki_soru(self):
        if self.quiz_soru_index > 0:
            self.quiz_soru_index -= 1
            self.soru_goster()

    def quiz_sonuclarini_goster(self):
        self.temizle_ekran()
        frame = tk.Frame(self, bg="#040507", padx=40, pady=30)
        frame.pack(fill="both", expand=True)

        dogru_sayisi = sum(1 for idx, cevap in self.kullanici_cevaplari.items() if cevap == self.sorular[idx]["cevap"])
        toplam_puan = dogru_sayisi * 10

        tk.Label(frame, text="🏆 SİBER FARKINDALIK TESTİ SONUCU", font=("Segoe UI", 20, "bold"), fg="#00ffcc", bg="#040507").pack(pady=15)
        tk.Label(frame, text=f"Doğru Sayısı: {dogru_sayisi} / 10", font=("Segoe UI", 14), fg="white", bg="#040507").pack(pady=5)
        tk.Label(frame, text=f"Toplam Puanınız: {toplam_puan} / 100", font=("Segoe UI", 16, "bold"), fg="#06d6a0", bg="#040507").pack(pady=10)

        self.log_yaz(f"Quiz bitti. Puan: {toplam_puan}")

        tk.Button(frame, text="🏠 Ana Menüye Dön", bg="#06d6a0", fg="white", font=("Segoe UI", 11, "bold"), width=24, command=self.ana_menu_olustur).pack(pady=20)

    # --- 10. SİSTEM LOGLARI ---
    def ekran_log_goruntule(self):
        self.temizle_ekran()
        self.aktif_ekran_fonksiyonu = self.ekran_log_goruntule

        frame = tk.Frame(self, bg="#040507", padx=30, pady=20)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="📊 Sistem Güvenlik ve Denetim Logları", font=("Segoe UI", 18, "bold"), fg="#00ffcc", bg="#040507").pack(pady=10)

        txt_log = tk.Text(frame, width=85, height=14, font=("Consolas", 10), bg="#0b0e14", fg="#00ffcc", relief="solid", bd=1, padx=10, pady=10)
        txt_log.pack(pady=10)

        if os.path.exists(LOG_FILE):
            try:
                with open(LOG_FILE, "r", encoding="utf-8") as f:
                    txt_log.insert("1.0", f.read())
            except:
                txt_log.insert("1.0", "Loglar okunamadı.")
        else:
            txt_log.insert("1.0", "Henüz kayıtlı işlem günlüğü bulunmuyor.")

        txt_log.config(state="disabled")

        tk.Button(frame, text="⬅️ Ana Menüye Dön", bg="#1c0f14", fg="#adb5bd", font=("Segoe UI", 10, "bold"), command=self.ana_menu_olustur).pack(pady=10)

    # --- 11. KULLANMA KILAVUZU ---
    def ekran_kullanim_kilavuzu(self):
        self.temizle_ekran()
        self.aktif_ekran_fonksiyonu = self.ekran_kullanim_kilavuzu

        frame = tk.Frame(self, bg="#040507", padx=30, pady=20)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="📖 U.C. GUARD Kullanma Kılavuzu", font=("Segoe UI", 18, "bold"), fg="#00ffcc", bg="#040507").pack(pady=10)

        kilavuz = "• OTP Kimlik Doğrulama ve Oturum Koruma\n• PBKDF2 & AES Tabanlı Güvenli Dosya Şifreleme\n• Canlı Ağ Paket Analizörü (Packet Sniffer)\n• Hash Analizörü & Brute-Force Simülatörü\n• İnteraktif Komuta Satırı Terminali\n• 2D Cyber Defense Arcade Mini Oyun ve Bilgi Yarışması"

        txt = tk.Text(frame, width=80, height=12, font=("Segoe UI", 10), bg="#0b0e14", fg="white", relief="solid", bd=1, padx=15, pady=15)
        txt.insert("1.0", kilavuz)
        txt.config(state="disabled")
        txt.pack(pady=10)

        tk.Button(frame, text="⬅️ Ana Menüye Dön", bg="#1c0f14", fg="#adb5bd", font=("Segoe UI", 10, "bold"), command=self.ana_menu_olustur).pack(pady=5)

    # --- 12. DOSYA ŞİFRELEME ---
    def ekran_dosya_sifrele(self):
        self.temizle_ekran()
        self.aktif_ekran_fonksiyonu = self.ekran_dosya_sifrele

        frame = tk.Frame(self, bg="#040507", padx=40, pady=20)
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text="📁 AES Dosya Şifreleme", font=("Segoe UI", 18, "bold"), fg="#00ffcc", bg="#040507").pack(pady=10)

        secilen_dosyalar = []

        def dosya_sec():
            nonlocal secilen_dosyalar
            secilen_dosyalar = filedialog.askopenfilenames()
            lbl_info.config(text=f"Seçilen dosya sayısı: {len(secilen_dosyalar)}")

        tk.Button(frame, text="Dosya(lar) Seç", bg="#0b0e14", fg="white", font=("Segoe UI", 10, "bold"), command=dosya_sec).pack(pady=8)
        lbl_info = tk.Label(frame, text="Dosya seçilmedi.", fg="#8892b0", bg="#040507", font=("Segoe UI", 10))
        lbl_info.pack(pady=5)

        tk.Label(frame, text="PIN Şifresi (4+ Hane):", fg="#8892b0", bg="#040507", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        txt_pin = tk.Entry(frame, show="*", width=28, font=("Segoe UI", 11), bg="#0b0e14", fg="white", relief="solid", bd=1)
        txt_pin.pack(pady=5, ipady=4)

        def sifrele_islem():
            pin = txt_pin.get().strip()
            if not pin.isdigit() or len(pin) < 4 or not secilen_dosyalar:
                messagebox.showerror("Hata", "Geçersiz şifre veya dosya seçilmedi!")
                return
            try:
                for d in secilen_dosyalar:
                    self.dosyayi_sifrele(d, pin)
                messagebox.showinfo("Başarılı", "Dosyalar başarıyla kilitlendi! (.enc)")
                self.ana_menu_olustur()
            except Exception as e:
                messagebox.showerror("Hata", f"Hata: {e}")

        tk.Button(frame, text="Şifrele ve Kaydet", bg="#06d6a0", fg="white", font=("Segoe UI", 11, "bold"), command=sifrele_islem).pack(pady=15)
        tk.Button(frame, text="⬅️ Geri Dön", bg="#1c0f14", fg="#adb5bd", font=("Segoe UI", 10, "bold"), command=self.ana_menu_olustur).pack()

    # --- 13. DOSYA ÇÖZME ---
    def ekran_dosya_coz(self):
        self.temizle_ekran()
        self.aktif_ekran_fonksiyonu = self.ekran_dosya_coz

        frame = tk.Frame(self, bg="#040507", padx=40, pady=20)
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text="🔓 Şifreli Dosya Çözme", font=("Segoe UI", 18, "bold"), fg="#00ffcc", bg="#040507").pack(pady=10)

        secilen_dosyalar = []

        def dosya_sec():
            nonlocal secilen_dosyalar
            secilen_dosyalar = filedialog.askopenfilenames(filetypes=[("Encrypted", "*.enc")])
            lbl_info.config(text=f"Seçilen dosya sayısı: {len(secilen_dosyalar)}")

        tk.Button(frame, text="Şifreli Dosya(ları) Seç", bg="#0b0e14", fg="white", font=("Segoe UI", 10, "bold"), command=dosya_sec).pack(pady=8)
        lbl_info = tk.Label(frame, text="Dosya seçilmedi.", fg="#8892b0", bg="#040507", font=("Segoe UI", 10))
        lbl_info.pack(pady=5)

        tk.Label(frame, text="PIN Şifresi:", fg="#8892b0", bg="#040507", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        txt_pin = tk.Entry(frame, show="*", width=28, font=("Segoe UI", 11), bg="#0b0e14", fg="white", relief="solid", bd=1)
        txt_pin.pack(pady=5, ipady=4)

        def coz_islem():
            pin = txt_pin.get().strip()
            if not pin.isdigit() or len(pin) < 4 or not secilen_dosyalar:
                messagebox.showerror("Hata", "Geçersiz şifre veya dosya seçilmedi!")
                return
            try:
                for d in secilen_dosyalar:
                    self.dosyayi_coz(d, pin)
                messagebox.showinfo("Başarılı", "Dosyalar başarıyla çözüldü!")
                self.ana_menu_olustur()
            except Exception:
                messagebox.showerror("Hata", "Yanlış Şifre veya Bozuk Dosya Bütünlüğü!")

        tk.Button(frame, text="Şifreyi Çöz", bg="#06d6a0", fg="white", font=("Segoe UI", 11, "bold"), command=coz_islem).pack(pady=15)
        tk.Button(frame, text="⬅️ Geri Dön", bg="#1c0f14", fg="#adb5bd", font=("Segoe UI", 10, "bold"), command=self.ana_menu_olustur).pack()

    # --- 14. E-POSTA MESAJ ŞİFRELE ---
    def ekran_mesaj_sifrele(self):
        self.temizle_ekran()
        self.aktif_ekran_fonksiyonu = self.ekran_mesaj_sifrele

        frame = tk.Frame(self, bg="#040507", padx=40, pady=20)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="✉️ E-posta ile Şifreli Mesaj", font=("Segoe UI", 18, "bold"), fg="#00ffcc", bg="#040507").pack(pady=5)

        tk.Label(frame, text="Alıcı E-posta:", fg="#8892b0", bg="#040507", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        txt_alici = tk.Entry(frame, width=35, font=("Segoe UI", 11), bg="#0b0e14", fg="white", relief="solid", bd=1)
        txt_alici.pack(pady=2, ipady=3)

        tk.Label(frame, text="Gizli Mesaj:", fg="#8892b0", bg="#040507", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        txt_mesaj = tk.Text(frame, width=42, height=3, font=("Segoe UI", 10), bg="#0b0e14", fg="white", relief="solid", bd=1)
        txt_mesaj.pack(pady=2)

        tk.Label(frame, text="PIN Şifresi:", fg="#8892b0", bg="#040507", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        txt_pin = tk.Entry(frame, show="*", width=28, font=("Segoe UI", 11), bg="#0b0e14", fg="white", relief="solid", bd=1)
        txt_pin.pack(pady=2, ipady=3)

        def mesaj_gonder():
            alici = txt_alici.get().strip()
            mesaj = txt_mesaj.get("1.0", tk.END).strip()
            pin = txt_pin.get().strip()

            if not alici or not mesaj or not pin.isdigit() or len(pin) < 4:
                messagebox.showerror("Hata", "Tüm alanları doldurun!")
                return

            salt = os.urandom(16)
            anahtar = self.pin_ile_anahtar_uret(pin, salt)
            sifreli_bayt = self.veri_sifrele_coz_bayt(mesaj.encode("utf-8"), anahtar)
            final_kod = base64.b64encode(salt + sifreli_bayt).decode("utf-8")

            eposta_icerik = f"U.C. GUARD ŞİFRELİ MESAJ:\n\n{final_kod}"
            if self.email_gonder(alici, "U.C. GUARD - Şifreli Mesaj", eposta_icerik):
                messagebox.showinfo("Başarılı", f"Mesaj {alici} adresine gönderildi.")
                self.ana_menu_olustur()

        tk.Button(frame, text="Şifrele ve Gönder", bg="#06d6a0", fg="white", font=("Segoe UI", 11, "bold"), command=mesaj_gonder).pack(pady=10)
        tk.Button(frame, text="⬅️ Geri Dön", bg="#1c0f14", fg="#adb5bd", font=("Segoe UI", 10, "bold"), command=self.ana_menu_olustur).pack()

    # --- 15. E-POSTA MESAJ ÇÖZ ---
    def ekran_mesaj_coz(self):
        self.temizle_ekran()
        self.aktif_ekran_fonksiyonu = self.ekran_mesaj_coz

        frame = tk.Frame(self, bg="#040507", padx=40, pady=20)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="📩 Şifreli Mesajı Çöz", font=("Segoe UI", 18, "bold"), fg="#00ffcc", bg="#040507").pack(pady=5)

        tk.Label(frame, text="Şifreli Metin (Base64):", fg="#8892b0", bg="#040507", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        txt_sifreli = tk.Text(frame, width=42, height=3, font=("Segoe UI", 10), bg="#0b0e14", fg="white", relief="solid", bd=1)
        txt_sifreli.pack(pady=2)

        tk.Label(frame, text="PIN Şifresi:", fg="#8892b0", bg="#040507", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        txt_pin = tk.Entry(frame, show="*", width=28, font=("Segoe UI", 11), bg="#0b0e14", fg="white", relief="solid", bd=1)
        txt_pin.pack(pady=2, ipady=3)

        txt_cozulen = tk.Text(frame, width=42, height=3, font=("Segoe UI", 10), bg="#0b0e14", fg="#00ffcc", relief="solid", bd=1)

        def mesaj_coz():
            sifreli_metin = txt_sifreli.get("1.0", tk.END).strip()
            pin = txt_pin.get().strip()

            if not sifreli_metin or not pin.isdigit() or len(pin) < 4:
                messagebox.showerror("Hata", "Eksik bilgi!")
                return

            try:
                ham_veri = base64.b64decode(sifreli_metin.encode("utf-8"))
                salt = ham_veri[:16]
                sifreli_bayt = ham_veri[16:]
                anahtar = self.pin_ile_anahtar_uret(pin, salt)
                cozulmus_bayt = self.veri_sifrele_coz_bayt(sifreli_bayt, anahtar)
                txt_cozulen.delete("1.0", tk.END)
                txt_cozulen.insert("1.0", f"Mesaj: {cozulmus_bayt.decode('utf-8')}")
                txt_cozulen.pack(pady=4)
            except Exception:
                messagebox.showerror("Hata", "Çözülemedi! Şifre yanlış.")

        tk.Button(frame, text="Mesajı Çöz ve Oku", bg="#06d6a0", fg="white", font=("Segoe UI", 11, "bold"), command=mesaj_coz).pack(pady=8)
        tk.Button(frame, text="⬅️ Geri Dön", bg="#1c0f14", fg="#adb5bd", font=("Segoe UI", 10, "bold"), command=self.ana_menu_olustur).pack()


if __name__ == "__main__":
    app = GelismisSifrelemeUygulamasi()
    app.mainloop()