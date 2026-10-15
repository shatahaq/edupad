import { API_URL, DATA_SOURCE } from "../api/client";
import { Icon } from "../components/Icon";
import { PageHeader } from "../components/PageHeader";
import { go } from "../lib/router";

const FAQ = [
  ["Mengapa aktivitas agent tidak berubah?", "Pastikan Office API aktif dan indikator sumber data menunjukkan Server live. Agent hanya berpindah saat backend mengirim tugas atau aktivitas nyata."],
  ["Mengapa riwayat percakapan kosong?", "Riwayat muncul setelah SUPABASE_URL dan kredensial backend yang sesuai tersedia, lalu perangkat EduPad mengirim percakapan ke tabel yang digunakan backend."],
  ["Di mana data keuangan disimpan?", "Untuk tahap ini, transaksi dan anggaran disimpan pada localStorage browser. Data belum tersinkron ke Supabase agar tidak ada perubahan skema tanpa persetujuan."],
  ["Apakah fitur keuangan memakai DeepSeek?", "Tidak. Perhitungan saldo, anggaran, dan laporan dilakukan langsung di browser sehingga tidak memakai kuota API AI."],
  ["Bagaimana mengembalikan tampilan kantor?", "Tekan tombol bingkai pada kontrol zoom. Tampilan akan kembali ke 100% dan posisi kamera kembali ke tengah."],
] as const;

export function HelpPage() {
  return (
    <div className="help-page">
      <PageHeader title="Bantuan" subtitle="Panduan singkat menggunakan EduPad" live={false} />

      <section className="help-hero card">
        <div><span className="eyebrow">MULAI DARI SINI</span><h2>Apa yang ingin Anda lakukan?</h2><p>Pilih bagian yang ingin dibuka. Semua istilah dibuat sederhana untuk penggunaan mahasiswa.</p></div>
        <div className="help-actions">
          <button onClick={() => go("office")}><Icon name="bot" /><span><strong>Lihat AI Office</strong><small>Pantau agent dan tugas backend</small></span></button>
          <button onClick={() => go("keuangan")}><Icon name="wallet" /><span><strong>Atur keuangan</strong><small>Catat transaksi dan lihat laporan</small></span></button>
          <button onClick={() => go("tugas")}><Icon name="clipboard" /><span><strong>Periksa tugas</strong><small>Lihat tugas kuliah dan deadline</small></span></button>
        </div>
      </section>

      <div className="help-grid">
        <section className="card help-panel">
          <div className="help-panel-head"><Icon name="help" /><div><h2>Pertanyaan umum</h2><p>Jawaban untuk kendala yang sering muncul.</p></div></div>
          <div className="help-faq">{FAQ.map(([question, answer], index) => <details key={question} open={index === 0}><summary>{question}<span>+</span></summary><p>{answer}</p></details>)}</div>
        </section>

        <aside className="help-stack">
          <section className="card help-panel">
            <div className="help-panel-head"><Icon name="activity" /><div><h2>Pemeriksaan cepat</h2><p>Konfigurasi yang sedang dipakai.</p></div></div>
            <dl className="help-diagnostics"><div><dt>Sumber data</dt><dd className={DATA_SOURCE === "live" ? "good-text" : "warn-text"}>{DATA_SOURCE === "live" ? "Server live" : "Data contoh"}</dd></div><div><dt>Alamat backend</dt><dd className="mono">{API_URL || "Satu domain"}</dd></div><div><dt>Halaman kantor</dt><dd><button onClick={() => go("office")}>Buka sekarang</button></dd></div></dl>
          </section>
          <section className="card help-panel">
            <div className="help-panel-head"><Icon name="sparkle" /><div><h2>Kontrol kantor</h2><p>Navigasi peta dengan cepat.</p></div></div>
            <ul className="help-shortcuts"><li><kbd>Scroll</kbd><span>Perbesar atau perkecil kantor</span></li><li><kbd>Drag</kbd><span>Geser peta saat diperbesar</span></li><li><kbd>Klik bot</kbd><span>Buka profil dan riwayat tugas</span></li><li><kbd>Klik ruang</kbd><span>Buka fungsi dan statistik ruangan</span></li></ul>
          </section>
        </aside>
      </div>
    </div>
  );
}
