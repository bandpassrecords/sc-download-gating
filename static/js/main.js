/**
 * SoundCloud Download Gating By BandPass Records - Modern JavaScript
 * Enhanced interactions and UX improvements
 */

(function() {
    'use strict';

    // ============================================
    // Navigation Scroll Effect
    // ============================================
    
    const navbar = document.querySelector('.navbar');
    if (navbar) {
        let lastScroll = 0;
        
        window.addEventListener('scroll', function() {
            const currentScroll = window.pageYOffset;
            
            if (currentScroll > 50) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
            
            lastScroll = currentScroll;
        });
    }

    // ============================================
    // Smooth Scroll
    // ============================================
    
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href !== '#' && href.length > 1) {
                e.preventDefault();
                const target = document.querySelector(href);
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            }
        });
    });

    // ============================================
    // Toast Notifications
    // ============================================
    
    window.showToast = function(message, type = 'info') {
        // Remove existing toasts
        const existingToasts = document.querySelectorAll('.toast-notification');
        existingToasts.forEach(toast => toast.remove());
        
        const toast = document.createElement('div');
        toast.className = `toast-notification toast-${type}`;
        toast.innerHTML = `
            <div class="toast-content">
                <i class="fas ${getToastIcon(type)}"></i>
                <span>${message}</span>
            </div>
        `;
        
        // Add styles if not already added
        if (!document.getElementById('toast-styles')) {
            const style = document.createElement('style');
            style.id = 'toast-styles';
            style.textContent = `
                .toast-notification {
                    position: fixed;
                    top: 20px;
                    left: 20px;
                    background: #1e293b;
                    color: #f1f5f9;
                    padding: 1rem 1.5rem;
                    border-radius: 0.75rem;
                    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
                    border: 1px solid #334155;
                    z-index: 10000;
                    animation: slideInLeft 0.3s ease-out;
                    display: flex;
                    align-items: center;
                    gap: 0.75rem;
                    min-width: 300px;
                    max-width: 500px;
                }
                
                .toast-success {
                    border-left: 4px solid #10b981;
                    background: #1e293b;
                    color: #f1f5f9;
                }
                
                .toast-error {
                    border-left: 4px solid #ef4444;
                    background: #1e293b;
                    color: #f1f5f9;
                }
                
                .toast-info {
                    border-left: 4px solid #06b6d4;
                    background: #1e293b;
                    color: #f1f5f9;
                }
                
                .toast-warning {
                    border-left: 4px solid #f59e0b;
                    background: #1e293b;
                    color: #f1f5f9;
                }
                
                .toast-content {
                    display: flex;
                    align-items: center;
                    gap: 0.75rem;
                    color: #f1f5f9;
                }
                
                .toast-content i {
                    color: inherit;
                }
                
                @keyframes slideInLeft {
                    from {
                        transform: translateX(-100%);
                        opacity: 0;
                    }
                    to {
                        transform: translateX(0);
                        opacity: 1;
                    }
                }
            `;
            document.head.appendChild(style);
        }
        
        document.body.appendChild(toast);
        
        // Auto remove after 4 seconds
        setTimeout(() => {
            toast.style.animation = 'slideInLeft 0.3s ease-out reverse';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    };
    
    function getToastIcon(type) {
        const icons = {
            success: 'fa-check-circle',
            error: 'fa-exclamation-circle',
            warning: 'fa-exclamation-triangle',
            info: 'fa-info-circle'
        };
        return icons[type] || icons.info;
    }

    // ============================================
    // Form Enhancements
    // ============================================
    
    // Auto-submit on filter changes with debounce
    const filterForms = document.querySelectorAll('form[data-auto-submit]');
    filterForms.forEach(form => {
        const inputs = form.querySelectorAll('input, select');
        let timeout;
        
        inputs.forEach(input => {
            input.addEventListener('change', function() {
                clearTimeout(timeout);
                timeout = setTimeout(() => {
                    form.submit();
                }, 300);
            });
        });
    });

    // File upload preview
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        input.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                // Get or create file info display
                let fileInfo = input.parentElement.querySelector('.file-info');
                if (!fileInfo) {
                    fileInfo = document.createElement('div');
                    fileInfo.className = 'file-info mt-2';
                    input.parentElement.appendChild(fileInfo);
                }
                
                // Check if this is an XML file input (has accept=".xml" attribute)
                const isXmlInput = input.hasAttribute('accept') && input.getAttribute('accept').includes('.xml');
                
                // Validate file type first (for XML inputs)
                if (isXmlInput && !file.name.toLowerCase().endsWith('.xml')) {
                    fileInfo.innerHTML = `
                        <div class="alert alert-danger mb-0">
                            <i class="fas fa-exclamation-triangle"></i> 
                            Please select an XML file.
                        </div>
                    `;
                    input.value = '';
                    // Remove file info after a short delay
                    setTimeout(() => {
                        if (fileInfo && fileInfo.parentElement) {
                            fileInfo.remove();
                        }
                    }, 3000);
                    return;
                }
                
                // Validate file size
                if (file.size > 250 * 1024 * 1024) {
                    fileInfo.innerHTML = `
                        <div class="alert alert-danger mb-0">
                            <i class="fas fa-exclamation-triangle"></i> 
                            File size exceeds 250MB limit
                        </div>
                    `;
                    input.value = '';
                    // Remove file info after a short delay
                    setTimeout(() => {
                        if (fileInfo && fileInfo.parentElement) {
                            fileInfo.remove();
                        }
                    }, 3000);
                    return;
                }
                
                // Only show file info if validation passes
                const fileName = file.name;
                const fileSize = (file.size / 1024 / 1024).toFixed(2);
                
                fileInfo.innerHTML = `
                    <div class="alert alert-info mb-0">
                        <i class="fas fa-file"></i> 
                        <strong>${fileName}</strong> (${fileSize} MB)
                    </div>
                `;
            }
        });
    });

    // ============================================
    // Card Hover Effects - Removed movement animation
    // ============================================

    // ============================================
    // Search Enhancement
    // ============================================
    
    const searchInputs = document.querySelectorAll('input[type="search"], input[name="query"]');
    searchInputs.forEach(input => {
        let searchTimeout;
        
        input.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const form = this.closest('form');
            
            if (form && form.dataset.autoSubmit) {
                searchTimeout = setTimeout(() => {
                    form.submit();
                }, 500);
            }
        });
    });

    // ============================================
    // Copy to Clipboard
    // ============================================
    
    window.copyToClipboard = function(text, successMessage = 'Copied to clipboard!') {
        if (navigator.clipboard) {
            navigator.clipboard.writeText(text).then(() => {
                showToast(successMessage, 'success');
            }).catch(() => {
                showToast('Failed to copy', 'error');
            });
        } else {
            // Fallback for older browsers
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            document.body.appendChild(textarea);
            textarea.select();
            
            try {
                document.execCommand('copy');
                showToast(successMessage, 'success');
            } catch (err) {
                showToast('Failed to copy', 'error');
            }
            
            document.body.removeChild(textarea);
        }
    };

    // ============================================
    // Loading States
    // ============================================
    
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = this.querySelector('button[type="submit"]');
            if (submitBtn && !submitBtn.disabled) {
                submitBtn.disabled = true;
                const originalText = submitBtn.innerHTML;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
                
                // Re-enable after 10 seconds as fallback
                setTimeout(() => {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalText;
                }, 10000);
            }
        });
    });

    // ============================================
    // Utility Functions
    // ============================================
    
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // ============================================
    // Intersection Observer for Animations
    // ============================================
    
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in-up');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);
    
    // Observe all cards and sections
    document.querySelectorAll('.card, section, .stat-card').forEach(el => {
        observer.observe(el);
    });

    // ============================================
    // Initialize on DOM Ready
    // ============================================
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
    function init() {
        console.log('SoundCloud Download Gating By BandPass Records - Modern UI initialized');
    }

})();

