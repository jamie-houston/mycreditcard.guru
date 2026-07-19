// Section-collapse handler roadmap-results.js expects on the page —
// normally defined in index.html; this page just needs the bare minimum.
function toggleSection(sectionKey) {
    const content = document.getElementById(`content-${sectionKey}`);
    const toggle = document.getElementById(`toggle-${sectionKey}`);
    if (!content || !toggle) return;
    if (content.style.display === 'none') {
        content.style.display = 'block';
        toggle.style.transform = 'rotate(0deg)';
    } else {
        content.style.display = 'none';
        toggle.style.transform = 'rotate(-90deg)';
    }
}

document.addEventListener('DOMContentLoaded', loadSharedRoadmap);

async function loadSharedRoadmap() {
    const shareUuid = window.shareUuid;
    const container = document.getElementById('results');
    try {
        const response = await fetch(`${API_BASE}/roadmaps/shared/${shareUuid}/`);
        if (!response.ok) {
            throw new Error(`Failed to fetch roadmap: ${response.status}`);
        }
        const data = await response.json();

        const generatedAt = data.generated_at ? new Date(data.generated_at) : null;
        renderRoadmapResults(data, {
            container,
            readOnly: true,
            banner: generatedAt ? `Generated on ${generatedAt.toLocaleDateString()}` : '',
            noScroll: true,
        });
    } catch (error) {
        console.error('Error loading shared roadmap:', error);
        container.innerHTML = `
            <div class="error" style="text-align:center; padding: 40px; color: var(--muted);">
                This roadmap is no longer public, or doesn't exist.
            </div>
        `;
    }
}
