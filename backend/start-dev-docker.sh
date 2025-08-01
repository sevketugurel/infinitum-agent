#!/bin/bash

# Development Docker Start Script for Enhanced Logging System
# Bu script geliştirme ortamı için Docker deployment'ı yardım eder

set -e  # Herhangi bir hatada çık

echo "🔧 Infinitum AI Agent Development ortamını başlatılıyor..."

# Renkler
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Renkli çıktı fonksiyonları
print_status() {
    echo -e "${BLUE}[BİLGİ]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[BAŞARILI]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[UYARI]${NC} $1"
}

print_error() {
    echo -e "${RED}[HATA]${NC} $1"
}

# Docker ve Docker Compose kontrolü
check_dependencies() {
    print_status "Bağımlılıklar kontrol ediliyor..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker yüklü değil. Lütfen önce Docker'ı yükleyin."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose yüklü değil. Lütfen önce Docker Compose'u yükleyin."
        exit 1
    fi
    
    print_success "Bağımlılık kontrolü tamamlandı"
}

# Gerekli dizinleri oluştur
create_directories() {
    print_status "Gerekli dizinler oluşturuluyor..."
    
    mkdir -p logs
    mkdir -p examples
    
    # Doğru izinleri ayarla
    chmod 755 logs
    chmod 755 examples
    
    print_success "Dizinler oluşturuldu"
}

# Environment dosyası kurulumu
setup_environment() {
    if [ ! -f .env ]; then
        print_status "Environment dosyası ayarlanıyor..."
        cp .env.docker .env
        print_warning ".env dosyası şablondan oluşturuldu. Lütfen gerçek API anahtarlarınızla güncelleyin!"
        print_warning ".env dosyasını düzenleyin ve şunları ayarlayın:"
        echo "  - GOOGLE_API_KEY"
        echo "  - GEMINI_API_KEY" 
        echo "  - SERPAPI_API_KEY"
        echo "  - OPENAI_API_KEY (opsiyonel)"
        echo "  - SENTRY_DSN (opsiyonel, hata izleme için)"
        echo ""
        
        # .env dosyasını development için otomatik optimize et
        sed -i.bak 's/ENVIRONMENT=production/ENVIRONMENT=development/' .env
        sed -i.bak 's/LOG_LEVEL=INFO/LOG_LEVEL=DEBUG/' .env
        sed -i.bak 's/ENABLE_STRUCTURED_LOGGING=true/ENABLE_STRUCTURED_LOGGING=false/' .env
        sed -i.bak 's/ENABLE_RICH_LOGGING=false/ENABLE_RICH_LOGGING=true/' .env
        sed -i.bak 's/ENABLE_DEBUG_LOGGING=false/ENABLE_DEBUG_LOGGING=true/' .env
        rm .env.bak
        
        print_success "Development ortamı için .env dosyası optimize edildi"
        
        read -p "Devam etmek için .env dosyasını güncelledikten sonra Enter'a basın..."
    else
        print_success "Environment dosyası mevcut"
    fi
}

# Uygulamayı build et ve deploy et
build_and_deploy() {
    print_status "Development ortamı için Docker image'ı build ediliyor..."
    
    # Mevcut container'ları durdur
    print_status "Mevcut container'lar durduruluyor..."
    docker-compose -f docker-compose.dev.yml down || true
    
    # Yeni image'ı build et
    print_status "Yeni image build ediliyor..."
    docker-compose -f docker-compose.dev.yml build --no-cache
    
    # Servisleri başlat
    print_status "Development servisleri başlatılıyor..."
    docker-compose -f docker-compose.dev.yml up -d
    
    print_success "Development deployment tamamlandı"
}

# Servislerin hazır olmasını bekle
wait_for_services() {
    print_status "Servislerin hazır olması bekleniyor..."
    
    # Ana uygulama için bekle
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:8080/healthz > /dev/null 2>&1; then
            print_success "Uygulama hazır!"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            print_error "Uygulama beklenen sürede başlatılamadı"
            print_status "Loglar kontrol ediliyor..."
            docker-compose -f docker-compose.dev.yml logs infinitum-ai-agent
            exit 1
        fi
        
        print_status "Uygulama bekleniyor... (deneme $attempt/$max_attempts)"
        sleep 5
        ((attempt++))
    done
}

# Erişim bilgilerini göster
show_access_info() {
    print_success "🎉 Development ortamı başarıyla kuruldu!"
    echo ""
    echo "📊 Servislerinize erişin:"
    echo "  • Uygulama API: http://localhost:8080"
    echo "  • Health Check: http://localhost:8080/healthz"
    echo "  • Logging Dashboard: http://localhost:8080/admin/logs/dashboard"
    echo "  • Logging Health: http://localhost:8080/admin/logging/health"
    echo "  • Prometheus Metrics: http://localhost:9090/metrics"
    echo ""
    echo "📁 Log dosyaları konumu: ./logs/"
    echo "🔧 Konfigürasyon dosyası: .env"
    echo ""
    echo "🚀 Development için Yeni Özellikler:"
    echo "  ✅ Rich console logging (renkli ve güzel formatlanmış)"
    echo "  ✅ DEBUG seviye logging"
    echo "  ✅ Request correlation ID'leri"
    echo "  ✅ Performance monitoring"
    echo "  ✅ Canlı logging dashboard"
    echo "  ✅ Prometheus metrics"
    echo "  ✅ Debug logging aktif"
    echo "  ✅ Düşük threshold (0.5s) ile slow operation detection"
    echo ""
    echo "🔧 Development Komutları:"
    echo "  • Logları göster: docker-compose -f docker-compose.dev.yml logs -f"
    echo "  • Restart: docker-compose -f docker-compose.dev.yml restart"
    echo "  • Stop: docker-compose -f docker-compose.dev.yml down"
    echo "  • Status: docker-compose -f docker-compose.dev.yml ps"
    echo ""
}

# Logları göster fonksiyonu
show_logs() {
    print_status "Uygulama logları gösteriliyor..."
    docker-compose -f docker-compose.dev.yml logs -f infinitum-ai-agent
}

# Ana çalıştırma
main() {
    echo "=================================="
    echo "   Development Ortamı Kurulumu"
    echo "=================================="
    echo ""
    
    check_dependencies
    create_directories
    setup_environment
    build_and_deploy
    wait_for_services
    show_access_info
    
    # Kullanıcı logları görmek istiyor mu
    echo ""
    read -p "Uygulama loglarını görmek ister misiniz? (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        show_logs
    fi
}

# Script argümanlarını işle
case "${1:-}" in
    "logs")
        print_status "Loglar gösteriliyor..."
        docker-compose -f docker-compose.dev.yml logs -f infinitum-ai-agent
        ;;
    "restart")
        print_status "Servisler yeniden başlatılıyor..."
        docker-compose -f docker-compose.dev.yml restart
        wait_for_services
        show_access_info
        ;;
    "stop")
        print_status "Servisler durduruluyor..."
        docker-compose -f docker-compose.dev.yml down
        print_success "Servisler durduruldu"
        ;;
    "status")
        print_status "Servis durumu kontrol ediliyor..."
        docker-compose -f docker-compose.dev.yml ps
        ;;
    "build")
        print_status "Rebuild ediliyor..."
        docker-compose -f docker-compose.dev.yml down
        docker-compose -f docker-compose.dev.yml build --no-cache
        docker-compose -f docker-compose.dev.yml up -d
        wait_for_services
        show_access_info
        ;;
    *)
        main
        ;;
esac