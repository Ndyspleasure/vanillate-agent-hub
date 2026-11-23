# Konektor Claude Pro melalui HTTPS

**Keputusan Founder.** Endpoint resmi adalah https://mcp.vanillate.id/mcp. Akses baca untuk vanillate-bot dan vanillate-web. Dashboard menggunakan hostname tersendiri. SQLite, Ollama dan MCP stdio tetap di komputer Founder.

**Deployment.** Gunakan proyek Vercel terpisah dengan Root Directory `remote-mcp`, Node 24 dan branch main. Modul menggunakan MCP SDK Streamable HTTP stateless. Tanpa konfigurasi OAuth lengkap fungsi mengembalikan 503. Setelah terkonfigurasi, permintaan tanpa login menerima 401 beserta alamat metadata OAuth. Arahkan hanya subdomain mcp ke record yang disediakan Vercel dan tunggu sertifikat aktif.

**Login sekali di Claude.** Gunakan authorization server OAuth yang mendukung authorization code + PKCE S256, discovery, serta access token JWT RS256/ES256 untuk resource persis https://mcp.vanillate.id/mcp. Daftarkan aplikasi Claude dengan callback resmi yang ditampilkan/didokumentasikan oleh Claude. Sediakan refresh token sesuai kebijakan issuer. Daftarkan scope hub.read. Di pengaturan lanjutan konektor Claude isi client ID dan, jika diperlukan oleh issuer, client secret. Server memeriksa issuer, expiry, audience, subject Founder, ID aplikasi dan scope pada setiap permintaan. Isi server-side Vercel Production Environment:

| Variabel | Nilai |
|---|---|
| MCP_OAUTH_ISSUER | Identifier issuer HTTPS persis, termasuk trailing slash jika ada |
| MCP_OAUTH_JWKS | URL HTTPS public signing keys yang dipublikasikan issuer |
| MCP_ALLOWED_SUBJECT | sub akun Founder pada issuer tersebut |
| MCP_CLAUDE_CLIENT_ID | ID aplikasi OAuth yang dipakai Claude |
| HUB_BRIDGE_ORIGIN | Origin HTTPS gateway privat yang menerima permintaan dari Vercel |
| HUB_BOT_READER, HUB_WEB_READER | Dua token Reader Hub terpisah, masing-masing dengan scope proyek terkait |

Hanya izinkan GET pada /projects/vanillate-bot/context dan /projects/vanillate-web/context melalui gateway yang telah disetujui. Komputer memulai tunnel keluar. Langkah konfigurasi PC perlu dilakukan pada komputer Founder. Gunakan pengaturan Environment Variables untuk nilai rahasia dan redeploy setelah konfigurasi. Token OAuth Claude berakhir di MCP; panggilan ke PC memakai token Reader masing-masing. list_projects mengembalikan daftar statis dua proyek; get_project_context mengambil hasil live dan mengembalikan error jika PC terputus. Akses fallback Git tetap melalui konektor GitHub resmi.

**Verifikasi.** Jalankan npm ci dan npm test dari remote-mcp. Setelah deployment, uji discovery dan respons 401 dari jaringan eksternal, lanjutkan login Claude lalu panggil get_project_context untuk setiap proyek. Aktifkan konektor untuk penggunaan rutin setelah tes live berhasil.
