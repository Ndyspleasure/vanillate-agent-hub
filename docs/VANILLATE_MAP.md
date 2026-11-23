# Atlas Vanillate · 23 November 2026

Founder menetapkan dua proyek utama, bot Discord **Vanillate.ID** dan **website vanillate.id**. Database Media menyimpan aset. **Vanillate Match** adalah bot kedua yang mengelola sesi DM sendiri. Peta terdiri dari satu ikhtisar lintas-repo dan dua peta modul terperinci. Setiap peta menjadi satu scope akses Hub. Snapshot merekam isi Git pada revisi di bawah. Status layanan produksi dan data pemain tidak diperiksa.

| Peran | Revisi sumber pada main | Titik masuk |
|---|---|---|
| Bot utama | [Vanillate.ID @ f8fe82a](https://github.com/Ndyspleasure/Vanillate.ID/tree/f8fe82ae93910605bfd65c9d46d23cf2791bc493) | Node.js, discord.js, index.js, src/commands, src/events |
| Website utama | [vanillate-website @ eea8798](https://github.com/Ndyspleasure/vanillate-website/tree/eea87987cf4ae5f2901ee4ffb65fbd7dc23c59ce) | Astro, src/pages, src/lib, supabase, workflow GitHub Pages |
| Media | [database-media-web @ 6d0593b](https://github.com/Ndyspleasure/database-media-web/tree/6d0593b1aa7d9864994cdc9b1649b12b7d6164b0) | gifs, story-media, tebak-gambar, tebak-kata, tools |
| Bot match | [AnonymousBotDiscord @ 7aca8a9](https://github.com/Ndyspleasure/AnonymousBotDiscord/tree/7aca8a95f9771d3d0b96b21a9bc3e25b514b0c24) | src/matching.js, src/relay.js, src/store.js. README menjelaskan persistensi PostgreSQL opsional. |

Saat inspeksi, HEAD bawaan repo media mengarah ke cabang lain. Atlas memakai main untuk inventaris media dan memeriksa SHA konsumen secara terpisah.

## Kontrak antarproyek

| Perubahan yang hendak ditelusuri | Mulai di sini | Lanjutkan ke |
|---|---|---|
| Admin mengubah konfigurasi server | Website, docs/DASHBOARD-SERVER.md dan src/lib/dashboard | Bot, docs/dashboard-sync.md dan src/dashboard. Website mengirim konfigurasi yang diinginkan, bot mengeksekusinya. |
| Admin membuka ringkasan game/sosial/server | Website, docs/CMS-BACA-DATABASE-BOT.md dan src/lib/cms-read | Bot, src/cms/registry.js dan src/cms/handlers/read.js. Dokumen mencatat permintaan melalui bot_commands, hasil agregat, serta reuse singkat. Bedakan dari jalur push statistik opsional dalam docs/WEBSITE-SYNC.md. |
| Harga, rilis, dan konten bot di situs | Website, docs/AUTO-SYNC-DATA.md, docs/PIPELINE-TERBIT.md dan .github/workflows/sync-data.yml | Periksa sumber data bot pada revisi yang dipakai workflow. Dokumen lama menyebut nama repo sambung-kata-bot. |
| Gambar Vanillate Story berubah | Bot, src/game/story/media.js | URL bawaan jsDelivr mengacu ke [story-media @ 6f64399](https://github.com/Ndyspleasure/database-media-web/tree/6f6439967e74f1e1b8b0901124e75c828536180d/story-media). Perubahan pada main repo media baru berpengaruh setelah referensi konsumen atau konfigurasi berubah. |
| Pemain masuk ke Match | Bot utama, src/social/hub/views.js | Match, README.md dan src/matching.js. Social Hub menampilkan tautan instalasi. Pencocokan dan relay DM berada di Match. |

## Menelusuri dua peta utama

Bot mencakup Game Hub, Vanillate Dungeon, Vanillate Story, dashboard server, CMS bot, dompet pemain, Social Hub, database bot, dan dukungan pemain. Website mencakup halaman publik, katalog bot, dashboard server, pembacaan data CMS, panel developer, editorial/blog, portal partner, skema CMS, dan publikasi website. Tiap modul membawa rujukan kode, dokumen, dan pengujian atau berkas pendamping yang benar-benar ada di commit terkait.

Pada Atlas privat pilih **Proyek aktif**, lalu **Daftar** untuk mencari path, misalnya `src/game/vdungeon` atau `src/lib/cms-read`. Pilih hasil untuk membuka sumber dan melihat hubungan satu langkah. Saat sebuah modul berubah, periksa bukti pada commit yang lebih baru sebelum memperbarui snapshot.

## Hub dan domain

Katalog yang sama tersedia untuk impor lokal dan pratinjau privat. Dari checkout Hub, dengan HUB_DB menunjuk database yang sudah diinisialisasi dan HUB_TOKEN berisi kredensial Founder global, jalankan:

```sh
python -m hub.seed
```

Impor mengisi proyek `vanillate-ecosystem`, `vanillate-bot`, dan `vanillate-web` dalam satu transaksi. Impor ulang pada data identik tidak menambah entri. Konflik dengan data yang sudah ada membatalkan seluruh transaksi untuk ditinjau Founder. Setelah impor, sambungkan dashboard lokal dengan token yang memiliki scope terkait. MCP dapat mencari modul melalui get_project_context pada HUB_PROJECT yang sesuai.

Target produksi Atlas kini Vercel, sesuai [keputusan Founder](adr/0002-vercel-personal-computer.md). Pratinjau Sites berasal dari tahap sebelumnya.

Hostname yang dipilih untuk **Atlas Agent Hub** adalah `dashboard.vanillate.id`. Dashboard pengaturan server Discord milik website tetap berada di `vanillate.id/dashboard`. Atlas privat berisi snapshot; koneksi API lokal tetap memakai konfigurasi Hub. MCP berjalan melalui stdio.
