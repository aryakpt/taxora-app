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
  composer: { period: 'Tax period', yearPlaceholder: 'e.g. 2025', taxpayer: 'Taxpayer', unspecified: 'Not specified', individual: 'Individual', business: 'Business', contextHint: 'Optional context helps with period-specific answers', questionLabel: 'Ask a tax question', questionPlaceholder: 'Ask about Indonesian tax…', send: 'Send', sendLabel: 'Send question', keyboard: '↵ to send · ⇧ ↵ new line', disclaimer: 'Taxora can make mistakes. Verify important information against official sources.' },
  messages: {
    assistant: 'Taxora assistant', user: 'You', aiResponse: 'AI response', reviewingSources: 'Reviewing sources', loadingAnswer: 'Searching verified sources and preparing an answer…',
    insufficientEvidence: 'Insufficient verified evidence', clarificationNeeded: 'More information may help', failed: 'The answer could not be completed', clarify: 'Information to clarify', limitations: 'Limitations', legalBasis: 'Legal basis', source: 'source', sources: 'sources', regulation: 'REGULATION', effective: 'Effective {{date}}', effectiveUnknown: 'Effective date not specified', viewOriginal: 'View original source', helpful: 'Helpful answer', unhelpful: 'Unhelpful answer',
  },
  regulations: { eyebrow: 'KNOWLEDGE BASE', title: 'Regulation library', intro: 'Browse published regulations available to the assistant. Each entry links to its original source.', emptyTitle: 'No published regulations found', emptyDescription: 'Only approved, published documents appear here. Connect to the backend and check again later.' },
  admin: {
    eyebrow: 'ADMINISTRATION', title: 'Knowledge admin', intro: 'Submit a public regulation source for processing, then review its ingestion status.', submitted: 'Ingestion request submitted.', formTitle: 'Submit a regulation', formDescription: 'Only authorized administrators can submit documents. Submitted sources require review before publication.', sourceUrl: 'Official source URL', regulationNumber: 'Regulation number', regulationNumberPlaceholder: 'e.g. 28/2026', regulationType: 'Regulation type', titleField: 'Title', titlePlaceholder: 'Full regulation title', issuer: 'Issuing authority', topic: 'Topic', other: 'Other', submit: 'Submit for processing', recentJobs: 'Recent ingestion jobs', noJobs: 'No ingestion jobs available.', noDetails: 'No additional details', statuses: { queued: 'Queued', processing: 'Processing', review_required: 'Review required', approved: 'Approved', published: 'Published', failed: 'Failed' },
  },
  auth: { secureAccount: 'SECURE ACCOUNT ACCESS', loginTitle: 'Welcome back', registerTitle: 'Create your account', loginDescription: 'Sign in to continue your Indonesian tax consultation.', registerDescription: 'Create an account to save and revisit your consultations.', fullName: 'Full name', email: 'Email address', password: 'Password', confirmPassword: 'Confirm password', passwordRequirement: 'Use at least 12 characters.', passwordsDoNotMatch: 'The passwords do not match.', invalidCredentials: 'Email or password is incorrect.', emailAlreadyRegistered: 'An account with this email already exists.', requestFailed: 'We could not complete the request. Please try again.', working: 'Please wait…', signIn: 'Sign in', createAccount: 'Create account', noAccount: 'New to Taxora?', hasAccount: 'Already have an account?', providerKeyNotice: 'Taxora provides AI access. You do not need to provide an AI provider API key.', footer: 'Your session is protected with an HTTP-only cookie.', checkingSession: 'Checking your session…' },
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
  composer: { period: 'Masa pajak', yearPlaceholder: 'mis. 2025', taxpayer: 'Wajib pajak', unspecified: 'Belum ditentukan', individual: 'Orang pribadi', business: 'Badan usaha', contextHint: 'Konteks tambahan membantu menjawab pertanyaan terkait periode', questionLabel: 'Ajukan pertanyaan pajak', questionPlaceholder: 'Tanyakan tentang pajak Indonesia…', send: 'Kirim', sendLabel: 'Kirim pertanyaan', keyboard: '↵ untuk kirim · ⇧ ↵ baris baru', disclaimer: 'Taxora dapat keliru. Verifikasi informasi penting melalui sumber resmi.' },
  messages: {
    assistant: 'Asisten Taxora', user: 'Anda', aiResponse: 'Jawaban AI', reviewingSources: 'Meninjau sumber', loadingAnswer: 'Mencari sumber terverifikasi dan menyiapkan jawaban…',
    insufficientEvidence: 'Bukti terverifikasi belum memadai', clarificationNeeded: 'Informasi tambahan dapat membantu', failed: 'Jawaban tidak dapat diselesaikan', clarify: 'Informasi yang perlu diklarifikasi', limitations: 'Keterbatasan', legalBasis: 'Dasar hukum', source: 'sumber', sources: 'sumber', regulation: 'PERATURAN', effective: 'Berlaku {{date}}', effectiveUnknown: 'Tanggal berlaku tidak dicantumkan', viewOriginal: 'Lihat sumber asli', helpful: 'Jawaban membantu', unhelpful: 'Jawaban tidak membantu',
  },
  regulations: { eyebrow: 'KNOWLEDGE BASE', title: 'Pustaka peraturan', intro: 'Jelajahi peraturan yang telah dipublikasikan dan tersedia bagi asisten. Setiap entri terhubung ke sumber aslinya.', emptyTitle: 'Tidak ada peraturan yang dipublikasikan', emptyDescription: 'Hanya dokumen yang disetujui dan dipublikasikan yang ditampilkan. Hubungkan ke backend dan coba lagi nanti.' },
  admin: {
    eyebrow: 'ADMINISTRASI', title: 'Admin knowledge base', intro: 'Kirim sumber peraturan publik untuk diproses, lalu tinjau status ingestion-nya.', submitted: 'Permintaan ingestion dikirim.', formTitle: 'Kirim peraturan', formDescription: 'Hanya administrator berwenang yang dapat mengirim dokumen. Sumber yang dikirim harus ditinjau sebelum dipublikasikan.', sourceUrl: 'URL sumber resmi', regulationNumber: 'Nomor peraturan', regulationNumberPlaceholder: 'mis. 28/2026', regulationType: 'Jenis peraturan', titleField: 'Judul', titlePlaceholder: 'Judul lengkap peraturan', issuer: 'Instansi penerbit', topic: 'Topik', other: 'Lainnya', submit: 'Kirim untuk diproses', recentJobs: 'Job ingestion terbaru', noJobs: 'Belum ada job ingestion.', noDetails: 'Tidak ada detail tambahan', statuses: { queued: 'Dalam antrean', processing: 'Diproses', review_required: 'Perlu ditinjau', approved: 'Disetujui', published: 'Dipublikasikan', failed: 'Gagal' },
  },
  auth: { secureAccount: 'AKSES AKUN YANG AMAN', loginTitle: 'Selamat datang kembali', registerTitle: 'Buat akun Anda', loginDescription: 'Masuk untuk melanjutkan konsultasi pajak Indonesia.', registerDescription: 'Buat akun untuk menyimpan dan melihat kembali konsultasi Anda.', fullName: 'Nama lengkap', email: 'Alamat email', password: 'Kata sandi', confirmPassword: 'Konfirmasi kata sandi', passwordRequirement: 'Gunakan minimal 12 karakter.', passwordsDoNotMatch: 'Kata sandi tidak cocok.', invalidCredentials: 'Email atau kata sandi salah.', emailAlreadyRegistered: 'Akun dengan email ini sudah terdaftar.', requestFailed: 'Permintaan tidak dapat diproses. Silakan coba lagi.', working: 'Mohon tunggu…', signIn: 'Masuk', createAccount: 'Buat akun', noAccount: 'Belum menggunakan Taxora?', hasAccount: 'Sudah memiliki akun?', providerKeyNotice: 'Taxora menyediakan akses AI. Anda tidak perlu memberikan API key dari penyedia AI.', footer: 'Sesi Anda dilindungi dengan cookie HTTP-only.', checkingSession: 'Memeriksa sesi Anda…' },
}

export const resources = { en: { translation: en }, id: { translation: id } } as const
