// =========================================
// GENESIS AGI - Marketing Website Scripts
// Interactive & Dynamic Functionality
// =========================================

document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initScrollAnimations();
    initCodeCopy();
    initNeuralNetwork();
    initSmoothScroll();
    initVideoPlaceholder();
});

// ============= NAVIGATION ============= 
function initNavigation() {
    const nav = document.getElementById('navbar');
    const hamburger = document.getElementById('hamburger');
    const navMenu = document.getElementById('nav-menu');
    const navLinks = document.querySelectorAll('.nav-link');

    // Scroll effect for navbar
    let lastScroll = 0;
    window.addEventListener('scroll', () => {
        const currentScroll = window.pageYOffset;
        
        if (currentScroll > 100) {
            nav.classList.add('scrolled');
        } else {
            nav.classList.remove('scrolled');
        }
        
        lastScroll = currentScroll;
    });

    // Mobile menu toggle
    if (hamburger) {
        hamburger.addEventListener('click', () => {
            hamburger.classList.toggle('active');
            navMenu.classList.toggle('active');
            document.body.style.overflow = navMenu.classList.contains('active') ? 'hidden' : '';
        });
    }

    // Close mobile menu on link click
    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            if (hamburger) {
                hamburger.classList.remove('active');
                navMenu.classList.remove('active');
                document.body.style.overflow = '';
            }
        });
    });

    // Active link highlighting
    const sections = document.querySelectorAll('section[id]');
    
    window.addEventListener('scroll', () => {
        const scrollY = window.pageYOffset;
        
        sections.forEach(section => {
            const sectionHeight = section.offsetHeight;
            const sectionTop = section.offsetTop - 100;
            const sectionId = section.getAttribute('id');
            const navLink = document.querySelector(`.nav-link[href="#${sectionId}"]`);
            
            if (scrollY > sectionTop && scrollY <= sectionTop + sectionHeight) {
                navLinks.forEach(link => link.classList.remove('active'));
                if (navLink) navLink.classList.add('active');
            }
        });
    });
}

// ============= SMOOTH SCROLL ============= 
function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href === '#' || !href) return;
            
            e.preventDefault();
            const target = document.querySelector(href);
            
            if (target) {
                const offsetTop = target.offsetTop - 80;
                window.scrollTo({
                    top: offsetTop,
                    behavior: 'smooth'
                });
            }
        });
    });
}

// ============= SCROLL ANIMATIONS ============= 
function initScrollAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -100px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);

    // Observe elements with data-aos attribute
    document.querySelectorAll('[data-aos]').forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(30px)';
        el.style.transition = 'all 0.6s ease-out';
        observer.observe(el);
    });

    // Parallax effect for hero background
    window.addEventListener('scroll', () => {
        const scrolled = window.pageYOffset;
        const neuralNetwork = document.getElementById('neural-network');
        if (neuralNetwork && scrolled < window.innerHeight) {
            neuralNetwork.style.transform = `translateY(${scrolled * 0.5}px)`;
        }
    });
}

// ============= CODE COPY FUNCTIONALITY ============= 
function copyCode(button) {
    const codeBlock = button.closest('.code-block');
    const code = codeBlock.querySelector('code');
    const text = code.textContent;

    navigator.clipboard.writeText(text).then(() => {
        // Visual feedback
        const originalHTML = button.innerHTML;
        button.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M3 8l4 4 8-8" stroke="currentColor" stroke-width="2"/>
            </svg>
            Copied!
        `;
        button.style.color = '#00ff88';

        setTimeout(() => {
            button.innerHTML = originalHTML;
            button.style.color = '';
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy:', err);
        button.textContent = 'Failed';
        setTimeout(() => {
            button.innerHTML = originalHTML;
        }, 2000);
    });
}

// ============= NEURAL NETWORK ANIMATION ============= 
function initNeuralNetwork() {
    const canvas = document.createElement('canvas');
    const neuralNetwork = document.getElementById('neural-network');
    
    if (!neuralNetwork) return;
    
    neuralNetwork.appendChild(canvas);
    const ctx = canvas.getContext('2d');
    
    let width = canvas.width = neuralNetwork.offsetWidth;
    let height = canvas.height = neuralNetwork.offsetHeight;
    
    // Nodes for the network
    const nodes = [];
    const nodeCount = Math.min(50, Math.floor((width * height) / 15000));
    
    class Node {
        constructor() {
            this.x = Math.random() * width;
            this.y = Math.random() * height;
            this.vx = (Math.random() - 0.5) * 0.5;
            this.vy = (Math.random() - 0.5) * 0.5;
            this.radius = 2;
        }
        
        update() {
            this.x += this.vx;
            this.y += this.vy;
            
            if (this.x < 0 || this.x > width) this.vx *= -1;
            if (this.y < 0 || this.y > height) this.vy *= -1;
        }
        
        draw() {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(0, 255, 136, 0.5)';
            ctx.fill();
        }
    }
    
    // Create nodes
    for (let i = 0; i < nodeCount; i++) {
        nodes.push(new Node());
    }
    
    // Animation loop
    function animate() {
        ctx.clearRect(0, 0, width, height);
        
        // Update and draw nodes
        nodes.forEach(node => {
            node.update();
            node.draw();
        });
        
        // Draw connections
        for (let i = 0; i < nodes.length; i++) {
            for (let j = i + 1; j < nodes.length; j++) {
                const dx = nodes[i].x - nodes[j].x;
                const dy = nodes[i].y - nodes[j].y;
                const distance = Math.sqrt(dx * dx + dy * dy);
                
                if (distance < 150) {
                    ctx.beginPath();
                    ctx.moveTo(nodes[i].x, nodes[i].y);
                    ctx.lineTo(nodes[j].x, nodes[j].y);
                    ctx.strokeStyle = `rgba(0, 255, 136, ${0.2 * (1 - distance / 150)})`;
                    ctx.lineWidth = 1;
                    ctx.stroke();
                }
            }
        }
        
        requestAnimationFrame(animate);
    }
    
    animate();
    
    // Handle resize
    window.addEventListener('resize', () => {
        width = canvas.width = neuralNetwork.offsetWidth;
        height = canvas.height = neuralNetwork.offsetHeight;
    });
}

// ============= TYPING ANIMATION ============= 
function typeWriter(element, text, speed = 50) {
    let i = 0;
    element.textContent = '';
    
    function type() {
        if (i < text.length) {
            element.textContent += text.charAt(i);
            i++;
            setTimeout(type, speed);
        }
    }
    
    type();
}

// ============= COUNTER ANIMATION ============= 
function animateCounter(element, target, duration = 2000) {
    const start = 0;
    const increment = target / (duration / 16);
    let current = start;
    
    const timer = setInterval(() => {
        current += increment;
        if (current >= target) {
            element.textContent = target;
            clearInterval(timer);
        } else {
            element.textContent = Math.floor(current);
        }
    }, 16);
}

// ============= INTERSECTION OBSERVER FOR STATS ============= 
const statsObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            const statNumbers = entry.target.querySelectorAll('.stat-number');
            statNumbers.forEach(stat => {
                const target = parseInt(stat.textContent);
                if (!isNaN(target)) {
                    animateCounter(stat, target);
                }
            });
            statsObserver.unobserve(entry.target);
        }
    });
}, { threshold: 0.5 });

// Observe stat sections
document.querySelectorAll('.hero-stats, .enterprise-stats').forEach(section => {
    if (section) statsObserver.observe(section);
});

// ============= KEYBOARD NAVIGATION ============= 
document.addEventListener('keydown', (e) => {
    // ESC to close mobile menu
    if (e.key === 'Escape') {
        const hamburger = document.getElementById('hamburger');
        const navMenu = document.getElementById('nav-menu');
        if (hamburger && hamburger.classList.contains('active')) {
            hamburger.classList.remove('active');
            navMenu.classList.remove('active');
            document.body.style.overflow = '';
        }
    }
});

// ============= PERFORMANCE OPTIMIZATION ============= 
// Lazy load images when they're near viewport
if ('IntersectionObserver' in window) {
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                if (img.dataset.src) {
                    img.src = img.dataset.src;
                    img.removeAttribute('data-src');
                    observer.unobserve(img);
                }
            }
        });
    });

    document.querySelectorAll('img[data-src]').forEach(img => {
        imageObserver.observe(img);
    });
}

// ============= DETECT USER PREFERENCES ============= 
// Respect user's motion preferences
const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
if (prefersReducedMotion) {
    document.documentElement.style.setProperty('--transition-fast', '0s');
    document.documentElement.style.setProperty('--transition-normal', '0s');
    document.documentElement.style.setProperty('--transition-slow', '0s');
}

// ============= SCROLL PROGRESS INDICATOR ============= 
function updateScrollProgress() {
    const scrollProgress = document.createElement('div');
    scrollProgress.id = 'scroll-progress';
    scrollProgress.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        height: 3px;
        background: linear-gradient(90deg, #00ff88, #00ccff);
        z-index: 9999;
        transition: width 0.1s ease;
    `;
    document.body.appendChild(scrollProgress);
    
    window.addEventListener('scroll', () => {
        const windowHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
        const scrolled = (window.pageYOffset / windowHeight) * 100;
        scrollProgress.style.width = scrolled + '%';
    });
}

updateScrollProgress();

// ============= CONSOLE EASTER EGG ============= 
console.log('%c🧬 Genesis AGI Framework', 'color: #00ff88; font-size: 20px; font-weight: bold;');
console.log('%cThe Framework for Digital Beings', 'color: #a0a0b8; font-size: 14px;');
console.log('%c\nInterested in building with Genesis? Check out our docs:', 'color: #ffffff; font-size: 12px;');
console.log('%chttps://github.com/shaik-shahansha/genesis-agi', 'color: #00ccff; font-size: 12px;');
console.log('\n');

// ============= VIDEO PLACEHOLDER ============= 
function initVideoPlaceholder() {
    const videoPlaceholder = document.getElementById('main-video');
    if (!videoPlaceholder) return;
    
    // When you have the YouTube video link, replace this URL
    const YOUTUBE_VIDEO_ID = ''; // Add your YouTube video ID here
    
    videoPlaceholder.addEventListener('click', () => {
        if (YOUTUBE_VIDEO_ID) {
            // Replace placeholder with actual YouTube embed
            const iframe = document.createElement('iframe');
            iframe.style.cssText = 'width: 100%; height: 100%; border: none; border-radius: 16px;';
            iframe.src = `https://www.youtube.com/embed/${YOUTUBE_VIDEO_ID}?autoplay=1`;
            iframe.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture';
            iframe.allowFullscreen = true;
            
            videoPlaceholder.innerHTML = '';
            videoPlaceholder.appendChild(iframe);
        } else {
            // Show message that video is coming soon
            const message = document.createElement('div');
            message.style.cssText = 'text-align: center; padding: 2rem;';
            message.innerHTML = '<h3 style="color: var(--primary); margin-bottom: 1rem;">Video Coming Soon!</h3><p style="color: var(--text-muted);">Watch this space for a demonstration of Genesis Minds in action.</p>';
            videoPlaceholder.innerHTML = '';
            videoPlaceholder.appendChild(message);
            
            setTimeout(() => {
                location.reload();
            }, 3000);
        }
    });
}

// ============= CONSOLE EASTER EGG ============= 
console.log('%c🧬 Genesis AGI Framework', 'color: #00ff88; font-size: 20px; font-weight: bold;');
console.log('%cThe Framework for Digital Beings', 'color: #a0a0b8; font-size: 14px;');
console.log('%c\nInterested in building with Genesis? Check out our docs:', 'color: #ffffff; font-size: 12px;');
console.log('%chttps://github.com/shaik-shahansha/genesis-agi', 'color: #00ccff; font-size: 12px;');
console.log('\n');

// ============= ANALYTICS PLACEHOLDER ============= 
// Add your analytics tracking here
function trackEvent(category, action, label) {
    // Example: Google Analytics, Plausible, etc.
    console.log('Event tracked:', category, action, label);
}

// Track CTA clicks
document.querySelectorAll('.btn-primary, .btn-secondary').forEach(button => {
    button.addEventListener('click', () => {
        const text = button.textContent.trim();
        trackEvent('CTA', 'Click', text);
    });
});

// ============= POPUP MODALS ============= 
function openPrivacyPopup(event) {
    event.preventDefault();
    const popup = document.getElementById('privacyPopup');
    if (popup) {
        popup.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

function openTermsPopup(event) {
    event.preventDefault();
    const popup = document.getElementById('termsPopup');
    if (popup) {
        popup.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

function closePopup(popupId) {
    const popup = document.getElementById(popupId);
    if (popup) {
        popup.classList.remove('active');
        document.body.style.overflow = '';
    }
}

// Close popup on Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closePopup('privacyPopup');
        closePopup('termsPopup');
    }
});

// Make functions globally available
window.openPrivacyPopup = openPrivacyPopup;
window.openTermsPopup = openTermsPopup;
window.closePopup = closePopup;

// ============= EXPORT FOR TESTING ============= 
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        copyCode,
        animateCounter,
        typeWriter,
        openPrivacyPopup,
        openTermsPopup,
        closePopup
    };
}

