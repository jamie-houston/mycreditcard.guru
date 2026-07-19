// Shared utilities used across templates. Loaded in base.html's <head>,
// before {% block content %}, so these globals exist before any page script runs.

// Phase K: household entity names (ProfileEntity.name) are user
// input — escape before interpolating into HTML anywhere on the site.
function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

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

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        border-radius: 8px;
        color: white;
        font-weight: 500;
        z-index: 1000;
        transition: all 0.3s ease;
        ${type === 'success' ? 'background: #3FCF8E; color: #06251A;' :
          type === 'error' ? 'background: #F87171;' : 'background: #5C6675;'}
    `;
    notification.textContent = message;

    document.body.appendChild(notification);

    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => {
            if (notification.parentNode) {
                document.body.removeChild(notification);
            }
        }, 300);
    }, 3000);
}

function showError(message) {
    const sections = ['cardCollection', 'categoryOptimization', 'spendingProfile'];
    sections.forEach(sectionId => {
        const element = document.getElementById(sectionId);
        if (element && element.innerHTML.includes('Loading')) {
            element.innerHTML = `<div class="error">${message}</div>`;
        }
    });
}

async function loadOwnedCardIds() {
    return new Set(await UserDataManager.getCards());
}
