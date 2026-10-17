import type { CSSProperties } from "react";
import { PageIntro } from "../components/PageIntro";
import { Section } from "../components/Section";
import { OWL_COLOR, owlSrc, type OwlName } from "../lib/owls";

const BUTTONS = [
  ["Tahan", "Bicara, lalu lepas untuk mengirim pertanyaan."],
  ["Tekan sekali", "Putar ulang jawaban terakhir."],
  ["Tekan dua kali", "Mulai percakapan baru."],
  ["Tekan saat EduPad bicara", "Hentikan suara. Tahan terus untuk langsung bertanya lagi."],
] as const;

const PHRASES: { owl: OwlName; name: string; topic: string; examples: string[] }[] = [
  {
    owl: "pixel",
    name: "PIXEL",
    topic: "Materi kuliah",
    examples: ["Pertemuan lima Pemrograman Visual bahas apa?", "Jelaskan normalisasi 3NF", "Ada materi baru di Classroom?"],
  },
  {
    owl: "tempo",
    name: "TEMPO",
    topic: "Tugas, presensi, jadwal",
    examples: ["Tugas apa yang deadline minggu ini?", "Ada absen apa hari ini?", "Kuliah besok apa?"],
  },
  {
    owl: "sora",
    name: "SORA",
    topic: "Belajar dan kuis",
    examples: ["Uji aku Basis Data pertemuan dua", "Aku belum paham rekursi", "Hari ini aku belajar apa?", "Mulai (saat SORA menawarkan bantuan)"],
  },
  {
    owl: "koin",
    name: "KOIN",
    topic: "Keuangan",
    examples: ["Tadi beli makan dua puluh lima ribu", "Sisa anggaran makanku berapa?", "Atur anggaran transportasi tiga ratus ribu", "Hapus yang tadi"],
  },
];

/** Mode Suara: semua lewat suara, untuk mahasiswa tunanetra (server: voice/mode.py). */
const VOICE_MODE = [
  ["Nyalakan", "Ucapkan “aktifkan mode suara”, atau lewat Pengaturan di dashboard."],
  ["Bunyi naik", "Mulai merekam: silakan bicara sambil menahan tombol."],
  ["Bunyi turun", "Rekaman terkirim; ketukan pelan berarti EduPad sedang berpikir."],
  ["Jawaban", "Seluruh isinya dibacakan. Jawaban panjang ditutup “mau dilanjutkan?”; jawab “lanjut”."],
  ["Pemberitahuan", "Presensi, deadline, dan peringatan dibacakan, bukan hanya tampil di layar."],
  ["Kecepatan", "Ucapkan “bicara lebih cepat” atau “bicara lebih lambat”."],
] as const;

const CARDS = [
  ["Presensi dibuka", "Muncul dengan bunyi saat presensi bisa diisi, lengkap dengan jam tutupnya."],
  ["Deadline", "Dua hari dan tiga jam sebelum tugas ditutup."],
  ["Peringatan dini", "Saat jatah tidak hadir hampir habis atau anggaran tinggal sedikit."],
  ["Waktunya mengulang", "Sore hari, untuk topik kuis yang perlu diulang atau bantuan yang disiapkan SORA."],
] as const;

export function HelpPage() {
  return (
    <>
      <PageIntro owl="nova" title="Cara pakai">
        Tahan tombol di EduPad, bicara, lalu lepas. Jawabannya dibacakan dan poin pentingnya tampil di layar.
      </PageIntro>

      <div className="grid-3-2">
        <div className="column">
          <Section title="Yang bisa kamu ucapkan">
            <div className="phrase-groups">
              {PHRASES.map((group) => (
                <div key={group.owl} className="phrase-group" style={{ "--owl": OWL_COLOR[group.owl] } as CSSProperties}>
                  <img src={owlSrc(group.owl)} alt="" width={44} height={44} />
                  <div>
                    <strong>{group.topic}</strong>
                    <span className="item-meta">dikerjakan {group.name}</span>
                    <ul>
                      {group.examples.map((text) => (
                        <li key={text}>“{text}”</li>
                      ))}
                    </ul>
                  </div>
                </div>
              ))}
            </div>
          </Section>

          <Section title="Tentang EduPad">
            <p className="prose">
              EduPad adalah asisten belajar berbentuk perangkat kecil yang cukup diajak bicara. Ia membaca materi dosen, tugas,
              presensi, dan jadwal kuliahmu, mengingatkan sebelum terlambat, dan menguji pemahamanmu lewat kuis lisan. Dibuat
              untuk mendukung pendidikan yang berkualitas dan setara (SDG 4 dan 10): bisa dipakai tanpa layar besar, Mode
              Suara membuatnya bisa dipakai mahasiswa tunanetra, dan kekosongan materi kuliah terlihat lewat Equity Radar.
            </p>
          </Section>
        </div>

        <div className="column">
          <Section title="Tombol perangkat">
            <ul className="list">
              {BUTTONS.map(([action, effect]) => (
                <li key={action}>
                  <span className="tag">{action}</span>
                  <span className="item-text">{effect}</span>
                </li>
              ))}
            </ul>
          </Section>

          <Section title="Mode Suara" note="Dipakai tanpa melihat layar, dirancang untuk mahasiswa tunanetra">
            <ul className="list">
              {VOICE_MODE.map(([name, effect]) => (
                <li key={name}>
                  <span className="tag">{name}</span>
                  <span className="item-text">{effect}</span>
                </li>
              ))}
            </ul>
          </Section>

          <Section title="Kartu di layar EduPad">
            <ul className="list">
              {CARDS.map(([name, when]) => (
                <li key={name}>
                  <div className="item-main">
                    <strong>{name}</strong>
                    <span>{when}</span>
                  </div>
                </li>
              ))}
            </ul>
          </Section>

          <Section title="AI Office">
            <ul className="list">
              <li>
                <span className="tag">Scroll</span>
                <span className="item-text">Perbesar atau perkecil kantor</span>
              </li>
              <li>
                <span className="tag">Geser</span>
                <span className="item-text">Pindahkan peta saat diperbesar</span>
              </li>
              <li>
                <span className="tag">Klik owl</span>
                <span className="item-text">Lihat apa yang sedang dikerjakannya</span>
              </li>
            </ul>
          </Section>
        </div>
      </div>
    </>
  );
}
