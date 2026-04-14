// Core JavaScript
function initMobileMenu() {
    const mobileMenuBtn = document.getElementById('mobile-menu-btn');
    const mobileMenu = document.getElementById('mobile-menu');
    const closeMenuBtn = document.getElementById('close-menu-btn');
    if (mobileMenuBtn && mobileMenu) {
        mobileMenuBtn.onclick = () => { mobileMenu.classList.remove('hidden'); document.body.style.overflow = 'hidden'; };
        if (closeMenuBtn) closeMenuBtn.onclick = () => { mobileMenu.classList.add('hidden'); document.body.style.overflow = 'auto'; };
    }
}

function initLikeButtons() {
    document.querySelectorAll('.like-btn').forEach(btn => {
        btn.onclick = function() {
            const postId = this.dataset.postId;
            const icon = this.querySelector('i');
            const countSpan = this.querySelector('.likes-count');
            fetch(`/post/${postId}/like/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '', 'X-Requested-With': 'XMLHttpRequest' }
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'liked') icon.classList.add('text-red-600');
                else icon.classList.remove('text-red-600');
                if (countSpan) countSpan.textContent = data.likes_count;
            });
        };
    });
}

document.addEventListener('DOMContentLoaded', () => {
    initMobileMenu();
    initLikeButtons();
});
// Handle unblock form submission via AJAX
document.querySelectorAll('#unblock-form, .block-form').forEach(form => {
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        fetch(this.action, {
            method: 'POST',
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: new FormData(this)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Reload the page to update the UI
                window.location.reload();
            }
        })
        .catch(error => {
            console.error('Error:', error);
            window.location.reload();
        });
    });
});
