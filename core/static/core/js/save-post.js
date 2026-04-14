// Save/Unsave Post Functionality
document.addEventListener('DOMContentLoaded', function() {
    function initSaveButtons() {
        document.querySelectorAll('.save-btn').forEach(btn => {
            // Remove existing event listeners to avoid duplicates
            btn.removeEventListener('click', handleSaveClick);
            btn.addEventListener('click', handleSaveClick);
        });
    }
    
    async function handleSaveClick(e) {
        e.preventDefault();
        const btn = e.currentTarget;
        const postId = btn.dataset.postId;
        const icon = btn.querySelector('i');
        const textSpan = btn.querySelector('span');
        
        // Disable button during request
        btn.style.opacity = '0.5';
        btn.style.pointerEvents = 'none';
        
        try {
            const response = await fetch(`/post/${postId}/save/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                if (data.saved) {
                    icon.classList.add('text-indigo-600');
                    if (textSpan) textSpan.textContent = 'Saved';
                    // Show success message
                    showToast('Post saved to your bookmarks');
                } else {
                    icon.classList.remove('text-indigo-600');
                    if (textSpan) textSpan.textContent = 'Save';
                    showToast('Post removed from saved items');
                }
            } else {
                showToast('Error: ' + (data.error || 'Something went wrong'), 'error');
            }
        } catch (error) {
            console.error('Save post error:', error);
            showToast('Failed to save post. Please try again.', 'error');
        } finally {
            btn.style.opacity = '';
            btn.style.pointerEvents = '';
        }
    }
    
    function showToast(message, type = 'success') {
        // Create toast container if not exists
        let toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:1000';
            document.body.appendChild(toastContainer);
        }
        
        const toast = document.createElement('div');
        toast.className = `bg-${type === 'success' ? 'green' : 'red'}-500 text-white px-4 py-2 rounded-lg shadow-lg mb-2`;
        toast.style.cssText = 'animation: slideIn 0.3s ease-out';
        toast.textContent = message;
        toastContainer.appendChild(toast);
        
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transition = 'opacity 0.3s';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
    
    // Initialize on page load
    initSaveButtons();
    
    // Re-initialize for HTMX loaded content
    document.body.addEventListener('htmx:afterSwap', initSaveButtons);
});
