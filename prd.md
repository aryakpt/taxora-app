# PRODUCT REQUIREMENTS DOCUMENT (PRD)
## AI Tax Assistant Indonesia — MVP

**Versi:** 1.0  
**Status:** Draft untuk implementasi  
**Produk:** AI Tax Assistant Indonesia  
**Jenis aplikasi:** Web application berbasis AI  
**Bahasa utama:** Bahasa Indonesia  
**Domain awal:** Pajak Penghasilan (PPh) dan Pajak Pertambahan Nilai (PPN)

---

# 1. Product Overview

## 1.1 Latar Belakang

AI Tax Assistant Indonesia merupakan aplikasi konsultasi perpajakan berbasis AI yang membantu pengguna memahami ketentuan perpajakan Indonesia melalui percakapan bahasa natural.

Aplikasi menggunakan pendekatan Retrieval-Augmented Generation (RAG) untuk mengambil informasi dari dokumen peraturan yang telah diindeks, kemudian menghasilkan jawaban yang dilengkapi dasar hukum, kutipan, dan tautan sumber.

Aplikasi tidak hanya berfungsi sebagai chatbot generik. Nilai utamanya adalah kemampuan untuk:

1. Menjawab pertanyaan berdasarkan dokumen hukum yang dapat diverifikasi.
2. Mengidentifikasi peraturan dan pasal yang relevan.
3. Memperhatikan periode berlakunya ketentuan perpajakan.
4. Meminta klarifikasi jika informasi kasus pengguna belum mencukupi.
5. Membedakan sumber peraturan resmi dengan dokumen penjelas internal.
6. Menyatakan ketidakpastian ketika bukti yang tersedia tidak memadai.

## 1.2 Product Vision

Menjadi asisten konsultasi perpajakan Indonesia yang membantu masyarakat memahami aturan pajak secara lebih mudah, transparan, dan berbasis sumber hukum yang dapat ditelusuri.

## 1.3 Product Goals

- Menyediakan chatbot konsultasi PPh dan PPN.
- Mengimplementasikan RAG dengan hybrid retrieval.
- Menampilkan dasar hukum yang mendukung jawaban.
- Mengelola metadata dan versi dokumen peraturan.
- Mendukung pencarian berdasarkan tanggal atau periode pajak.
- Mendukung dokumen internal dengan kontrol akses.
- Menyediakan evaluasi kualitas retrieval dan jawaban.
- Membuat fondasi teknis yang dapat diperluas ke otomatisasi perpajakan pada tahap berikutnya.

## 1.4 Non-Goals

Fitur berikut tidak termasuk MVP:

- Pengisian dan pengiriman SPT secara otomatis.
- Integrasi langsung dengan sistem administrasi DJP.
- Perhitungan dan pelaporan pajak otomatis yang bersifat definitif.
- Crawling dan analisis laporan keuangan perusahaan sebagai produk terpisah.
- Integrasi SLIK OJK atau credit scoring.
- Pengambilan data wajib pajak dari sistem pemerintah yang membutuhkan otorisasi khusus.
- Fine-tuning model bahasa sebagai kebutuhan awal.
- Penggantian konsultasi profesional untuk kasus kompleks.

---

# 2. Target Users

## 2.1 Primary Users

Aplikasi ditujukan kepada pengguna umum dengan beragam profil, termasuk:

- Wajib pajak orang pribadi.
- Pelaku UMKM.
- Pemilik usaha.
- Karyawan yang ingin memahami kewajiban PPh.
- Pengusaha yang ingin memahami ketentuan PPN.
- Pengguna yang ingin menemukan dasar hukum atas pertanyaan perpajakan.

## 2.2 Admin Users

Administrator bertanggung jawab atas pengelolaan knowledge base, validasi dokumen, pemantauan proses ingestion, dan evaluasi kualitas sistem.

## 2.3 Reviewer Users

Reviewer merupakan pengguna internal yang memiliki kewenangan untuk memeriksa kualitas dokumen atau jawaban, memverifikasi metadata hukum, dan menyetujui dokumen sebelum dipublikasikan ke knowledge base.

Peran administrator dan reviewer dapat digabungkan pada tahap awal, tetapi izin dan tindakan administratif harus tetap dibedakan secara logis.

---

# 3. Product Scope

## 3.1 MVP Features

| ID | Fitur | Prioritas |
|---|---|---|
| FR-01 | Chat interface | P0 |
| FR-02 | AI-powered tax Q&A | P0 |
| FR-03 | Regulatory knowledge base | P0 |
| FR-04 | Hybrid retrieval | P0 |
| FR-05 | Citation and source panel | P0 |
| FR-06 | Tax period awareness | P0 |
| FR-07 | Conversation history | P1 |
| FR-08 | Clarification questions | P1 |
| FR-09 | Document ingestion management | P1 |
| FR-10 | Internal document access control | P0 |
| FR-11 | Feedback mechanism | P1 |
| FR-12 | Evaluation and monitoring | P0 |
| FR-13 | Regulation change relationships | P1 |
| FR-14 | Admin knowledge base dashboard | P1 |

P0 berarti wajib tersedia untuk pilot MVP. P1 berarti dapat dikembangkan setelah alur inti berfungsi, selama dependensi keamanan dan kualitas tetap terpenuhi.

## 3.2 Tax Domain Scope

Knowledge base awal mencakup:

### PPh

- Konsep dan ketentuan umum PPh.
- Subjek dan objek pajak.
- Tarif dan dasar pengenaan yang relevan.
- PPh orang pribadi.
- PPh badan.
- PPh pemotongan atau pemungutan yang dipilih untuk cakupan awal.
- Kewajiban administrasi yang berkaitan dengan ketentuan tersebut.

### PPN

- Konsep dasar PPN.
- Barang dan jasa yang relevan terhadap ketentuan PPN.
- Pengusaha Kena Pajak (PKP).
- Tarif dan dasar pengenaan pajak.
- Pengecualian dan fasilitas yang relevan.
- Kewajiban administrasi PPN.

Cakupan setiap topik harus ditentukan melalui inventaris dokumen dan dataset evaluasi. Sistem tidak boleh mengklaim mendukung seluruh ketentuan PPh dan PPN sebelum kelengkapan knowledge base diverifikasi.

---

# 4. Functional Requirements

## FR-01 — Chat Interface

**Description:** Pengguna dapat mengajukan pertanyaan perpajakan melalui antarmuka percakapan.

Requirements:

- Pengguna dapat mengetik pertanyaan dalam bahasa Indonesia.
- Pengguna dapat mengirim pertanyaan menggunakan tombol atau keyboard.
- Sistem menampilkan indikator proses selama jawaban sedang dibuat.
- Sistem menampilkan jawaban dalam format yang mudah dibaca.
- Sistem menampilkan sumber hukum yang mendukung jawaban.
- Sistem menampilkan pesan kesalahan jika permintaan gagal.
- Sistem menyediakan tombol untuk mengirim pertanyaan lanjutan.
- Sistem tidak menampilkan jawaban sukses jika proses backend gagal.

Acceptance criteria:

- Pengguna dapat mengirim dan menerima jawaban melalui chat.
- UI membedakan pesan pengguna dan jawaban AI.
- Loading, error, dan empty states tersedia.
- Respons yang mengandung sitasi menampilkan sumber yang dapat dibuka.
- Antarmuka tidak menampilkan data percakapan pengguna lain.

## FR-02 — AI Tax Consultation

**Description:** Sistem menghasilkan jawaban perpajakan berdasarkan pertanyaan dan evidence yang ditemukan.

Requirements:

- Sistem mengidentifikasi topik PPh atau PPN.
- Sistem mengambil dokumen relevan dari knowledge base.
- Sistem menyusun jawaban berdasarkan evidence yang tersedia.
- Sistem membedakan fakta yang diberikan pengguna dari asumsi.
- Sistem mengajukan pertanyaan klarifikasi jika informasi penting belum tersedia.
- Sistem menyatakan keterbatasan jika bukti tidak cukup.
- Sistem tidak boleh membuat nomor peraturan, pasal, kutipan, atau URL sumber yang tidak terverifikasi.
- Sistem tidak boleh menyimpulkan bahwa suatu ketentuan berlaku hanya karena ditemukan melalui semantic search.

Acceptance criteria:

- Jawaban substantif memiliki referensi evidence yang valid.
- Jawaban tidak mengarang sumber hukum.
- Ketika sumber tidak mencukupi, sistem menyatakan keterbatasan dan tidak mengarang kesimpulan.
- Ketika fakta kasus belum mencukupi, sistem meminta klarifikasi yang relevan.

## FR-03 — Regulatory Knowledge Base

**Description:** Sistem menyimpan dokumen peraturan dan bagian-bagian hukum dalam struktur yang dapat dicari.

Sumber awal:

- Database Peraturan BPK.
- JDIH Kementerian Keuangan.
- Peraturan dan publikasi regulasi DJP.
- Dokumen internal yang penggunaannya telah diizinkan.

Contoh sumber awal:

- https://peraturan.bpk.go.id/Details/348562/pmk-no-28-tahun-2026
- https://www.jdih.kemenkeu.go.id/
- https://pajak.go.id/id/peraturan

Requirements:

- Sistem menyimpan URL sumber.
- Sistem menyimpan metadata peraturan.
- Sistem menyimpan versi dan hash dokumen.
- Sistem menyimpan tanggal penetapan dan tanggal berlaku jika tersedia.
- Sistem menyimpan status verifikasi dokumen.
- Sistem memisahkan dokumen resmi dari dokumen internal.
- Sistem mendukung perubahan dan pengindeksan ulang dokumen.
- Sistem mempertahankan hubungan antara chunk, pasal, ayat, versi, dan peraturan induk.
- Sistem tidak mengasumsikan bahwa seluruh dokumen pada suatu situs otomatis lengkap atau mutakhir.

Acceptance criteria:

- Setiap chunk dapat ditelusuri kembali ke dokumen dan bagian sumbernya.
- Dokumen dengan hash yang sama tidak diproses sebagai versi baru tanpa alasan.
- Perubahan dokumen dapat terdeteksi.
- Dokumen yang belum lolos validasi tidak otomatis dipublikasikan sebagai evidence terverifikasi.

## FR-04 — Hybrid Retrieval

**Description:** Sistem mencari sumber hukum menggunakan keyword search dan vector search.

Requirements:

- Implementasikan semantic search menggunakan embedding.
- Implementasikan keyword search menggunakan PostgreSQL full-text search atau mekanisme setara.
- Gabungkan hasil pencarian menggunakan metode ranking yang terukur, seperti Reciprocal Rank Fusion.
- Terapkan metadata filtering sebelum evidence diberikan kepada LLM.
- Gunakan reranking jika tersedia dan meningkatkan kualitas retrieval.
- Batasi jumlah evidence yang diberikan ke model.
- Pertahankan ID chunk dan metadata sumber selama proses retrieval.

Acceptance criteria:

- Pencarian nomor peraturan dan istilah hukum dapat menemukan dokumen yang tepat.
- Pencarian menggunakan bahasa natural dapat menemukan bagian yang relevan.
- Hasil retrieval dapat diperiksa dan dievaluasi secara terpisah dari kualitas generasi jawaban.
- Dokumen yang tidak memiliki izin akses tidak muncul dalam evidence.

## FR-05 — Citation and Source Panel

**Description:** Sistem menampilkan sumber hukum yang mendukung jawaban.

Setiap sumber idealnya memuat:

- Jenis dan nomor peraturan.
- Judul peraturan.
- Pasal atau ayat yang relevan.
- Kutipan yang sesuai dengan dokumen.
- URL sumber resmi.
- Status verifikasi.
- Informasi periode berlaku jika telah diverifikasi.

Acceptance criteria:

- Setiap referensi berasal dari record knowledge base yang benar-benar ada.
- Kutipan sesuai dengan teks sumber yang disimpan.
- Tautan menuju sumber yang tepat.
- Sistem tidak menganggap keberadaan sumber sebagai bukti bahwa seluruh klaim dalam jawaban didukung sumber tersebut.

## FR-06 — Tax Period Awareness

**Description:** Sistem memperhatikan periode pajak atau tanggal transaksi yang disebutkan pengguna.

Requirements:

- Pengguna dapat menyebutkan periode pajak dalam pertanyaan.
- Sistem dapat meminta periode pajak jika diperlukan.
- Retrieval menggunakan informasi temporal yang tersedia.
- Sistem memperhatikan tanggal berlaku, perubahan, pencabutan, dan ketentuan peralihan yang telah diverifikasi.
- Sistem membedakan tanggal berlaku hukum dengan tanggal dokumen diindeks.
- Jika status hukum belum dapat ditentukan, sistem menyatakan keterbatasan.

Acceptance criteria:

- Pengujian terhadap kasus perubahan aturan menggunakan sumber acuan yang sesuai.
- Sistem tidak secara otomatis menggunakan dokumen terbaru untuk seluruh pertanyaan historis.
- Sistem tidak menyatakan ketentuan pasti berlaku jika metadata atau konteks hukumnya belum cukup.

## FR-07 — Conversation History

**Description:** Pengguna dapat melihat percakapan sebelumnya.

Requirements:

- Setiap percakapan terhubung ke pemiliknya.
- Pengguna hanya dapat mengakses percakapan yang diizinkan.
- Percakapan menyimpan pesan dan referensi evidence yang digunakan.
- Konteks percakapan dapat digunakan untuk pertanyaan lanjutan.
- Konteks tidak boleh mengesampingkan fakta baru atau periode pajak yang diperbarui pengguna.
- Pengguna dapat menghapus percakapan sesuai kebijakan retensi aplikasi.

Acceptance criteria:

- Histori dapat dimuat kembali.
- Isolasi antar-pengguna teruji.
- Penghapusan percakapan mengikuti kebijakan penyimpanan dan penghapusan data yang berlaku.

## FR-08 — Clarification Questions

**Description:** Sistem meminta informasi tambahan jika diperlukan untuk memberikan jawaban yang tepat.

Contoh informasi:

- Jenis wajib pajak.
- Jenis transaksi.
- Tanggal atau periode pajak.
- Status PKP.
- Jenis penghasilan atau aktivitas usaha.

Requirements:

- Sistem hanya menanyakan informasi yang relevan.
- Sistem tidak menganggap informasi yang tidak diberikan sebagai fakta.
- Sistem dapat memberikan jawaban umum jika memungkinkan, sambil menjelaskan informasi yang belum diketahui.
- Sistem tidak mengumpulkan data sensitif yang tidak diperlukan.

Acceptance criteria:

- Pertanyaan klarifikasi spesifik dan relevan.
- Sistem dapat melanjutkan analisis setelah pengguna memberikan informasi.
- Sistem membedakan informasi yang diketahui, diasumsikan, dan belum diketahui.

## FR-09 — Document Ingestion Management

**Description:** Administrator mengelola proses memasukkan dokumen ke knowledge base.

Requirements:

- Administrator dapat memasukkan URL sumber yang diizinkan atau mengunggah dokumen yang diperbolehkan.
- Sistem mengekstrak teks dokumen.
- Sistem mendukung OCR ketika diperlukan.
- Sistem mendeteksi duplikasi.
- Sistem membentuk struktur pasal dan ayat sejauh memungkinkan.
- Sistem menghasilkan embedding.
- Sistem menampilkan status proses.
- Sistem mencatat error dan kegagalan ekstraksi.
- Sistem mendukung validasi dan persetujuan sebelum dokumen aktif.
- Sistem menyediakan mekanisme re-indexing.

Acceptance criteria:

- Status ingestion dapat berupa queued, processing, review_required, approved, published, atau failed.
- Dokumen yang gagal diproses tidak diam-diam dianggap berhasil.
- Administrator dapat mengetahui alasan kegagalan.
- Dokumen internal tidak menjadi searchable bagi pengguna yang tidak memiliki izin.

## FR-10 — Internal Document Access Control

**Description:** Sistem mengelola akses ke dokumen internal.

Requirements:

- Dokumen internal memiliki klasifikasi dan kebijakan akses.
- Pengguna harus terautentikasi untuk mengakses dokumen yang dibatasi.
- Retrieval menerapkan authorization filter.
- Prompt LLM hanya memuat dokumen yang diizinkan.
- Cache dan conversation history tidak boleh membocorkan dokumen lintas pengguna atau tenant.
- Semua tindakan administratif penting dicatat.

Acceptance criteria:

- Pengujian akses negatif membuktikan bahwa pengguna tanpa izin tidak dapat mengambil isi dokumen internal.
- Sumber terbatas tidak ditampilkan dalam kutipan atau jawaban kepada pengguna yang tidak berhak.
- Penghapusan atau pencabutan izin berlaku pada query berikutnya sesuai mekanisme invalidasi yang diterapkan.

## FR-11 — User Feedback

**Description:** Pengguna dapat memberikan penilaian terhadap jawaban.

Requirements:

- Pengguna dapat memberi feedback positif atau negatif.
- Pengguna dapat memilih alasan, seperti sumber tidak relevan, jawaban salah, atau informasi kurang.
- Feedback dikaitkan dengan request dan versi sistem.
- Feedback digunakan untuk perbaikan dan evaluasi, bukan otomatis dianggap sebagai fakta hukum.

Acceptance criteria:

- Feedback tersimpan dan dapat ditelusuri.
- Feedback tidak langsung mengubah knowledge base tanpa proses validasi.

## FR-12 — Evaluation and Monitoring

**Description:** Sistem menyediakan mekanisme evaluasi dan observabilitas.

Requirements:

- Mencatat latency.
- Mencatat token usage dan biaya jika disediakan oleh provider.
- Mencatat retrieval result IDs.
- Mencatat status validasi sitasi.
- Mendukung dataset evaluasi tetap.
- Mendukung pengujian regresi ketika prompt, model, embedding, atau indeks berubah.
- Tidak menyimpan data sensitif secara berlebihan dalam log.

Acceptance criteria:

- Hasil evaluasi dapat dibandingkan antarversi.
- Kegagalan retrieval dan generasi dapat dibedakan.
- Perubahan yang menurunkan kualitas dapat dideteksi melalui regression test.

---

# 5. Technical Architecture

## 5.1 Recommended Stack

| Component | Technology |
|---|---|
| Frontend | React / Next.js + TypeScript |
| Backend | Python + FastAPI |
| Primary database | PostgreSQL |
| Vector search | pgvector |
| Keyword search | PostgreSQL full-text search |
| Original document storage | S3-compatible object storage |
| LLM | Provider API dengan structured output |
| Embedding | Multilingual embedding model |
| Background processing | Worker dan scheduler |
| Authentication | OIDC/OAuth 2.0 atau solusi setara |
| Testing | pytest, frontend testing framework, integration tests |
| Deployment | Docker-based deployment |

AI coding agent harus memeriksa repository yang tersedia sebelum memutuskan untuk menggunakan stack tersebut secara persis. Jika repository sudah memiliki teknologi yang sesuai, prioritaskan konsistensi dengan implementasi yang ada dan dokumentasikan setiap penyimpangan.

## 5.2 Backend Modules

Gunakan modular monolith dengan modul berikut:

- `auth`: authentication dan authorization.
- `chat`: pengelolaan request konsultasi.
- `conversation`: histori dan konteks percakapan.
- `query_understanding`: klasifikasi topik dan ekstraksi konteks.
- `retrieval`: keyword search, vector search, dan ranking.
- `regulations`: metadata dan versi peraturan.
- `ingestion`: ekstraksi, normalisasi, dan indexing.
- `legal_validation`: validasi temporal dan relasi peraturan.
- `generation`: penyusunan jawaban oleh LLM.
- `citation_validation`: validasi sumber dan kutipan.
- `evaluation`: dataset pengujian dan metrik.
- `observability`: logging, latency, dan biaya.

Setiap modul harus memiliki tanggung jawab yang jelas dan tidak mengakses database modul lain melalui logika yang tersebar tanpa batas.

## 5.3 Request Flow

1. Frontend mengirim pertanyaan ke backend.
2. Backend memverifikasi identitas dan akses pengguna.
3. Sistem mengidentifikasi topik dan konteks pertanyaan.
4. Sistem memeriksa apakah klarifikasi diperlukan.
5. Retrieval mencari evidence yang relevan.
6. Legal validation memeriksa metadata dan periode hukum.
7. Evidence assembly membentuk konteks untuk LLM.
8. LLM menghasilkan jawaban terstruktur.
9. Citation validator memeriksa sumber dan dukungan klaim.
10. Backend mengembalikan jawaban beserta referensi yang valid.
11. Request dan hasil evaluasi operasional dicatat dengan memperhatikan privasi.

Jika sumber tidak memadai, sistem harus menggunakan jalur insufficient-evidence dan tidak memaksakan jawaban definitif.

---

# 6. Data Model

Implementasikan tabel inti berikut.

## 6.1 `regulations`

Menyimpan identitas peraturan.

- `id`: UUID primary key.
- `regulation_number`: nomor peraturan.
- `regulation_type`: UU, PP, PMK, PER, dan lainnya.
- `title`: judul.
- `issuer`: instansi penerbit.
- `topic`: kategori pajak.
- `created_at`: waktu pembuatan record.

## 6.2 `regulation_versions`

Menyimpan versi dokumen.

- `id`: UUID primary key.
- `regulation_id`: foreign key.
- `source_url`: URL sumber.
- `document_hash`: hash dokumen.
- `issued_at`: tanggal penetapan.
- `effective_from`: tanggal mulai berlaku jika diketahui.
- `effective_until`: tanggal akhir berlaku jika diketahui.
- `status`: status verifikasi hukum.
- `verified_at`: waktu verifikasi.
- `created_at`: waktu ingestion.

## 6.3 `legal_provisions`

Menyimpan struktur hukum.

- `id`: UUID primary key.
- `version_id`: foreign key.
- `parent_id`: relasi hierarki.
- `provision_type`: bab, pasal, ayat, huruf, atau lampiran.
- `article_number`: nomor pasal.
- `paragraph_number`: nomor ayat.
- `ordinal`: urutan.
- `text`: teks sumber.

## 6.4 `document_chunks`

Menyimpan unit retrieval.

- `id`: UUID primary key.
- `provision_id`: foreign key.
- `chunk_text`: teks.
- `embedding`: vector dengan dimensi yang sesuai model.
- `token_count`: jumlah token jika tersedia.
- `index_version`: versi indeks.

## 6.5 `regulation_relations`

Menyimpan hubungan antarperaturan.

- `id`: UUID primary key.
- `source_version_id`: foreign key.
- `target_version_id`: foreign key.
- `relation_type`: amends, revokes, implements, atau references.
- `evidence_provision_id`: bagian sumber yang mendukung relasi.
- `effective_from`: waktu berlaku relasi jika diketahui.
- `verified_at`: waktu verifikasi relasi.

## 6.6 Application Tables

Buat tabel berikut:

- `users`
- `user_profiles`
- `conversations`
- `messages`
- `consultation_contexts`
- `answer_evidence`
- `document_access_policies`
- `ingestion_jobs`
- `evaluation_runs`
- `user_feedback`
- `audit_logs`

Gunakan foreign keys, constraint, indexes, dan migrations yang sesuai.

Jangan menggunakan data contoh sebagai pengganti metadata hukum yang belum diverifikasi. Data demo harus diberi label sebagai fixture atau sample.

---

# 7. API Requirements

Semua endpoint menggunakan prefix `/api/v1`.

## 7.1 Chat

`POST /api/v1/chat`

Request:

```json
{
  "conversation_id": null,
  "question": "Bagaimana ketentuan PPN untuk transaksi saya?",
  "context": {
    "tax_period": "2026",
    "taxpayer_type": "business",
    "transaction_type": null
  }
}
```

Response minimum:

```json
{
  "request_id": "uuid",
  "conversation_id": "uuid",
  "answer_status": "answered",
  "answer": "Jawaban berbasis evidence.",
  "claims": [],
  "sources": [],
  "missing_information": [],
  "limitations": [],
  "latency_ms": 1200
}
```

Nilai di atas merupakan contoh format, bukan hasil runtime. Gunakan Pydantic schemas untuk validasi request dan response. Nilai `answer_status` harus berupa enum yang didefinisikan dalam implementasi, minimal mencakup jawaban tersedia, klarifikasi diperlukan, bukti tidak cukup, dan kegagalan proses.

## 7.2 Conversations

- `GET /api/v1/conversations`
- `GET /api/v1/conversations/{id}`
- `DELETE /api/v1/conversations/{id}`

Semua endpoint harus memeriksa kepemilikan atau izin akses.

## 7.3 Regulations

- `GET /api/v1/regulations`
- `GET /api/v1/regulations/{id}`
- `GET /api/v1/regulations/{id}/provisions`

Endpoint hanya menampilkan dokumen dan metadata yang boleh dilihat oleh pengguna.

## 7.4 Feedback

`POST /api/v1/feedback`

## 7.5 Admin Ingestion

- `POST /api/v1/admin/ingestion`
- `GET /api/v1/admin/ingestion/{id}`
- `POST /api/v1/admin/ingestion/{id}/approve`
- `POST /api/v1/admin/ingestion/{id}/publish`

Endpoint administratif harus membutuhkan role yang sesuai.

---

# 8. RAG Implementation Requirements

## 8.1 Ingestion Pipeline

Implementasikan urutan berikut:

1. Acquire dokumen dari sumber yang diizinkan.
2. Simpan file asli beserta metadata sumber.
3. Hitung hash dokumen.
4. Ekstrak teks dari PDF atau format yang didukung.
5. Gunakan OCR jika diperlukan.
6. Normalisasi teks tanpa menghilangkan isi hukum.
7. Identifikasi bab, pasal, ayat, huruf, dan lampiran sejauh memungkinkan.
8. Simpan struktur hukum.
9. Bentuk chunks yang mempertahankan konteks pasal dan ayat.
10. Buat embedding.
11. Indeks teks untuk keyword search.
12. Validasi metadata dan kualitas ekstraksi.
13. Publikasikan dokumen yang telah disetujui.
14. Catat status dan hasil ingestion.

Ingestion harus idempotent sehingga proses yang diulang tidak menghasilkan duplikasi tanpa alasan.

## 8.2 Chunking Strategy

Prioritaskan struktur hukum dibandingkan fixed token chunking.

Requirements:

- Pertahankan hubungan antara chunk dan pasal/ayat.
- Jangan memisahkan pengecualian dari aturan utama tanpa konteks.
- Simpan referensi peraturan induk.
- Gunakan overlap hanya jika diperlukan.
- Jangan memodifikasi redaksi sumber hukum.
- Bedakan teks asli dan teks hasil normalisasi.

## 8.3 Retrieval Strategy

Urutan retrieval:

1. Extract query terms dan metadata yang diketahui.
2. Jalankan keyword search.
3. Jalankan vector search.
4. Terapkan authorization filters.
5. Gabungkan ranking.
6. Terapkan legal metadata filters.
7. Lakukan reranking jika tersedia.
8. Pilih evidence sesuai relevance dan batas konteks.
9. Kembalikan evidence beserta metadata dan ID sumber.

Parameter seperti top-k, embedding model, dan reranking threshold harus dapat dikonfigurasi serta dievaluasi, bukan dianggap optimal sejak awal.

## 8.4 Generation Strategy

Prompt LLM harus mewajibkan:

- Jawaban dalam bahasa Indonesia.
- Penggunaan evidence yang diberikan.
- Tidak membuat sumber atau kutipan baru.
- Pembedaan fakta, asumsi, dan ketidakpastian.
- Klarifikasi jika informasi kasus belum memadai.
- Pengungkapan keterbatasan jika evidence tidak cukup.
- Structured output sesuai schema.
- Penolakan terhadap instruksi yang ditemukan di dalam dokumen sumber jika instruksi tersebut berusaha mengubah kebijakan sistem.

## 8.5 Citation Validation

Backend harus memvalidasi:

- ID evidence benar-benar ada.
- Evidence merupakan bagian dari dokumen yang diizinkan.
- Metadata sumber sesuai record database.
- Kutipan sesuai teks sumber.
- Klaim yang disitasi memiliki dukungan evidence yang relevan.

Validasi struktur JSON saja tidak cukup. Klaim yang tidak didukung harus diperbaiki, diberi status tidak terverifikasi, atau dihilangkan dari kesimpulan definitif.

---

# 9. Security and Privacy Requirements

Implementasikan kontrol minimum berikut:

1. Secrets dan API keys disimpan melalui environment variables atau secret manager.
2. Jangan memasukkan secret ke source code atau repository.
3. Authentication dan authorization wajib untuk fitur yang membutuhkan identitas.
4. Akses dokumen internal dibatasi pada tingkat record dan tenant jika relevan.
5. Authorization filter diterapkan sebelum evidence masuk ke prompt.
6. Validasi file upload dan batasi tipe serta ukuran file.
7. Batasi request size, upload size, dan penggunaan LLM.
8. Terapkan rate limiting pada endpoint yang relevan.
9. Gunakan parameterized queries dan validasi input.
10. Jangan menyimpan informasi pajak sensitif dalam log secara berlebihan.
11. Tetapkan kebijakan retensi dan penghapusan data.
12. Audit tindakan administratif dan perubahan dokumen.
13. Lindungi dari prompt injection melalui dokumen dan user input.
14. Terapkan akses least privilege untuk database dan storage.
15. Pastikan error tidak mengekspos secret, prompt internal, atau dokumen terbatas.

Jangan mengklaim aplikasi sepenuhnya aman atau patuh terhadap regulasi hanya karena kontrol dasar telah diterapkan. Kesiapan produksi membutuhkan security review dan pemeriksaan kepatuhan yang sesuai.

---

# 10. Non-Functional Requirements

## 10.1 Performance

Target awal untuk pilot:

- Respons chat memiliki loading state.
- Backend mengembalikan hasil atau status proses yang jelas.
- Target p95 latency awal maksimal 15 detik untuk pertanyaan yang dapat dijawab, tidak termasuk antrean eksternal yang tidak dikendalikan aplikasi.
- Ingestion berjalan asynchronous.
- Timeout dan retry untuk kegagalan provider diterapkan secara terbatas.

Target latency harus dievaluasi terhadap model, ukuran konteks, dan lingkungan deployment yang dipilih.

## 10.2 Reliability

- Kegagalan LLM tidak menyebabkan crash seluruh backend.
- Kegagalan ingestion tercatat.
- Proses ingestion dapat diulang.
- Database migrations dapat dijalankan secara terkontrol.
- Error response konsisten.
- Regression tests dijalankan setelah perubahan retrieval atau prompt.

## 10.3 Maintainability

- Pisahkan business logic dari route handlers.
- Gunakan typed schemas.
- Dokumentasikan konfigurasi.
- Gunakan migrations.
- Hindari hardcoding model provider dan parameter retrieval.
- Gunakan dependency injection jika membantu testing.
- Sediakan README dan dokumentasi setup.

## 10.4 Observability

Catat sekurang-kurangnya:

- Request ID.
- Latency per tahap.
- Retrieval result IDs.
- Status citation validation.
- Model dan versi prompt.
- Token usage dan biaya jika tersedia.
- Status ingestion.
- Error code.

Jangan mencatat seluruh prompt atau data kasus sensitif secara default. Jika logging konten diperlukan untuk debugging, batasi akses dan gunakan mekanisme redaksi.

---

# 11. Evaluation Plan

Buat dataset evaluasi sekitar 200–300 pertanyaan sebagai target awal pilot.

Setiap item idealnya berisi:

- Pertanyaan.
- Fakta kasus.
- Periode pajak.
- Sumber dan pasal acuan.
- Jawaban acuan yang ditinjau reviewer.
- Status apakah evidence mencukupi.
- Kategori risiko kesalahan.

Kategori pertanyaan harus mencakup:

- Pertanyaan faktual PPh.
- Pertanyaan faktual PPN.
- Kasus penerapan sederhana.
- Kasus yang membutuhkan beberapa peraturan.
- Pertanyaan historis.
- Peraturan yang diubah atau dicabut.
- Pertanyaan ambigu.
- Dokumen internal terbatas.
- Pertanyaan di luar cakupan.

Bandingkan tiga konfigurasi:

A. LLM tanpa RAG.  
B. RAG standar.  
C. Legal-aware RAG dengan temporal filtering dan citation validation.

## 11.1 Proposed Acceptance Thresholds

Target berikut adalah ambang awal untuk dievaluasi dan disetujui tim, bukan hasil yang sudah dicapai.

| Metric | Initial Target |
|---|---:|
| Retrieval Recall@5 | ≥ 90% |
| Citation validity | ≥ 98% |
| Citation support | ≥ 90% |
| Answer correctness | ≥ 90% |
| Temporal accuracy | ≥ 95% |
| Access-control tests | 100% pass |
| Critical legal error | 0 known unresolved critical errors |

Definisikan denominator, metode sampling, dan kriteria penilaian setiap metrik. Evaluasi harus dilakukan pada dataset yang tidak digunakan untuk menyetel sistem.

Setiap kesalahan kritis yang ditemukan harus dianalisis. Angka agregat tidak boleh digunakan untuk menutupi kegagalan pada kasus berisiko tinggi.

---

# 12. User Interface Requirements

## 12.1 Main Chat Page

Komponen minimum:

- Application header.
- New conversation button.
- Conversation history.
- Chat message list.
- Input field.
- Send button.
- Loading indicator.
- Error message.
- Source citation panel.
- Feedback controls.

## 12.2 Answer Layout

Jawaban dapat ditampilkan dalam bagian:

1. Kesimpulan.
2. Penjelasan.
3. Dasar hukum.
4. Penerapan pada kasus.
5. Asumsi dan informasi yang belum diketahui.
6. Keterbatasan atau kebutuhan verifikasi.

Jangan memaksakan seluruh bagian jika tidak relevan. Jawaban sederhana sebaiknya tetap ringkas.

## 12.3 Source Panel

Setiap item sumber menampilkan:

- Nomor dan judul peraturan.
- Pasal atau ayat.
- Kutipan.
- Status verifikasi.
- Tanggal berlaku jika diketahui.
- Link ke sumber asli.

## 12.4 Admin Dashboard

Fitur minimum:

- Daftar dokumen.
- Status ingestion.
- Status verifikasi.
- Error ekstraksi.
- Metadata peraturan.
- Approval dan publication workflow.
- Riwayat perubahan.
- Hasil evaluasi.

---

# 13. Implementation Plan for AI Coding Agent

AI coding agent harus mengikuti tahapan implementasi berikut.

## Phase 0 — Repository Inspection

Sebelum menulis kode:

- Periksa struktur repository.
- Identifikasi framework dan dependency yang sudah tersedia.
- Periksa konfigurasi, migrations, testing, dan dokumentasi.
- Identifikasi bagian yang dapat digunakan kembali.
- Jangan menghapus atau mengganti teknologi yang sudah berjalan tanpa alasan teknis.
- Buat implementation plan dan daftar asumsi.

Deliverable: repository assessment dan implementation plan.

## Phase 1 — Foundation

Implementasikan:

- Project configuration.
- Environment configuration.
- Database connection.
- Database migrations.
- Authentication dan authorization dasar.
- Logging dan error handling.
- Health endpoint.
- Automated test setup.

Deliverable: aplikasi dapat dijalankan dan dites secara lokal.

## Phase 2 — Knowledge Base

Implementasikan:

- Regulation schema.
- Document ingestion.
- PDF text extraction.
- OCR integration point.
- Structural chunking.
- Embedding generation.
- Keyword indexing.
- Vector indexing.
- Document approval workflow.
- Source metadata.

Deliverable: dokumen dapat dimasukkan, diproses, dan dicari.

## Phase 3 — RAG Pipeline

Implementasikan:

- Query understanding.
- Hybrid retrieval.
- Metadata filtering.
- Evidence assembly.
- LLM integration.
- Structured output.
- Citation validation.
- Insufficient-evidence handling.

Deliverable: backend dapat menjawab pertanyaan menggunakan dokumen yang telah diindeks.

## Phase 4 — Frontend

Implementasikan:

- Chat interface.
- Conversation history.
- Source panel.
- Loading dan error states.
- Feedback.
- Admin dashboard dasar.

Deliverable: pengguna dapat menjalankan alur konsultasi dari UI.

## Phase 5 — Evaluation and Hardening

Implementasikan:

- Unit tests.
- Integration tests.
- Retrieval evaluation.
- Citation validation tests.
- Temporal regression tests.
- Access-control tests.
- Error handling tests.
- Performance measurement.
- Setup dan deployment documentation.

Deliverable: MVP memenuhi acceptance criteria yang telah ditetapkan atau melaporkan gap yang masih tersisa.

## Execution Rules

- Kerjakan secara bertahap dan dapat diuji.
- Jangan membuat seluruh aplikasi dalam satu perubahan besar.
- Jalankan tests setelah setiap tahap.
- Jangan menandai fitur selesai sebelum benar-benar diimplementasikan dan diuji.
- Jangan mengarang API key, kredensial, dokumen hukum, atau hasil evaluasi.
- Gunakan fixtures yang jelas diberi label untuk testing.
- Jika akses ke provider eksternal belum tersedia, buat adapter dan mock yang eksplisit; jangan berpura-pura integrasi sudah berhasil.
- Jika terjadi konflik requirement, prioritaskan keamanan, integritas sumber hukum, dan requirement yang eksplisit.
- Laporkan perubahan file, tests yang dijalankan, hasil aktual, keterbatasan, dan langkah berikutnya.

---

# 14. Definition of Done

MVP dianggap selesai untuk pilot ketika:

- [ ] Aplikasi dapat dijalankan melalui dokumentasi setup.
- [ ] Database migrations dapat dijalankan.
- [ ] Dokumen yang telah disetujui dapat diproses dan diindeks.
- [ ] Keyword search dan vector search berfungsi.
- [ ] Pengguna dapat mengajukan pertanyaan melalui UI.
- [ ] Jawaban menggunakan evidence yang diambil dari knowledge base.
- [ ] Citation validation diterapkan.
- [ ] Sistem dapat menangani insufficient evidence.
- [ ] Sistem mendukung konteks periode pajak.
- [ ] Akses dokumen internal telah diuji.
- [ ] Conversation history menerapkan ownership checks.
- [ ] Unit dan integration tests lulus.
- [ ] Evaluation dataset dan laporan hasil tersedia.
- [ ] Tidak ada critical legal error yang diketahui dan belum ditangani pada dataset acceptance.
- [ ] README menjelaskan setup, konfigurasi, ingestion, pengujian, dan deployment.
- [ ] Keterbatasan dan fitur yang belum selesai terdokumentasi.

Kelulusan acceptance criteria merupakan syarat untuk pilot, bukan bukti bahwa sistem sudah layak digunakan sebagai satu-satunya dasar pengambilan keputusan pajak.

---

# 15. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Dokumen tidak lengkap | Validasi kelengkapan dan cakupan sumber |
| Metadata tanggal salah | Review metadata dan temporal tests |
| Jawaban berhalusinasi | Evidence grounding dan citation validation |
| Chunking merusak konteks hukum | Structural chunking |
| Dokumen internal bocor | Access filtering dan security tests |
| Peraturan berubah | Re-ingestion dan version tracking |
| LLM gagal atau timeout | Error handling dan bounded retry |
| Biaya model meningkat | Token limits, monitoring, dan configurable models |
| Retrieval menemukan aturan yang tidak relevan | Hybrid search, reranking, dan metadata filtering |
| Evaluasi bias | Dataset held-out dan reviewer independen |
| Prompt injection | Treat retrieved documents as untrusted content |

---

# 16. Final Instructions to AI Coding Agent

Build the application according to this PRD, using it as the primary product specification.

Before implementation, inspect the existing repository and report the current architecture, available components, and any conflicts with the specification.

Implement the MVP incrementally, starting with the data foundation and a working RAG pipeline. Prioritize source integrity, legal metadata, citation traceability, temporal correctness, and access control over visual polish or additional features.

Use real integrations only when credentials and access are available. Do not fabricate regulation content, successful API responses, evaluation scores, or external system capabilities.

Keep configuration externalized. Provide database migrations, tests, sample environment configuration, a README, and an implementation report.

When a requirement cannot be completed because an external dependency, source, or credential is unavailable, implement an explicit interface or safe fallback and document the limitation.

Do not implement automatic SPT filing, SLIK OJK integration, or company financial intelligence in this MVP.

The final deliverable must be a runnable, testable application with a documented setup process—not merely a prototype UI or a collection of code snippets.
