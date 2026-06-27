// ================================
// PC_WORKMAN LANDING PAGE SCRIPT
// Interactive Features & Animations
// ================================

// === VARIABLES ===
const sidebar = document.getElementById('sidebar');
const mobileMenuToggle = document.getElementById('mobileMenuToggle');
const navLinks = document.querySelectorAll('.nav-link');
const sections = document.querySelectorAll('section[id]');
const quizForm = document.getElementById('quizForm');
const quizResult = document.getElementById('quizResult');
const faqItems = document.querySelectorAll('.faq-item');

// === TYPING ANIMATION ===
const typingText = document.getElementById('typingText');
const originalText = typingText ? typingText.textContent : '';
let typingIndex = 0;
let isTyping = true;

function typeText() {
    if (!typingText) return;
    
    if (isTyping) {
        if (typingIndex < originalText.length) {
            typingText.textContent = originalText.substring(0, typingIndex + 1);
            typingIndex++;
            setTimeout(typeText, 80); // Typing speed
        } else {
            isTyping = false;
            setTimeout(typeText, 3000); // Pause before restart
        }
    } else {
        // Reset and restart typing
        typingIndex = 0;
        isTyping = true;
        typingText.textContent = '';
        setTimeout(typeText, 500);
    }
}

// Start typing animation when page loads
window.addEventListener('load', () => {
    setTimeout(typeText, 1000); // Delay before starting
});

// === MINI SIDEBAR (desktop): collapsed by default — no expand-then-collapse flash ===
// The HTML already ships .sidebar.mini + body.sidebar-docked so it paints collapsed
// on the first frame; this just reasserts it (and stays a no-op on mobile ≤768).
if (window.innerWidth > 768 && sidebar) {
    sidebar.classList.add('mini');
    document.body.classList.add('sidebar-docked');
}

// === MOBILE MENU TOGGLE ===
mobileMenuToggle.addEventListener('click', () => {
    sidebar.classList.toggle('active');
    document.body.style.overflow = sidebar.classList.contains('active') ? 'hidden' : 'auto';
});

// Close sidebar when clicking outside on mobile
document.addEventListener('click', (e) => {
    if (window.innerWidth <= 768 && 
        !sidebar.contains(e.target) && 
        !mobileMenuToggle.contains(e.target) &&
        sidebar.classList.contains('active')) {
        sidebar.classList.remove('active');
        document.body.style.overflow = 'auto';
    }
});

// === SMOOTH SCROLL & ACTIVE SECTION HIGHLIGHTING ===
navLinks.forEach(link => {
    link.addEventListener('click', (e) => {
        const targetId = link.getAttribute('href');
        // Real page links (download/, blog/) must navigate normally —
        // only in-page #anchors get the smooth-scroll treatment.
        if (!targetId || !targetId.startsWith('#')) return;
        e.preventDefault();
        const targetSection = document.querySelector(targetId);
        
        if (targetSection) {
            const offset = 80;
            const targetPosition = targetSection.offsetTop - offset;
            
            window.scrollTo({
                top: targetPosition,
                behavior: 'smooth'
            });
            
            // Close mobile menu after click
            if (window.innerWidth <= 768) {
                sidebar.classList.remove('active');
                document.body.style.overflow = 'auto';
            }
        }
    });
});

// Update active nav link on scroll
function updateActiveNav() {
    let current = '';
    const scrollPosition = window.scrollY + 100;
    
    sections.forEach(section => {
        const sectionTop = section.offsetTop;
        const sectionHeight = section.clientHeight;
        
        if (scrollPosition >= sectionTop && scrollPosition < sectionTop + sectionHeight) {
            current = section.getAttribute('id');
        }
    });
    
    navLinks.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('data-section') === current) {
            link.classList.add('active');
        }
    });
}

window.addEventListener('scroll', updateActiveNav);
updateActiveNav(); // Initial call

// === INTERACTIVE QUIZ ===
const quizResponses = {
    'lag': {
        answer: 'Wykryłem potencjalny bottleneck! Twój CPU może być przeciążony podczas gry. To częsty problem przy starszych procesorach lub podczas jednoczesnego streamowania.',
        suggestions: [
            'Zamknij niepotrzebne aplikacje w tle (Chrome, Discord, itp.)',
            'Obniż ustawienia graficzne w grze (szczególnie CPU-intensive features jak shadows, physics)',
            'Sprawdź czy nie ma procesów pożerających zasoby (użyj PC_Workman Suspicious Processes)',
            'Rozważ upgrade CPU lub włącz Performance Mode w Windows'
        ]
    },
    'temperatura': {
        answer: 'AI wykrywa problem z chłodzeniem! Wysokie temperatury mogą być spowodowane zapchaniem wentylatorów kurzem, wyschniętą pastą termoprzewodzącą lub nieoptymalnymi fan curves.',
        suggestions: [
            'Oczyść wentylatory z kurzu (sprężone powietrze)',
            'Wymień pastę termoprzewodzącą (szczególnie jeśli laptop ma 3+ lata)',
            'Ustaw agresywniejsze fan curves w PC_Workman Cooling Control',
            'Sprawdź czy wentylatory działają prawidłowo',
            'Rozważ laptop cooling pad lub lepszą wentylację obudowy'
        ]
    },
    'szybkość': {
        answer: 'System działa wolno? To może być problem z dyskiem, RAM-em lub zbyt wieloma aplikacjami startującymi z Windows. PC_Workman hck_GPT może zoptymalizować autostart i usługi!',
        suggestions: [
            'Wyłącz niepotrzebne aplikacje z autostartu (Task Manager → Startup)',
            'Użyj hck_GPT do optymalizacji usług Windows (18-pytaniowa diagnostyka)',
            'Sprawdź czy masz wystarczająco RAM (8GB minimum dla Windows 11)',
            'Rozważ upgrade na SSD jeśli używasz HDD',
            'Zrób skanowanie antywirusowe (minersy kryptowalut spowalniają system!)'
        ]
    },
    'miner': {
        answer: 'ALERT! Podejrzenie złośliwego oprogramowania. PC_Workman wykrywa procesy które mogą być minersami kryptowalut lub malware pożerającym zasoby.',
        suggestions: [
            'Użyj PC_Workman Suspicious Processes Detection NATYCHMIAST',
            'Sprawdź Task Manager → Szczegóły i posortuj po CPU usage',
            'Zrób full scan Windows Defender lub Malwarebytes',
            'Sprawdź ostatnio zainstalowane programy (Panel Sterowania)',
            'Zmień hasła po usunięciu malware (szczególnie crypto wallets!)'
        ]
    },
    'default': {
        answer: 'Hmm, problem brzmi nietypowo. Mogę polecić pełną diagnostykę z PC_Workman! AI przeanalizuje logi systemowe, procesy w tle, temperatury, napięcia i historię performance issues.',
        suggestions: [
            'Uruchom PC_Workman Full System Scan',
            'Użyj hck_GPT do kompleksowej diagnostyki (18 pytań)',
            'Sprawdź Event Viewer w Windows (błędy systemowe)',
            'Zrób backup danych na wszelki wypadek',
            'Dołącz do community HCK_Labs na X/LinkedIn z opisem problemu'
        ]
    }
};

quizForm.addEventListener('submit', (e) => {
    e.preventDefault();
    
    const symptom = document.getElementById('symptom').value.toLowerCase();
    const aiAnswer = document.getElementById('aiAnswer');
    const aiSuggestions = document.getElementById('aiSuggestions');
    
    // Show thinking animation
    quizResult.classList.remove('hidden');
    aiAnswer.textContent = '';
    aiSuggestions.innerHTML = '';
    
    // Simulate AI thinking delay
    setTimeout(() => {
        let response = quizResponses['default'];
        
        // Simple keyword matching
        if (symptom.includes('lag') || symptom.includes('fps') || symptom.includes('przycina')) {
            response = quizResponses['lag'];
        } else if (symptom.includes('temperatura') || symptom.includes('nagrzewa') || symptom.includes('gorący') || symptom.includes('przegrzewa')) {
            response = quizResponses['temperatura'];
        } else if (symptom.includes('wolno') || symptom.includes('wolny') || symptom.includes('długo') || symptom.includes('zacina')) {
            response = quizResponses['szybkość'];
        } else if (symptom.includes('miner') || symptom.includes('wirus') || symptom.includes('malware') || symptom.includes('podejrzan')) {
            response = quizResponses['miner'];
        }
        
        // Display answer
        aiAnswer.textContent = response.answer;
        
        // Display suggestions
        response.suggestions.forEach(suggestion => {
            const li = document.createElement('li');
            li.textContent = suggestion;
            aiSuggestions.appendChild(li);
        });
        
        // Smooth scroll to result
        setTimeout(() => {
            quizResult.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }, 100);
    }, 1500);
});

// === FAQ ACCORDION ===
faqItems.forEach(item => {
    const question = item.querySelector('.faq-question');
    
    question.addEventListener('click', () => {
        const isActive = item.classList.contains('active');
        
        // Close all other items
        faqItems.forEach(otherItem => {
            otherItem.classList.remove('active');
        });
        
        // Toggle current item
        if (!isActive) {
            item.classList.add('active');
        }
    });
});

// === NEWSLETTER FORMS ===
const newsletterForms = document.querySelectorAll('.newsletter-form, .footer-newsletter');

newsletterForms.forEach(form => {
    form.addEventListener('submit', (e) => {
        e.preventDefault();
        const email = form.querySelector('input[type="email"]').value;
        
        // Simulate newsletter signup
        alert(`🎉 Dzięki! ${email} został dodany do listy. Sprawdź maila za kilka minut!`);
        form.reset();
    });
});

// === INTERSECTION OBSERVER FOR ANIMATIONS ===
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
        }
    });
}, observerOptions);

// Observe feature cards, killer cards, blog cards
const animatedElements = document.querySelectorAll(
    '.feature-card, .killer-card, .blog-card, .comparison-table, .story-content'
);

animatedElements.forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(30px)';
    el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
    observer.observe(el);
});

// === SCROLL PROGRESS INDICATOR (Optional Enhancement) ===
function updateScrollProgress() {
    const winScroll = document.documentElement.scrollTop;
    const height = document.documentElement.scrollHeight - document.documentElement.clientHeight;
    const scrolled = (winScroll / height) * 100;
    
    // Update a progress bar if you want to add one later
    // For now, just console log for debugging
    // console.log('Scroll progress:', scrolled + '%');
}

window.addEventListener('scroll', updateScrollProgress);

// === PARALLAX EFFECT FOR HERO ===
const heroBackground = document.querySelector('.hero-background');

if (heroBackground) {
    window.addEventListener('scroll', () => {
        const scrolled = window.pageYOffset;
        heroBackground.style.transform = `translateY(${scrolled * 0.5}px)`;
        heroBackground.style.opacity = 1 - scrolled / 800;
    });
}

// === DYNAMIC YEAR IN FOOTER ===
const currentYear = new Date().getFullYear();
const footerText = document.querySelector('.footer-bottom p');
if (footerText && currentYear > 2024) {
    footerText.textContent = footerText.textContent.replace('2024-2025', `2024-${currentYear}`);
}

// === EASTER EGG: Konami Code ===
let konamiCode = [];
const konamiSequence = ['ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight', 'b', 'a'];

document.addEventListener('keydown', (e) => {
    konamiCode.push(e.key);
    konamiCode = konamiCode.slice(-10);
    
    if (konamiCode.join(',') === konamiSequence.join(',')) {
        // Easter egg activated!
        document.body.style.animation = 'rainbow 2s ease-in-out';
        alert('🎮 KONAMI CODE UNLOCKED! 🔥\n\nGratulacje! Odkryłeś easter egg PC_Workman!\nMarcin mówi: "Building in public, gaming like a pro!" 💪');
        
        // Add rainbow animation
        const style = document.createElement('style');
        style.textContent = `
            @keyframes rainbow {
                0% { filter: hue-rotate(0deg); }
                100% { filter: hue-rotate(360deg); }
            }
        `;
        document.head.appendChild(style);
    }
});

// === PERFORMANCE MONITORING (Dev Tool) ===
if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    console.log('%c🔥 PC_WORKMAN LANDING PAGE', 'font-size: 20px; color: #00FF99; font-weight: bold;');
    console.log('%cBuilt with ❤️ by HCK_Labs', 'font-size: 14px; color: #00D9FF;');
    console.log('%cCheck out the repo: https://github.com/HCK_Labs/PC_Workman', 'font-size: 12px; color: #8892B0;');
    
    // Log page load performance
    window.addEventListener('load', () => {
        const perfData = performance.timing;
        const loadTime = perfData.loadEventEnd - perfData.navigationStart;
        console.log(`⚡ Page loaded in ${loadTime}ms`);
    });
}

// === INITIALIZE ===
console.log('✅ PC_Workman Landing Page initialized');
console.log('🤖 All interactive features loaded');
console.log('🚀 Building in public on 10-year-old laptop!');

// === GLOBAL TOP NAV: hide on scroll down, reveal on scroll up ===
(function () {
    const topnav = document.getElementById('globalTopnav');
    if (!topnav) return;
    let lastY = window.scrollY;
    let ticking = false;
    function onScroll() {
        const y = window.scrollY;
        if (y > lastY && y > 90) {
            topnav.classList.add('gt-hidden');      // scrolling down
        } else {
            topnav.classList.remove('gt-hidden');   // scrolling up / near top
        }
        lastY = y;
        ticking = false;
    }
    window.addEventListener('scroll', () => {
        if (!ticking) { window.requestAnimationFrame(onScroll); ticking = true; }
    }, { passive: true });

    // Remember the language choice (no auto-redirect — SEO-safe)
    topnav.querySelectorAll('.gt-lang a[data-lang]').forEach(a => {
        a.addEventListener('click', () => localStorage.setItem('pcw_lang', a.getAttribute('data-lang')));
    });
})();
