const en = {
  language: { select: 'Select language', english: 'English', indonesian: 'Bahasa Indonesia' },
  common: { documentTitle: 'Taxora — Tax, made clearer', close: 'Close', workspace: 'Workspace', secureWorkspace: 'Secure workspace', help: 'Help', loading: 'Loading…', published: 'Published', originalSource: 'Original source', refresh: 'Refresh' },
  navigation: {
    closeNavigation: 'Close navigation', openNavigation: 'Open navigation', toggleSidebar: 'Toggle sidebar', newConversation: 'New consultation', workspace: 'WORKSPACE', taxAssistant: 'Tax assistant', regulationLibrary: 'Regulation library', knowledgeAdmin: 'Knowledge admin', recent: 'RECENT', searchConversations: 'Search conversations', emptyHistory: 'Your consultations will appear here.', evidenceFirst: 'Evidence-first answers', sourcesToVerify: 'Sources you can verify.', signOut: 'Sign out', signedIn: 'Signed in',
  },
  chat: {
    eyebrow: 'YOUR INDONESIAN TAX COMPANION', title: 'Tax, made clearer.', subtitle: 'Grounded guidance on Indonesian tax regulations, with sources you can verify.', evidenceGrounded: 'Evidence-grounded', sourceCited: 'Source-cited', periodAware: 'Period-aware', promptHeading: 'START WITH A QUESTION', promptHint: 'Choose a prompt or write your own', disclaimer: 'Answers are based on available sources and are not a substitute for professional tax advice.',
    prompts: {
      ppn: { label: 'Understand PPN', question: 'What should I know about PPN for a small business?' },
      pph: { label: 'Explore PPh', question: 'How does personal income tax work in Indonesia?' },
      regulation: { label: 'Check a regulation', question: 'How can I find the current rules for becoming a PKP?' },
      period: { label: 'Ask about a period', question: 'What tax rules apply to a transaction in 2024?' },
    },
  },
  composer: { questionLabel: 'Ask a tax question', questionPlaceholder: 'Ask about Indonesian tax. Mention the tax year and the kind of taxpayer if they matter…', send: 'Send', sendLabel: 'Send question', keyboard: '↵ to send · ⇧ ↵ new line', disclaimer: 'Taxora can make mistakes. Verify important information against official sources.' },
  messages: {
    assistant: 'Taxora assistant', user: 'You', aiResponse: 'AI response', reviewingSources: 'Reviewing sources', loadingAnswer: 'Searching verified sources and preparing an answer. This can take up to a minute.',
    generalAnswer: 'General AI knowledge · not verified against regulations', insufficientEvidence: 'Insufficient verified evidence', clarificationNeeded: 'More information may help', outOfScope: 'Outside Taxora\'s scope', failed: 'The answer could not be completed', clarify: 'Information to clarify', limitations: 'Limitations', legalBasis: 'Legal basis', source: 'source', sources: 'sources', regulation: 'REGULATION', effective: 'Effective {{date}}', effectiveUnknown: 'Effective date not specified', viewOriginal: 'View original source', helpful: 'Helpful answer', unhelpful: 'Unhelpful answer',
  },
  history: { actions: 'Actions for {{title}}', rename: 'Rename', renameLabel: 'Conversation name', delete: 'Delete', cancel: 'Cancel', confirmTitle: 'Delete conversation?', confirmText: '“{{title}}” and all its messages will be deleted. This cannot be undone.' },
  account: { menu: 'Account', unnamed: 'Account', roles: { user: 'User', reviewer: 'Reviewer', admin: 'Admin' } },
  regulations: { eyebrow: 'KNOWLEDGE BASE', title: 'Regulation library', intro: 'Browse published regulations available to the assistant. Each entry links to its original source.', emptyTitle: 'No published regulations found', emptyDescription: 'Only approved, published documents appear here. Connect to the backend and check again later.' },
  admin: {
    eyebrow: 'ADMINISTRATION', title: 'Knowledge admin', intro: 'Add official regulations to the knowledge base. Every document is reviewed against its source before the assistant can use it.', reviewerIntro: 'Check extracted documents against their official source, then approve them for publication.',
    submitted: 'Document queued for processing.', formTitle: 'Add a regulation', formDescription: 'Metadata is entered by you, never guessed by AI. The document stays hidden from users until it is approved and published.',
    sourceMode: 'Document source', modeUrl: 'Official link', modeUpload: 'Upload PDF', file: 'PDF file', fileHint: 'Text-based PDF, max 30 MB. Scanned documents are not supported yet.',
    sourceUrl: 'Official source URL', sourceUrlHint: 'Direct PDF download link from peraturan.bpk.go.id, jdih.kemenkeu.go.id or pajak.go.id (not the detail page).', sourceUrlUploadHint: 'The official link shown to users as the citation source.',
    regulationNumber: 'Regulation number', regulationNumberPlaceholder: 'e.g. 28 TAHUN 2026', regulationType: 'Regulation type', titleField: 'Title', titlePlaceholder: 'Full regulation title', issuer: 'Issuing authority', topic: 'Topic', other: 'Other',
    issuedAt: 'Issued on', effectiveFrom: 'Effective from', effectiveUntil: 'Effective until', datesHint: 'Optional now; the reviewer can still fill in the dates. Without an effective date the document applies to every tax period.',
    submit: 'Submit for processing', submitting: 'Submitting…', recentJobs: 'Ingestion jobs', autoRefresh: 'Updating automatically', noJobs: 'No ingestion jobs yet.', noDetails: 'No additional details',
    statuses: { queued: 'Queued', processing: 'Processing', review_required: 'Review required', approved: 'Approved', published: 'Published', failed: 'Failed' },
    review: {
      title: 'Document review', result: 'Result', error: 'Error', verifiedAt: 'Approved on', downloadOriginal: 'Download stored original',
      dates: 'Regulation dates', saveDates: 'Save dates', datesSaved: 'Dates saved.', datesFrozen: 'Dates are locked after approval. An admin can fix them with Correct metadata.',
      sections: 'Extracted sections', sectionCount_one: '{{count}} section', sectionCount_other: '{{count}} sections', article: 'Article {{number}}', sectionMeta: '{{chars}} characters · {{chunks}} chunks',
      kinds: { preamble: 'Preamble', attachment: 'Attachment', article: 'Article' },
      noEffectiveDate: 'No effective date set: the document will be used for every tax period.', confirm: 'I compared the extracted text and metadata with the official source.',
      approve: 'Approve', approved: 'Document approved. An admin can now publish it.', saveFirst: 'Save or undo the date changes first.',
      publish: 'Publish', published: 'Document published. The assistant can now cite it.', waitingForAdmin: 'Approved. Waiting for an admin to publish.',
      retry: 'Retry', retried: 'Job queued again.', isPublished: 'Published and available to the assistant and the regulation library.',
    },
    correction: {
      title: 'Correct metadata', open: 'Correct metadata', intro: 'Fix wrong dates, title, issuer or topic. The legal text and the regulation number stay as reviewed; re-submit the document if those are wrong.',
      reason: 'Reason for the correction', reasonPlaceholder: 'e.g. Effective date per Article 27: 1 May 2026', save: 'Save correction', cancel: 'Cancel',
      saved: 'Metadata corrected and recorded in the audit log.', liveNote: 'This document is published: the assistant uses the new values immediately.', history: 'Correction history',
      fields: { title: 'Title', issuer: 'Issuer', topic: 'Topic', issued_at: 'Issued on', effective_from: 'Effective from', effective_until: 'Effective until' },
    },
  },
  auth: { secureAccount: 'SECURE ACCOUNT ACCESS', loginTitle: 'Welcome back', registerTitle: 'Create your account', loginDescription: 'Sign in to continue your Indonesian tax consultation.', registerDescription: 'Create an account to save and revisit your consultations.', fullName: 'Full name', email: 'Email address', password: 'Password', confirmPassword: 'Confirm password', passwordRequirement: 'Use at least 12 characters.', passwordsDoNotMatch: 'The passwords do not match.', invalidCredentials: 'Email or password is incorrect.', emailAlreadyRegistered: 'An account with this email already exists.', requestFailed: 'We could not complete the request. Please try again.', working: 'Please wait…', signIn: 'Sign in', createAccount: 'Create account', noAccount: 'New to Taxora?', hasAccount: 'Already have an account?', providerKeyNotice: 'Taxora provides AI access. You do not need to provide an AI provider API key.', footer: 'Your session is protected with an HTTP-only cookie.', checkingSession: 'Checking your session…', orWithEmail: 'or with email', googleFailed: 'Google sign-in failed. Please try again.', googleEmailTaken: 'This email is already linked to a different Google account.' },
} as const

type TranslationShape<T> = {
  [Key in keyof T]: T[Key] extends string ? string : TranslationShape<T[Key]>
}

const id: TranslationShape<typeof en> = {
  language: { select: 'Pilih bahasa', english: 'English', indonesian: 'Bahasa Indonesia' },
  common: { documentTitle: 'Taxora — Pajak lebih mudah dipahami', close: 'Tutup', workspace: 'Ruang kerja', secureWorkspace: 'Ruang kerja aman', help: 'Bantuan', loading: 'Memuat…', published: 'Dipublikasikan', originalSource: 'Sumber asli', refresh: 'Muat ulang' },
  navigation: {
    closeNavigation: 'Tutup navigasi', openNavigation: 'Buka navigasi', toggleSidebar: 'Tampilkan/sembunyikan sidebar', newConversation: 'Konsultasi baru', workspace: 'RUANG KERJA', taxAssistant: 'Asisten pajak', regulationLibrary: 'Pustaka peraturan', knowledgeAdmin: 'Admin knowledge base', recent: 'TERBARU', searchConversations: 'Cari percakapan', emptyHistory: 'Percakapan Anda akan muncul di sini.', evidenceFirst: 'Jawaban berbasis bukti', sourcesToVerify: 'Sumber yang dapat diverifikasi.', signOut: 'Keluar', signedIn: 'Sudah masuk',
  },
  chat: {
    eyebrow: 'ASISTEN PAJAK INDONESIA ANDA', title: 'Pajak, lebih mudah dipahami.', subtitle: 'Panduan berbasis peraturan pajak Indonesia, dilengkapi sumber yang dapat Anda verifikasi.', evidenceGrounded: 'Berbasis bukti', sourceCited: 'Dengan sitasi sumber', periodAware: 'Memperhatikan periode', promptHeading: 'MULAI DENGAN PERTANYAAN', promptHint: 'Pilih pertanyaan atau tulis sendiri', disclaimer: 'Jawaban berdasarkan sumber yang tersedia dan bukan pengganti konsultasi profesional perpajakan.',
    prompts: {
      ppn: { label: 'Memahami PPN', question: 'Apa yang perlu diketahui usaha kecil tentang PPN?' },
      pph: { label: 'Mengenal PPh', question: 'Bagaimana cara kerja pajak penghasilan orang pribadi di Indonesia?' },
      regulation: { label: 'Cari peraturan', question: 'Bagaimana cara mengetahui ketentuan terbaru untuk menjadi PKP?' },
      period: { label: 'Tanya periode pajak', question: 'Ketentuan pajak apa yang berlaku untuk transaksi pada tahun 2024?' },
    },
  },
  composer: { questionLabel: 'Ajukan pertanyaan pajak', questionPlaceholder: 'Tanyakan tentang pajak Indonesia. Sebutkan tahun pajak dan jenis wajib pajak jika relevan…', send: 'Kirim', sendLabel: 'Kirim pertanyaan', keyboard: '↵ untuk kirim · ⇧ ↵ baris baru', disclaimer: 'Taxora dapat keliru. Verifikasi informasi penting melalui sumber resmi.' },
  messages: {
    assistant: 'Asisten Taxora', user: 'Anda', aiResponse: 'Jawaban AI', reviewingSources: 'Meninjau sumber', loadingAnswer: 'Mencari sumber terverifikasi dan menyiapkan jawaban. Ini bisa memakan waktu hingga satu menit.',
    generalAnswer: 'Pengetahuan umum AI · belum diverifikasi dengan peraturan', insufficientEvidence: 'Bukti terverifikasi belum memadai', clarificationNeeded: 'Informasi tambahan dapat membantu', outOfScope: 'Di luar cakupan Taxora', failed: 'Jawaban tidak dapat diselesaikan', clarify: 'Informasi yang perlu diklarifikasi', limitations: 'Keterbatasan', legalBasis: 'Dasar hukum', source: 'sumber', sources: 'sumber', regulation: 'PERATURAN', effective: 'Berlaku {{date}}', effectiveUnknown: 'Tanggal berlaku tidak dicantumkan', viewOriginal: 'Lihat sumber asli', helpful: 'Jawaban membantu', unhelpful: 'Jawaban tidak membantu',
  },
  history: { actions: 'Tindakan untuk {{title}}', rename: 'Ganti nama', renameLabel: 'Nama percakapan', delete: 'Hapus', cancel: 'Batal', confirmTitle: 'Hapus percakapan?', confirmText: '“{{title}}” beserta semua pesannya akan dihapus. Tindakan ini tidak dapat dibatalkan.' },
  account: { menu: 'Akun', unnamed: 'Akun', roles: { user: 'Pengguna', reviewer: 'Reviewer', admin: 'Admin' } },
  regulations: { eyebrow: 'KNOWLEDGE BASE', title: 'Pustaka peraturan', intro: 'Jelajahi peraturan yang telah dipublikasikan dan tersedia bagi asisten. Setiap entri terhubung ke sumber aslinya.', emptyTitle: 'Tidak ada peraturan yang dipublikasikan', emptyDescription: 'Hanya dokumen yang disetujui dan dipublikasikan yang ditampilkan. Hubungkan ke backend dan coba lagi nanti.' },
  admin: {
    eyebrow: 'ADMINISTRASI', title: 'Admin knowledge base', intro: 'Tambahkan peraturan resmi ke knowledge base. Setiap dokumen ditinjau terhadap sumbernya sebelum dapat digunakan asisten.', reviewerIntro: 'Periksa dokumen hasil ekstraksi terhadap sumber resminya, lalu setujui untuk dipublikasikan.',
    submitted: 'Dokumen masuk antrean pemrosesan.', formTitle: 'Tambah peraturan', formDescription: 'Metadata diisi oleh Anda, tidak pernah ditebak AI. Dokumen tersembunyi dari pengguna sampai disetujui dan dipublikasikan.',
    sourceMode: 'Sumber dokumen', modeUrl: 'Tautan resmi', modeUpload: 'Unggah PDF', file: 'File PDF', fileHint: 'PDF berbasis teks, maks. 30 MB. Dokumen hasil scan belum didukung.',
    sourceUrl: 'URL sumber resmi', sourceUrlHint: 'Tautan unduhan PDF langsung dari peraturan.bpk.go.id, jdih.kemenkeu.go.id, atau pajak.go.id (bukan halaman detail).', sourceUrlUploadHint: 'Tautan resmi yang ditampilkan ke pengguna sebagai sumber kutipan.',
    regulationNumber: 'Nomor peraturan', regulationNumberPlaceholder: 'mis. 28 TAHUN 2026', regulationType: 'Jenis peraturan', titleField: 'Judul', titlePlaceholder: 'Judul lengkap peraturan', issuer: 'Instansi penerbit', topic: 'Topik', other: 'Lainnya',
    issuedAt: 'Tanggal ditetapkan', effectiveFrom: 'Berlaku mulai', effectiveUntil: 'Berlaku sampai', datesHint: 'Opsional sekarang; reviewer masih bisa mengisinya. Tanpa tanggal berlaku, dokumen dipakai untuk semua periode pajak.',
    submit: 'Kirim untuk diproses', submitting: 'Mengirim…', recentJobs: 'Job ingestion', autoRefresh: 'Diperbarui otomatis', noJobs: 'Belum ada job ingestion.', noDetails: 'Tidak ada detail tambahan',
    statuses: { queued: 'Dalam antrean', processing: 'Diproses', review_required: 'Perlu ditinjau', approved: 'Disetujui', published: 'Dipublikasikan', failed: 'Gagal' },
    review: {
      title: 'Tinjauan dokumen', result: 'Hasil', error: 'Kesalahan', verifiedAt: 'Disetujui pada', downloadOriginal: 'Unduh dokumen asli yang tersimpan',
      dates: 'Tanggal peraturan', saveDates: 'Simpan tanggal', datesSaved: 'Tanggal disimpan.', datesFrozen: 'Tanggal terkunci setelah disetujui. Admin dapat memperbaikinya lewat Koreksi metadata.',
      sections: 'Bagian hasil ekstraksi', sectionCount_one: '{{count}} bagian', sectionCount_other: '{{count}} bagian', article: 'Pasal {{number}}', sectionMeta: '{{chars}} karakter · {{chunks}} potongan',
      kinds: { preamble: 'Pembukaan', attachment: 'Lampiran', article: 'Pasal' },
      noEffectiveDate: 'Tanggal berlaku belum diisi: dokumen akan dipakai untuk semua periode pajak.', confirm: 'Saya sudah membandingkan teks hasil ekstraksi dan metadata dengan sumber resmi.',
      approve: 'Setujui', approved: 'Dokumen disetujui. Admin sekarang bisa mempublikasikannya.', saveFirst: 'Simpan atau batalkan perubahan tanggal dulu.',
      publish: 'Publikasikan', published: 'Dokumen dipublikasikan. Asisten sekarang bisa mengutipnya.', waitingForAdmin: 'Disetujui. Menunggu admin mempublikasikan.',
      retry: 'Ulangi', retried: 'Job dimasukkan ke antrean lagi.', isPublished: 'Dipublikasikan dan tersedia untuk asisten serta pustaka peraturan.',
    },
    correction: {
      title: 'Koreksi metadata', open: 'Koreksi metadata', intro: 'Perbaiki tanggal, judul, instansi, atau topik yang keliru. Teks pasal dan nomor peraturan tetap seperti yang sudah ditinjau; kirim ulang dokumen jika keduanya salah.',
      reason: 'Alasan koreksi', reasonPlaceholder: 'mis. Tanggal berlaku sesuai Pasal 27: 1 Mei 2026', save: 'Simpan koreksi', cancel: 'Batal',
      saved: 'Metadata dikoreksi dan dicatat di audit log.', liveNote: 'Dokumen ini sudah dipublikasikan: asisten langsung memakai nilai baru.', history: 'Riwayat koreksi',
      fields: { title: 'Judul', issuer: 'Instansi', topic: 'Topik', issued_at: 'Tanggal ditetapkan', effective_from: 'Berlaku mulai', effective_until: 'Berlaku sampai' },
    },
  },
  auth: { secureAccount: 'AKSES AKUN YANG AMAN', loginTitle: 'Selamat datang kembali', registerTitle: 'Buat akun Anda', loginDescription: 'Masuk untuk melanjutkan konsultasi pajak Indonesia.', registerDescription: 'Buat akun untuk menyimpan dan melihat kembali konsultasi Anda.', fullName: 'Nama lengkap', email: 'Alamat email', password: 'Kata sandi', confirmPassword: 'Konfirmasi kata sandi', passwordRequirement: 'Gunakan minimal 12 karakter.', passwordsDoNotMatch: 'Kata sandi tidak cocok.', invalidCredentials: 'Email atau kata sandi salah.', emailAlreadyRegistered: 'Akun dengan email ini sudah terdaftar.', requestFailed: 'Permintaan tidak dapat diproses. Silakan coba lagi.', working: 'Mohon tunggu…', signIn: 'Masuk', createAccount: 'Buat akun', noAccount: 'Belum menggunakan Taxora?', hasAccount: 'Sudah memiliki akun?', providerKeyNotice: 'Taxora menyediakan akses AI. Anda tidak perlu memberikan API key dari penyedia AI.', footer: 'Sesi Anda dilindungi dengan cookie HTTP-only.', checkingSession: 'Memeriksa sesi Anda…', orWithEmail: 'atau dengan email', googleFailed: 'Masuk dengan Google gagal. Silakan coba lagi.', googleEmailTaken: 'Email ini sudah terhubung ke akun Google lain.' },
}

export const resources = { en: { translation: en }, id: { translation: id } } as const
