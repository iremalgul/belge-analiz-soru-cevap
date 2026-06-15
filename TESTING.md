# TESTING.md — Test ve Doğrulama
 
---
 
## Test Yaklaşımı
 
Sistemi beş farklı belge tipiyle test ettim. Her belge tipi farklı bir zorluğu temsil ediyordu: düz Türkçe metin, çok sayfalı Türkçe rapor, tablolu İngilizce belge, düz İngilizce metin ve taranmış görüntü. Her biri için hem belgede cevabı olan sorular hem de belgede olmayan bilgileri hedefleyen tuzak sorular sordum.
 
Debug paneli (`/debug/search`) sayesinde bazı sorularda retrieval katmanını da ayrıca test ettim — LLM'e gitmeden hangi chunk'ların döndüğünü ve benzerlik skorlarını kontrol ettim.
 
---
 
## 1. Türkçe Kısa PDF (`turkce_kisa.pdf`)
 
YZ ve makine öğrenmesi konulu 2 sayfalık Türkçe belge.
 
| Soru | Sistem Yanıtı | Sonuç |
|---|---|---|
| Makine öğrenmesinin kaç temel öğrenme şekli var ve bunlar nelerdir? | Üç temel öğrenme şekli vardır: denetimli öğrenme (etiketli veriler), denetimsiz öğrenme (sistem veriyi kendi kendine gruplar), pekiştirmeli öğrenme (ajan ödül-ceza mekanizmasıyla öğrenir). | ✅ Doğru |
| Alan Turing'in yapay zeka alanındaki rolü nedir? | Alan Turing, yapay zeka alanının temellerini atan çalışmalarıyla bu alanda önemli bir rol oynamıştır. 1950'li yıllarda yapay zekanın gelişimine katkıda bulunmuştur. | ✅ Doğru |
| Otonom araç alanında hangi şirketler yatırım yapıyor? | Tesla, Waymo, Mercedes-Benz | ✅ Doğru |
| GPT-4'ün kaç parametresi var? | Bu bilgi belgede yer almamaktadır. | ✅ Doğru (tuzak) |
| Derin öğrenmenin dezavantajları nelerdir? | Bu bilgi belgede yer almamaktadır. | ✅ Doğru (tuzak) |

<img width="1424" height="531" alt="Ekran görüntüsü 2026-06-14 151713" src="https://github.com/user-attachments/assets/792775e6-ee69-4136-9f84-a918bd99c3a7" />
<img width="1442" height="744" alt="Ekran görüntüsü 2026-06-14 151803" src="https://github.com/user-attachments/assets/59e89d9c-2cf3-432f-96f4-fb7abace3bc1" />

---
 
## 2. Türkçe Uzun PDF (`turkce_uzun.pdf`)
 
Türkiye sektörel değerlendirme raporu, 6+ sayfa.
 
| Soru | Sistem Yanıtı | Sonuç |
|---|---|---|
| Türkiye'nin fındık üretimindeki dünya payı nedir? | Türkiye, fındık üretiminde dünyanın yüzde 70-75'ini karşılamaktadır. | ✅ Doğru |
| TOGG'un ilk ürettiği araç modeli nedir ve ne zaman teslimata başladı? | TOGG'un ilk ürettiği araç modeli TOGG T10X'tir ve 2023 yılında teslimata başlamıştır. | ✅ Doğru |
| GAP projesi kaç baraj ve kaç hidroelektrik santralden oluşuyor? | GAP projesi toplam 22 baraj ve 19 hidroelektrik santralden oluşmaktadır. | ✅ Doğru |
| Trendyol'un değerlemesi hangi rakamla belirtilmiş ve bu onu nasıl bir konuma getiriyor? | Trendyol'un değerlemesi 16,5 milyar dolar olarak belirtilmiştir ve bu değerlemeyle bölgenin en değerli teknoloji şirketi olma unvanını korumaktadır. | ✅ Doğru |
| Türkiye'nin 2024 yılı enflasyon hedefi yüzde kaçtır? | Bu bilgi belgede yer almamaktadır. | ✅ Doğru (tuzak) |
| Papara'nın kullanıcı sayısı kaçtır? | Bu bilgi belgede yer almamaktadır. | ✅ Doğru (tuzak) |

<img width="1433" height="664" alt="Ekran görüntüsü 2026-06-14 152055" src="https://github.com/user-attachments/assets/059dcdcb-83bd-4fb9-a39e-193c47548602" />
<img width="1452" height="629" alt="Ekran görüntüsü 2026-06-14 152109" src="https://github.com/user-attachments/assets/8e540869-dbaa-4f48-99cb-e21922c1a1bf" />

### Debug Paneli Gözlemi
 
"Türkiye'nin 2024 yılı enflasyon hedefi yüzde kaçtır?" sorusunu debug panelinde test ettim. Retrieval 3 chunk döndürdü (skor: 0.876, 0.858, 0.833) — belgede enflasyondan bahseden bölümler geldi ama hedef rakamı hiçbirinde yoktu. LLM doğru şekilde "bu bilgi belgede yer almamaktadır" dedi.

<img width="1411" height="761" alt="Ekran görüntüsü 2026-06-14 220838" src="https://github.com/user-attachments/assets/1f7ffd7a-c22d-4e01-8bd5-aa897d065ed9" />

 
## 3. İngilizce Tablolu PDF (`english_with_tables.pdf`)
 
Global ekonomi göstergeleri, iki tablo içeriyor.
 
| Soru | Sistem Yanıtı | Sonuç |
|---|---|---|
| Which country had the highest Q2 2024 growth rate? | India had the highest Q2 2024 growth rate at 6.9%. | ✅ Doğru |
| Which country has the largest population but lower GDP per capita than Brazil? | India has the largest population but a lower GDP per capita than Brazil. | ✅ Doğru (çıkarım gerektiriyor) |
| Did Germany experience any economic contraction in 2024? Which quarter? | Yes, Germany experienced mild contraction in Q2 2024. | ✅ Doğru |
| What is France's quarterly GDP growth rate for Q3 2024? | Bu bilgi belgede yer almamaktadır. / This information is not found in the document. | ✅ Doğru (tuzak) |
| What does the IMF project for 2026 global GDP growth? | Bu bilgi belgede yer almamaktadır. / This information is not found in the document. | ✅ Doğru (tuzak) |<img width="1467" height="702" alt="Ekran görüntüsü 2026-06-14 171844" src="https://github.com/user-attachments/assets/031e4f68-b74c-47c2-8604-a1f9a65a521e" />


<img width="1457" height="654" alt="Ekran görüntüsü 2026-06-14 153416" src="https://github.com/user-attachments/assets/43976861-d741-4bfb-8eb0-7b6f257e6f09" />
<img width="1446" height="452" alt="Ekran görüntüsü 2026-06-14 153430" src="https://github.com/user-attachments/assets/ffba278b-542b-4335-a890-9d0ff0d59098" />

---
 
## 4. İngilizce Orta Boy PDF (`english_medium.pdf`)
 
Yenilenebilir enerji teknolojileri, 4 sayfa.
 
| Soru | Sistem Yanıtı | Sonuç |
|---|---|---|
| By how much has the cost of solar PV technology fallen over the past decade? | The cost of solar photovoltaic technology has fallen by more than 90 percent over the past decade. | ✅ Doğru |
| What was the global installed solar capacity in 2023? | The global installed solar capacity reached 1.6 terawatts in 2023. | ✅ Doğru |
| Where is the Hornsdale Power Reserve located and what did it demonstrate? | The Hornsdale Power Reserve is located in South Australia. It demonstrated that battery storage could respond to grid events faster than conventional power plants. | ✅ Doğru |
| What percentage of global greenhouse gas emissions are covered by carbon pricing? | Approximately 23 percent of global greenhouse gas emissions are covered by carbon pricing instruments. | ✅ Doğru (belgede derine gömülü bilgi) |
| What is the efficiency of the best solar panel currently available for purchase? | Modern commercial solar panels achieve efficiencies of 20 to 23 percent. Laboratory records have exceeded 29 percent. | ⚠️ Kısmi (tuzak sorusuna belgedeki en yakın bilgiyi verdi, "en iyi satın alınabilir panel" bilgisi belgede yok ama bunu söylemedi) |

<img width="1467" height="702" alt="Ekran görüntüsü 2026-06-14 171844" src="https://github.com/user-attachments/assets/6a6bf02e-60ec-4837-bf86-87158d32fc37" />
<img width="1446" height="452" alt="Ekran görüntüsü 2026-06-14 153430" src="https://github.com/user-attachments/assets/d6dab946-3241-4c00-af99-92f09aca6c38" />

---
 
## 5. Taranmış Belge (`taranmis_belge.png`)
 
Tarım Bakanlığı başvuru formu, checkbox'lı taranmış görüntü.
 
| Soru | Sistem Yanıtı | Sonuç |
|---|---|---|
| Başvuru sahibinin adı soyadı nedir? | Başvuru sahibinin adı soyadı: Mehmet Yılmaz | ✅ Doğru |
| İşletmenin arazi büyüklüğü kaç dekardır? | İşletmenin arazi büyüklüğü 85 dekardır. | ✅ Doğru |
| Kaç baş büyükbaş hayvan var? | 12 baş büyükbaş hayvan bulunmaktadır. | ✅ Doğru |
| Hangi destek türleri işaretlenmiş? | İlk testte: Gübre, Tohum, Makine alımı, Sulama (hepsi işaretli gösterdi) | ❌ Hatalı — OCR önişleme öncesi |
| Hangi destek türleri işaretlenmiş? | OCR önişleme sonrası: Gübre desteği, Tohum desteği, Sulama altyapısı desteği | ✅ Doğru — Makine alımı işaretsizdi, doğru filtrelendi |
| Başvuru ne zaman onaylandı? | Bu bilgi belgede yer almamaktadır. / This information is not found in the document. | ✅ Doğru (tuzak) |
| Başvurucunun banka hesap numarası nedir? | Bu bilgi belgede yer almamaktadır. / This information is not found in the document. | ✅ Doğru (tuzak) |

<img width="1447" height="764" alt="Ekran görüntüsü 2026-06-14 172040" src="https://github.com/user-attachments/assets/c102690e-7d3f-4aca-a266-400a755c1ee0" />
<img width="1470" height="696" alt="Ekran görüntüsü 2026-06-14 172052" src="https://github.com/user-attachments/assets/850d5adc-2b6f-44fa-91c3-b69d74bc3946" />
 
### Checkbox OCR Süreci
OCR önişleme eklenmeden önce sistem checkbox'ları yanlış okuyordu — `[X]` karakteri `LX)` olarak, `[ ]` karakteri `| 1)` olarak geliyordu. LLM bu OCR gürültüsünü ayırt edemediği için işaretsiz olan "Makine alımı desteği" de işaretli olarak gösterildi.
 
Görüntüye 2x büyütme, keskinleştirme ve binary threshold uygulandıktan sonra OCR checkbox sembollerini doğru okudu ve sonuç düzeldi.
 
---
 
## Genel Gözlemler
 
**Dil tutarlılığı:** Türkçe sorulara Türkçe, İngilizce sorulara İngilizce yanıt verdi. Tek istisna: tablolu PDF testinde İngilizce sorulara zaman zaman iki dilli yanıt döndü ("Bu bilgi belgede yer almamaktadır. / This information is not found in the document."). İşlevsel olarak doğru ama biçim tutarsız.
 
**Kaynak gösterimi:** Yanıtların yanında hangi belgeden, hangi bölümden ve kaçıncı benzerlik skoru ile geldiği görülebiliyor. Bu özellikle çok belgeli senaryolarda güven artırıyor.
 
**Tuzak soruları:** Test edilen tüm tuzak sorularında sistem "Bu bilgi belgede yer almamaktadır." yanıtı verdi. Hiçbirinde uydurma yanıt üretmedi.
 
---
 
## Sistemin Yetersiz Kaldığı Durumlar
 
**En iyi satın alınabilir panel sorusu:** "What is the efficiency of the best solar panel currently available for purchase?" sorusuna sistem ticari panel ve laboratuvar rekoru bilgilerini verdi ama sorulan spesifik bilginin belgede olmadığını belirtmedi. Belgede ilgili sayılar var ama soru farklı bir şey soruyor — sistem bu ayrımı her zaman yapmıyor.
 
**Çok uzun belgelerde yükleme süresi:** `turkce_uzun.pdf` gibi 6+ sayfalık belgelerde embedding süresi uzayabilir. Retrieval kalitesi etkilenmiyor.
 
---
