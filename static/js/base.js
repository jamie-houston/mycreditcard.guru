        // Global user state
        let currentUser = null;
        let isAuthenticated = false;

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

        // Initialize user authentication state
        async function initUserState() {
            try {
                const response = await fetch(`${API_BASE}/users/status/`);
                const data = await response.json();
                const wasAuthenticated = isAuthenticated;
                const previousUser = currentUser;

                isAuthenticated = data.authenticated;
                currentUser = data.user;

                // Handle user state changes
                if (wasAuthenticated !== isAuthenticated ||
                    (previousUser && currentUser && previousUser.id !== currentUser.id)) {
                    await handleUserStateChange(wasAuthenticated, isAuthenticated, previousUser, currentUser);
                }

                return data;
            } catch (error) {
                console.error('Error checking user status:', error);
                isAuthenticated = false;
                currentUser = null;
                return { authenticated: false, user: null };
            }
        }

        // Handle user authentication state changes
        async function handleUserStateChange(wasAuthenticated, isNowAuthenticated, previousUser, newUser) {
            console.log('User state changed:', { wasAuthenticated, isNowAuthenticated, previousUser, newUser });

            if (wasAuthenticated && !isNowAuthenticated) {
                // User logged out - clear all local data
                console.log('🔓 User logged out, clearing local data');
                clearUserData();
                // Clear the sync completion flag so future logins can trigger sync
                localStorage.removeItem('dataSyncCompletedFor');
            } else if (!wasAuthenticated && isNowAuthenticated) {
                // User logged in - handle data synchronization
                console.log('🔒 User logged in, handling data synchronization');
                await handleLoginDataSync();
            } else if (wasAuthenticated && isNowAuthenticated && previousUser && newUser && previousUser.id !== newUser.id) {
                // Different user logged in - clear old data and sync new
                console.log('🔄 Different user logged in, switching user data');
                clearUserData();
                await syncUserDataFromServer();
                localStorage.setItem('dataSyncCompletedFor', String(newUser.id));
            }

            // Refresh current page data
            console.log('🔄 Refreshing page data after state change');
            if (typeof loadUserCards === 'function') {
                await loadUserCards();
            }
            if (typeof filterCategories === 'function') {
                await filterCategories();
            }
            if (typeof filterCards === 'function') {
                filterCards();
            }
        }

        // Clear all user data from localStorage
        function clearUserData() {
            console.log('🗑️ Clearing user data from localStorage...');
            console.log('Before clear - userCards:', localStorage.getItem('userCards'));
            console.log('Before clear - userSpending:', localStorage.getItem('userSpending'));
            console.log('Before clear - userPreferences:', localStorage.getItem('userPreferences'));
            console.log('Before clear - userCardDetails:', localStorage.getItem('userCardDetails'));

            localStorage.removeItem('userSpending');
            localStorage.removeItem('userCards');
            localStorage.removeItem('userPreferences');
            localStorage.removeItem('userCardDetails');

            console.log('After clear - userCards:', localStorage.getItem('userCards'));
            console.log('After clear - userSpending:', localStorage.getItem('userSpending'));
            console.log('✅ All user data cleared from localStorage');
        }

        // Handle data synchronization when user logs in
        async function handleLoginDataSync() {
            try {
                // Check if sync has already been completed for this account.
                // Stored in localStorage (not sessionStorage) so it survives
                // closing the tab/browser - otherwise every new browser
                // session looks like a fresh login and re-prompts.
                const syncCompletedFor = localStorage.getItem('dataSyncCompletedFor');
                if (syncCompletedFor && currentUser && syncCompletedFor === String(currentUser.id)) {
                    console.log('📋 Data sync already completed for this account, skipping');
                    return;
                }

                // Get local data before syncing
                const localCards = LocalStorage.getCards();
                const localSpending = LocalStorage.getSpending();
                const localPreferences = LocalStorage.getPreferences();
                const localCardDetails = LocalStorage.getCardDetails();

                const hasLocalData = localCards.length > 0;

                // Get server data
                const serverResponse = await fetch(`${API_BASE}/users/data/`);
                const serverData = await serverResponse.json();

                const hasServerData = (serverData.cards && serverData.cards.length > 0) ||
                                    (serverData.spending && Object.keys(serverData.spending).length > 0);

                // Only a real conflict if the local and server card sets
                // actually differ - if they already match (e.g. a previous
                // merge already synced them), there's nothing to ask about.
                const serverCards = serverData.cards || [];
                const cardsMatch = localCards.length === serverCards.length &&
                    localCards.every(c => serverCards.includes(c));

                if (hasLocalData && hasServerData && !cardsMatch) {
                    // Both have data and they differ - ask user what to do
                    await showDataSyncModal(localCards, localSpending, localCardDetails, serverData);
                } else if (hasLocalData && !hasServerData) {
                    // Only local data - save it to server (new user scenario)
                    console.log('📤 Saving local data to new user account');
                    await saveLocalDataToServer(localCards, localSpending, localPreferences, localCardDetails);
                    await syncUserDataFromServer();
                    // Mark sync as completed
                    localStorage.setItem('dataSyncCompletedFor', String(currentUser.id));
                } else {
                    // Only server data, no data at all, or local already matches server
                    console.log('📥 Syncing data from server');
                    await syncUserDataFromServer();
                    // Mark sync as completed
                    localStorage.setItem('dataSyncCompletedFor', String(currentUser.id));
                }

            } catch (error) {
                console.error('Error handling login data sync:', error);
                // Fallback to just syncing from server
                await syncUserDataFromServer();
                // Mark sync as completed even on error to prevent repeated prompts
                if (currentUser) {
                    localStorage.setItem('dataSyncCompletedFor', String(currentUser.id));
                }
            }
        }

        // Sync user data from server when logging in
        async function syncUserDataFromServer() {
            try {
                // Force refresh of user data from server
                const serverData = await fetch(`${API_BASE}/users/data/`);
                const data = await serverData.json();

                // Update localStorage with server data
                if (data.spending) {
                    localStorage.setItem('userSpending', JSON.stringify(data.spending));
                }
                if (data.cards) {
                    localStorage.setItem('userCards', JSON.stringify(data.cards));
                }
                if (data.preferences) {
                    localStorage.setItem('userPreferences', JSON.stringify(data.preferences));
                }

                console.log('User data synced from server:', data);
            } catch (error) {
                console.error('Error syncing user data from server:', error);
            }
        }

        // Show modal to handle data conflict when both local and server data exist
        async function showDataSyncModal(localCards, localSpending, localCardDetails, serverData) {
            return new Promise((resolve) => {
                // Create modal HTML
                const modalHtml = `
                    <div id="dataSyncModal" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.7); z-index: 10000; display: flex; align-items: center; justify-content: center;">
                        <div style="background: var(--surface); border: 1px solid var(--border); border-radius: 16px; max-width: 600px; width: 90%; padding: 32px; max-height: 80vh; overflow-y: auto;">
                            <h2 style="margin: 0 0 20px 0; color: var(--text-strong);">Sync Your Data</h2>
                            <p style="color: var(--muted); margin-bottom: 20px;">
                                We found credit cards stored locally on this device and cards associated with your account.
                                How would you like to handle this?
                            </p>

                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0;">
                                <div style="border: 1px solid var(--border); border-radius: 12px; padding: 16px; background: var(--bg);">
                                    <h4 style="margin: 0 0 8px 0; color: var(--text);">Local Data</h4>
                                    <p style="margin: 0 0 8px 0; font-size: 14px; color: var(--muted);">${localCards.length} cards saved locally</p>
                                    ${localCards.length > 0 ? `<div style="font-size: 12px; color: var(--muted-2);">Cards stored on this device</div>` : ''}
                                </div>
                                <div style="border: 1px solid var(--border); border-radius: 12px; padding: 16px; background: var(--bg);">
                                    <h4 style="margin: 0 0 8px 0; color: var(--text);">Account Data</h4>
                                    <p style="margin: 0 0 8px 0; font-size: 14px; color: var(--muted);">${(serverData.cards || []).length} cards in your account</p>
                                    ${(serverData.cards || []).length > 0 ? `<div style="font-size: 12px; color: var(--muted-2);">Saved to your account</div>` : ''}
                                </div>
                            </div>

                            <div style="display: flex; flex-direction: column; gap: 12px; margin: 24px 0;">
                                <button
                                    onclick="handleDataSyncChoice('keep_account')"
                                    style="background: var(--surface); border: 1px solid var(--border); color: var(--text); padding: 12px 20px; border-radius: 8px; font-weight: 600; cursor: pointer; transition: background 0.2s;"
                                >
                                    Keep Account Data (Replace local data)
                                </button>
                                <button
                                    onclick="handleDataSyncChoice('merge')"
                                    style="background: var(--accent); color: var(--accent-ink); border: none; padding: 12px 20px; border-radius: 8px; font-weight: 600; cursor: pointer; transition: filter 0.2s;"
                                >
                                    Merge Both (Add local cards to account)
                                </button>
                                <button
                                    onclick="handleDataSyncChoice('keep_local')"
                                    style="background: var(--surface); border: 1px solid var(--border); color: var(--text); padding: 12px 20px; border-radius: 8px; font-weight: 600; cursor: pointer; transition: background 0.2s;"
                                >
                                    Keep Local Data (Replace account data)
                                </button>
                            </div>

                            <p style="font-size: 12px; color: var(--muted-2); margin-top: 16px;">
                                Tip: Merging is usually the best option to keep all your cards.
                            </p>
                        </div>
                    </div>
                `;

                // Add modal to page
                document.body.insertAdjacentHTML('beforeend', modalHtml);

                // Handle user choice
                window.handleDataSyncChoice = async (choice) => {
                    const modal = document.getElementById('dataSyncModal');
                    modal.remove();

                    try {
                        if (choice === 'keep_account') {
                            // Just sync from server, overwriting local data
                            await syncUserDataFromServer();
                        } else if (choice === 'merge') {
                            // Add local cards to server, then sync everything
                            await saveLocalDataToServer(localCards, localSpending, {}, localCardDetails);
                            await syncUserDataFromServer();
                        } else if (choice === 'keep_local') {
                            // Replace server data with local data
                            await saveLocalDataToServer(localCards, localSpending, {}, localCardDetails);
                            await syncUserDataFromServer();
                        }

                        // Mark sync as completed to prevent repeated prompts
                        if (currentUser) {
                            localStorage.setItem('dataSyncCompletedFor', String(currentUser.id));
                        }
                        console.log('✅ Data sync completed with choice:', choice);

                    } catch (error) {
                        console.error('Error applying data sync choice:', error);
                        // Still mark as completed to prevent infinite prompts
                        if (currentUser) {
                            localStorage.setItem('dataSyncCompletedFor', String(currentUser.id));
                        }
                    }

                    resolve();
                };
            });
        }

        // Save local data to server for new users
        async function saveLocalDataToServer(cards, spending, preferences, cardDetails) {
            try {
                // Save cards first
                for (const cardId of cards) {
                    const details = cardDetails[cardId] || {};
                    await fetch('/api/cards/user-cards/add/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCookie('csrftoken')
                        },
                        body: JSON.stringify({
                            card_id: cardId,
                            nickname: details.nickname || '',
                            opened_date: details.opened_date || null,
                            notes: details.notes || ''
                        })
                    });
                }

                // Save spending and preferences if they exist
                if (Object.keys(spending).length > 0 || Object.keys(preferences).length > 0) {
                    await fetch('/api/users/data/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCookie('csrftoken')
                        },
                        body: JSON.stringify({
                            spending: spending,
                            cards: cards,
                            preferences: preferences
                        })
                    });
                }

                console.log('✅ Local data saved to server');
            } catch (error) {
                console.error('Error saving local data to server:', error);
            }
        }

        // Local storage utilities for anonymous users
        class LocalStorage {
            static getSpending() {
                try {
                    return JSON.parse(localStorage.getItem('userSpending') || '{}');
                } catch {
                    return {};
                }
            }

            static setSpending(spending) {
                localStorage.setItem('userSpending', JSON.stringify(spending));
            }

            static getCards() {
                try {
                    return JSON.parse(localStorage.getItem('userCards') || '[]');
                } catch {
                    return [];
                }
            }

            static setCards(cards) {
                localStorage.setItem('userCards', JSON.stringify(cards));
            }

            static getPreferences() {
                try {
                    return JSON.parse(localStorage.getItem('userPreferences') || '{}');
                } catch {
                    return {};
                }
            }

            static setPreferences(preferences) {
                localStorage.setItem('userPreferences', JSON.stringify(preferences));
            }

            static getCardDetails() {
                try {
                    return JSON.parse(localStorage.getItem('userCardDetails') || '{}');
                } catch {
                    return {};
                }
            }

            static setCardDetails(cardId, details) {
                const cardDetails = this.getCardDetails();
                cardDetails[cardId] = details;
                localStorage.setItem('userCardDetails', JSON.stringify(cardDetails));
            }
        }

        // Phase K: household entities cache, invalidated on any mutation.
        // Auth-only feature — anon users always get [].
        let _householdEntitiesCache = null;

        // Unified data management (handles both authenticated and anonymous users)
        class UserDataManager {
            static async saveSpending(spending) {
                if (isAuthenticated) {
                    try {
                        const response = await fetch(`${API_BASE}/users/data/`, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': getCookie('csrftoken')
                            },
                            body: JSON.stringify({
                                spending: spending,
                                cards: await this.getCards(),
                                preferences: await this.getPreferences()
                            })
                        });
                        return response.ok;
                    } catch (error) {
                        console.error('Error saving spending:', error);
                        return false;
                    }
                } else {
                    LocalStorage.setSpending(spending);
                    return true;
                }
            }

            static async getSpending() {
                if (isAuthenticated) {
                    try {
                        const response = await fetch(`${API_BASE}/users/data/`);
                        const data = await response.json();
                        return data.spending || {};
                    } catch (error) {
                        console.error('Error loading spending:', error);
                        return {};
                    }
                } else {
                    return LocalStorage.getSpending();
                }
            }

            static async saveCards(cards) {
                if (isAuthenticated) {
                    try {
                        const response = await fetch(`${API_BASE}/users/data/`, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': getCookie('csrftoken')
                            },
                            body: JSON.stringify({
                                spending: await this.getSpending(),
                                cards: cards,
                                preferences: await this.getPreferences()
                            })
                        });
                        return response.ok;
                    } catch (error) {
                        console.error('Error saving cards:', error);
                        return false;
                    }
                } else {
                    LocalStorage.setCards(cards);
                    return true;
                }
            }

            static async getCards() {
                if (isAuthenticated) {
                    try {
                        const response = await fetch(`${API_BASE}/users/data/`);
                        const data = await response.json();
                        return data.cards || [];
                    } catch (error) {
                        console.error('Error loading cards:', error);
                        return [];
                    }
                } else {
                    return LocalStorage.getCards();
                }
            }

            static async getPreferences() {
                if (isAuthenticated) {
                    try {
                        const response = await fetch(`${API_BASE}/users/data/`);
                        const data = await response.json();
                        return data.preferences || {};
                    } catch (error) {
                        console.error('Error loading preferences:', error);
                        return {};
                    }
                } else {
                    return LocalStorage.getPreferences();
                }
            }

            // Which spending credits the user values — server-persisted for
            // both auth and anon (session-key) users, so no LocalStorage
            // branch is needed here.
            static async getCreditPreferences() {
                try {
                    const response = await fetch(`${API_BASE}/cards/credit-preferences/`);
                    const data = await response.json();
                    return data.preferences || {};
                } catch (error) {
                    console.error('Error loading credit preferences:', error);
                    return {};
                }
            }

            static async saveCreditPreferences(preferences) {
                try {
                    const response = await fetch(`${API_BASE}/cards/credit-preferences/`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCookie('csrftoken')
                        },
                        body: JSON.stringify({ preferences })
                    });
                    return response.ok;
                } catch (error) {
                    console.error('Error saving credit preferences:', error);
                    return false;
                }
            }

            static async getCreditUsages() {
                try {
                    const response = await fetch(`${API_BASE}/cards/credit-usage/`);
                    const data = await response.json();
                    return data.usages || {};
                } catch (error) {
                    console.error('Error loading credit usages:', error);
                    return {};
                }
            }

            static async saveCreditUsages(usages) {
                try {
                    const response = await fetch(`${API_BASE}/cards/credit-usage/`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCookie('csrftoken')
                        },
                        body: JSON.stringify({ usages })
                    });
                    return response.ok;
                } catch (error) {
                    console.error('Error saving credit usages:', error);
                    return false;
                }
            }


            // New methods for handling detailed user cards
            static async getUserCardsDetails() {
                if (isAuthenticated) {
                    try {
                        const response = await fetch(`${API_BASE}/cards/user-cards/`);
                        const data = await response.json();
                        // Active cards only — mirrors the retired
                        // users/cards/details/ endpoint's server-side filter.
                        return (data || []).filter(uc => !uc.closed_date);
                    } catch (error) {
                        console.error('Error fetching user cards details:', error);
                        return [];
                    }
                } else {
                    // For anonymous users, return simple card objects with IDs
                    const cardIds = LocalStorage.getCards();
                    const cardDetails = LocalStorage.getCardDetails();
                    return cardIds.map(id => ({
                        card: { id: id },
                        nickname: cardDetails[id]?.nickname || '',
                        opened_date: cardDetails[id]?.opened_date || null
                    }));
                }
            }

            static async addCardWithDetails(cardId, nickname, openedDate) {
                if (isAuthenticated) {
                    try {
                        const response = await fetch(`${API_BASE}/cards/user-cards/toggle/`, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': getCookie('csrftoken')
                            },
                            body: JSON.stringify({
                                card_id: cardId,
                                action: 'add',
                                nickname: nickname,
                                opened_date: openedDate || null
                            })
                        });
                        const data = await response.json();
                        return data.success;
                    } catch (error) {
                        console.error('Error adding card with details:', error);
                        return false;
                    }
                } else {
                    // For anonymous users, add to cards list and store details
                    const cards = await this.getCards();
                    cards.push(cardId);
                    await this.saveCards(cards);
                    LocalStorage.setCardDetails(cardId, { nickname, opened_date: openedDate || null });
                    return true;
                }
            }

            static async updateCardDetails(cardId, nickname, openedDate, bonusEarnedDate, bonusOverride, owner) {
                if (isAuthenticated) {
                    try {
                        // The surviving cards/ update endpoint is keyed by
                        // UserCard id, not CreditCard id — resolve it first.
                        // Phase K note: with multiple copies of the same
                        // card (different owners), this still resolves to
                        // the FIRST matching row — see openEditCardDetailsModal.
                        const userCards = await this.getUserCardsDetails();
                        const existing = userCards.find(uc => uc.card.id === cardId);
                        if (!existing) {
                            return false;
                        }
                        const body = {
                            nickname: nickname,
                            opened_date: openedDate || null,
                            bonus_earned_date: bonusEarnedDate || null,
                            bonus_override: bonusOverride
                        };
                        if (owner) {
                            body.owner = owner;
                        }
                        const response = await fetch(`${API_BASE}/cards/user-cards/${existing.id}/`, {
                            method: 'PATCH',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': getCookie('csrftoken')
                            },
                            body: JSON.stringify(body)
                        });
                        return response.ok;
                    } catch (error) {
                        console.error('Error updating card details:', error);
                        return false;
                    }
                } else {
                    // For anonymous users, store in localStorage
                    LocalStorage.setCardDetails(cardId, {
                        nickname, opened_date: openedDate || null,
                        bonus_earned_date: bonusEarnedDate || null,
                        bonus_override: bonusOverride
                    });
                    return true;
                }
            }

            static async getCardDetails(cardId) {
                if (isAuthenticated) {
                    const userCards = await this.getUserCardsDetails();
                    return userCards.find(uc => uc.card.id === cardId) || null;
                } else {
                    const cardDetails = LocalStorage.getCardDetails();
                    return cardDetails[cardId] || {
                        nickname: '', opened_date: null,
                        bonus_earned_date: null, bonus_override: null
                    };
                }
            }

            // Phase K: household entities (multi-player households). Auth-only —
            // anonymous users always get an empty list, matching the locked
            // scope (session/localStorage users stay single-player).
            static async getEntities(forceRefresh = false) {
                if (!isAuthenticated) {
                    return [];
                }
                if (_householdEntitiesCache && !forceRefresh) {
                    return _householdEntitiesCache;
                }
                try {
                    const response = await fetch(`${API_BASE}/cards/profile-entities/`);
                    if (!response.ok) {
                        return [];
                    }
                    _householdEntitiesCache = await response.json();
                    return _householdEntitiesCache;
                } catch (error) {
                    console.error('Error fetching household entities:', error);
                    return [];
                }
            }

            static async addEntity(name, kind) {
                try {
                    const response = await fetch(`${API_BASE}/cards/profile-entities/`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCookie('csrftoken')
                        },
                        body: JSON.stringify({ name, kind })
                    });
                    const data = await response.json();
                    if (!response.ok) {
                        return { success: false, error: data.error || 'Failed to add household member' };
                    }
                    _householdEntitiesCache = null;
                    return { success: true, entity: data };
                } catch (error) {
                    console.error('Error adding household entity:', error);
                    return { success: false, error: 'Network error' };
                }
            }

            static async renameEntity(entityId, name) {
                try {
                    const response = await fetch(`${API_BASE}/cards/profile-entities/${entityId}/`, {
                        method: 'PATCH',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCookie('csrftoken')
                        },
                        body: JSON.stringify({ name })
                    });
                    const data = await response.json();
                    if (!response.ok) {
                        return { success: false, error: data.error || 'Failed to rename' };
                    }
                    _householdEntitiesCache = null;
                    return { success: true };
                } catch (error) {
                    console.error('Error renaming household entity:', error);
                    return { success: false, error: 'Network error' };
                }
            }

            static async removeEntity(entityId) {
                try {
                    const response = await fetch(`${API_BASE}/cards/profile-entities/${entityId}/`, {
                        method: 'DELETE',
                        headers: { 'X-CSRFToken': getCookie('csrftoken') }
                    });
                    if (!response.ok) {
                        const data = await response.json().catch(() => ({}));
                        return { success: false, error: data.error || 'Failed to remove' };
                    }
                    _householdEntitiesCache = null;
                    return { success: true };
                } catch (error) {
                    console.error('Error removing household entity:', error);
                    return { success: false, error: 'Network error' };
                }
            }
        }

        async function toggleCardOwnership(cardId, button) {
            try {
                const hasCard = button.textContent.includes('I have this');
                const action = hasCard ? 'add' : 'remove';

                button.disabled = true;
                button.textContent = '...';

                // Update local data first
                const userCards = await UserDataManager.getCards();
                if (hasCard) {
                    if (!userCards.includes(cardId)) {
                        userCards.push(cardId);
                    }
                } else {
                    const index = userCards.indexOf(cardId);
                    if (index > -1) userCards.splice(index, 1);
                }
                await UserDataManager.saveCards(userCards);

                if (isAuthenticated) {
                    // Sync with authenticated API
                    try {
                        const response = await fetch(`${API_BASE}/cards/user-cards/toggle/`, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': getCookie('csrftoken')
                            },
                            body: JSON.stringify({
                                card_id: cardId,
                                action: action
                            })
                        });

                        const data = await response.json();

                        if (!data.success) {
                            // Revert local changes if API call failed
                            const revertCards = await UserDataManager.getCards();
                            if (hasCard) {
                                const index = revertCards.indexOf(cardId);
                                if (index > -1) revertCards.splice(index, 1);
                            } else {
                                if (!revertCards.includes(cardId)) {
                                    revertCards.push(cardId);
                                }
                            }
                            await UserDataManager.saveCards(revertCards);
                            alert('Error updating card ownership');
                            return;
                        }
                    } catch (apiError) {
                        console.error('API sync error:', apiError);
                        // Keep local changes even if API fails
                    }
                }

                updateButtonState(button, hasCard);

            } catch (error) {
                console.error('Error:', error);
                alert('Error updating card ownership');
            } finally {
                button.disabled = false;
            }
        }

        function updateButtonState(button, hasCard) {
            if (hasCard) {
                button.textContent = '❌ Remove from my cards';
                button.className = 'danger';
            } else {
                button.textContent = '✅ I have this card';
                button.className = 'success';
            }
        }

        // Card Detail Modal functionality
        let currentModalCard = null;

        async function openCardModal(cardId) {
            try {
                // Show loading modal first
                const modal = document.getElementById('cardModal');
                document.getElementById('modalCardName').textContent = 'Loading...';
                document.getElementById('modalCardIssuer').textContent = '';
                modal.style.display = 'block';

                // Fetch card details
                const response = await fetch(`${API_BASE}/cards/cards/${cardId}/`);
                if (!response.ok) {
                    throw new Error('Failed to fetch card details');
                }
                const card = await response.json();
                currentModalCard = card;

                // Populate modal with card data
                populateCardModal(card);

            } catch (error) {
                console.error('Error loading card details:', error);
                closeCardModal();
                alert('Error loading card details. Please try again.');
            }
        }

        async function populateCardModal(card) {
            // Check if user owns this card and has a nickname
            const userCards = await UserDataManager.getCards();
            const hasCard = userCards.includes(card.id);
            let displayName = card.name;

            if (hasCard) {
                const cardDetails = await UserDataManager.getCardDetails(card.id);
                if (cardDetails?.nickname) {
                    displayName = `${card.name} (${cardDetails.nickname})`;
                }
            }

            // Basic card info
            document.getElementById('modalCardName').textContent = displayName;
            document.getElementById('modalCardIssuer').textContent = card.issuer?.name || 'Unknown Issuer';
            document.getElementById('modalCardType').textContent = card.card_type ? card.card_type.charAt(0).toUpperCase() + card.card_type.slice(1) : 'Personal';
            document.getElementById('modalAnnualFee').textContent = `$${card.annual_fee || 0}`;
            document.getElementById('modalRewardType').textContent = card.primary_reward_type?.name || 'Unknown';

            // Point value
            let rewardMultiplier = card.metadata?.reward_value_multiplier || 0.01;
            if (rewardMultiplier >= 0.5) rewardMultiplier /= 100.0;
            document.getElementById('modalPointValue').textContent = `${(rewardMultiplier * 100).toFixed(1)}¢ each`;

            // Network (if available in metadata)
            const network = card.metadata?.network || 'Not specified';
            document.getElementById('modalNetwork').textContent = network;

            // Signup bonus
            const signupBonus = card.signup_bonus_amount;
            const signupBonusSection = document.getElementById('modalSignupBonusSection');
            const signupRequirement = document.getElementById('modalSignupRequirement');

            if (signupBonus && signupBonus > 0) {
                const bonusType = card.signup_bonus_type?.name || 'points';
                document.getElementById('modalSignupBonus').textContent =
                    `${signupBonus.toLocaleString()} ${bonusType}`;

                // Show spending requirement if available
                const spendingReq = card.metadata?.signup_spending_requirement;
                const timeLimit = card.metadata?.signup_time_limit_months || 3;
                if (spendingReq) {
                    document.getElementById('modalSignupSpending').textContent =
                        `$${spendingReq.toLocaleString()} in ${timeLimit} months`;
                    signupRequirement.style.display = 'block';
                } else {
                    signupRequirement.style.display = 'none';
                }
                signupBonusSection.style.display = 'block';
            } else {
                document.getElementById('modalSignupBonus').textContent = 'None';
                signupRequirement.style.display = 'none';
                signupBonusSection.style.display = 'block';
            }

            // User-specific card details
            await populateUserCardDetails(card.id);

            // Reward categories
            populateRewardCategories(card.reward_categories || []);

            // Credits/Benefits
            await populateCardCredits(card.credits || []);

            // Update ownership button
            updateModalOwnershipButton(card.id);
        }

        async function populateUserCardDetails(cardId) {
            try {
                const userCards = await UserDataManager.getCards();
                const hasCard = userCards.includes(cardId);
                const userDetailsSection = document.getElementById('modalUserDetailsSection');

                if (hasCard) {
                    const cardDetails = await UserDataManager.getCardDetails(cardId);

                    // Show nickname
                    const nicknameEl = document.getElementById('modalUserNickname');
                    nicknameEl.textContent = cardDetails?.nickname || 'None';

                    // Show opening date
                    const openingDateEl = document.getElementById('modalUserOpeningDate');
                    if (cardDetails?.opened_date) {
                        const date = new Date(cardDetails.opened_date);
                        openingDateEl.textContent = date.toLocaleDateString();
                    } else {
                        openingDateEl.textContent = 'Not set';
                    }

                    // Show bonus earned date
                    const bonusEarnedDateEl = document.getElementById('modalUserBonusEarnedDate');
                    if (cardDetails?.bonus_earned_date) {
                        const date = new Date(cardDetails.bonus_earned_date);
                        bonusEarnedDateEl.textContent = date.toLocaleDateString();
                    } else {
                        bonusEarnedDateEl.textContent = 'Not set';
                    }

                    // Show bonus override status
                    const bonusOverrideEl = document.getElementById('modalUserBonusOverride');
                    if (cardDetails?.bonus_override === true) {
                        bonusOverrideEl.textContent = 'Confirmed earned';
                    } else if (cardDetails?.bonus_override === false) {
                        bonusOverrideEl.textContent = 'Confirmed not earned';
                    } else {
                        bonusOverrideEl.textContent = 'Auto (inferred from issuer rules)';
                    }

                    // Show owner name (multi-player households)
                    const ownerItem = document.getElementById('modalUserOwnerItem');
                    const ownerEl = document.getElementById('modalUserOwner');
                    if (cardDetails?.owner_name) {
                        ownerEl.textContent = cardDetails.owner_name;
                        ownerItem.style.display = 'block';
                    } else {
                        ownerItem.style.display = 'none';
                    }

                    userDetailsSection.style.display = 'block';
                } else {
                    userDetailsSection.style.display = 'none';
                }
            } catch (error) {
                console.error('Error loading user card details:', error);
                document.getElementById('modalUserDetailsSection').style.display = 'none';
            }
        }

        function populateRewardCategories(rewardCategories) {
            const rewardsList = document.getElementById('modalRewardsList');
            const rewardsSection = document.getElementById('modalRewardsSection');

            if (!rewardCategories || rewardCategories.length === 0) {
                rewardsList.innerHTML = '<li style="text-align: center; color: #6b7280; padding: 20px;">No specific reward categories</li>';
                rewardsSection.style.display = 'block';
                return;
            }

            const activeRewards = rewardCategories.filter(cat => cat.is_active);

            if (activeRewards.length === 0) {
                rewardsList.innerHTML = '<li style="text-align: center; color: #6b7280; padding: 20px;">No active reward categories</li>';
                rewardsSection.style.display = 'block';
                return;
            }

            const rewardsHtml = activeRewards.map(reward => {
                const categoryName = reward.category?.display_name || reward.category?.name || 'Unknown Category';
                const rate = parseFloat(reward.reward_rate || 0);
                const maxSpend = reward.max_annual_spend;

                let limitHtml = '';
                if (maxSpend) {
                    limitHtml = `<div class="modal-rewards-limit">Up to $${parseInt(maxSpend).toLocaleString()}/year</div>`;
                }

                return `
                    <li class="modal-rewards-item">
                        <div>
                            <div class="modal-rewards-category">${categoryName}</div>
                            ${limitHtml}
                        </div>
                        <div class="modal-rewards-rate">${rate}x</div>
                    </li>
                `;
            }).join('');

            rewardsList.innerHTML = rewardsHtml;
            rewardsSection.style.display = 'block';
        }

        function getCurrentPeriodLabel(timesPerYear) {
            const now = new Date();
            const year = now.getFullYear();
            const p = parseInt(timesPerYear || 1);
            if (p === 12) {
                const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
                return `${monthNames[now.getMonth()]} ${year}`;
            } else if (p === 4) {
                const quarter = Math.floor(now.getMonth() / 3) + 1;
                return `Q${quarter} ${year}`;
            } else if (p === 2) {
                const half = now.getMonth() < 6 ? "H1" : "H2";
                return `${half} ${year}`;
            } else {
                return `${year}`;
            }
        }

        function getPeriodKeyJS(timesPerYear) {
            const now = new Date();
            const year = now.getFullYear();
            const p = parseInt(timesPerYear || 1);
            if (p === 12) {
                return `${year}-${String(now.getMonth() + 1).padStart(2, '0')}`;
            } else if (p === 4) {
                const quarter = Math.floor(now.getMonth() / 3) + 1;
                return `${year}-Q${quarter}`;
            } else if (p === 2) {
                const half = now.getMonth() < 6 ? 1 : 2;
                return `${year}-H${half}`;
            } else {
                return `${year}`;
            }
        }

        // Formats a per-occurrence credit value with its frequency and the
        // resulting annual total, e.g. "$7/mo = $84/yr" instead of just "$7".
        function _formatCreditValue(value, timesPerYear, currency) {
            const v = parseFloat(value || 0);
            if (v <= 0) return 'Included';

            const isUSD = !currency || currency === 'USD';
            const fmt = (n) => isUSD ? `$${n.toLocaleString(undefined, {maximumFractionDigits: 0})}` : `${n.toLocaleString(undefined, {maximumFractionDigits: 0})} ${currency}`;

            const perYear = timesPerYear || 1;
            if (perYear <= 1) {
                return `${fmt(v)}/yr`;
            }
            const annual = v * perYear;
            const freqLabel = perYear === 12 ? '/mo' : perYear === 4 ? '/qtr' : perYear === 52 ? '/wk' : ` × ${perYear}/yr`;
            return `${fmt(v)}${freqLabel} = ${fmt(annual)}/yr`;
        }

        const OFFER_TYPE_LABELS = {
            statement_credit: 'Statement credit',
            discount: 'Discount',
            points_miles: 'Points / miles',
            membership: 'Membership',
            companion_pass: 'Companion pass',
            other: 'Other',
        };

        function _offerTypeBadge(offerType) {
            const label = OFFER_TYPE_LABELS[offerType];
            if (!label) return '';
            return `<span class="modal-credit-offer-type" style="font-size: 0.75em; color: var(--muted-2); border: 1px solid var(--border); border-radius: 4px; padding: 1px 6px; margin-left: 6px;">${label}</span>`;
        }

        async function populateCardCredits(credits) {
            const creditsList = document.getElementById('modalCreditsList');
            const creditsSection = document.getElementById('modalCreditsSection');

            if (!credits || credits.length === 0) {
                creditsList.innerHTML = '<div style="text-align: center; color: #6b7280; padding: 20px;">No special benefits or credits listed for this card</div>';
                creditsSection.style.display = 'block';
                return;
            }

            const activeCredits = credits.filter(credit => credit.is_active);

            if (activeCredits.length === 0) {
                creditsList.innerHTML = '<div style="text-align: center; color: #6b7280; padding: 20px;">No active benefits or credits</div>';
                creditsSection.style.display = 'block';
                return;
            }

            // Same server-persisted opt-in preferences the profile page and
            // the recommendation engine read — a credit only counts toward
            // value if the user has checked it here or on /profile/.
            const preferences = await UserDataManager.getCreditPreferences();
            const userCards = await UserDataManager.getCards();
            const isOwned = currentModalCard ? userCards.includes(currentModalCard.id) : false;
            const usages = isOwned ? await UserDataManager.getCreditUsages() : {};

            const creditsHtml = activeCredits.map(credit => {
                const value = parseFloat(credit.value || 0);
                const currency = credit.currency || 'USD';
                const valueDisplay = _formatCreditValue(value, credit.times_per_year, currency);

                // Get proper display name and description from spending_credit or category
                let creditName = 'Benefit';
                let creditDescription = credit.description || '';
                const slug = credit.spending_credit?.slug;

                if (credit.spending_credit) {
                    // For spending credits (like airport_lounge, precheck, etc.)
                    creditName = credit.spending_credit.display_name;
                    creditDescription = credit.spending_credit.description || creditDescription;
                } else if (credit.category) {
                    // For category-based credits (like travel, dining, etc.)
                    creditName = credit.category.display_name;
                    creditDescription = credit.category.description || creditDescription;
                }

                // Only spending-credit-backed benefits are individually
                // toggle-able (matches profile.html) — category credits are
                // counted automatically by the engine whenever the user has
                // matching spending, so there's nothing to opt in/out of.
                const offerTypeBadge = _offerTypeBadge(credit.offer_type);

                if (!slug) {
                    return `
                        <div class="modal-credit-item">
                            <div class="modal-credit-content">
                                <div class="modal-credit-name">${creditName}${offerTypeBadge}</div>
                                ${creditDescription ? `<div class="modal-credit-description">${creditDescription}</div>` : ''}
                                <div class="modal-credit-note">Counted automatically based on your spending</div>
                            </div>
                            <div class="modal-credit-value">${valueDisplay}</div>
                        </div>
                    `;
                }

                const isUsed = preferences[slug] === true;
                const isUsedThisPeriod = usages[credit.id] === true;

                let usageTrackingHtml = '';
                if (isUsed && isOwned) {
                    const periodLabel = getCurrentPeriodLabel(credit.times_per_year);
                    usageTrackingHtml = `
                        <div class="modal-credit-usage-row" style="margin-top: 6px; display: flex; align-items: center; gap: 6px; font-size: 12px;">
                            <input type="checkbox" id="modalCreditPeriodUse_${credit.id}" ${isUsedThisPeriod ? 'checked' : ''}
                                   onchange="toggleModalCreditUsagePeriod(${credit.id}, this.checked)"
                                   style="cursor: pointer;">
                            <label for="modalCreditPeriodUse_${credit.id}" style="cursor: pointer; color: var(--muted); margin: 0; font-weight: normal;">
                                Used this period (${periodLabel})
                            </label>
                        </div>
                    `;
                }

                return `
                    <div class="modal-credit-item${isUsed ? '' : ' modal-credit-unused'}">
                        <div class="modal-credit-checkbox">
                            <input type="checkbox" id="modalCreditUse_${slug}" ${isUsed ? 'checked' : ''}
                                   onchange="toggleModalCreditUsage('${slug}', this.checked)"
                                   title="I use this benefit">
                        </div>
                        <div class="modal-credit-content">
                            <label for="modalCreditUse_${slug}" style="cursor:pointer;">
                                <div class="modal-credit-name">${creditName}${offerTypeBadge}</div>
                            </label>
                            ${creditDescription ? `<div class="modal-credit-description">${creditDescription}</div>` : ''}
                            ${!isUsed ? '<div class="modal-credit-note">Not counted — you said you don\'t use this</div>' : ''}
                            ${usageTrackingHtml}
                        </div>
                        <div class="modal-credit-value">${isUsed ? valueDisplay : '$0'}</div>
                    </div>
                `;
            }).join('');

            creditsList.innerHTML = `<div class="modal-credits-list">${creditsHtml}</div>`;
            creditsSection.style.display = 'block';
        }

        async function toggleModalCreditUsage(slug, checked) {
            try {
                await UserDataManager.saveCreditPreferences({ [slug]: checked });
                if (currentModalCard) {
                    await populateCardCredits(currentModalCard.credits || []);
                }
            } catch (error) {
                console.error('Error updating credit preference:', error);
            }
        }

        async function toggleModalCreditUsagePeriod(creditId, checked) {
            try {
                await UserDataManager.saveCreditUsages({ [creditId]: checked });
                if (currentModalCard) {
                    await populateCardCredits(currentModalCard.credits || []);
                }
                if (typeof loadCreditsProfile === 'function') {
                    await loadCreditsProfile();
                }
            } catch (error) {
                console.error('Error updating credit usage period:', error);
            }
        }


        async function updateModalOwnershipButton(cardId) {
            try {
                const userCards = await UserDataManager.getCards();
                const hasCard = userCards.includes(cardId);
                const ownershipButton = document.getElementById('modalOwnershipButton');
                const addAnotherButton = document.getElementById('modalAddAnotherButton');

                if (hasCard) {
                    ownershipButton.textContent = '❌ Remove from my cards';
                    ownershipButton.className = 'danger';
                    ownershipButton.onclick = removeLastCardModal;
                    addAnotherButton.style.display = 'inline-block';
                } else {
                    ownershipButton.textContent = '✅ I have this card';
                    ownershipButton.className = 'success';
                    ownershipButton.onclick = toggleCardOwnershipModal;
                    addAnotherButton.style.display = 'none';
                }
            } catch (error) {
                console.error('Error checking card ownership:', error);
            }
        }

        function refreshPageDisplay() {
            if (typeof filterCards === 'function') {
                filterCards();
            } else if (typeof displayCards === 'function' && typeof allCards !== 'undefined') {
                displayCards(allCards);
            } else if (typeof loadRoadmap === 'function') {
                loadRoadmap();
            } else if (typeof loadProfileData === 'function') {
                loadProfileData();
            }
        }

        async function addAnotherCardModal() {
            if (!currentModalCard) return;
            const cardId = currentModalCard.id;
            const cardType = currentModalCard.card_type;

            try {
                // Close detail modal
                closeCardModal();

                // Open ownership modal for adding another instance
                if (typeof window.openCardOwnershipModal === 'function') {
                    window.openCardOwnershipModal(cardId, null, cardType);
                } else {
                    console.error('window.openCardOwnershipModal is not defined');
                }
            } catch (error) {
                console.error('Error adding another card:', error);
            }
        }

        async function removeLastCardModal() {
            if (!currentModalCard) return;

            const button = document.getElementById('modalOwnershipButton');
            const cardId = currentModalCard.id;

            try {
                const userCards = await UserDataManager.getCards();
                const index = userCards.indexOf(cardId);
                if (index > -1) userCards.splice(index, 1);

                button.disabled = true;
                button.textContent = '...';

                await UserDataManager.saveCards(userCards);
                await updateModalOwnershipButton(cardId);

                // Refresh displays
                refreshPageDisplay();

            } catch (error) {
                console.error('Error removing card:', error);
                alert('Error removing card');
            } finally {
                button.disabled = false;
            }
        }

        async function toggleCardOwnershipModal() {
            if (!currentModalCard) return;

            const button = document.getElementById('modalOwnershipButton');
            const cardId = currentModalCard.id;
            const cardType = currentModalCard.card_type;

            try {
                const userCards = await UserDataManager.getCards();
                const hasCard = userCards.includes(cardId);

                if (hasCard) {
                    await removeLastCardModal();
                } else {
                    closeCardModal();
                    if (typeof window.openCardOwnershipModal === 'function') {
                        window.openCardOwnershipModal(cardId, null, cardType);
                    } else {
                        // Fallback simple add if the ownership modal is not loaded on this page
                        button.disabled = true;
                        button.textContent = '...';
                        const success = await UserDataManager.addCardWithDetails(cardId, '', null);
                        if (success) {
                            alert('Card added to your collection!');
                            refreshPageDisplay();
                        } else {
                            alert('Error adding card. Please try again.');
                        }
                    }
                }
            } catch (error) {
                console.error('Error updating card ownership:', error);
                alert('Error updating card ownership');
            } finally {
                button.disabled = false;
            }
        }

        function closeCardModal() {
            document.getElementById('cardModal').style.display = 'none';
            currentModalCard = null;
        }

        async function openEditCardDetailsModal() {
            if (!currentModalCard) return;
            const cardId = currentModalCard.id;
            const cardType = currentModalCard.card_type;
            const existingUserCard = await UserDataManager.getCardDetails(cardId);
            const isOwned = (existingUserCard && existingUserCard.id) ? existingUserCard : null;
            closeCardModal();
            openCardOwnershipModal(cardId, isOwned, cardType);
        }

        // Card Ownership Modal Functions
        async function openCardOwnershipModal(cardId, existingUserCard = null, cardType = 'personal') {
            const modal = document.getElementById('cardOwnershipModal');
            if (!modal) return;

            const form = document.getElementById('cardOwnershipForm');
            const modalTitle = document.getElementById('modalTitle');

            const hasExistingId = Boolean(existingUserCard && existingUserCard.id);

            // Set modal title and add auth status indicator
            if (isAuthenticated) {
                modalTitle.textContent = hasExistingId ? 'Edit Card Details' : 'Add Card to Collection';
            } else {
                modalTitle.innerHTML = hasExistingId ?
                    'Edit Card Details <span style="background: #5C6675; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: 500; margin-left: 8px;">Local Mode</span>' :
                    'Add Card to Collection <span style="background: #5C6675; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: 500; margin-left: 8px;">Local Mode</span>';
            }

            // Store card ID in form
            form.dataset.cardId = cardId;
            form.dataset.userCardId = hasExistingId ? existingUserCard.id : '';

            // Pre-fill form if editing existing card
            if (hasExistingId) {
                form.nickname.value = existingUserCard.nickname || '';
                form.opened_date.value = existingUserCard.opened_date || '';
                form.closed_date.value = existingUserCard.closed_date || '';
                if (form.bonus_earned_date) form.bonus_earned_date.value = existingUserCard.bonus_earned_date || '';
                if (form.bonus_override) {
                    form.bonus_override.value =
                        existingUserCard.bonus_override === true ? 'true' :
                        existingUserCard.bonus_override === false ? 'false' : '';
                }
                form.notes.value = existingUserCard.notes || '';
            } else {
                form.reset();
            }

            // Phase K: owner selector — shown when authed and there are > 1 entities of matching kind (personal vs. business)
            const ownerGroup = document.getElementById('cardOwnershipOwnerGroup');
            const ownerSelect = document.getElementById('ownershipOwner');
            const entities = await UserDataManager.getEntities();
            
            let resolvedCardType = cardType;
            let cardObj = (typeof allCards !== 'undefined' && Array.isArray(allCards) ? allCards.find(c => c.id === parseInt(cardId)) : null) || existingUserCard?.card;
            if (cardObj && cardObj.card_type) {
                resolvedCardType = cardObj.card_type;
            } else if (isAuthenticated && (!cardObj || !cardObj.card_type)) {
                try {
                    const res = await fetch(`${API_BASE}/cards/cards/${cardId}/`);
                    if (res.ok) {
                        const fetchedCard = await res.json();
                        if (fetchedCard && fetchedCard.card_type) {
                            resolvedCardType = fetchedCard.card_type;
                        }
                    }
                } catch (e) {
                    console.error('Error fetching card details for card type:', e);
                }
            }

            const isBusinessCard = resolvedCardType === 'business';
            const candidates = entities.filter(e => (e.kind === 'business') === isBusinessCard);

            if (isAuthenticated && candidates.length > 1) {
                ownerSelect.innerHTML = candidates.map(e =>
                    `<option value="${e.id}">${escapeHtml(e.name)}${e.is_primary ? ' (Primary)' : ''}</option>`
                ).join('');
                const defaultId = candidates.find(e => e.is_primary)?.id || candidates[0].id;
                const currentOwnerId = existingUserCard?.owner?.id || existingUserCard?.owner;
                ownerSelect.value = currentOwnerId ?? defaultId;
                ownerGroup.style.display = 'block';
            } else {
                ownerGroup.style.display = 'none';
            }

            // Show/hide local storage notice
            const localNotice = document.getElementById('localStorageNotice');
            if (localNotice) {
                localNotice.style.display = isAuthenticated ? 'none' : 'block';
            }

            modal.classList.add('show');
            document.body.style.overflow = 'hidden';
        }

        function closeCardOwnershipModal() {
            const modal = document.getElementById('cardOwnershipModal');
            if (modal) {
                modal.classList.remove('show');
            }
            document.body.style.overflow = '';
        }

        async function saveCardOwnership(event) {
            event.preventDefault();

            const form = event.target;
            const cardId = form.dataset.cardId;
            const userCardId = form.dataset.userCardId;
            const submitBtn = form.querySelector('button[type="submit"]');

            const ownerGroupVisible = document.getElementById('cardOwnershipOwnerGroup').style.display !== 'none';
            const bonusOverrideRaw = form.bonus_override ? form.bonus_override.value : '';
            const bonusOverride = bonusOverrideRaw === '' ? null : bonusOverrideRaw === 'true';

            const formData = {
                card_id: parseInt(cardId),
                nickname: form.nickname.value,
                opened_date: form.opened_date.value || null,
                closed_date: form.closed_date.value || null,
                bonus_earned_date: form.bonus_earned_date ? (form.bonus_earned_date.value || null) : null,
                bonus_override: bonusOverride,
                notes: form.notes.value
            };
            if (ownerGroupVisible) {
                formData.owner = form.owner.value;
            }

            try {
                submitBtn.disabled = true;
                submitBtn.textContent = 'Saving...';

                let success = false;

                if (isAuthenticated) {
                    let response;
                    if (userCardId) {
                        response = await fetch(`${API_BASE}/cards/user-cards/${userCardId}/`, {
                            method: 'PATCH',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': getCookie('csrftoken')
                            },
                            body: JSON.stringify(formData)
                        });
                    } else {
                        response = await fetch(`${API_BASE}/cards/user-cards/add/`, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': getCookie('csrftoken')
                            },
                            body: JSON.stringify(formData)
                        });
                    }

                    if (response.ok) {
                        success = true;
                    } else {
                        const errorData = await response.json();
                        console.error('API Error:', errorData);
                        showNotification(errorData.error || 'Failed to save card details', 'error');
                    }
                } else {
                    // Local storage mode
                    const cards = await UserDataManager.getCards();
                    if (!cards.includes(parseInt(cardId))) {
                        cards.push(parseInt(cardId));
                        await UserDataManager.saveCards(cards);
                    }

                    LocalStorage.setCardDetails(parseInt(cardId), {
                        nickname: formData.nickname,
                        opened_date: formData.opened_date,
                        closed_date: formData.closed_date,
                        bonus_earned_date: formData.bonus_earned_date,
                        bonus_override: formData.bonus_override,
                        notes: formData.notes,
                        owner: formData.owner || null
                    });

                    success = true;
                }

                if (success) {
                    closeCardOwnershipModal();
                    showNotification(userCardId ? 'Card details updated!' : 'Card added to your collection!', 'success');
                    refreshPageDisplay();
                }
            } catch (error) {
                console.error('Error saving card ownership:', error);
                showNotification('An error occurred while saving', 'error');
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = userCardId ? 'Save Details' : 'Add Card';
            }
        }

        window.openCardOwnershipModal = openCardOwnershipModal;
        window.closeCardOwnershipModal = closeCardOwnershipModal;
        window.saveCardOwnership = saveCardOwnership;

        // Close modal when clicking outside of it
        window.onclick = function(event) {
            const cardModal = document.getElementById('cardModal');
            const editModal = document.getElementById('editCardDetailsModal');
            const ownershipModal = document.getElementById('cardOwnershipModal');

            if (event.target === cardModal) {
                closeCardModal();
            } else if (event.target === editModal) {
                closeEditCardDetailsModal();
            } else if (event.target === ownershipModal) {
                if (typeof closeCardOwnershipModal === 'function') closeCardOwnershipModal();
            }
        };

        // Close modal with Escape key
        document.addEventListener('keydown', function(event) {
            if (event.key === 'Escape') {
                const editModal = document.getElementById('editCardDetailsModal');
                const cardModal = document.getElementById('cardModal');
                const ownershipModal = document.getElementById('cardOwnershipModal');

                if (editModal && editModal.style.display === 'block') {
                    closeEditCardDetailsModal();
                } else if (cardModal && cardModal.style.display === 'block') {
                    closeCardModal();
                } else if (ownershipModal && (ownershipModal.classList.contains('show') || ownershipModal.style.display === 'block')) {
                    if (typeof closeCardOwnershipModal === 'function') closeCardOwnershipModal();
                }
            }
        });

        // Manual functions for immediate state changes
        window.handleLogout = function() {
            console.log('Manual logout triggered');
            clearUserData();
            isAuthenticated = false;
            currentUser = null;

            // Refresh current page data immediately
            if (typeof loadUserCards === 'function') {
                loadUserCards();
            }
            if (typeof filterCategories === 'function') {
                filterCategories();
            }
            if (typeof filterCards === 'function') {
                filterCards();
            }

            // Also check again after a short delay to catch any async logout
            setTimeout(async () => {
                console.log('Checking logout state after delay');
                await initUserState();
            }, 1000);
        };

        window.handleLogin = async function() {
            console.log('Manual login triggered');
            await initUserState();
        };

        // Mobile menu toggle
        window.toggleMobileMenu = function() {
            const drawer = document.getElementById('mobileMenuDrawer');
            drawer.classList.toggle('open');
        };

        // Close mobile menu when clicking a link or outside
        document.addEventListener('DOMContentLoaded', function() {
            const menuItems = document.querySelectorAll('.mobile-menu-item');
            const drawer = document.getElementById('mobileMenuDrawer');
            const menuToggle = document.querySelector('.mobile-menu-toggle');

            menuItems.forEach(item => {
                item.addEventListener('click', function() {
                    drawer.classList.remove('open');
                });
            });

            // Close menu when clicking outside
            document.addEventListener('click', function(event) {
                if (!drawer.contains(event.target) && !menuToggle.contains(event.target)) {
                    drawer.classList.remove('open');
                }
            });
        });

        // Test function to manually trigger logout
        window.testLogout = function() {
            console.log('🧪 Testing logout manually');
            handleLogout();
        };

        // Test function to check localStorage state
        window.testLocalStorage = function() {
            console.log('🧪 Current localStorage state:');
            console.log('userCards:', localStorage.getItem('userCards'));
            console.log('userSpending:', localStorage.getItem('userSpending'));
            console.log('userPreferences:', localStorage.getItem('userPreferences'));
            console.log('userCardDetails:', localStorage.getItem('userCardDetails'));
            console.log('isAuthenticated:', isAuthenticated);
            console.log('currentUser:', currentUser);
        };

        // Initialize user state when page loads
        document.addEventListener('DOMContentLoaded', function() {
            initUserState();

            // Check for user state changes periodically
            setInterval(async () => {
                await initUserState();
            }, 30000); // Check every 30 seconds
        });
