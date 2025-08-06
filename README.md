<div align="center" style="display: flex; align-items: center; justify-content: center; gap: 15px;">

<img src="https://github.com/user-attachments/assets/3f224ae6-a71e-4092-8934-fb1f5c214d03" alt="Infinitum AI Agent Logo" width="100" height="100" />

# Infinitum AI Agent


**Yapay Zeka Destekli Akıllı Ürün Arama ve Öneri Platformu**

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116%2B-green.svg)](https://fastapi.tiangolo.com)
[![Google Cloud](https://img.shields.io/badge/Google%20Cloud-Vertex%20AI-orange.svg)](https://cloud.google.com/vertex-ai)
[![CrewAI](https://img.shields.io/badge/CrewAI-0.150%2B-purple.svg)](https://crewai.com)
[![Gemini](https://img.shields.io/badge/Gemini-2.5%20Pro-purple.svg)](https://ai.google.dev/gemini-api)

*Gemini LLM, Vector Search ve Multi-Agent AI Sistemleri ile güçlendirilmiş akıllı ürün arama*

</div>

---

## 📖 Proje Hakkında

Infinitum AI Agent, kullanıcıların doğal dilde yaptıkları istekleri anlayarak, internetten en uygun ürünleri bulan ve kişiselleştirilmiş öneriler sunan gelişmiş bir yapay zeka platformudur.

### Örnek Kullanım Senaryosu

**Kullanıcı:** Uygulamada arama kısmına *"Kız kardeşimin düğünü var ve kıyafet bulmam gerekiyor bana elbiseler ve kombinler bul."* şeklinde bir prompt girer.

**AI Agent Süreci:**
1.  **İstek Analizi** - Gemini LLM isteği analiz eder (düğün, kadın kıyafeti, kombinler, düğünde giyilebilecek ürünler)
2.  **Akıllı Arama** - Multi-agent sistem farklı e-ticaret sitelerinde veya kendi Vertex veritabanında arama yapar 
3.  **Ürün Filtreleme** - Bulunan ürünler kalite, fiyat ve uygunluk açısından değerlendirilir
4.  **Kişiselleştirme** - Kullanıcı tercihlerine göre en uygun seçenekler belirlenir
5.  **Paket Önerisi** - Komple kombinler ve alternatifler sunulur

**Sonuç:** Kullanıcı, düğün için uygun elbiseler, ayakkabılar, aksesuarlar ve komple kombinleri içeren kişiselleştirilmiş bir paket önerisi alır. Ek olarak paketler, ürünler için yorumlardan ve açıklamalardan analiz ederek "Neden bu ürün/paket?" gibi açıklamalar ekleyerek kullanıcaya gösterir.

---

## Projeden Ekran Görüntüleri

<!-- Buraya ekran görüntüleri eklenecek -->

###  Arama Arayüzü
<img width="1912" height="1015" alt="Screenshot 2025-08-06 at 17 26 55" src="https://github.com/user-attachments/assets/5e1ceabe-5c6c-4a32-a4a2-308be5adbb26" />

###  AI Arama Süreci ve Ek Prompt girilmesi
<img width="1912" height="1017" alt="Screenshot 2025-08-06 at 17 27 54" src="https://github.com/user-attachments/assets/92719d34-f991-4482-b0c1-c626343ed8d6" />

###  Arama Sonuçları
<img width="1912" height="1014" alt="Screenshot 2025-08-06 at 17 28 15" src="https://github.com/user-attachments/assets/f2e9fcf0-b198-48f0-ab22-51a33f40c830" />

<img width="1912" height="1012" alt="Screenshot 2025-08-06 at 17 28 51" src="https://github.com/user-attachments/assets/7ffe458e-e856-4122-a411-4a3fee018d03" />

---

##  Temel Özellikler

###  **Gelişmiş AI Yetenekleri**
- **Gemini 2.5 Pro/Flash Entegrasyonu** - Akıllı sorgu işleme ve keyword extraction için LLM
- **Multi-Agent Mimarisi** - CrewAI destekli agentlar ile araştırma ve analiz
- **Semantik Vector Arama** - Vertex AI embeddings ile benzerlik eşleştirmesi
- **Akıllı Sorgu Geliştirme** - Bağlam farkında arama optimizasyonu

###  **Akıllı Ürün Keşfi**
- **Hibrit Arama Motoru** - Semantik arama ile geleneksel anahtar kelime eşleştirmesini birleştirir
- **Akıllı Paket Oluşturma** - Kullanıcı niyetine göre AI tarafından düzenlenmiş ürün paketleri
- **Kişiselleştirilmiş Öneriler** - Kullanıcı bağlamı ve tercih öğrenimi
- **Çoklu Kaynak Veri Toplama** - SerpAPI, web scraping ve ürün veritabanları
- **Fiyat Karşılaştırması ve Analizi** - Birden fazla satıcıdan gerçek zamanlı fiyat verileri

### 🏗 **Üretime Hazır Altyapı**
- **Ölçeklenebilir Bulut Mimarisi** - Otomatik ölçeklendirme ile Google Cloud Run
- **Kapsamlı İzleme** - Yapılandırılmış loglama, metrikler ve izleme
- **Güvenlik Öncelikli** - JWT kimlik doğrulama, girdi doğrulama ve güvenli kimlik bilgisi yönetimi
- **Yüksek Performans** - Asenkron işlemler, caching ve bağlantı havuzu mekanizmaları kullanıldı

##  API Örnekleri

###  **Temel Sohbet İsteği**
```bash
curl -X POST "http://localhost:8080/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "200 TL altında kablosuz kulaklık bul",
    "conversation_id": "conv-123"
  }'
```
<img width="1920" height="1050" alt="Screenshot 2025-08-06 at 17 34 14" src="https://github.com/user-attachments/assets/43bcdea1-e781-45c4-8e74-b7285175b8e8" />


###  **Paket Oluşturma**
```bash
curl -X POST "http://localhost:8080/api/v1/packages" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "I want to buy home accessories",
    "metadata": {
      "source": "postman-test",
      "category": "home-decor"
    },
    "user_id": "{{user_id}}",
    "preferences": {
      "budget_range": "mid-range",
      "style": "modern"
    }
  }'
```
<img width="1920" height="1050" alt="Screenshot 2025-08-06 at 17 40 10" src="https://github.com/user-attachments/assets/e4f10d5e-ea52-4f56-a318-0710c5dce689" />

---

# Mimari Genel Bakış

## **5 Workflow**
```mermaid
sequenceDiagram
    participant User
    participant API as FastAPI
    participant Gemini as Gemini LLM
    participant Agents as CrewAI Agents
    participant Search as Vector Search
    participant DB as Firestore

    User->>API: Send Query
    API->>Gemini: 1. Analyze Intent
    Gemini-->>API: Extracted Keywords
    API->>Agents: 2. Multi-Source Search
    Agents->>Search: SerpAPI + Web Scraping
    Search-->>Agents: Product URLs
    API->>Agents: 3. Filter & Validate
    Agents-->>API: Prioritized URLs
    API->>Agents: 4. Extract Data
    Agents-->>API: Structured Products
    API->>Gemini: 5. Curate Response
    Gemini-->>API: Personalized Package
    API->>DB: Save Session
    API-->>User: Final Response
```

##  **Google Cloud Platform Altyapısı**

![WhatsApp Image 2025-08-06 at 14 54 57](https://github.com/user-attachments/assets/bea8f505-5030-4d1f-b423-aab7e86b72c4)

### **Kullanılan GCP Servisleri**
- **[Vertex AI](https://cloud.google.com/vertex-ai)** - Gemini LLM hosting ve vector search
- <img width="1800" height="1130" alt="Screenshot 2025-08-06 at 18 51 41" src="https://github.com/user-attachments/assets/8db0cb09-5757-4324-98b3-9edaef754379" />
- **[Cloud Run](https://cloud.google.com/run)** - Serverless container deployment
- **[Firestore](https://cloud.google.com/firestore)** - NoSQL document database
- <img width="1800" height="1130" alt="Screenshot 2025-08-06 at 18 53 24" src="https://github.com/user-attachments/assets/cf870e2b-ecb2-45d0-97aa-9d11e9bc1bb2" />
- **[Secret Manager](https://cloud.google.com/secret-manager)** - API key management
- **[Cloud Storage](https://cloud.google.com/storage)** - Vector embeddings storage
- <img width="1800" height="1130" alt="Screenshot 2025-08-06 at 18 55 09" src="https://github.com/user-attachments/assets/5f59e327-8e8d-418b-8ac2-217572ded01d" />
- **[Container Registry](https://cloud.google.com/container-registry)** - Docker image 

---
##  **RAG (Retrieval-Augmented Generation) Sistemi**

Infinitum AI Agent, gelişmiş bir RAG mimarisi kullanarak kullanıcı sorgularını işler ve kişiselleştirilmiş ürün önerileri sunmayı amaçlamaktadır:

### **RAG İş Akışı:**

1. ** Query Processing (Sorgu İşleme)**
   - Kullanıcının doğal dil sorgusunu Gemini LLM ile analiz eder
   - Anahtar kelimeleri, kategorileri ve kullanıcı niyetini çıkarır
   - Sorguyu yapılandırılmış arama parametrelerine dönüştürür

2. ** Retrieval (Bilgi Getirme)**
   - **Vector Search**: Vertex AI ile 768 boyutlu embeddings kullanarak semantik arama
   - **External APIs**: SerpAPI ile gerçek zamanlı ürün verisi çekme
   - **Web Scraping**: Crawl4AI ile e-ticaret sitelerinden ürün detayları
   - **Database Query**: Firestore'dan geçmiş arama sonuçları ve kullanıcı tercihleri

3. ** Augmentation (Veri Zenginleştirme)**
   - Çekilen ürün verilerini kalite, fiyat ve uygunluk açısından filtreler
   - Kullanıcı profiline göre relevans skorları hesaplar
   - Benzer ürünleri gruplar ve paket önerileri oluşturur
   - Ürün yorumları ve açıklamalarını analiz eder

4. ** Generation (Yanıt Üretme)**
   - Zenginleştirilmiş veriyi Gemini LLM'e context olarak verir
   - Kişiselleştirilmiş ürün paketleri ve açıklamalar üretir
   - "Neden bu ürün?" mantığını açıklayan detaylar ekler
   - Kullanıcı dostu format ve sunum oluşturur

### **RAG'in Avantajları:**
- **Doğruluk**: Gerçek zamanlı veri ile güncel bilgi
- **Dinamiklik**: Sürekli güncellenen ürün katalogu
- **Akıllılık**: LLM'in anlama yetisi + güncel veri
- **Hız**: Vector search ile milisaniye cevap süresi
- **Kişiselleştirme**: Kullanıcı geçmişi ile özelleştirilmiş öneriler

---

###  **Yapılandırılmış Loglama**
```bash
# Sağlık kontrolü
curl http://localhost:8080/healthz

# Detaylı sistem durumu
curl http://localhost:8080/health/detailed

# Prometheus metrikleri
curl http://localhost:8080/metrics
```
# Admin Log Dashboard
Geliştirme sürecinde katmanları ve logları daha iyi analiz edebilmek için geliştirilmiştir.
http://localhost:8080/admin/logs/dashboard

<img width="1800" height="1130" alt="Screenshot 2025-08-06 at 17 44 55" src="https://github.com/user-attachments/assets/05109cfc-c813-402a-9e8c-86f3abcfc415" />

---


##  Hedeflenen Kullanıcı Profilleri

###  **E-Ticaret Entegrasyonu**
Infinitum AI Agent, büyük e-ticaret platformlarının arama deneyimini devrim niteliğinde geliştirmeyi hedeflemektedir:

- **[Trendyol](https://www.trendyol.com) ve [Hepsiburada](https://www.hepsiburada.com)** - Türkiye'nin önde gelen e-ticaret platformuna AI destekli API tabanlı entegrasyon
- **Diğer E-Ticaret Platformları** - GittiGidiyor, N11, Amazon Türkiye gibi platformlara uyarlanabilir çözümler

###  **Fiyat Karşılaştırma Platformu**
Mevcut fiyat karşılaştırma sitelerine alternatif olarak yeni nesil bir platform geliştirme hedefi:

- **[Akakçe](https://www.akakce.com) ve [Cimri](https://www.cimri.com)   Benzeri Platform** - AI destekli akıllı fiyat karşılaştırması ve Gelişmiş ürün analizi ve öneri sistemi
- **Yenilikçi Özellikler** - Doğal dil işleme ile akıllı arama, otomatik paket önerileri, kişiselleştirilmiş alışveriş deneyimi

###  **Ticari Hedefler**
- **B2B Entegrasyon** - Mevcut e-ticaret platformlarına API tabanlı entegrasyon
- **B2C Platform** - Bağımsız akıllı alışveriş asistanı platformu
- **SaaS Çözümü** - E-ticaret şirketleri için hazır AI arama çözümü
- **White-Label Ürün** - Markalı çözümler için özelleştirilebilir platform

---

## Dökümantasyonlar

**[📖 Dokümantasyonu Okuyun](backend/docs/README.md)** • **[🔧 Hızlı Kurulum](#-hızlı-başlangıç)** • **[💬 Topluluğa Katılın](https://github.com/your-org/infinitum-ai-agent/discussions)**

---

** BTK Hackathon'25 için Infinitum AI Ekibi tarafından geliştirilmiştir**

*Gelişmiş AI ve makine öğrenmesi ile akıllı ürün keşfini güçlendiriyoruz*

</div>
