let activePillarFilter = 'All';
let currentPage = 1;
const ROWS_PER_PAGE = 25;

const findingsData = (typeof REPORT_DATA !== 'undefined' && REPORT_DATA.findings) ? REPORT_DATA.findings : [];
const pillarsData = (typeof REPORT_DATA !== 'undefined' && REPORT_DATA.pillars) ? REPORT_DATA.pillars : [];

const reportMeta = {
    accountId: (typeof REPORT_DATA !== 'undefined' && REPORT_DATA.accountId) ? REPORT_DATA.accountId : 'unknown',
    region: (typeof REPORT_DATA !== 'undefined' && REPORT_DATA.region) ? REPORT_DATA.region : 'unknown',
    generatedAt: (typeof REPORT_DATA !== 'undefined' && REPORT_DATA.generatedAt) ? REPORT_DATA.generatedAt : '',
    reportId: (typeof REPORT_DATA !== 'undefined' && REPORT_DATA.reportId) ? REPORT_DATA.reportId : 'IR-UNKNOWN',
    appVersion: (typeof REPORT_DATA !== 'undefined' && REPORT_DATA.appVersion) ? REPORT_DATA.appVersion : '0.0.0',
    scanDuration: (typeof REPORT_DATA !== 'undefined' && REPORT_DATA.scanDuration) ? REPORT_DATA.scanDuration : 'N/A',
    overallScore: (typeof REPORT_DATA !== 'undefined' && REPORT_DATA.overallScore) ? REPORT_DATA.overallScore : 0,
    monthlySavings: (typeof REPORT_DATA !== 'undefined' && REPORT_DATA.monthlySavings) ? REPORT_DATA.monthlySavings : 0,
};

const SEVERITY_CONFIG = {
    Critical: { color: '#dc4f4f', label: 'Critical' },
    High: { color: '#d97706', label: 'High' },
    Medium: { color: '#ca8a04', label: 'Medium' },
    Low: { color: '#2563eb', label: 'Low' },
};

document.addEventListener('DOMContentLoaded', () => {
    try {
        const activeTheme =
            document.documentElement.getAttribute('data-theme') ||
            localStorage.getItem('theme') ||
            'dark';

        document.documentElement.setAttribute('data-theme', activeTheme);
        updateThemeIcons(activeTheme);

        animateValue('overall-score-text', 0, reportMeta.overallScore, 1200);
        animateValue('total-savings-text', 0, reportMeta.monthlySavings, 1500, true);

        initProgressRing(reportMeta.overallScore);

        setTimeout(() => {
            document.querySelectorAll('[data-width]').forEach((bar) => {
                bar.style.width = bar.getAttribute('data-width') || '0%';
            });
        }, 450);

        document.querySelectorAll('#pillar-grid > article').forEach((card, i) => {
            card.style.opacity = '0';
            setTimeout(() => {
                card.style.opacity = '1';
                card.classList.add('animate-fade-in');
            }, i * 70);
        });

        renderFindings();
        updateBadge();
        syncPrintMetaFields();
    } catch (e) {
        console.error('Error during report initialization:', e);
    }
});

function syncPrintMetaFields() {
    setText('print-report-id-value', reportMeta.reportId);
    setText('print-scan-duration', reportMeta.scanDuration || 'N/A');
    setText('print-app-version', reportMeta.appVersion || '0.0.0');
}

function initProgressRing(score) {
    const ring = document.getElementById('overall-ring');
    if (!ring) return;

    const radius = ring.r.baseVal.value;
    const circumference = 2 * Math.PI * radius;

    ring.style.strokeDasharray = `${circumference} ${circumference}`;
    ring.style.strokeDashoffset = `${circumference}`;

    let strokeColor = '#dc4f4f';
    if (score >= 75) strokeColor = '#2f9e8f';
    else if (score >= 50) strokeColor = '#d97706';

    ring.style.stroke = strokeColor;

    setTimeout(() => {
        const offset = circumference - (score / 100) * circumference;
        ring.style.strokeDashoffset = `${offset}`;
    }, 350);
}

function toggleScoringGuide() {
    const panel = document.getElementById('score-guide-panel');
    const chevron = document.getElementById('score-guide-chevron');
    const toggle = document.getElementById('score-guide-toggle');
    if (!panel || !toggle || !chevron) return;

    const open = panel.classList.toggle('is-open');
    chevron.classList.toggle('is-open', open);
    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    panel.setAttribute('aria-hidden', open ? 'false' : 'true');
}

function ensureScoringGuideOpen() {
    const panel = document.getElementById('score-guide-panel');
    const chevron = document.getElementById('score-guide-chevron');
    const toggle = document.getElementById('score-guide-toggle');
    if (!panel || !toggle || !chevron) return;

    panel.classList.add('is-open');
    chevron.classList.add('is-open');
    toggle.setAttribute('aria-expanded', 'true');
    panel.setAttribute('aria-hidden', 'false');
}

function exportEngineeringReport() {
    ensureScoringGuideOpen();
    setExportStatus('Opening print dialog. Save as PDF to download the engineering report.');
    window.print();
}

function filterByPillar(pillar, btn) {
    activePillarFilter = pillar;
    currentPage = 1;

    document.querySelectorAll('.filter-pill').forEach((button) => {
        button.classList.remove('active');
    });

    if (btn) btn.classList.add('active');
    renderFindings();
}

function filterFindings() {
    currentPage = 1;
    renderFindings();
}

function getFilteredFindings() {
    const severityFilter = document.getElementById('severity-filter')?.value || 'All';
    const searchTerm = (document.getElementById('finding-search')?.value || '').trim().toLowerCase();

    return findingsData.filter((f) => {
        const matchesPillar = activePillarFilter === 'All' || f.pillar === activePillarFilter;
        const matchesSeverity = severityFilter === 'All' || f.severity === severityFilter;

        const plainDescription = stripTags(f.description || '').toLowerCase();
        const matchesSearch = !searchTerm
            || String(f.resource_id || '').toLowerCase().includes(searchTerm)
            || String(f.title || '').toLowerCase().includes(searchTerm)
            || plainDescription.includes(searchTerm);

        return matchesPillar && matchesSeverity && matchesSearch;
    });
}

function renderFindings() {
    const filtered = getFilteredFindings();
    const tbody = document.getElementById('findings-tbody');
    const emptyState = document.getElementById('empty-state');
    const table = document.getElementById('findings-table');

    if (!tbody || !table) return;

    if (filtered.length === 0) {
        tbody.innerHTML = '';
        emptyState?.classList.remove('hidden');
        table.classList.add('hidden');
        updateBadge(0);
        renderPagination(0);
        return;
    }

    emptyState?.classList.add('hidden');
    table.classList.remove('hidden');

    const totalPages = Math.ceil(filtered.length / ROWS_PER_PAGE);
    currentPage = Math.min(Math.max(currentPage, 1), totalPages);

    const start = (currentPage - 1) * ROWS_PER_PAGE;
    const pageItems = filtered.slice(start, start + ROWS_PER_PAGE);

    tbody.innerHTML = pageItems.map(buildRow).join('');

    updateBadge(filtered.length);
    renderPagination(filtered.length);
}

function buildRow(f) {
    const severity = SEVERITY_CONFIG[f.severity] || SEVERITY_CONFIG.Low;
    const pillarSlug = f.pillar_slug || (f.pillar ? f.pillar.toLowerCase().split(' ')[0] : 'other');
    const plainDescription = truncate(stripTags(f.description || ''), 140);
    const safeId = JSON.stringify(f.finding_id || '');

    return `
    <tr class="finding-row" data-pillar="${escapeHtml(f.pillar || '')}" data-severity="${escapeHtml(f.severity || '')}" onclick='openDrawer(${safeId})'>
        <td class="findings-table-td">
            <span class="finding-resource mono">${escapeHtml(f.resource_id || '-')}</span>
            <span class="finding-region">${escapeHtml(f.region || '')}</span>
        </td>
        <td class="findings-table-td">
            <span class="badge badge-pillar" data-pillar="${escapeHtml(pillarSlug)}">${escapeHtml(f.pillar || '-')}</span>
        </td>
        <td class="findings-table-td">
            <span class="finding-title">${escapeHtml(f.title || '-')}</span>
            <span class="finding-desc">${escapeHtml(plainDescription)}</span>
        </td>
        <td class="findings-table-td">
            <span class="badge badge-${escapeHtml((f.severity || 'Low').toLowerCase())}">${escapeHtml(severity.label)}</span>
        </td>
        <td class="findings-table-td table-actions">
            <button class="btn-ghost btn-ghost--small" onclick='event.stopPropagation(); openDrawer(${safeId});' type="button">View</button>
        </td>
    </tr>`;
}

function renderPagination(totalCount) {
    const container = document.getElementById('pagination');
    if (!container) return;

    const totalPages = Math.ceil(totalCount / ROWS_PER_PAGE);
    if (totalPages <= 1) {
        container.innerHTML = '';
        return;
    }

    const start = (currentPage - 1) * ROWS_PER_PAGE + 1;
    const end = Math.min(currentPage * ROWS_PER_PAGE, totalCount);

    container.innerHTML = `
    <div class="pagination-inner">
        <span class="pagination-meta">Showing ${start}-${end} of ${totalCount}</span>
        <button class="btn-ghost btn-ghost--small ${currentPage === 1 ? 'is-disabled' : ''}"
            type="button"
            onclick="changePage(${currentPage - 1})"
            ${currentPage === 1 ? 'disabled' : ''}>Prev</button>
        <span class="pagination-current">${currentPage} / ${totalPages}</span>
        <button class="btn-ghost btn-ghost--small ${currentPage === totalPages ? 'is-disabled' : ''}"
            type="button"
            onclick="changePage(${currentPage + 1})"
            ${currentPage === totalPages ? 'disabled' : ''}>Next</button>
    </div>`;
}

function changePage(page) {
    const filtered = getFilteredFindings();
    const totalPages = Math.ceil(filtered.length / ROWS_PER_PAGE);

    if (page < 1 || page > totalPages) return;

    currentPage = page;
    renderFindings();
    document.getElementById('findings-section')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function openDrawer(findingId) {
    const data = findingsData.find((f) => f.finding_id === findingId);
    if (!data) return;

    setText('drawer-title', data.title);
    setText('drawer-pillar', data.pillar);
    setText('drawer-resource', data.resource_id);
    setText('drawer-effort', data.effort ? `${data.effort} effort` : '');
    setHTML('drawer-description', data.description);
    setHTML('drawer-remediation', data.remediation);

    const badge = document.getElementById('drawer-severity-badge');
    if (badge) {
        const severity = SEVERITY_CONFIG[data.severity] || SEVERITY_CONFIG.Low;
        badge.textContent = severity.label;
        badge.className = `badge badge-${(data.severity || 'Low').toLowerCase()}`;
    }

    document.body.classList.add('drawer-open', 'overflow-hidden');
    const overlay = document.getElementById('drawer-overlay');
    if (overlay) {
        overlay.style.opacity = '1';
        overlay.style.pointerEvents = 'auto';
    }
}

function closeDrawer() {
    document.body.classList.remove('drawer-open', 'overflow-hidden');

    const overlay = document.getElementById('drawer-overlay');
    if (overlay) {
        overlay.style.opacity = '0';
        overlay.style.pointerEvents = 'none';
    }
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
    updateThemeIcons(next);
}

function updateThemeIcons(theme) {
    const sunIcon = document.getElementById('sun-icon');
    const moonIcon = document.getElementById('moon-icon');

    if (!sunIcon || !moonIcon) return;

    if (theme === 'light') {
        sunIcon.classList.remove('hidden');
        moonIcon.classList.add('hidden');
        return;
    }

    sunIcon.classList.add('hidden');
    moonIcon.classList.remove('hidden');
}

function updateBadge(count) {
    const total = count !== undefined ? count : getFilteredFindings().length;

    const badge = document.getElementById('total-findings-badge');
    if (badge) badge.textContent = `${total} Items`;

    const showing = document.getElementById('showing-text');
    if (showing) showing.textContent = `Showing ${total} items total.`;
}

function scrollToPillar(pillarName) {
    document.getElementById('findings-section')?.scrollIntoView({ behavior: 'smooth' });

    const button = Array.from(document.querySelectorAll('.filter-pill'))
        .find((btn) => btn.dataset.pillar === pillarName);

    filterByPillar(pillarName, button || null);
}

function setExportStatus(message, isError = false) {
    const status = document.getElementById('export-status');
    if (!status) return;

    status.classList.remove('hidden', 'export-status--error');
    if (isError) status.classList.add('export-status--error');
    status.textContent = message;
}

function animateValue(id, start, end, duration, isCurrency = false) {
    const element = document.getElementById(id);
    if (!element) return;

    let startTimestamp = null;

    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;

        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        const value = progress * (end - start) + start;

        element.textContent = isCurrency
            ? `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
            : `${Math.floor(value)}`;

        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };

    window.requestAnimationFrame(step);
}

function truncate(text, maxLength) {
    if (!text) return '';
    return text.length > maxLength ? `${text.slice(0, maxLength)}...` : text;
}

function stripTags(html) {
    if (!html) return '';
    return String(html).replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
}

function setText(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = value || '';
}

function setHTML(id, value) {
    const element = document.getElementById(id);
    if (element) element.innerHTML = value || '';
}

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

window.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') closeDrawer();
});
