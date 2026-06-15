# DEVLOG — Belge Analiz Soru-Cevap Sistemi
 
---
 
## 1. Başlangıç: Problemi Parçalamak
 
Hedef net görünüyordu — kullanıcı belge yüklesin, soru sorsun, sistem belgeden yanıt versin. Ama bu akış aslında birbirinden bağımsız üç farklı problem içeriyordu:
 
1. Belgeden metin çıkarmak (PDF, resim, OCR)
2. Soruyla en alakalı parçaları bulmak (embedding + vektör arama)
3. Bulunan parçalardan yanıt üretmek (LLM)
Bu ayrımı baştan yapmak işe yaradı. Bir şey çalışmadığında hangi katmanda sorun olduğunu hızlı anlayabildim.
 
---
 
## 2. Retrieval Kalitesi
 
### Sorun retrieval'da mı, LLM'de mi?
 
İlk versiyonda sistem bazı sorulara doğru, bazılarına yanlış yanıt veriyordu. Nerede bozulduğunu anlamak için `/debug/search` diye bir endpoint yazdım — LLM'e hiç gitmeden sadece hangi chunk'ların döndüğünü ve benzerlik skorlarını gösteriyordu. Sonuç net oldu: retrieval %90 skor veriyordu ama LLM yine de "bu bilgi belgede yok" diyordu. Sorun LLM'deydi.
 
### Embedding modeli değişikliği
 
Başta MiniLM kullandım. Türkçe metinlerde semantik benzerliği iyi yakalamıyordu. `intfloat/multilingual-e5-small`'a geçtim. Bu modelin bir özelliği var: sorguları `"query: {metin}"`, belge parçalarını `"passage: {metin}"` prefix'iyle encode etmek retrieval kalitesini belirgin şekilde artırıyor. Bunu atlasaydım modelin gerçek performansını göremezdim.
 
### Chunk boyutu
 
500 kelimelik chunk'lar çok büyüktü, alakalı bilgi ortada kayboluyordu. 250 kelimeye indirdim, 80 kelime örtüşme ekledim, `top_k`'yı 5'ten 10'a çıkardım.
 
---
 
## 3. LLM Sağlayıcısı Kararı
 
### Groq
 
Ücretsiz ve hızlıydı. Ama `llama-3.1-8b-instant` Türkçe belge analizinde yetersiz kaldı — talimatları tam takip etmiyor, bağlam penceresinde kayboluyordu. Retrieval düzgün çalışıyor, LLM yanıltıcı cevap üretiyordu.
 
### Gemini — Türkiye'den kota sıfır
 
API key aldım, bağladım. İlk istekte `429 quota exceeded, limit: 0` hatası. Türkiye'den Gemini ücretsiz tier'a erişim yoktu. SDK meselesini de hallettim — `google-generativeai` deprecated olmuş, `google-genai`'ya geçtim, bu sefer `404` aldım. Sonunda ücretli provider'a geçtim.
 
Bu süreçte kaybettiğim zaman önlenebilirdi. Şimdi bilsem ücretli provider'a direkt başlardım.
 
### gpt-4o-mini
 
Fiyat/kalite karşılaştırması yaptım:
 
| Model | ~1000 soru maliyeti |
|---|---|
| gpt-4o-mini | $0.63 |
| Claude Haiku 4.5 | $4.50 |
| gpt-4o | $10.50 |
 
gpt-4o-mini seçtim. En ucuzu ve Türkçe talimat takibinde sağlamdı.
 
---
 
## 4. Kaynak Gösterimi — Skor Formülü Hatası
 
### Neden her belge yüksek skor alıyordu?
 
Birden fazla belge yüklenince alakasız belgeler de kaynak olarak çıkıyordu. Debug paneline baktım, alakasız belge %80 skor alıyordu. Kodda şu formül vardı:
 
```python
score = 1 - distance / 2
```
 
ChromaDB cosine distance pratikte 0-1 arasında kalıyor. Bu formül aslında `score = 0.5 + cosine_similarity / 2` anlamına geliyor. Tamamen alakasız bir metin bile minimum 0.50 skor alıyordu. Koyduğum `MIN_RELEVANCE_SCORE = 0.30` eşiği hiçbir şeyi filtrelemiyordu.
 
Düzeltme:
 
```python
score = max(0.0, 1 - distance)
```
 
Bölme kaldırılınca gerçek değerler ortaya çıktı. Alakalı içerik 0.85+, alakasız 0.50-0.65 skoru almaya başladı.
 
### Görece eşik
 
Formül düzeltilince alakalı belge 0.86, alakasız 0.80 aldı. Mutlak eşik bu farkı ayırt edemiyordu. En yüksek skorun 0.05 altında kalan chunk'ları eleme kuralı ekledim.
 
### LLM kendi kaynağını söylesin
 
Tüm retrieved chunk'ların belgesi kaynak olarak görünüyordu ama LLM hepsini kullanmıyordu. Her chunk'a numara verdim `[1]`, `[2]`... LLM'den yanıtın sonuna `SOURCES: 2,5` formatında hangi numaraları kullandığını yazdırmasını istedim. Regex ile parse ettim, sadece gerçekten kullanılan chunk'ların belgesi gösterildi.
 
---
 
## 5. Halüsinasyonu Önlemek
 
RAG sisteminin en kritik riski şu: retrieval doğru chunk'ı getirse bile LLM o chunk'ı görmezden gelip kendi bilgisinden cevap üretebilir. Ya da belgede gerçekten olmayan bir bilgiyi "var gibi" söyleyebilir.
 
### Sistem prompt tasarımı
 
İlk versiyonda sistem prompt genel ve yumuşaktı: "Belgede yoksa söyle." Bu yetmiyordu — LLM bazen belge içeriğiyle kendi bilgisini karıştırıyordu.
 
Promptu sertleştirdim: "YALNIZCA verilen belge parçalarındaki bilgiyi kullan. Kendi bilginden hiçbir şey ekleme, tahmin yürütme, yorum yapma, tamamlama yapma." Özellikle bu üç yasak kelimeyi — tahmin, yorum, tamamlama — eklediğimde fark belirgin oldu.
 
Ayrıca "Bu bilgi belgede yok" cümlesini son çare olarak tanımladım. Başlarda LLM bunu çok kolay kullanıyordu; ilgili bilgi belgede farklı kelimelerle geçse bile "bulunamadı" diyordu. "Bilgi farklı ifadeyle veya dolaylı biçimde geçiyor olabilir, dikkatlice tara" kuralı eklenince bu sorun azaldı.
 
### temperature = 0.1
 
LLM'in yaratıcılığını neredeyse sıfıra indirdim. Yüksek temperature'da model boşlukları doldurmaya, tahmin etmeye meyilli oluyor. 0.1'de belgede ne yazıyorsa onu üretiyor, üretmiyor.
 
### Eşik altındaysa LLM'e hiç gönderme
 
Retrieval hiç alakalı chunk bulamazsa ya da en yüksek skor 0.40'ın altındaysa LLM çağrılmıyor. Bağlam olmadan LLM'e soru sormak en büyük halüsinasyon riskidir — elimine ettim. Bu durumda küçük bir çağrıyla sadece "sorunun dilinde içerik bulunamadı söyle" diyorum.
 
### LLM kendi kullandığı numarayı söylesin
 
Context'teki her chunk numaralandırıldı. LLM yanıtın sonuna `SOURCES: 2,5` gibi gerçekten kullandığı numaraları yazmak zorunda. Bu hem kaynağı izlenebilir yapıyor hem de LLM'i "hangi parçadan alıyorum?" diye düşünmeye zorluyor. Numaralandırılmamış bağlamda model hangi kaynağı ne kadar kullandığını belirsiz bırakabiliyor.
 
---
 
## 6. Dil Sorunu
 
### İngilizce soru → Türkçe cevap
 
Sistem prompt Türkçe yazılmıştı. Model Türkçe'ye bias yapıyordu. Türkçe karakter tespitine (`ğüşıöçĞÜŞİÖÇ`) dayalı dil algılama yazmayı denedim — İngilizce klavye kullananlar veya özel karakter yoksa çalışmıyordu, kırılgandı.
 
Çözüm: sistem prompt'un kendisini İngilizce yazdım, LLM'e "sorunun dilinde yanıtla" dedim. Kendi dil algısına bıraktım. Sonuç çok daha tutarlı oldu.
 
### Bulunamadı mesajı
 
İçerik bulunamazsa LLM çağrılmıyor, kod direkt sabit mesaj dönüyordu — iki dilli çıkıyordu. Dil tespit kodu yazmak istemedim. Çözüm: içerik bulunamadığında da LLM'i çağırıyorum, sadece "sorunun dilinde bir cümleyle içerik bulunamadı söyle" diyorum.
 
---
 
## 7. Checkbox OCR Sorunu
 
### Form belgelerinde yanlış işaret tespiti
 
Checkbox içeren bir formda sistem işaretsiz alanı işaretli gösterdi. Debug panelinde chunk metnine baktım, OCR şunları üretmişti:
 
```
[X]  →  LX)
[ ]  →  | 1)
```
 
LLM bu karakterlerin OCR hatası olduğunu bilemiyordu.
 
### İlk deneme: metin normalizasyonu
 
`[X]` varyantlarını `[CHECKED]`, `[ ]` varyantlarını `[UNCHECKED]`'e çevirmeyi denedim. Regex'ler tüm varyantları tutamadı, bazı metinler bozuldu, sonuç daha kötü oldu.
 
### Doğru yaklaşım: semptomla değil kaynakla uğraş
 
Sorun OCR'ın küçük sembolleri düşük çözünürlükte yanlış okumasıydı. OCR'dan önce görüntüyü iyileştirdim:
 
- 2x büyütme (LANCZOS)
- Keskinleştirme
- Kontrast normalizasyonu
- Binary threshold
Önişleme sonrası OCR `[X]` ve `[ ]` sembollerini doğru okudu. LLM'e doğru metin gelince sorun kendiliğinden çözüldü.
 
 
---
 
## 8. Geriye Bakınca
 
### Doğru kararlar
 
**Debug aracını erkenden yazmak.** `/debug/search` olmadan "sorun LLM'de mi retrieval'da mı" sorusunu çok daha uzun süre çözemezdim.
 
**Katmanlı mimari.** Ingestion, retrieval ve generation'ı ayrı tutmak, LLM sağlayıcısını değiştirmeyi tek dosya meselesi yaptı.
 
**Kaynakta çözmek.** Checkbox sorununda önce metin normalizasyonu denedim, olmadı. OCR kalitesini artırmak hem daha temiz hem daha kalıcı oldu.
 
### Farklı yapardım
 
Ücretli LLM'e daha erkenden geçerdim. Ücretsiz alternatifleri denemek için harcadığım zaman, aylarca gpt-4o-mini kullanmaktan pahalıya geldi.
 
Skor formülünü baştan doğru yazardım. `1 - distance`, bölme yok. Hata yüzeysel bakışta fark edilmiyor ama tüm filtreleme mekanizmasını işlevsiz bırakıyordu.
 
Sistem prompt'u baştan İngilizce yazardım.
 
---