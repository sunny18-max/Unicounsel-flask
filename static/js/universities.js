document.addEventListener('DOMContentLoaded', async function() {
    const container = document.getElementById('universityCards');
    const detailOverlay = document.getElementById('uniDetailOverlay');
    const detailContent = document.getElementById('uniDetailContent');
    const detailCloseBtn = document.getElementById('uniDetailCloseBtn');
    if (!container) return;

    const MAX_UNIVERSITIES = 100;

    function storageKeyForUni(uni) {
        return `counseling_${uni.name}`;
    }

    function loadCounselingState(uni) {
        try {
            const raw = localStorage.getItem(storageKeyForUni(uni));
            if (!raw) {
                return {
                    status: 'not_started',
                    checklist: {},
                    notes: '',
                    deadline: ''
                };
            }
            const parsed = JSON.parse(raw);
            return {
                status: parsed.status || 'not_started',
                checklist: parsed.checklist || {},
                notes: parsed.notes || '',
                deadline: parsed.deadline || ''
            };
        } catch (e) {
            console.error('Error reading counseling state', e);
            return {
                status: 'not_started',
                checklist: {},
                notes: '',
                deadline: ''
            };
        }
    }

    function saveCounselingState(uni, state) {
        try {
            localStorage.setItem(storageKeyForUni(uni), JSON.stringify(state));
        } catch (e) {
            console.error('Error saving counseling state', e);
        }
    }

    function getDefaultChecklistItems() {
        return [
            'Updated CV / Resume',
            'Academic transcripts / mark sheets',
            'Degree / provisional certificate',
            'Statement of Purpose (SOP)',
            'Letters of Recommendation (LORs)',
            'English proficiency (IELTS/TOEFL/PTE)',
            'Standardized tests (GRE/GMAT/SAT, if needed)',
            'Passport copy',
            'Financial proofs / bank statements'
        ];
    }

    function formatDeadlineInfo(deadline) {
        if (!deadline) return '';
        const today = new Date();
        const target = new Date(deadline + 'T00:00:00');
        const diffMs = target.getTime() - today.getTime();
        const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));
        if (isNaN(diffDays)) return '';
        if (diffDays > 0) {
            return `${diffDays} day${diffDays === 1 ? '' : 's'} left`;
        } else if (diffDays === 0) {
            return 'Deadline is today';
        } else {
            return `Deadline passed (${Math.abs(diffDays)} day${diffDays === -1 ? '' : 's'} ago)`;
        }
    }

    function getStatusLabel(status) {
        if (status === 'shortlisted') return 'Shortlisted';
        if (status === 'applied') return 'Applied';
        if (status === 'offer') return 'Offer received';
        if (status === 'rejected') return 'Rejected';
        return 'Not started';
    }

    async function openDetail(uni) {
        if (!detailOverlay || !detailContent) return;

        const baseCountry = uni.country || 'N/A';
        const baseStream = uni.stream || '';
        const baseWebsite = (uni.web_pages && uni.web_pages[0]) ? uni.web_pages[0] : '';
        const brochureUrl = uni.brochure_url || '';
        const infoUrl = uni.info_url || '';
        const fees = uni.fees || '';
        const imageUrl = uni.image_url || '';
        const counselingInfo = uni.counseling_info || '';

        const counselingState = loadCounselingState(uni);

        const safeWebsite = baseWebsite && (baseWebsite.startsWith('http') ? baseWebsite : 'https://' + baseWebsite);

        detailContent.innerHTML = `
            <div class="uni-detail-header">
                <h2>${uni.name}</h2>
                <p class="uni-detail-sub">${baseCountry}${baseStream ? ' · ' + baseStream : ''}</p>
            </div>
            <div class="uni-detail-loading">Loading details from Wikipedia...</div>
        `;
        detailOverlay.style.display = 'flex';
        document.body.style.overflow = 'hidden';

        let wikipediaSummary = '';
        let wikipediaImage = '';

        try {
            const params = new URLSearchParams({ name: uni.name });
            const resp = await fetch(`/api/university_detail?${params.toString()}`);
            if (resp.ok) {
                const data = await resp.json();
                wikipediaSummary = data.wikipedia_summary || '';
                wikipediaImage = data.wikipedia_image || '';
            }
        } catch (e) {
            console.error('Error fetching university detail:', e);
        }

        const finalImage = wikipediaImage || imageUrl;

        const checklistItems = getDefaultChecklistItems();
        const deadlineInfo = formatDeadlineInfo(counselingState.deadline);

        detailContent.innerHTML = `
            <div class="uni-detail-header">
                <h2>${uni.name}</h2>
                <p class="uni-detail-sub">${baseCountry}${baseStream ? ' · ' + baseStream : ''}</p>
            </div>
            ${finalImage ? `<div class="uni-detail-image"><img src="${finalImage}" alt="${uni.name}"></div>` : ''}
            <div class="uni-detail-body">
                ${uni.address ? `<p><strong>Address:</strong> ${uni.address}</p>` : ''}
                ${fees ? `<p><strong>Fees / Tuition:</strong> ${fees}</p>` : ''}
                ${wikipediaSummary ? `<p class="uni-detail-wiki"><strong>About this university (from Wikipedia):</strong><br>${wikipediaSummary}</p>` : ''}
                ${counselingInfo ? `<div class="uni-detail-docs"><strong>Documents required to apply:</strong><br>${counselingInfo}</div>` : ''}
                <div class="uni-detail-counseling">
                    <h3>Counseling tracker</h3>
                    <div class="uni-detail-status-row">
                        <label for="counsel-status">Status:</label>
                        <select id="counsel-status">
                            <option value="not_started" ${counselingState.status === 'not_started' ? 'selected' : ''}>Not started</option>
                            <option value="shortlisted" ${counselingState.status === 'shortlisted' ? 'selected' : ''}>Shortlisted</option>
                            <option value="applied" ${counselingState.status === 'applied' ? 'selected' : ''}>Applied</option>
                            <option value="offer" ${counselingState.status === 'offer' ? 'selected' : ''}>Offer received</option>
                            <option value="rejected" ${counselingState.status === 'rejected' ? 'selected' : ''}>Rejected</option>
                        </select>
                    </div>
                    <div class="uni-detail-deadline-row">
                        <label for="counsel-deadline">Application deadline:</label>
                        <input type="date" id="counsel-deadline" value="${counselingState.deadline || ''}">
                        <span class="uni-detail-deadline-info">${deadlineInfo}</span>
                    </div>
                    <div class="uni-detail-checklist">
                        <p><strong>Application checklist:</strong></p>
                        <ul>
                            ${checklistItems.map(item => {
                                const checked = counselingState.checklist[item] ? 'checked' : '';
                                const safeId = 'chk_' + btoa(item).replace(/=/g, '');
                                return `<li><label><input type="checkbox" data-item="${item}" id="${safeId}" ${checked}> ${item}</label></li>`;
                            }).join('')}
                        </ul>
                    </div>
                    <div class="uni-detail-notes">
                        <label for="counsel-notes"><strong>Counseling notes / next steps:</strong></label>
                        <textarea id="counsel-notes" rows="4" placeholder="Add call notes, scholarship info, next steps, etc.">${counselingState.notes || ''}</textarea>
                    </div>
                    <div class="uni-detail-explore-row">
                        <button type="button" id="explore-campus-btn" class="btn" style="${counselingState.status === 'offer' ? '' : 'display:none;'}">
                            <i class="fas fa-location-dot"></i> Explore around campus
                        </button>
                    </div>
                </div>
            </div>
            <div class="uni-detail-actions">
                ${safeWebsite ? `<a href="${safeWebsite}" target="_blank" rel="noopener noreferrer" class="primary"><i class="fas fa-globe"></i> Official website</a>` : ''}
                ${brochureUrl ? `<a href="${brochureUrl}" target="_blank" rel="noopener noreferrer"><i class="fas fa-file-pdf"></i> Brochures / Prospectus</a>` : ''}
                ${infoUrl ? `<a href="${infoUrl}" target="_blank" rel="noopener noreferrer"><i class="fas fa-circle-info"></i> Info / Wikipedia page</a>` : ''}
            </div>
        `;

        const statusSelect = detailContent.querySelector('#counsel-status');
        const deadlineInput = detailContent.querySelector('#counsel-deadline');
        const deadlineInfoEl = detailContent.querySelector('.uni-detail-deadline-info');
        const notesEl = detailContent.querySelector('#counsel-notes');
        const checklistInputs = Array.from(detailContent.querySelectorAll('.uni-detail-checklist input[type="checkbox"]'));
        const exploreBtn = detailContent.querySelector('#explore-campus-btn');

        if (statusSelect) {
            statusSelect.addEventListener('change', () => {
                const state = loadCounselingState(uni);
                state.status = statusSelect.value;
                saveCounselingState(uni, state);
                if (exploreBtn) {
                    if (state.status === 'offer') {
                        exploreBtn.style.display = '';
                    } else {
                        exploreBtn.style.display = 'none';
                    }
                }
            });
        }

        if (deadlineInput) {
            deadlineInput.addEventListener('change', () => {
                const state = loadCounselingState(uni);
                state.deadline = deadlineInput.value;
                saveCounselingState(uni, state);
                if (deadlineInfoEl) {
                    deadlineInfoEl.textContent = formatDeadlineInfo(deadlineInput.value);
                }
            });
        }

        if (notesEl) {
            notesEl.addEventListener('input', () => {
                const state = loadCounselingState(uni);
                state.notes = notesEl.value;
                saveCounselingState(uni, state);
            });
        }

        checklistInputs.forEach(input => {
            input.addEventListener('change', () => {
                const item = input.getAttribute('data-item');
                const state = loadCounselingState(uni);
                state.checklist = state.checklist || {};
                state.checklist[item] = input.checked;
                saveCounselingState(uni, state);
            });
        });

        if (exploreBtn) {
            exploreBtn.addEventListener('click', () => {
                const params = new URLSearchParams({ name: uni.name });
                const url = `/explore?${params.toString()}`;
                window.open(url, '_blank', 'noopener');
            });
        }
    }

    function closeDetail() {
        if (!detailOverlay) return;
        detailOverlay.style.display = 'none';
        document.body.style.overflow = '';
    }

    if (detailCloseBtn && detailOverlay) {
        detailCloseBtn.addEventListener('click', closeDetail);
        detailOverlay.addEventListener('click', (e) => {
            if (e.target === detailOverlay) {
                closeDetail();
            }
        });
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') closeDetail();
        });
    }

    async function loadUniversities() {
        try {
            container.innerHTML = '<p class="uni-card-empty">Loading universities...</p>';
            const response = await fetch('/api/universities');
            let universities = await response.json();

            if (!universities || universities.length === 0) {
                container.innerHTML = '<p class="uni-card-empty">No universities available for this stream yet.</p>';
                return;
            }

            universities = universities
                .sort((a, b) => a.name.localeCompare(b.name))
                .slice(0, MAX_UNIVERSITIES);

            container.innerHTML = '';
            universities.forEach(uni => {
                const card = document.createElement('article');
                card.className = 'uni-card';

                const country = uni.country || 'N/A';
                const stream = uni.stream || '';
                const website = (uni.web_pages && uni.web_pages[0]) ? uni.web_pages[0] : '';
                const brochureUrl = uni.brochure_url || '';
                const infoUrl = uni.info_url || '';
                const fees = uni.fees || '';
                const imageUrl = uni.image_url || '';
                const counselingInfo = uni.counseling_info || '';

                const counselingState = loadCounselingState(uni);
                const statusLabel = getStatusLabel(counselingState.status);

                const safeWebsite = website && (website.startsWith('http') ? website : 'https://' + website);

                card.innerHTML = `
                    <div class="uni-card-header">
                        <div class="uni-card-title">${uni.name}</div>
                        <span class="uni-card-tag">${country}</span>
                    </div>
                    ${imageUrl ? `<div class="uni-card-image"><img src="${imageUrl}" alt="${uni.name}"></div>` : ''}
                    <div class="uni-card-meta">
                        ${stream ? `Stream: ${stream}` : ''}
                        ${fees ? `<br>Fees: ${fees}` : ''}
                        ${counselingInfo ? `<br><span class="uni-card-note">${counselingInfo}</span>` : ''}
                        <br><span class="uni-card-status">Status: ${statusLabel}</span>
                    </div>
                    <div class="uni-card-actions">
                        ${safeWebsite ? `<a href="${safeWebsite}" target="_blank" rel="noopener noreferrer" class="primary"><i class="fas fa-globe"></i> Website</a>` : ''}
                        ${brochureUrl ? `<a href="${brochureUrl}" target="_blank" rel="noopener noreferrer"><i class="fas fa-file-pdf"></i> Brochures</a>` : ''}
                        ${infoUrl ? `<a href="${infoUrl}" target="_blank" rel="noopener noreferrer"><i class="fas fa-circle-info"></i> More info</a>` : ''}
                    </div>
                `;
                card.addEventListener('click', (evt) => {
                    // avoid double-opening when clicking on action links
                    const target = evt.target;
                    if (target.tagName === 'A' || target.closest('a')) {
                        return;
                    }
                    openDetail(uni);
                });

                container.appendChild(card);
            });
        } catch (error) {
            console.error('Error loading universities:', error);
            container.innerHTML = '<p class="uni-card-empty">Error loading universities. Please try again.</p>';
        }
    }

    loadUniversities();
});
