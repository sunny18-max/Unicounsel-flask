// Main application code
document.addEventListener('DOMContentLoaded', function() {
    // Constants
    const MAX_UNIVERSITIES = 2000; // Limit number of universities to load for better performance
    
    // Initialize the map with performance settings
    const map = L.map('map', {
        zoomControl: false,
        preferCanvas: true
    }).setView([20, 0], 2);
    
    // Add OpenStreetMap tiles with better performance
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 18,
        reuseTiles: true,
        updateWhenIdle: true
    }).addTo(map);
    
    // Add zoom control
    L.control.zoom({ position: 'topright' }).addTo(map);

    let markers = [];
    let selectedUniversity = null;
    const sidePanel = document.getElementById('sidePanel');
    const closePanelBtn = document.getElementById('closePanel');

    const defaultIcon = L.icon({
        iconUrl: 'https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon.png',
        iconSize: [25, 41],
        iconAnchor: [12, 41],
        popupAnchor: [1, -34],
        shadowUrl: 'https://unpkg.com/leaflet@1.7.1/dist/images/marker-shadow.png'
    });

    // Function to load universities with limit
    async function loadUniversities() {
        try {
            document.getElementById('info').textContent = 'Loading universities...';
            const response = await fetch('/api/universities');
            let universities = await response.json();
            
            // Limit the number of universities for better performance
            if (universities.length > MAX_UNIVERSITIES) {
                // Sort by name to ensure consistent results
                universities = universities
                    .sort((a, b) => a.name.localeCompare(b.name))
                    .slice(0, MAX_UNIVERSITIES);
                
                console.log(`Loaded ${universities.length} universities (limited to ${MAX_UNIVERSITIES} for performance)`);
                document.getElementById('info').textContent = 
                    `Showing ${universities.length} universities (limited to ${MAX_UNIVERSITIES} for performance).`;
            } else {
                document.getElementById('info').textContent = `Showing ${universities.length} universities.`;
            }
            
            currentUniversities = universities;
            updateMapMarkers(universities);
            updateFilters(universities);
        } catch (error) {
            console.error('Error loading universities:', error);
            document.getElementById('info').textContent = 'Error loading universities. Please try again.';
        }
    }

    // Update map markers
    function updateMapMarkers(universities) {
        // Clear existing markers
        markers.forEach(marker => map.removeLayer(marker));
        markers = [];

        if (universities.length === 0) {
            document.getElementById('info').textContent = 'No universities found. Try different filters.';
            document.getElementById('sidePanel').classList.remove('active');
            return;
        }

        // Add new markers
        universities.forEach(uni => {
            const marker = L.marker([uni.lat, uni.lng], {
                title: uni.name,
                alt: uni.name,
                riseOnHover: true
            }).addTo(map);
            
            marker.universityData = uni;
            
            marker.on('click', () => {
                showUniversityDetails(uni);
                highlightMarker(marker);
                
                // Pan to marker with offset for the side panel
                const offset = window.innerWidth > 768 ? [0, -200] : [0, 0];
                map.panTo([uni.lat, uni.lng], { 
                    animate: true,
                    duration: 0.5,
                    paddingTopLeft: [0, 0],
                    paddingBottomRight: [window.innerWidth > 768 ? 400 : 0, 0]
                });
            });
            
            // Add hover effect
            marker.on('mouseover', () => {
                marker.setZIndexOffset(1000);
            });
            
            markers.push(marker);
        });

        // Fit bounds to show all markers
        if (markers.length > 0) {
            const group = L.featureGroup(markers);
            const bounds = group.getBounds();
            
            // Only fit bounds if we have valid bounds
            if (bounds.isValid()) {
                map.fitBounds(bounds.pad(0.1));
            }
            
            // Show first university by default if panel is not already open
            if (markers.length > 0 && !document.querySelector('.side-panel.active')) {
                showUniversityDetails(markers[0].universityData);
                highlightMarker(markers[0]);
            }
        }
    }

    function openSidePanel() {
        if (sidePanel) {
            sidePanel.classList.add('active');
        }
    }

    function closeSidePanel(resetSelection = false) {
        if (sidePanel) {
            sidePanel.classList.remove('active');
        }
        if (resetSelection && selectedUniversity) {
            selectedUniversity.setIcon(defaultIcon);
            selectedUniversity = null;
        }
    }

    // Show university details in side panel
    function showUniversityDetails(university) {
        const detailsDiv = document.getElementById('universityDetails');
        detailsDiv.innerHTML = `
            <h3>${university.name}</h3>
            <div class="info-item">
                <strong>Country</strong>
                <p>${university.country || 'N/A'}</p>
            </div>
            <div class="info-item">
                <strong>Website</strong>
                <p>${university.web_pages && university.web_pages[0] ? 
                    `<a href="${university.web_pages[0].startsWith('http') ? '' : '//'}${university.web_pages[0]}" target="_blank" rel="noopener noreferrer">
                        ${university.web_pages[0]}
                    </a>` : 
                    'N/A'}
                </p>
            </div>
            <div class="info-item">
                <strong>Location</strong>
                <p>Latitude: ${university.lat.toFixed(4)}<br>Longitude: ${university.lng.toFixed(4)}</p>
            </div>
            ${university.domains && university.domains.length > 0 ? `
            <div class="info-item">
                <strong>Domains</strong>
                <p>${university.domains.join(', ')}</p>
            </div>` : ''}
            ${university['state-province'] ? `
            <div class="info-item">
                <strong>State/Province</strong>
                <p>${university['state-province']}</p>
            </div>` : ''}
        `;

        openSidePanel();
    }

    // Highlight selected marker
    function highlightMarker(selectedMarker) {
        markers.forEach(marker => {
            if (marker === selectedMarker) {
                marker.setIcon(L.icon({
                    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
                    iconSize: [25, 41],
                    iconAnchor: [12, 41],
                    popupAnchor: [1, -34],
                    shadowUrl: 'https://unpkg.com/leaflet@1.7.1/dist/images/marker-shadow.png'
                }));
                selectedUniversity = marker;
            } else {
                marker.setIcon(defaultIcon);
            }
        });
    }

    // Update filter dropdowns
    function updateFilters(universities) {
        const countrySelect = document.getElementById('countrySelect');
        const uniqueCountries = [...new Set(universities.map(u => u.country).filter(Boolean))].sort();
        
        // Clear and populate country dropdown
        countrySelect.innerHTML = '<option value="">All Countries</option>';
        uniqueCountries.forEach(country => {
            const option = document.createElement('option');
            option.value = country;
            option.textContent = country;
            countrySelect.appendChild(option);
        });

        // Update university dropdown when country changes
        countrySelect.addEventListener('change', updateUniversityDropdown);
        
        // Initial population of university dropdown
        updateUniversityDropdown();
    }

    // Update university dropdown based on selected country
    function updateUniversityDropdown() {
        const country = document.getElementById('countrySelect').value;
        const universitySelect = document.getElementById('universitySelect');
        
        // Clear existing options
        universitySelect.innerHTML = '<option value="">All Universities</option>';
        
        // Get universities for the selected country or all if no country selected
        const filtered = country ? 
            markers.map(m => m.universityData).filter(uni => uni.country === country) :
            markers.map(m => m.universityData);
        
        // Add universities to dropdown
        filtered.forEach(uni => {
            const option = document.createElement('option');
            option.value = uni.name;
            option.textContent = uni.name;
            universitySelect.appendChild(option);
        });
    }

    // Filter universities based on selections
    function filterUniversities() {
        const country = document.getElementById('countrySelect').value;
        const universityName = document.getElementById('universitySelect').value;
        
        // First, ensure all markers are visible and reset their style
        markers.forEach(marker => {
            marker.addTo(map);
            marker.setIcon(defaultIcon);
            marker.setOpacity(1);
            marker.setZIndexOffset(0);
        });
        
        // If a specific university is selected, highlight it and center the map
        if (universityName) {
            const marker = markers.find(m => m.universityData.name === universityName);
            if (marker) {
                const selectedUni = marker.universityData;
                showUniversityDetails(selectedUni);
                highlightMarker(marker);
                
                // Center the map on the selected marker
                map.setView([selectedUni.lat, selectedUni.lng], 12);
                
                // Dim other markers
                markers.forEach(m => {
                    if (m !== marker) {
                        m.setOpacity(0.5);
                        m.setZIndexOffset(-1000);
                    }
                });
            }
        } 
        // If only country is selected, show all universities in that country
        else if (country) {
            markers.forEach(marker => {
                if (marker.universityData.country !== country) {
                    map.removeLayer(marker);
                } else {
                    marker.addTo(map);
                    marker.setOpacity(1);
                    marker.setZIndexOffset(0);
                }
            });
            
            // Fit bounds to show all filtered markers
            const filteredMarkers = markers.filter(m => m.universityData.country === country);
            if (filteredMarkers.length > 0) {
                const group = L.featureGroup(filteredMarkers);
                const bounds = group.getBounds();
                if (bounds.isValid()) {
                    map.fitBounds(bounds.pad(0.1));
                }
            }
        }
        // If no filters, show all markers
        else {
            const group = L.featureGroup(markers);
            const bounds = group.getBounds();
            if (bounds.isValid()) {
                map.fitBounds(bounds.pad(0.1));
            }
        }
    }

    // Reset button functionality (unified)
    document.getElementById('resetBtn').addEventListener('click', () => {
        // Reset dropdowns
        document.getElementById('countrySelect').value = '';
        document.getElementById('universitySelect').value = '';
        updateUniversityDropdown();
        filterUniversities();

        // Close side panel and clear selection
        closeSidePanel(true);

        // Reset map view to show all markers
        if (markers.length > 0) {
            const group = L.featureGroup(markers);
            const bounds = group.getBounds();
            if (bounds.isValid()) {
                map.fitBounds(bounds.pad(0.1));
            }
        } else {
            map.setView([20, 0], 2);
        }
    });

    // Handle map zoom events to update visible markers
    let updateTimeout;
    map.on('moveend', function() {
        clearTimeout(updateTimeout);
        updateTimeout = setTimeout(() => {
            if (markers.length > 0) {
                const bounds = map.getBounds();
                markers.forEach(marker => {
                    const markerPos = marker.getLatLng();
                    if (bounds.contains(markerPos)) {
                        marker.addTo(map);
                    } else {
                        map.removeLayer(marker);
                    }
                });
            }
        }, 100);
    });

    // Close panel when clicking outside
    document.addEventListener('click', (e) => {
        const isClickInside = sidePanel && sidePanel.contains(e.target);
        const isMarkerClick = e.target.closest('.leaflet-marker-icon');
        
        if (!isClickInside && !isMarkerClick && sidePanel && sidePanel.classList.contains('active')) {
            closeSidePanel(false);
        }
    });

    // Prevent panel from closing when clicking inside it
    if (sidePanel) {
        sidePanel.addEventListener('click', (e) => {
            e.stopPropagation();
        });
    }

    // Event listeners
    document.getElementById('countrySelect').addEventListener('change', () => {
        updateUniversityDropdown();
        filterUniversities();
    });

    document.getElementById('universitySelect').addEventListener('change', () => {
        filterUniversities();        
        // If a university is selected, show its details
        const selectedUni = document.getElementById('universitySelect').value;
        if (selectedUni) {
            const marker = markers.find(m => m.universityData.name === selectedUni);
            if (marker) {
                showUniversityDetails(marker.universityData);
                map.setView([marker.universityData.lat, marker.universityData.lng], 12);
                highlightMarker(marker);
            }
        }
    });

    // Dedicated close button behaviour
    if (closePanelBtn) {
        closePanelBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            closeSidePanel(true);
        });
    }

    // Close panel when clicking on the map (for mobile)
    map.on('click', () => {
        if (window.innerWidth <= 992) {
            closeSidePanel(false);
        }
    });

    // Initial load
    loadUniversities();
});
