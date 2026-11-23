# Mengambil konteks proyek

Mulai dari MCP atau API lokal dengan identitas dan scope proyek yang diberikan. Status perangkat dibaca melalui GET /api/computer-status. Online berarti backend menjawab probe. Offline berarti jalur ke backend tidak terjangkau saat diperiksa; komputer tidur, jaringan putus, atau backend berhenti dapat menghasilkan gejala yang sama. Status belum diketahui berarti bukti belum cukup. Jika akses ditolak (401/403), periksa izin dan hentikan permintaan ke data Hub yang dilindungi.

## Saat Hub atau MCP tidak terjangkau

Jalankan pemeriksaan berikut dari lingkungan agen yang tetap online dan sudah memiliki akses Git sendiri. Pemeriksaan ini dapat dijalankan dengan Python 3.12 dan Git, tanpa database lokal atau token Hub.

```sh
python -m hub.git_context
# Untuk tugas khusus website
python -m hub.git_context --project vanillate-web
```

1. Alat mengambil main terbaru Agent Hub, membaca katalog pada commit tersebut, lalu membandingkan SHA bukti dengan main terbaru repo yang relevan. Output JSON memberikan revisi, path berubah (sampel maksimum 30) dan ID node yang perlu ditinjau. Jika command tidak tersedia gunakan konektor GitHub resmi agen untuk membaca hub/catalog/vanillate.json pada main, resolve SHA branch main setiap repo dan bandingkan dengan SHA bukti. Untuk database-media-web gunakan main secara eksplisit.
2. Pada status changed, baca berkas relevan di SHA baru lewat konektor resmi. Periksa relasi dengan node yang menjadi sumber atau target dan terutama kolom evidence. Tinjau path baru yang belum dipetakan. Sebutkan SHA, path, hubungan terdampak dan kondisi yang belum diverifikasi. Status current hanya menyatakan SHA sama. Jika diff atau akses gagal laporkan hasil parsial; kode keluar 2 menunjukkan ada repo yang belum lengkap.
3. Gunakan hanya repo yang memang diizinkan bagi identitas agen. Katalog Git mencakup metadata yang telah dicatat di repo tersebut. Keputusan Founder, antrean, audit dan data privat lokal hanya dapat dibaca sesuai izin saat Hub tersedia. Usulan koreksi peta tetap bersifat teknis sampai ditinjau. Pemeriksaan tidak menulis ke repo, SQLite, atau layanan produksi.
4. Saat Hub pulih, ambil ulang konteks lokal dan cocokkan versi sebelum mengusulkan pembaruan. Agen yang ikut mati bersama PC baru bisa melakukan pemeriksaan setelah kembali aktif.
