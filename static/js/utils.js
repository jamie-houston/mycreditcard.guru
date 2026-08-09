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

// Promise-returning replacements for native confirm()/prompt(). Native dialogs
// hard-freeze browser automation until a human dismisses them, which is what
// made the confirm paths untestable. Builds its own overlay rather than reusing
// .modal, which is display:none until the .modal[style*="block"] hack fires.
function openDialog({message, confirmLabel, cancelLabel, cancelValue, withInput = false, defaultValue = ''}) {
    return new Promise(resolve => {
        const previouslyFocused = document.activeElement;

        const overlay = document.createElement('div');
        overlay.className = 'confirm-dialog-overlay';
        overlay.setAttribute('data-testid', 'confirm-dialog');
        overlay.setAttribute('role', 'dialog');
        overlay.setAttribute('aria-modal', 'true');
        overlay.innerHTML = `
            <div class="modal-content confirm-dialog-content">
                <div class="modal-body">
                    <p class="confirm-dialog-message"></p>
                    ${withInput ? '<input type="text" class="confirm-dialog-input" data-testid="confirm-dialog-input">' : ''}
                    <div class="confirm-dialog-actions">
                        <button type="button" class="btn-secondary" data-testid="confirm-dialog-cancel"></button>
                        <button type="button" class="btn-primary" data-testid="confirm-dialog-accept"></button>
                    </div>
                </div>
            </div>`;

        // Set every caller-supplied string as text, never as markup — the rename
        // dialog's default value is ProfileEntity.name, which is user input.
        overlay.querySelector('.confirm-dialog-message').textContent = message;
        const cancelButton = overlay.querySelector('[data-testid="confirm-dialog-cancel"]');
        const acceptButton = overlay.querySelector('[data-testid="confirm-dialog-accept"]');
        cancelButton.textContent = cancelLabel;
        acceptButton.textContent = confirmLabel;
        const input = overlay.querySelector('.confirm-dialog-input');
        if (input) input.value = defaultValue;

        function close(value) {
            document.removeEventListener('keydown', onKeydown, true);
            overlay.remove();
            if (previouslyFocused && previouslyFocused.focus) previouslyFocused.focus();
            resolve(value);
        }

        function onKeydown(event) {
            if (event.key === 'Escape') {
                // Capture phase + stopPropagation so dismissing this dialog does
                // not also close a #cardModal underneath it.
                event.stopPropagation();
                close(cancelValue);
            } else if (event.key === 'Enter' && input) {
                event.preventDefault();
                close(input.value);
            }
        }

        acceptButton.addEventListener('click', () => close(input ? input.value : true));
        cancelButton.addEventListener('click', () => close(cancelValue));
        overlay.addEventListener('click', event => {
            if (event.target === overlay) close(cancelValue);
        });
        document.addEventListener('keydown', onKeydown, true);

        document.body.appendChild(overlay);
        (input || acceptButton).focus();
    });
}

function confirmDialog(message, {confirmLabel = 'OK', cancelLabel = 'Cancel'} = {}) {
    return openDialog({message, confirmLabel, cancelLabel, cancelValue: false});
}

function promptDialog(message, defaultValue = '') {
    return openDialog({
        message, confirmLabel: 'OK', cancelLabel: 'Cancel',
        cancelValue: null, withInput: true, defaultValue,
    });
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
