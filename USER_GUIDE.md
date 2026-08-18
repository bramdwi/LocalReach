# 📖 Panduan Penggunaan — LocalReach Lead Engine (Mini SaaS)

Selamat datang di **LocalReach Lead Engine**, sebuah platform Mini SaaS lokal untuk mencari, memvalidasi data kontak (email & media sosial), memberikan skor kualitas, dan menyusun pesan penawaran (*cold pitch*) otomatis dari bisnis lokal di **Google Maps**.

---

## 🚀 1. Cara Menjalankan Aplikasi di Local

Pastikan Anda berada di direktori project, lalu jalankan perintah berikut di terminal:

```bash
python run_web.py
```

* Browser Anda akan otomatis terbuka ke alamat: **`http://127.0.0.1:8000`** *(atau `http://localhost:8000`)*.
* Jika ingin mengganti port, gunakan: `python run_web.py --port 8080`.

---

## 🧭 2. Antarmuka & Struktur Navigasi

### A. Sidebar Kiri (Recent Scrapes & Controls)
1. **`+ New Search`**: Tombol untuk kembali ke halaman pencarian utama (*Home Canvas*) kapan saja.
2. **`Recent Scrapes`**: Daftar riwayat batch pencarian sebelumnya yang tersimpan di folder `.tmp/`. Klik pada salah satu riwayat untuk langsung memuat dan menginspeksi datanya.
3. **`Upgrade Plan Card`**: Menampilkan paket langganan aktif (*Starter / Pro / Agency*) serta opsi upgrade kuota credit.
4. **`⚙️ Settings & System`**: Membuka modal pengaturan untuk memasukkan API Key, mengatur persona outreach, dan menghubungkan Google Sheets.

### B. Top Bar (Credit Tracker & User Profile)
* **🪙 Credit Balance**: Menampilkan sisa kuota credit Anda (contoh: `130 / 150 Credits`). Setiap prospek yang di-scrape dan diverifikasi akan menggunakan 1 credit.
* **Profil Pengguna**: Menampilkan nama akun aktif.

---

## 🔍 3. Cara Melakukan Pencarian Prospek (Scraping & Enrichment)

### Opsi 1: Mengetik Prompt Pencarian Khusus
Pada kotak prompt sentral:
1. Ketikkan kategori bisnis dan wilayah yang diinginkan secara spesifik.
   * *Contoh:* `dentists in Jakarta Selatan`
   * *Contoh:* `jasa interior design di Depok`
   * *Contoh:* `coffee shop near Canggu Bali`
2. Pilih jumlah prospek yang ingin diambil menggunakan tombol pill limit: **`10 leads`**, **`20 leads`**, atau **`50 leads`**.
3. Tekan tombol **`↑`** (atau tekan tombol `Enter`).

### Opsi 2: Menggunakan 4 Kartu Sinyal Siap Pakai (*Starting Points*)
Klik salah satu dari 4 kartu sinyal di bawah kotak prompt untuk menjalankan strategi outbound berbasis *trigger event*:
* **Recently Funded** (*Funding Signal*): Menargetkan bisnis bernilai tinggi yang siap berinvestasi pada solusi baru.
* **Currently Hiring** (*Hiring Signal*): Menargetkan klinik atau penyedia layanan yang membutuhkan efisiensi dan otomasi.
* **Rapidly Growing** (*Growth Signal*): Menargetkan studio desain/brand yang sedang bertumbuh pesat dan butuh upgrade sistem.
* **New Leadership** (*Leadership Signal*): Menargetkan kontraktor & jasa profesional yang siap merekrut vendor baru.

---

## 📊 4. Memahami Hasil Prospek & Status Pipeline

Setelah proses scraping dan enrichment selesai, Anda akan diarahkan ke halaman **Results View**:

### A. Metrik Utama Prospek (*Hero KPIs*)
* **Total Prospects**: Jumlah bisnis yang berhasil diambil dari Google Maps.
* **Verified Emails**: Persentase bisnis yang berhasil diekstraksi alamat email resminya dari homepage website mereka.
* **High-Intent (4–5★)**: Jumlah prospek berkualitas tinggi yang memenuhi kriteria penilaian (skor 4–5).
* **Social Intel**: Persentase prospek yang ditemukan akun Instagram, Facebook, LinkedIn, TikTok, atau X/Twitter-nya.

### B. Kolom Data pada Tabel Prospek
| Kolom | Keterangan |
|---|---|
| **Score** | Skor kualitas **1–5★** berdasarkan kepemilikan nomor telepon, website aktif, email, medsos, dan ulasan. |
| **Status** | Dropdown pipeline interaktif: **`New`**, **`Contacted`**, **`Qualified`**, **`Closed`**. |
| **Company & Rating** | Nama bisnis, kategori, dan rating bintang di Google Maps. |
| **Direct Contacts** | Email resmi yang ditemukan dan nomor telepon yang dapat dihubungi. |
| **Website & Socials** | Tautan ke website resmi dan profil media sosial bisnis. |
| **Outreach Pitch** | Tombol **`Inspect Pitch →`** untuk melihat dan menyalin draf email penawaran. |

---

## ✉️ 5. Menggunakan Slide-Over Pitch Drawer

Klik tombol **`Inspect Pitch →`** pada baris data mana pun untuk membuka panel samping:
1. **Intel Kontak Lengkap**: Klik tombol email untuk menyalin langsung (`📋 Copy`).
2. **Scoring Rubric Breakdown**: Melihat rincian alasan pemberian nilai skor pada prospek tersebut.
3. **Draf Email Personal (Cold Pitch)**:
   * Dibuat secara otomatis dengan mencantumkan nama bisnis, bidang kategori, dan nilai tambah yang relevan.
   * Klik **`📋 Copy Pitch Text`** untuk menyalin isi email.
   * Klik **`✉️ Launch Mail Client`** untuk langsung membuka aplikasi email Anda (Gmail/Apple Mail/Outlook) dengan subjek dan isi pesan yang sudah terisi otomatis.

---

## 📥 6. Mengekspor Data

* **Export CSV**: Klik tombol **`⬇️ Export CSV`** di bagian atas halaman hasil untuk mengunduh seluruh data prospek beserta kontak dan draf pitch ke dalam format file spreadsheet (.csv).
* **Push ke Google Sheets**: Klik tombol **`📊 Push to Sheets`** untuk mengirimkan data secara otomatis ke Google Spreadsheet yang telah dikonfigurasi.

---

## ⚙️ 7. Pengaturan & Konfigurasi API (Settings)

Klik tombol **`⚙️ Settings & System`** di sidebar kiri:
* **Tab API Keys**:
  * `SERPAPI_KEY`: Kunci API untuk scraping Google Maps (dapat diperoleh gratis 100 pencarian/bulan di [serpapi.com](https://serpapi.com)).
  * `OPENAI_API_KEY`: *(Opsional)* Kunci OpenAI jika ingin mengaktifkan pembuatan email dengan AI dinamis (`gpt-4o-mini`). Jika tidak diisi, sistem menggunakan template profesional bawaan.
* **Tab Outbound Persona**:
  * Mengatur *Sender Name*, *Agency/Company Name*, dan *Value Proposition* yang akan digunakan sebagai identitas pengirim pada draf email penawaran.
* **Tab Google Sheets**:
  * Memasukkan `Spreadsheet ID` atau URL Google Sheet tujuan sinkronisasi.
* **Tab DOE Directives**:
  * Melihat dokumentasi SOP (*Standard Operating Procedures*) teknis sistem.

---

## ❓ 8. FAQ & Tips Praktis

> **Q: Mengapa ada bisnis yang email-nya kosong?**  
> **A:** Beberapa listing Google Maps tidak memiliki tautan website, atau website bisnis tersebut menggunakan form kontak terenkripsi/tidak menampilkan email teks di homepage.

> **Q: Bagaimana jika kuota credit habis?**  
> **A:** Klik tombol **`Upgrade Plan`** pada sidebar untuk beralih ke paket *Pro* (350 credits) atau *Agency* (1.000 credits).

> **Q: Di mana file data disimpan secara lokal?**  
> **A:** Semua hasil pencarian berformat JSON dan laporan teks tersimpan di folder [`.tmp/`](file:///Users/bramdwi/Desktop/enrich_gmb_leads/.tmp) dan aman untuk diproses ulang kapan saja.
