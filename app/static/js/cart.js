// app/static/js/cart.js

(function() {
    'use strict';

    // ── AJAX Add to Cart ──
    function initAddToCart() {
        const buttons = document.querySelectorAll('.btn-add-cart');
        
        buttons.forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                
                const slug = this.dataset.slug;
                const form = this.closest('form') || document.createElement('form');
                const quantityInput = form.querySelector('input[name="quantity"]');
                const quantity = quantityInput ? quantityInput.value : 1;
                
                // Get button states
                const normalState = this.querySelector('.btn-normal');
                const loadingState = this.querySelector('.btn-loading-state');
                const addedState = this.querySelector('.btn-added-state');
                
                // Show loading
                if (normalState) normalState.style.display = 'none';
                if (loadingState) loadingState.style.display = 'inline';
                this.disabled = true;
                
                // Create form data
                const formData = new FormData();
                formData.append('quantity', quantity);
                
                // Send AJAX request
                fetch(`/cart/add/${slug}`, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                })
                .then(response => {
                    if (!response.ok) {
                        // If response is 405 or 401, redirect to login
                        if (response.status === 405 || response.status === 401) {
                            window.location.href = '/auth/login?next=' + encodeURIComponent(window.location.pathname);
                            return;
                        }
                        throw new Error('Server error: ' + response.status);
                    }
                    return response.json();
                })
                .then(data => {
                    if (data && data.success) {
                        // Show added state
                        if (loadingState) loadingState.style.display = 'none';
                        if (addedState) addedState.style.display = 'inline';
                        
                        // Update cart count
                        updateCartCount(data.cart_count);
                        
                        // Show success message
                        showToast(data.message, 'success');
                        
                        // Reset button after delay
                        setTimeout(() => {
                            if (addedState) addedState.style.display = 'none';
                            if (normalState) normalState.style.display = 'inline';
                            this.disabled = false;
                        }, 2000);
                    } else {
                        throw new Error(data?.message || 'Failed to add to cart');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    // Show error state
                    if (loadingState) loadingState.style.display = 'none';
                    if (normalState) normalState.style.display = 'inline';
                    this.disabled = false;
                    showToast(error.message || 'Error adding to cart. Please try again.', 'error');
                });
            });
        });
    }

    // ── Update Cart Count ──
    function updateCartCount(count) {
        const cartBadge = document.querySelector('.cart-badge');
        if (cartBadge) {
            cartBadge.textContent = count;
            cartBadge.classList.add('pop');
            setTimeout(() => cartBadge.classList.remove('pop'), 500);
        }
        
        // Update any other cart count displays
        document.querySelectorAll('.cart-count-display').forEach(el => {
            el.textContent = count;
        });
    }

    // ── Toast Notification ──
    function showToast(message, type = 'success') {
        const existingToast = document.querySelector('.toast-notification');
        if (existingToast) {
            existingToast.remove();
        }
        
        const toast = document.createElement('div');
        toast.className = 'toast-notification';
        toast.innerHTML = `
            <span class="toast-icon">${type === 'success' ? '✅' : '❌'}</span>
            <span class="toast-message">${message}</span>
            <button class="toast-close" onclick="this.parentElement.remove()">×</button>
        `;
        
        // Style the toast
        toast.style.cssText = `
            position: fixed;
            bottom: 24px;
            right: 24px;
            padding: 14px 20px;
            background: ${type === 'success' ? '#10b981' : '#ef4444'};
            color: white;
            border-radius: 12px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.15);
            z-index: 9999;
            display: flex;
            align-items: center;
            gap: 12px;
            min-width: 280px;
            max-width: 420px;
            animation: slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards;
            font-family: system-ui, -apple-system, sans-serif;
        `;
        
        document.body.appendChild(toast);
        
        // Auto remove after 4 seconds
        setTimeout(() => {
            if (toast.parentElement) {
                toast.style.opacity = '0';
                toast.style.transform = 'translateY(20px)';
                toast.style.transition = 'all 0.3s ease';
                setTimeout(() => toast.remove(), 300);
            }
        }, 4000);
    }

    // ── Handle Form-based Add to Cart (for detail page) ──
    function initFormAddToCart() {
        const forms = document.querySelectorAll('.add-to-cart-form');
        
        forms.forEach(form => {
            form.addEventListener('submit', function(e) {
                e.preventDefault();
                
                const submitBtn = this.querySelector('button[type="submit"]');
                const slug = submitBtn.dataset.slug || this.action.split('/').pop();
                const quantity = this.querySelector('input[name="quantity"]').value;
                
                // Get button states
                const normalState = submitBtn.querySelector('.btn-normal');
                const loadingState = submitBtn.querySelector('.btn-loading-state');
                const addedState = submitBtn.querySelector('.btn-added-state');
                
                // Show loading
                if (normalState) normalState.style.display = 'none';
                if (loadingState) loadingState.style.display = 'inline';
                submitBtn.disabled = true;
                
                // Create form data
                const formData = new FormData();
                formData.append('quantity', quantity);
                
                // Send AJAX request
                fetch(`/cart/add/${slug}`, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                })
                .then(response => {
                    if (!response.ok) {
                        if (response.status === 405 || response.status === 401) {
                            window.location.href = '/auth/login?next=' + encodeURIComponent(window.location.pathname);
                            return;
                        }
                        throw new Error('Server error: ' + response.status);
                    }
                    return response.json();
                })
                .then(data => {
                    if (data && data.success) {
                        // Show added state
                        if (loadingState) loadingState.style.display = 'none';
                        if (addedState) addedState.style.display = 'inline';
                        
                        // Update cart count
                        updateCartCount(data.cart_count);
                        showToast(data.message, 'success');
                        
                        // Reset button after delay
                        setTimeout(() => {
                            if (addedState) addedState.style.display = 'none';
                            if (normalState) normalState.style.display = 'inline';
                            submitBtn.disabled = false;
                        }, 2000);
                    } else {
                        throw new Error(data?.message || 'Failed to add to cart');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    if (loadingState) loadingState.style.display = 'none';
                    if (normalState) normalState.style.display = 'inline';
                    submitBtn.disabled = false;
                    showToast(error.message || 'Error adding to cart. Please try again.', 'error');
                });
            });
        });
    }

    // ── Add Slide Up Animation ──
    function addStyles() {
        const style = document.createElement('style');
        style.textContent = `
            @keyframes slideUp {
                from { opacity: 0; transform: translateY(20px) scale(0.95); }
                to { opacity: 1; transform: translateY(0) scale(1); }
            }
        `;
        document.head.appendChild(style);
    }

    // ── Initialize ──
    document.addEventListener('DOMContentLoaded', function() {
        addStyles();
        initAddToCart();
        initFormAddToCart();
    });

    // ── Expose for use in other scripts ──
    window.Cart = {
        updateCartCount: updateCartCount,
        showToast: showToast,
        initAddToCart: initAddToCart
    };

})();