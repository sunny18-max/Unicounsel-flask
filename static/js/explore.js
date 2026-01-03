document.addEventListener('DOMContentLoaded', function() {
    const root = document.getElementById('exploreRoot');
    if (!root) return;

    const name = root.getAttribute('data-name');
    const lat = parseFloat(root.getAttribute('data-lat'));
    const lng = parseFloat(root.getAttribute('data-lng'));

    const map = L.map('exploreMap', {
        zoomControl: false,
        preferCanvas: true
    }).setView([lat, lng], 14);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19,
    }).addTo(map);

    L.control.zoom({ position: 'topright' }).addTo(map);

    // Marker for the university itself
    const campusMarker = L.marker([lat, lng], {
        title: name,
        alt: name,
        riseOnHover: true
    }).addTo(map);
    campusMarker.bindPopup(`<strong>${name}</strong><br>Campus location`).openPopup();

    const sidePanel = document.getElementById('exploreSidePanel');
    const detailsEl = document.getElementById('exploreDetails');
    const closePanelBtn = document.getElementById('exploreClosePanel');
    const infoEl = document.getElementById('exploreInfo');

    const radiusSelect = document.getElementById('radiusSelect');
    const categoryCheckboxes = Array.from(root.querySelectorAll('input[type="checkbox"][data-category]'));

    let placeMarkers = [];

    function clearPlaceMarkers() {
        placeMarkers.forEach(m => map.removeLayer(m));
        placeMarkers = [];
    }

    function categoryEnabled(category) {
        const cb = categoryCheckboxes.find(c => c.getAttribute('data-category') === category);
        return !cb || cb.checked;
    }

    function iconForCategory(category) {
        const base = 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/';
        if (category === 'food') return base + 'marker-icon-2x-orange.png';
        if (category === 'essentials') return base + 'marker-icon-2x-blue.png';
        if (category === 'jobs') return base + 'marker-icon-2x-green.png';
        if (category === 'transport') return base + 'marker-icon-2x-violet.png';
        return base + 'marker-icon-2x-grey.png';
    }

    async function loadNearby() {
        clearPlaceMarkers();
        if (infoEl) infoEl.textContent = 'Loading nearby places...';

        const radius = parseInt(radiusSelect.value || '1500', 10);
        const url = `/api/nearby?lat=${encodeURIComponent(lat)}&lng=${encodeURIComponent(lng)}&radius=${radius}`;

        try {
            const resp = await fetch(url);
            if (!resp.ok) {
                throw new Error('Failed to load nearby places');
            }
            const places = await resp.json();
            if (!places || places.length === 0) {
                if (infoEl) infoEl.textContent = 'No nearby places found in this radius. Try increasing the radius.';
                return;
            }

            places.forEach(p => {
                if (!categoryEnabled(p.category)) return;
                const marker = L.marker([p.lat, p.lng], {
                    title: p.name || p.category,
                    alt: p.name || p.category,
                    icon: L.icon({
                        iconUrl: iconForCategory(p.category),
                        iconSize: [25, 41],
                        iconAnchor: [12, 41],
                        popupAnchor: [1, -34],
                        shadowUrl: 'https://unpkg.com/leaflet@1.7.1/dist/images/marker-shadow.png'
                    })
                }).addTo(map);

                marker.on('click', () => {
                    showPlaceDetails(p);
                });

                placeMarkers.push(marker);
            });

            if (infoEl) infoEl.textContent = `Showing ${placeMarkers.length} nearby places.`;
        } catch (e) {
            console.error(e);
            if (infoEl) infoEl.textContent = 'Error loading nearby places. Please try again.';
        }
    }

    function showPlaceDetails(place) {
        if (!detailsEl) return;
        detailsEl.innerHTML = `
            <h3>${place.name || 'Nearby place'}</h3>
            <div class="info-item">
                <strong>Category</strong>
                <p>${place.category_label || place.category}</p>
            </div>
            ${place.tags && place.tags['addr:street'] ? `
            <div class="info-item">
                <strong>Address</strong>
                <p>${place.tags['addr:street'] || ''} ${place.tags['addr:housenumber'] || ''}</p>
            </div>` : ''}
            ${place.tags && place.tags.website ? `
            <div class="info-item">
                <strong>Website</strong>
                <p><a href="${place.tags.website}" target="_blank" rel="noopener noreferrer">${place.tags.website}</a></p>
            </div>` : ''}
        `;
        sidePanel.classList.add('active');
    }

    if (closePanelBtn) {
        closePanelBtn.addEventListener('click', () => {
            sidePanel.classList.remove('active');
        });
    }

    radiusSelect.addEventListener('change', loadNearby);
    categoryCheckboxes.forEach(cb => cb.addEventListener('change', loadNearby));

    loadNearby();
});
